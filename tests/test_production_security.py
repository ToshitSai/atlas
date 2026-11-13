"""Atlas AI — Production Security Audit Test Suite."""

import io
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.rag_service import safe_filename, extract_document_text
from backend.live_search import is_safe_url

client = TestClient(app)


def test_anonymous_session_cookie():
    res = client.get("/api/health")
    assert res.status_code == 200
    cookies = res.cookies
    assert "atlas_sid" in cookies
    # The cookie is an opaque signed token, not a client-usable raw owner id.
    sid = cookies["atlas_sid"]
    assert len(sid) > 32
    assert sid.count(".") == 1
    assert all(c.isalnum() or c in "-_." for c in sid)


def test_tampered_session_cookie_is_rotated():
    user = TestClient(app)
    original = user.get("/api/health").cookies["atlas_sid"]
    tampered = original[:-1] + ("A" if original[-1] != "A" else "B")
    forged = TestClient(app, cookies={"atlas_sid": tampered})
    response = forged.get("/api/health")
    assert response.status_code == 200
    assert response.cookies.get("atlas_sid") != tampered


def test_path_traversal_sanitization():
    unsafe_names = [
        "../../etc/passwd",
        "..\\..\\Windows\\System32\\cmd.exe",
        "/var/log/secrets.txt",
        "....//....//config.json",
        "nested/sub/dir/myfile.pdf"
    ]
    for name in unsafe_names:
        clean = safe_filename(name)
        assert "/" not in clean
        assert "\\" not in clean
        assert ".." not in clean


def test_cross_session_document_isolation():
    # User 1 uploads document
    client1 = TestClient(app)
    res1 = client1.post(
        "/api/files",
        files={"file": ("secret_notes.txt", io.BytesIO(b"Confidential user 1 notes"), "text/plain")}
    )
    assert res1.status_code == 200
    doc1 = res1.json()
    doc_id = doc1["id"]

    # User 2 lists documents -> should be empty
    client2 = TestClient(app)
    res2 = client2.get("/api/documents")
    assert res2.status_code == 200
    docs2 = res2.json()["documents"]
    assert all(d["id"] != doc_id for d in docs2)

    # User 2 attempts to delete User 1's document -> forbidden / not found
    del_res = client2.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 403

    # Document still exists for User 1
    docs1 = client1.get("/api/documents").json()["documents"]
    assert any(d["id"] == doc_id for d in docs1)

    # Cleanup by User 1
    client1.delete(f"/api/documents/{doc_id}")


def test_ssrf_internal_network_rejections():
    # Loopbacks
    assert is_safe_url("http://127.0.0.1:8000/api") is False
    assert is_safe_url("http://localhost:3000/") is False
    assert is_safe_url("http://0.0.0.0:8000/") is False

    # Cloud metadata
    assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_url("http://metadata.google.internal/") is False

    # Private LAN
    assert is_safe_url("http://192.168.1.1/admin") is False
    assert is_safe_url("http://10.0.0.1/") is False
    assert is_safe_url("http://172.16.0.1/") is False

    # Dangerous schemes
    assert is_safe_url("file:///etc/shadow") is False
    assert is_safe_url("ftp://127.0.0.1/") is False


def test_oversized_document_rejection():
    # 51 MB dummy bytes
    oversized = b"a" * (51 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds maximum allowed size"):
        extract_document_text("large.txt", oversized)
