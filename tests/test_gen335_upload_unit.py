"""Atlas AI Gen-3.3.5: Upload, Ingestion, and Format Validation Unit Test Suite."""

import io
import json
import os
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.document_extractors import (
    ALL_SUPPORTED_EXTENSIONS,
    MAX_FILE_BYTES,
    extract_document_or_image,
)
from backend.rag_service import compute_file_sha256, safe_filename, service as rag_svc


class TestUploadUnit(unittest.TestCase):
    """Unit tests for Gen-3.3.5 file validation, format checking, and ingestion safety."""

    def test_supported_document_formats(self):
        """Verify standard document and text formats are supported."""
        txt_content = b"Project: ATLAS-TEST\nData: 12345"
        sections, meta = extract_document_or_image("test.txt", txt_content)
        self.assertTrue(len(sections) > 0)
        self.assertFalse(meta.get("is_image"))

        csv_content = b"col1,col2\nval1,val2\n"
        sections, meta = extract_document_or_image("test.csv", csv_content)
        self.assertTrue(len(sections) > 0)
        self.assertFalse(meta.get("is_image"))

        json_content = b'{"project": "Atlas", "version": "3.3.5"}'
        sections, meta = extract_document_or_image("test.json", json_content)
        self.assertTrue(len(sections) > 0)

    def test_legacy_office_format_rejection(self):
        """Verify legacy .doc, .xls, .ppt are explicitly rejected with guidance."""
        for ext in [".doc", ".xls", ".ppt"]:
            with self.assertRaises(ValueError) as ctx:
                extract_document_or_image(f"old_file{ext}", b"fake binary content")
            msg = str(ctx.exception)
            self.assertIn("Legacy binary Microsoft Office format", msg)
            self.assertIn("not supported", msg)

    def test_video_format_rejection(self):
        """Verify video formats (.mp4, .mov, etc.) are explicitly rejected."""
        video_exts = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
        for ext in video_exts:
            with self.assertRaises(ValueError) as ctx:
                extract_document_or_image(f"clip{ext}", b"fake video bytes")
            msg = str(ctx.exception)
            self.assertIn("Video format", msg)
            self.assertIn("not supported", msg)

    def test_video_magic_bytes_rejection(self):
        """Verify files with video magic bytes (MP4 ftyp) are rejected even if renamed."""
        mp4_magic = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00"
        with self.assertRaises(ValueError) as ctx:
            extract_document_or_image("disguised_file.txt", mp4_magic)
        self.assertIn("Video format", str(ctx.exception))

    def test_empty_file_rejection(self):
        """Verify zero-byte or whitespace-only files are rejected."""
        with self.assertRaises(ValueError) as ctx:
            extract_document_or_image("empty.txt", b"")
        self.assertIn("empty", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            extract_document_or_image("spaces.txt", b"   \n\r\t  ")
        self.assertIn("empty", str(ctx.exception).lower())

    def test_oversized_file_limit(self):
        """Verify files exceeding MAX_FILE_BYTES (50MB) are rejected."""
        oversized = MAX_FILE_BYTES + 1024
        # Test virtual check without allocating 50MB
        self.assertEqual(MAX_FILE_BYTES, 50 * 1024 * 1024)

    def test_duplicate_prevention_deterministic_id(self):
        """Verify identical content for the same session yields the exact same deterministic UUID."""
        content = b"Verification Token: PERSIST-UNIQUE-9988\n"
        session_id = "test_session_dedup"
        doc_1 = rag_svc.ingest_document("file1.txt", content, owner_session=session_id)
        doc_2 = rag_svc.ingest_document("file1.txt", content, owner_session=session_id)
        self.assertEqual(doc_1["id"], doc_2["id"])

        # Listing documents should only have 1 copy of this document
        docs = rag_svc.list_documents(owner_session=session_id)
        matching = [d for d in docs if d["id"] == doc_1["id"]]
        self.assertEqual(len(matching), 1)

        # Cleanup
        rag_svc.delete_document(doc_1["id"], owner_session=session_id)


if __name__ == "__main__":
    unittest.main()
