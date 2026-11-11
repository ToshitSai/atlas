"""Atlas AI — Embedding Consistency & Registry Test Suite."""

import pytest

from backend import embedding_registry
from backend.embedding_registry import (
    EmbeddingProfile,
    EmbeddingProviderUnavailableError,
    IncompatibleEmbeddingError,
    PROFILE_LOCAL_MINILM_384,
    PROFILE_OPENAI_SMALL_1536,
)


def test_embedding_profile_attributes():
    prof = PROFILE_LOCAL_MINILM_384
    assert prof.provider == "sentence-transformers"
    assert prof.model_id == "all-MiniLM-L6-v2"
    assert prof.dimensions == 384
    assert prof.normalized is True
    assert prof.index_version == "v1"

    data = prof.to_dict()
    assert data["dimensions"] == 384
    assert data["model_id"] == "all-MiniLM-L6-v2"


def test_incompatible_embedding_rejection():
    registry = embedding_registry.EmbeddingRegistry()

    # Empty vector
    with pytest.raises(IncompatibleEmbeddingError, match="non-empty list of floats"):
        registry.validate_vector_compatibility([], PROFILE_LOCAL_MINILM_384)

    # 1536-dim vector passed to 384-dim profile
    wrong_dim_vector = [0.1] * 1536
    with pytest.raises(IncompatibleEmbeddingError, match="Dimension mismatch"):
        registry.validate_vector_compatibility(wrong_dim_vector, PROFILE_LOCAL_MINILM_384)

    # 384-dim vector passed to 1536-dim profile
    small_dim_vector = [0.1] * 384
    with pytest.raises(IncompatibleEmbeddingError, match="Dimension mismatch"):
        registry.validate_vector_compatibility(small_dim_vector, PROFILE_OPENAI_SMALL_1536)


def test_openai_missing_key_explicit_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    registry = embedding_registry.EmbeddingRegistry()

    with pytest.raises(EmbeddingProviderUnavailableError, match="OpenAI API key .* is missing"):
        registry.generate_embeddings(["test text"], profile=PROFILE_OPENAI_SMALL_1536)


def test_no_silent_random_or_hash_fallback(monkeypatch):
    """Verify that when a provider cannot run, it raises EmbeddingProviderUnavailableError instead of injecting hash vectors."""
    registry = embedding_registry.EmbeddingRegistry()

    dummy_profile = EmbeddingProfile(
        provider="non_existent_provider",
        model_id="dummy",
        revision="1",
        dimensions=128,
        normalized=True,
        index_version="v1"
    )

    with pytest.raises(EmbeddingProviderUnavailableError, match="Unknown embedding provider"):
        registry.generate_embeddings(["some text"], profile=dummy_profile)
