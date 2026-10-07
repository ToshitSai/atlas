"""Backend-only document ingestion and retrieval primitives for Atlas RAG.

All optional infrastructure failures are returned as explicit configuration
errors; secrets and document contents are never logged.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, List, Optional

MAX_FILE_BYTES = 20 * 1024 * 1024
ALLOWED = {".pdf", ".txt", ".md", ".json", ".csv", ".png", ".jpg", ".jpeg", ".webp"}


def safe_filename(name: str) -> str:
    name = os.path.basename((name or "").replace("\\", "/"))
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name[:180] or "document"


def validate_upload(name: str, content: bytes) -> str:
    ext = os.path.splitext(name.lower())[1]
    if ext not in ALLOWED:
        raise ValueError("Unsupported file type. Upload PDF, TXT, MD, JSON, CSV, PNG, JPG, or WebP.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("File exceeds the 20 MB limit.")
    magic = {
        ".pdf": content.startswith(b"%PDF-"),
        ".png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": content.startswith(b"\xff\xd8\xff"),
        ".jpeg": content.startswith(b"\xff\xd8\xff"),
        ".webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
    }
    if ext in magic and not magic[ext]:
        raise ValueError("The file content does not match its extension.")
    return ext


def extract_text(name: str, content: bytes) -> List[Dict[str, Any]]:
    ext = os.path.splitext(name.lower())[1]
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = []
            for number, page in enumerate(reader.pages, 1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append({"page": number, "text": text})
            if not pages:
                raise ValueError("This PDF has no text layer; OCR is unavailable on this deployment.")
            return pages
        except ValueError:
            raise
        except Exception as exc:
            if "password" in str(exc).lower() or "encrypt" in str(exc).lower():
                raise ValueError("This PDF is password protected.") from exc
            raise ValueError("The PDF is corrupted or could not be read.") from exc
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Image OCR is unavailable on this deployment; upload the text or PDF text layer.")
    text = content.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("The uploaded document contains no text.")
    return [{"page": None, "text": text}]


def chunk_pages(pages: List[Dict[str, Any]], size: int = 2400, overlap: int = 400) -> List[Dict[str, Any]]:
    chunks = []
    for page in pages:
        text = page["text"]
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            chunks.append({"page": page.get("page"), "text": text[start:end], "start": start, "end": end})
            if end == len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks


def blob_upload(name: str, content: bytes) -> str:
    token = os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Vercel Blob is not configured (BLOB_READ_WRITE_TOKEN is missing).")
    key = f"atlas/{hashlib.sha256(content).hexdigest()}-{safe_filename(name)}"
    req = urllib.request.Request(
        "https://blob.vercel-storage.com/" + urllib.parse.quote(key),
        data=content, method="PUT",
        headers={"Authorization": f"Bearer {token}", "x-content-type": "application/octet-stream"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.headers.get("x-vercel-blob-url") or key
    except Exception as exc:
        raise RuntimeError("Private file storage upload failed.") from exc


def embed_texts(texts: List[str]) -> tuple[str, List[List[float]]]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Embeddings are not configured (OPENAI_API_KEY is missing).")
    model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    payload = json.dumps({"model": model, "input": texts}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/embeddings", data=payload, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode())
        return model, [item["embedding"] for item in sorted(data.get("data", []), key=lambda item: item.get("index", 0))]
    except Exception as exc:
        raise RuntimeError("Embedding generation failed.") from exc


def vector_literal(values: List[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"
