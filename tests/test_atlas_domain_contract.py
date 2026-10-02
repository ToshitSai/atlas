from pathlib import Path

from backend.auth import _authorized_parties


def test_public_metadata_uses_atlas_canonical_url():
    html = Path("index.html").read_text(encoding="utf-8")
    assert 'https://atlas-scientist.vercel.app/atlas' in html
    assert 'property="og:url"' in html
    assert 'name="twitter:title"' in html


def test_default_clerk_parties_accept_new_and_legacy_origins(monkeypatch):
    monkeypatch.delenv("CLERK_AUTHORIZED_PARTIES", raising=False)
    parties = _authorized_parties()
    assert "https://atlas-scientist.vercel.app" in parties
    assert "https://automl-scientist.vercel.app" in parties
