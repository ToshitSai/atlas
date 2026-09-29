"""Academic provider normalisation and failure behaviour."""
from backend import literature_search as literature


def test_openalex_records_preserve_real_metadata(monkeypatch):
    monkeypatch.setattr(literature, "_http_json", lambda *args, **kwargs: {"results": [{
        "id": "https://openalex.org/W1", "title": "Fraud paper", "doi": "https://doi.org/10.1/example",
        "publication_year": 2024, "cited_by_count": 12,
        "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
        "abstract_inverted_index": {"Fraud": [0], "evidence": [1]},
        "primary_location": {"landing_page_url": "https://example.test/paper", "pdf_url": "https://example.test/paper.pdf", "source": {"display_name": "Test Journal"}},
    }]})
    paper = literature.OpenAlexProvider().search_papers("fraud", 1)[0]
    assert paper["title"] == "Fraud paper"
    assert paper["abstract"] == "Fraud evidence"
    assert paper["authors"] == "Ada Lovelace"
    assert paper["doi"] == "https://doi.org/10.1/example"
    assert paper["citationCount"] == 12


def test_semantic_failure_falls_back_to_real_openalex_records(monkeypatch):
    monkeypatch.setattr(literature.SemanticScholarProvider, "search_papers", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("rate limited")))
    monkeypatch.setattr(literature.OpenAlexProvider, "search_papers", lambda *args, **kwargs: [{
        "id": "W1", "title": "Real paper", "abstract": "Evidence", "doi": "", "source": "OpenAlex"
    }])
    papers = literature._search_literature("fraud detection", 2)
    assert papers == [{"id": "W1", "title": "Real paper", "abstract": "Evidence", "doi": "", "source": "OpenAlex"}]


def test_no_provider_result_never_creates_placeholder_papers(monkeypatch):
    monkeypatch.setattr(literature.SemanticScholarProvider, "search_papers", lambda *args, **kwargs: [])
    monkeypatch.setattr(literature.OpenAlexProvider, "search_papers", lambda *args, **kwargs: [])
    assert literature._search_literature("obscure topic") == []
