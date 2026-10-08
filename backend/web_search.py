"""Web search tool for current-information questions and deep research.

Multi-provider with graceful degradation:
  1. Tavily   (TAVILY_API_KEY)
  2. Serper   (SERPER_API_KEY — Google results)
  3. Brave    (BRAVE_API_KEY)
  4. Scrape.do (SCRAPE_DO_API_KEY; search-results HTML fallback)
  5. DuckDuckGo Instant Answers (keyless; limited but real)

Returns a normalised list of {title, url, snippet, source}. It never
fabricates: if every provider fails, ``search_web`` returns [] and callers
must say so honestly instead of inventing current facts.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List

import backend.config  # auto-loads .env into os.environ

_TIMEOUT = 10
_USER_AGENT = "AI-Scientist-Assistant/1.0 (web research tool)"


def clean_snippet(value: str, limit: int = 400) -> str:
    """Normalize provider text and cut only at a sentence or word boundary."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    candidate = text[:limit].rstrip()
    sentence_end = max(candidate.rfind(". "), candidate.rfind("! "), candidate.rfind("? "))
    if sentence_end >= max(80, limit // 2):
        return candidate[:sentence_end + 1].rstrip()
    word_end = candidate.rfind(" ")
    return (candidate[:word_end] if word_end > 0 else candidate).rstrip(" ,;:-") + "..."


def result_matches_query(query: str, result: Dict[str, str]) -> bool:
    """Reject obvious title/snippet mismatches before presenting a hit."""
    ignored = {"a", "an", "and", "for", "from", "give", "get", "in", "link", "me", "of", "on", "open", "please", "site", "the", "to", "url", "website", "with"}
    terms = [word for word in re.findall(r"[a-z0-9]{3,}", (query or "").lower()) if word not in ignored]
    if not terms:
        return True
    haystack = " ".join(str(result.get(key) or "") for key in ("title", "url", "snippet")).lower()
    return any(re.search(rf"\b{re.escape(term)}\b", haystack) for term in terms)


def _http_json(url: str, data: Dict[str, Any] = None, headers: Dict[str, str] = None,
               timeout: int = _TIMEOUT) -> Any:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": _USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _search_tavily(query: str, limit: int) -> List[Dict[str, str]]:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return []
    data = _http_json("https://api.tavily.com/search", data={
        "api_key": key, "query": query, "max_results": limit, "search_depth": "basic"})
    return [{
        "title": r.get("title") or "",
        "url": r.get("url") or "",
        "snippet": clean_snippet(r.get("content") or ""),
        "source": "Tavily",
    } for r in data.get("results", [])]


def _search_serper(query: str, limit: int) -> List[Dict[str, str]]:
    key = os.environ.get("SERPER_API_KEY")
    if not key:
        return []
    data = _http_json("https://google.serper.dev/search", data={"q": query, "num": limit},
                      headers={"X-API-KEY": key, "Content-Type": "application/json"})
    return [{
        "title": r.get("title") or "",
        "url": r.get("link") or "",
        "snippet": clean_snippet(r.get("snippet") or ""),
        "source": "Google (Serper)",
    } for r in data.get("organic", [])]


def _search_brave(query: str, limit: int) -> List[Dict[str, str]]:
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        return []
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": query, "count": limit})
    data = _http_json(url, headers={"X-Subscription-Token": key, "Accept": "application/json"})
    return [{
        "title": r.get("title") or "",
        "url": r.get("url") or "",
        "snippet": clean_snippet(r.get("description") or ""),
        "source": "Brave",
    } for r in (data.get("web") or {}).get("results", [])]


def _search_scrape_do(query: str, limit: int) -> List[Dict[str, str]]:
    """Use Scrape.do to fetch a public search-results page.

    Scrape.do is a page-fetching API rather than a search index.  We use it
    only as a transport for DuckDuckGo's HTML results, then normalize the
    links exactly like other providers.  The token is never included in logs.
    """
    token = os.environ.get("SCRAPE_DO_API_KEY")
    if not token:
        return []
    target = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    endpoint = "https://api.scrape.do/?" + urllib.parse.urlencode({"token": token, "url": target})
    req = urllib.request.Request(endpoint, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    results: List[Dict[str, str]] = []
    # DDG's result markup is intentionally simple and stable; avoid a new
    # parser dependency for this optional provider.
    # Match anchors directly rather than attempting to balance nested result
    # divs (which vary between DDG's desktop and mobile markup).
    anchors = re.findall(r'<a\b[^>]*class=["\'][^"\']*result__a[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.S | re.I)
    for href_value, title_value in anchors:
        def _text(value: str) -> str:
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value)).strip()
        url = urllib.parse.unquote(href_value)
        if "uddg=" in url:
            url = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("uddg", [url])[0]
        results.append({"title": _text(title_value), "url": url,
                        "snippet": "",
                        "source": "Scrape.do (DuckDuckGo)"})
        if len(results) >= limit:
            break
    return results


# Words that make a query too specific for topic-abstract APIs (DDG/Wikipedia).
# "find the latest Python version" -> "Python" still returns a real abstract.
_TOPIC_NOISE_RE = re.compile(
    r"\b(find|get|show|me|the|a|an|latest|newest|current|recent|version|versions|"
    r"features|news|about|for|of|right now|today|release|research|investigate)\b", re.IGNORECASE)


def _simplify_query(query: str) -> str:
    """Progressively simpler variants of a query for topic-abstract APIs."""
    variants = [query]
    stripped = _TOPIC_NOISE_RE.sub(" ", query)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if stripped and stripped.lower() != query.lower():
        variants.append(stripped)
        # First capitalized word sequence (likely the actual subject).
        m = re.search(r"[A-Z][A-Za-z0-9.+#]*(?:\s+[A-Z][A-Za-z0-9.+#]*)*", stripped)
        if m and m.group(0).lower() != stripped.lower():
            variants.append(m.group(0))
    out, seen = [], set()
    for v in variants:
        if v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def _search_duckduckgo(query: str, limit: int) -> List[Dict[str, str]]:
    """Keyless Instant Answer API over simplified query variants, then a
    Wikipedia summary lookup as a last resort. Returns [] when nothing real
    is found — callers must stay honest about that."""
    out: List[Dict[str, str]] = []
    for variant in _simplify_query(query):
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": variant, "format": "json", "no_html": 1, "skip_disambig": 1})
        try:
            data = _http_json(url)
        except Exception as exc:
            print(f"[WEB SEARCH WARNING] duckduckgo: {exc}")
            data = {}
        # Acronym guard: DDG can disambiguate the whole topic to an unrelated
        # ALL-CAPS entity (query 'python version' -> 'PYTHON' cold-war plan).
        # Skip that response entirely and let the next variant / Wikipedia win.
        heading_all = data.get("Heading") or ""
        if heading_all.isupper() and len(heading_all) > 3 and not variant.isupper():
            data = {}
        if data.get("AbstractText"):
            out.append({
                "title": data.get("Heading") or variant,
                "url": data.get("AbstractURL") or "",
                "snippet": clean_snippet(data["AbstractText"]),
                "source": "DuckDuckGo",
            })
        for rt in data.get("RelatedTopics", []):
            text = rt.get("Text") or ""
            if not text:
                continue
            if rt.get("FirstURL"):
                if " - " in text and len(text) > 60:
                    title, snippet = text.split(" - ", 1)
                else:
                    title, snippet = text, text
                out.append({
                    "title": title[:120],
                    "url": rt["FirstURL"],
                    "snippet": clean_snippet(snippet),
                    "source": "DuckDuckGo",
                })
            if len(out) >= limit:
                return out[:limit]
        if out:
            return out[:limit]

    # Last resort: Wikipedia search API (keyless) to RESOLVE the topic, then
    # the summary REST API for real text. Searching instead of guessing the
    # title handles disambiguation ("python version" -> "Python (programming language)").
    for variant in _simplify_query(query):
        search_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": variant,
            "format": "json", "srlimit": 1,
        })
        try:
            hits = _http_json(search_url).get("query", {}).get("search", [])
            resolved_title = hits[0]["title"] if hits else None
        except Exception:
            resolved_title = None
        if not resolved_title:
            continue
        summary_url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                       + urllib.parse.quote(resolved_title.replace(" ", "_")))
        try:
            data = _http_json(summary_url)
            extract = data.get("extract") or ""
            # Disambiguation pages carry no usable summary — skip them.
            if extract and "may refer to" not in extract.lower():
                out.append({
                    "title": data.get("title") or resolved_title,
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page") or summary_url,
                    "snippet": clean_snippet(extract),
                    "source": "Wikipedia",
                })
                break
        except Exception:
            continue
    return out[:limit]


# Preference order: keyed, higher-quality providers first; keyless fallback last.
# Looked up by name at call time so tests (and future overrides) can patch them.
_PROVIDER_NAMES = ("tavily", "serper", "brave", "scrape_do", "duckduckgo")


def search_web(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """Search the live web using ``SEARCH_PROVIDER`` or the auto fallback.

    ``auto`` tries configured quality providers before the keyless fallback.
    An explicit provider is deliberately strict: if it is unconfigured or
    unavailable, callers receive no results and can state that current
    verification is unavailable instead of silently using a different source.
    """
    query = (query or "").strip()
    if not query:
        return []
    requested = os.environ.get("SEARCH_PROVIDER", "auto").strip().lower() or "auto"
    if requested == "auto":
        provider_names = _PROVIDER_NAMES
    elif requested in _PROVIDER_NAMES:
        provider_names = (requested,)
    else:
        print(f"[WEB SEARCH WARNING] unknown SEARCH_PROVIDER '{requested}'")
        return []
    for name in provider_names:
        provider = globals().get(f"_search_{name}")
        if provider is None:
            continue
        try:
            results = provider(query, limit) or []
        except Exception as exc:
            print(f"[WEB SEARCH WARNING] {name}: {exc}")
            results = []
        results = [r for r in results if (r.get("url") or r.get("snippet")) and result_matches_query(query, r)]
        if results:
            return results[:limit]
    return []
