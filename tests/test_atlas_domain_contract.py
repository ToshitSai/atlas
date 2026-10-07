from pathlib import Path


def test_public_metadata_uses_atlas_canonical_url():
    html = Path("index.html").read_text(encoding="utf-8")
    assert 'https://atlas-scientist.vercel.app/atlas' in html
    assert 'property="og:url"' in html
    assert 'name="twitter:title"' in html

