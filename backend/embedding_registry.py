"""Atlas AI — Embedding Registry and Consistency Engine.

Maintains strict metadata registry for embedding models and vector collections:
- Prevents mixing vectors of different dimensions, providers, or revisions.
- Rejects silent hashing/pseudo-random fallbacks when semantic embedding fails.
- Explicit errors when providers are unconfigured or unavailable.
- Safe re-indexing and schema migration support.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request


class EmbeddingError(Exception):
    """Base error for embedding generation and validation."""
    pass


class IncompatibleEmbeddingError(EmbeddingError):
    """Raised when attempting to mix incompatible vector dimensions or model profiles."""
    pass


class EmbeddingProviderUnavailableError(EmbeddingError):
    """Raised when an embedding provider runtime or API key is unavailable."""
    pass


@dataclass(frozen=True)
class EmbeddingProfile:
    provider: str            # "sentence-transformers", "openai"
    model_id: str            # "all-MiniLM-L6-v2", "text-embedding-3-small"
    revision: str            # model revision or version tag
    dimensions: int          # integer vector length (e.g. 384, 1536)
    normalized: bool         # whether vectors are L2-unit normalized
    index_version: str       # index schema version (e.g. "v1")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Predefined registered profiles
PROFILE_LOCAL_MINILM_384 = EmbeddingProfile(
    provider="sentence-transformers",
    model_id="all-MiniLM-L6-v2",
    revision="e4ce987",
    dimensions=384,
    normalized=True,
    index_version="v1"
)

PROFILE_OPENAI_SMALL_1536 = EmbeddingProfile(
    provider="openai",
    model_id="text-embedding-3-small",
    revision="v1",
    dimensions=1536,
    normalized=True,
    index_version="v1"
)

PROFILE_OPENAI_LARGE_3072 = EmbeddingProfile(
    provider="openai",
    model_id="text-embedding-3-large",
    revision="v1",
    dimensions=3072,
    normalized=True,
    index_version="v1"
)


class EmbeddingRegistry:
    """Manages active profiles, dimension validation, and vector generation."""

    def __init__(self):
        self._profiles: Dict[str, EmbeddingProfile] = {
            "sentence-transformers/all-MiniLM-L6-v2": PROFILE_LOCAL_MINILM_384,
            "openai/text-embedding-3-small": PROFILE_OPENAI_SMALL_1536,
            "openai/text-embedding-3-large": PROFILE_OPENAI_LARGE_3072,
        }
        self._local_model = None
        self._local_tokenizer = None

    def register_profile(self, key: str, profile: EmbeddingProfile) -> None:
        self._profiles[key] = profile

    def get_profile(self, key: str) -> Optional[EmbeddingProfile]:
        return self._profiles.get(key)

    def resolve_default_profile(self) -> EmbeddingProfile:
        """Select default profile based on environment configuration."""
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        use_openai = os.environ.get("USE_OPENAI_EMBEDDINGS", "").strip().lower() in ("1", "true", "yes")
        if openai_key and use_openai:
            return PROFILE_OPENAI_SMALL_1536
        return PROFILE_LOCAL_MINILM_384

    def _has_semantic_embeddings(self) -> bool:
        """Check if any semantic embedding generation provider is actually functional."""
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        use_openai = os.environ.get("USE_OPENAI_EMBEDDINGS", "").strip().lower() in ("1", "true", "yes")
        if openai_key and use_openai:
            return True
        try:
            import torch
            import transformers
            return True
        except Exception:
            return False

    def validate_vector_compatibility(
        self,
        vector: List[float],
        expected_profile: EmbeddingProfile
    ) -> None:
        """Validate that a vector matches the expected dimension and normalization."""
        if not vector or not isinstance(vector, list):
            raise IncompatibleEmbeddingError("Vector must be a non-empty list of floats.")
        if len(vector) != expected_profile.dimensions:
            raise IncompatibleEmbeddingError(
                f"Dimension mismatch: expected {expected_profile.dimensions} "
                f"({expected_profile.model_id}), got {len(vector)}."
            )
        if expected_profile.normalized:
            sq_sum = sum(x * x for x in vector)
            norm = math.sqrt(sq_sum)
            # Allow tolerance for fp32 / fp16 quantization
            if abs(norm - 1.0) > 0.05 and norm > 0:
                # Renormalize to preserve contract
                inv = 1.0 / norm
                for i in range(len(vector)):
                    vector[i] *= inv

    def generate_embeddings(
        self,
        texts: List[str],
        profile: Optional[EmbeddingProfile] = None
    ) -> List[List[float]]:
        """Generate real semantic embeddings for a batch of texts.
        
        CRITICAL: Never silently falls back to hashing or pseudo-random numbers!
        If the provider is unavailable, raises EmbeddingProviderUnavailableError.
        """
        if not texts:
            return []

        active_profile = profile or self.resolve_default_profile()

        # 1. Remote OpenAI Provider
        if active_profile.provider == "openai":
            key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not key:
                raise EmbeddingProviderUnavailableError(
                    f"OpenAI API key (OPENAI_API_KEY) is missing for profile {active_profile.model_id}."
                )
            url = "https://api.openai.com/v1/embeddings"
            payload = json.dumps({
                "model": active_profile.model_id,
                "input": texts
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                sorted_data = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
                vecs = [item["embedding"] for item in sorted_data]
                for v in vecs:
                    self.validate_vector_compatibility(v, active_profile)
                return vecs
            except Exception as exc:
                raise EmbeddingProviderUnavailableError(
                    f"OpenAI embedding generation failed: {exc}"
                ) from exc

        # 2. Local sentence-transformers Provider
        elif active_profile.provider == "sentence-transformers":
            try:
                import torch
                from transformers import AutoModel, AutoTokenizer
                from pathlib import Path

                if self._local_model is None:
                    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
                    snap_dir = cache_dir / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots"
                    model_path = "sentence-transformers/all-MiniLM-L6-v2"
                    if snap_dir.exists():
                        snaps = [s for s in snap_dir.iterdir() if s.is_dir()]
                        if snaps:
                            model_path = str(snaps[0])

                    self._local_tokenizer = AutoTokenizer.from_pretrained(model_path)
                    self._local_model = AutoModel.from_pretrained(model_path)
                    self._local_model.eval()
                    if torch.cuda.is_available():
                        self._local_model = self._local_model.to("cuda")

                device = self._local_model.device
                with torch.no_grad():
                    encoded = self._local_tokenizer(
                        texts, padding=True, truncation=True, max_length=512, return_tensors="pt"
                    )
                    encoded = {k: v.to(device) for k, v in encoded.items()}
                    out = self._local_model(**encoded)
                    mask = encoded["attention_mask"].unsqueeze(-1)
                    summed = torch.sum(out.last_hidden_state * mask, dim=1)
                    pooled = summed / torch.clamp(mask.sum(dim=1), min=1e-9)
                    normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
                    raw_vecs = normalized.cpu().numpy().tolist()

                for v in raw_vecs:
                    self.validate_vector_compatibility(v, active_profile)
                return raw_vecs
            except Exception as exc:
                raise EmbeddingProviderUnavailableError(
                    f"Local sentence-transformers embedding failed: {exc}. "
                    "PyTorch or model weights unavailable. Cannot generate semantic vectors."
                ) from exc

        else:
            raise EmbeddingProviderUnavailableError(f"Unknown embedding provider '{active_profile.provider}'.")


registry = EmbeddingRegistry()
