"""Server-side academic search providers for evidence-grounded research.

Providers return a single normalised paper shape. No provider invents an
abstract, paper, citation count, or DOI: missing upstream fields stay empty.
Semantic Scholar is preferred when configured; OpenAlex is the keyless,
production-safe academic fallback.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List

import backend.config

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_URL = "https://api.openalex.org/works"
_TIMEOUT = 10
_USER_AGENT = "AI-Scientist-Assistant/1.0 (academic research)"


class AcademicSearchProvider:
    """Small provider contract used by the deep-research pipeline."""
    name = "Academic"

    def search_papers(self, query: str, limit: int = 5, recent: bool = False) -> List[Dict[str, Any]]:
        raise NotImplementedError


def _http_json(url: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _normalise_title(value: str) -> str:
    return re.sub(r"\W+", "", (value or "").lower())


def _openalex_abstract(index: Dict[str, List[int]]) -> str:
    """Rebuild OpenAlex's inverted-index abstract only when actually supplied."""
    positions = [(position, word) for word, indexes in (index or {}).items()
                 for position in (indexes or []) if isinstance(position, int)]
    return " ".join(word for _, word in sorted(positions))


class SemanticScholarProvider(AcademicSearchProvider):
    name = "Semantic Scholar"

    def search_papers(self, query: str, limit: int = 5, recent: bool = False) -> List[Dict[str, Any]]:
        fields = "paperId,title,abstract,authors,year,venue,url,externalIds,citationCount,openAccessPdf"
        params = {"query": query, "limit": str(limit), "fields": fields}
        headers: Dict[str, str] = {}
        if key := os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
            headers["x-api-key"] = key
        data = _http_json(f"{SEMANTIC_SCHOLAR_URL}?{urllib.parse.urlencode(params)}", headers)
        papers = []
        for item in data.get("data", []):
            paper_id = item.get("paperId") or ""
            authors = [a.get("name", "").strip() for a in (item.get("authors") or []) if a.get("name")]
            external = item.get("externalIds") or {}
            doi = external.get("DOI") or ""
            papers.append({
                "id": paper_id, "paperId": paper_id, "title": item.get("title") or "",
                "abstract": item.get("abstract") or "", "authorsList": authors, "authors": ", ".join(authors),
                "year": item.get("year"), "venue": item.get("venue") or "",
                "url": item.get("url") or (f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""),
                "pdfUrl": ((item.get("openAccessPdf") or {}).get("url") or ""),
                "doi": doi, "citationCount": item.get("citationCount"), "source": self.name,
            })
        return papers


class OpenAlexProvider(AcademicSearchProvider):
    name = "OpenAlex"

    def search_papers(self, query: str, limit: int = 5, recent: bool = False) -> List[Dict[str, Any]]:
        params = {"search": query, "per-page": str(limit)}
        if recent:
            params["sort"] = "publication_date:desc"
        if key := os.environ.get("OPENALEX_API_KEY"):
            params["api_key"] = key
        data = _http_json(f"{OPENALEX_URL}?{urllib.parse.urlencode(params)}")
        papers = []
        for item in data.get("results", []):
            authors = [a.get("author", {}).get("display_name", "").strip()
                       for a in (item.get("authorships") or []) if a.get("author", {}).get("display_name")]
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            doi = item.get("doi") or ""
            papers.append({
                "id": item.get("id") or "", "paperId": item.get("id") or "",
                "title": item.get("title") or item.get("display_name") or "",
                "abstract": _openalex_abstract(item.get("abstract_inverted_index") or {}),
                "authorsList": authors, "authors": ", ".join(authors),
                "year": item.get("publication_year"), "venue": source.get("display_name") or location.get("raw_source_name") or "",
                "url": doi or location.get("landing_page_url") or item.get("id") or "",
                "pdfUrl": location.get("pdf_url") or "", "doi": doi,
                "citationCount": item.get("cited_by_count"), "source": self.name,
            })
        return papers


def _recent_requested(query: str) -> bool:
    return bool(re.search(r"\b(latest|recent|current|new)\b", query or "", re.I))


def _academic_query(query: str) -> str:
    """Remove conversational recency phrasing that hurts scholarly ranking."""
    cleaned = re.sub(r"\b(find|recent|latest|current|research|papers?|on|about)\b", " ", query, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or query


def _search_literature(objective: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve real academic records, deduplicated by DOI/id/title.

    A Semantic Scholar rate limit or outage falls through to OpenAlex; if both
    fail, an empty result truthfully communicates unavailable evidence.
    """
    query = _academic_query((objective or "").strip())
    if not query:
        return []
    results: List[Dict[str, Any]] = []
    for provider in (SemanticScholarProvider(), OpenAlexProvider()):
        try:
            results.extend(provider.search_papers(query, limit, _recent_requested(query)) or [])
        except Exception as exc:
            print(f"[ACADEMIC SEARCH WARNING] {provider.name}: {type(exc).__name__}: {exc}")
    unique, seen = [], set()
    for paper in results:
        identity = (paper.get("doi") or paper.get("id") or _normalise_title(paper.get("title") or "")).lower()
        if not identity or identity in seen or not paper.get("title"):
            continue
        seen.add(identity)
        unique.append(paper)
    return unique[:limit]


def search_literature(objective: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Public academic retrieval hook, retained for pipeline injection/tests."""
    return _search_literature(objective, limit)


# Backwards-compatible helpers retained for callers and tests.
def search_semantic_scholar(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    try:
        return SemanticScholarProvider().search_papers(query, limit, _recent_requested(query))
    except Exception as exc:
        print(f"[ACADEMIC SEARCH WARNING] Semantic Scholar: {type(exc).__name__}: {exc}")
        return []


def search_openalex(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    try:
        return OpenAlexProvider().search_papers(query, limit, _recent_requested(query))
    except Exception as exc:
        print(f"[ACADEMIC SEARCH WARNING] OpenAlex: {type(exc).__name__}: {exc}")
        return []
