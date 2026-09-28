"""Validated, dependency-light parsing for user supplied files."""
from __future__ import annotations
import csv, io, json, os
from typing import Any, Dict

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".cpp", ".c", ".h", ".sql", ".html", ".css"}
_ALLOWED = _TEXT_EXTENSIONS | {".csv", ".json", ".pdf"}


def validate_filename(filename: str) -> str:
    raw = (filename or "").replace("\\", "/")
    name = os.path.basename(raw)
    ext = os.path.splitext(name)[1].lower()
    if not name or "/" in raw or raw in {".", ".."} or ext not in _ALLOWED:
        raise ValueError("Supported file types are PDF, TXT, CSV, JSON, and common code files.")
    return ext


def parse_file_bytes(filename: str, content: bytes) -> Dict[str, Any]:
    ext = validate_filename(filename)
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("PDF parsing is not configured on this server.") from exc
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(f"[Page {i + 1}]\n{page}" for i, page in enumerate(pages))
        return {"fileType": "pdf", "pageCount": len(pages), "text": text, "metadata": {}}
    text = content.decode("utf-8", errors="replace")
    if ext == ".csv":
        rows = list(csv.reader(io.StringIO(text)))
        header = rows[0] if rows else []
        return {"fileType": "csv", "text": text, "metadata": {"columns": header, "rowCount": max(0, len(rows) - 1)}}
    if ext == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc.msg}.") from exc
        shape = "object" if isinstance(value, dict) else "array" if isinstance(value, list) else type(value).__name__
        return {"fileType": "json", "text": text, "metadata": {"shape": shape}}
    return {"fileType": "text", "text": text, "metadata": {"extension": ext}}
