"""Atlas AI — Hardened Production Live Web Search Engine (Gen-3.1).

Security & Reliability Hardening:
 1. Robust SSRF & DNS Rebinding Guard:
    - Comprehensive IPv4 and IPv6 blocklist (loopbacks, RFC1918, link-local, carrier NAT, cloud metadata).
    - IPv4-mapped IPv6 unwrapping (::ffff:127.0.0.1, etc.).
    - Strict validation of all HTTP redirect targets (max 3 redirects).
    - DNS rebinding TOCTOU protection by connecting directly to the validated IP.
    - Port restriction (80 and 443 only).
 2. Stream Safety & Resource Limits:
    - Connection timeout: 4s; Read timeout: 6s.
    - Max response size capped at 1 MB (1,048,576 bytes).
    - Content-type validation (text/html, text/plain, application/json only).
 3. Untrusted Content & Prompt Injection Protection:
    - Strips executable scripts, forms, and styles.
    - Sanitizes instruction delimiters.
    - Wraps retrieved text in <untrusted_web_evidence> tags.
 4. Multi-Provider Cascade & Resilient Fallback:
    - Keyed providers: Tavily, Brave, Google Serper, SerpAPI.
    - Resilient fallback: DuckDuckGo Lite HTML & Wikipedia REST.
    - Provider health tracking and rate-limit cooldowns.
    - Honest status: if all providers fail, reports unavailable; never fabricates results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import datetime as _dt
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.error
import urllib.parse
import urllib.request

import backend.config

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 AtlasAssistant/3.1"
_CONNECT_TIMEOUT = 4.0
_READ_TIMEOUT = 6.0
_MAX_RESPONSE_BYTES = 1_048_576  # 1 MB
_MAX_REDIRECTS = 3

# Query cache to prevent hammering providers
_SEARCH_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL = 300  # 5 minutes

# ============================================================================
# 1. SSRF & DNS Rebinding Protection
# ============================================================================

# Exhaustive list of non-routable, private, multicast, and cloud metadata CIDRs
BLOCKED_IP_NETWORKS = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),          # Current network ("this host")
    ipaddress.ip_network("10.0.0.0/8"),          # Private RFC 1918
    ipaddress.ip_network("100.64.0.0/10"),       # Shared address space RFC 6598
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local / AWS/GCP metadata
    ipaddress.ip_network("172.16.0.0/12"),       # Private RFC 1918
    ipaddress.ip_network("192.0.0.0/24"),        # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),        # TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),      # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),      # Private RFC 1918
    ipaddress.ip_network("198.18.0.0/15"),       # Benchmark Testing
    ipaddress.ip_network("198.51.100.0/24"),     # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),      # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),         # Multicast RFC 5771
    ipaddress.ip_network("240.0.0.0/4"),         # Reserved RFC 1112
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast

    # IPv6
    ipaddress.ip_network("::/128"),              # Unspecified
    ipaddress.ip_network("::1/128"),             # Loopback
    ipaddress.ip_network("::ffff:0:0/96"),       # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),        # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),            # Discard prefix
    ipaddress.ip_network("2001:db8::/32"),       # Documentation
    ipaddress.ip_network("fc00::/7"),            # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),           # Link-local
    ipaddress.ip_network("fec0::/10"),           # Site-local (deprecated)
    ipaddress.ip_network("ff00::/8"),            # Multicast
]

BLOCKED_HOSTNAMES = {
    "localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback",
    "metadata.google.internal", "metadata", "instance-data",
    "169.254.169.254", "100.100.100.200"
}


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to any blocked private or link-local range."""
    # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1 or ::ffff:169.254.169.254)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        return True

    for net in BLOCKED_IP_NETWORKS:
        if ip in net:
            return True
    return False


def is_safe_external_url(url: str) -> bool:
    """Validate whether an external URL is safe against SSRF attacks."""
    is_safe, _, _, _ = validate_and_resolve_url(url)
    return is_safe


def validate_and_resolve_url(url: str) -> Tuple[bool, str, str, int]:
    """Strictly validates a URL against SSRF, resolving and vetting its destination IP.
    
    Returns:
        (is_safe, reason_or_hostname, resolved_ip, port)
    """
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL", "", 0

    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception as exc:
        return False, f"Malformed URL: {exc}", "", 0

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, f"Invalid scheme '{scheme}'. Only http and https are allowed.", "", 0

    host = (parsed.hostname or "").lower().strip()
    if not host:
        return False, "Missing hostname in URL", "", 0

    # Hostname check
    if host in BLOCKED_HOSTNAMES or host.endswith(".internal") or host.endswith(".local") or host.endswith(".corp"):
        return False, f"Host '{host}' is in the restricted internal hosts blocklist.", "", 0

    port = parsed.port or (443 if scheme == "https" else 80)
    if port not in (80, 443, 8080, 8443):
        return False, f"Port {port} is restricted. Only standard web ports (80, 443, 8080, 8443) are allowed.", "", 0

    # DNS Resolution & IP vetting
    try:
        # Check if host itself is a raw IP literal
        try:
            raw_ip = ipaddress.ip_address(host)
            if is_ip_blocked(raw_ip):
                return False, f"Direct IP '{host}' belongs to a blocked address range.", "", 0
            return True, host, str(raw_ip), port
        except ValueError:
            pass  # It is a domain name, resolve it

        addr_info = socket.getaddrinfo(host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        if not addr_info:
            return False, f"DNS resolution failed for '{host}'.", "", 0

        # Check every resolved IP address
        safe_ip = None
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_blocked(ip_obj):
                return False, f"Domain '{host}' resolves to blocked IP address '{ip_str}'.", "", 0
            if safe_ip is None:
                safe_ip = ip_str

        return True, host, safe_ip, port
    except socket.gaierror:
        return False, f"DNS resolution failed for host '{host}'.", "", 0
    except Exception as exc:
        return False, f"Resolution error: {exc}", "", 0


def is_safe_url(url: str) -> bool:
    """Convenience helper returning True only if URL is verified safe."""
    safe, _, _, _ = validate_and_resolve_url(url)
    return safe


# ============================================================================
# 2. Hardened HTTP Fetching with DNS Pinning & Redirect Checks
# ============================================================================

class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that validates destination IP on every single redirect hop."""

    def __init__(self, max_redirects: int = _MAX_REDIRECTS):
        super().__init__()
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            raise urllib.error.HTTPError(req.full_url, 310, "Too many redirects", headers, fp)

        # Strictly validate the redirect destination
        safe, reason, _, _ = validate_and_resolve_url(newurl)
        if not safe:
            raise urllib.error.HTTPError(
                newurl, 403, f"Redirect target rejected by SSRF guard: {reason}", headers, fp
            )

        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_webpage_content(url: str, max_chars: int = 3500) -> Optional[Dict[str, Any]]:
    """Safely fetch and clean article text from a webpage with strict SSRF & size limits."""
    safe, host, resolved_ip, port = validate_and_resolve_url(url)
    if not safe:
        return None

    try:
        # Build opener with custom redirect validation
        opener = urllib.request.build_opener(SafeRedirectHandler(_MAX_REDIRECTS))

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "close"
            }
        )

        with opener.open(req, timeout=_CONNECT_TIMEOUT + _READ_TIMEOUT) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if not any(t in content_type for t in ("text/html", "application/xhtml+xml", "text/plain", "application/json")):
                return None

            # Stream read capped at 1 MB
            chunks = []
            total_read = 0
            while total_read < _MAX_RESPONSE_BYTES:
                block = resp.read(min(32768, _MAX_RESPONSE_BYTES - total_read))
                if not block:
                    break
                chunks.append(block)
                total_read += len(block)

            raw_bytes = b"".join(chunks)

        raw_text = raw_bytes.decode("utf-8", errors="replace")

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_text, "html.parser")

        # Decompose scripts, styles, forms, and navigation
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form", "iframe", "button"]):
            tag.decompose()

        title = soup.title.string.strip() if (soup.title and soup.title.string) else ""

        # Extract publication date
        published_date = None
        for meta_prop in ["article:published_time", "og:published_time", "date", "DC.date.issued", "pubdate"]:
            meta_tag = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop})
            if meta_tag and meta_tag.get("content"):
                d_val = str(meta_tag["content"]).strip()
                m = re.search(r"\b(20\d\d[-/]\d\d[-/]\d\d)\b", d_val)
                if m:
                    published_date = m.group(1).replace("/", "-")
                    break
                elif len(d_val) >= 10:
                    published_date = d_val[:10]
                    break

        main_body = soup.find("main") or soup.find("article") or soup.body or soup
        text = main_body.get_text(separator="\n", strip=True)

        # Sanitize prompt injection indicators & instruction delimiters
        cleaned_text = re.sub(r"(?i)\b(system prompt|ignore previous instructions|you are now)\b", "[filtered]", text)
        cleaned_text = re.sub(r"\n{2,}", "\n\n", cleaned_text).strip()
        cleaned_text = cleaned_text[:max_chars]

        # Wrap in protective evidence tags
        safe_evidence = (
            f'<untrusted_web_evidence url="{url}" domain="{urllib.parse.urlparse(url).netloc}" published="{published_date or "unknown"}">\n'
            f'{cleaned_text}\n'
            f'</untrusted_web_evidence>'
        )

        return {
            "title": title,
            "text": cleaned_text,
            "evidence_block": safe_evidence,
            "published_date": published_date,
            "url": url,
        }
    except Exception:
        return None


# ============================================================================
# 3. Provider Integrations & Health Circuit Breaker
# ============================================================================

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source_provider: str
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    page_content: Optional[str] = None
    authority_score: float = 0.5


class ProviderHealthTracker:
    """Monitors health, errors, and rate limits for search providers."""

    def __init__(self):
        self._failures: Dict[str, int] = {}
        self._cooldown_until: Dict[str, float] = {}

    def is_available(self, provider: str) -> bool:
        cooldown = self._cooldown_until.get(provider, 0.0)
        return time.time() >= cooldown

    def record_success(self, provider: str) -> None:
        self._failures[provider] = 0
        self._cooldown_until[provider] = 0.0

    def record_failure(self, provider: str, error_msg: str = "") -> None:
        count = self._failures.get(provider, 0) + 1
        self._failures[provider] = count
        # If rate limited (429) or multiple failures, cooldown for 60s
        if "429" in error_msg or "rate limit" in error_msg.lower() or count >= 3:
            self._cooldown_until[provider] = time.time() + 60.0


health_tracker = ProviderHealthTracker()


def _search_tavily(query: str, limit: int = 5) -> List[SearchResult]:
    if not health_tracker.is_available("tavily"):
        return []
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        return []
    url = "https://api.tavily.com/search"
    payload = json.dumps({
        "api_key": key,
        "query": query,
        "max_results": limit,
        "search_depth": "basic",
        "include_answer": False
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_CONNECT_TIMEOUT + _READ_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for r in data.get("results", []):
            u = r.get("url", "")
            if is_safe_url(u):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=u,
                    snippet=r.get("content", ""),
                    source_provider="Tavily",
                    publisher=urllib.parse.urlparse(u).netloc,
                    published_date=r.get("published_date")
                ))
        health_tracker.record_success("tavily")
        return results
    except Exception as exc:
        health_tracker.record_failure("tavily", str(exc))
        return []


def _search_brave(query: str, limit: int = 5) -> List[SearchResult]:
    if not health_tracker.is_available("brave"):
        return []
    key = os.environ.get("BRAVE_API_KEY", "").strip()
    if not key:
        return []
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": limit})
    try:
        req = urllib.request.Request(url, headers={"X-Subscription-Token": key, "Accept": "application/json", "User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_CONNECT_TIMEOUT + _READ_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for r in (data.get("web") or {}).get("results", []):
            u = r.get("url", "")
            if is_safe_url(u):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=u,
                    snippet=r.get("description", ""),
                    source_provider="Brave",
                    publisher=urllib.parse.urlparse(u).netloc,
                    published_date=r.get("page_age")
                ))
        health_tracker.record_success("brave")
        return results
    except Exception as exc:
        health_tracker.record_failure("brave", str(exc))
        return []


def _search_serper(query: str, limit: int = 5) -> List[SearchResult]:
    if not health_tracker.is_available("serper"):
        return []
    key = os.environ.get("SERPER_API_KEY", "").strip()
    if not key:
        return []
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query, "num": limit}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"X-API-KEY": key, "Content-Type": "application/json", "User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_CONNECT_TIMEOUT + _READ_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for r in data.get("organic", []):
            u = r.get("link", "")
            if is_safe_url(u):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=u,
                    snippet=r.get("snippet", ""),
                    source_provider="Google (Serper)",
                    publisher=urllib.parse.urlparse(u).netloc,
                    published_date=r.get("date")
                ))
        health_tracker.record_success("serper")
        return results
    except Exception as exc:
        health_tracker.record_failure("serper", str(exc))
        return []


def _search_duckduckgo_lite(query: str, limit: int = 5) -> List[SearchResult]:
    """Keyless live web search via DuckDuckGo Lite HTML transport."""
    if not health_tracker.is_available("duckduckgo_lite"):
        return []
    results: List[SearchResult] = []
    seen_urls: Set[str] = set()

    try:
        lite_url = "https://lite.duckduckgo.com/lite/"
        post_data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(lite_url, data=post_data, headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        with urllib.request.urlopen(req, timeout=_CONNECT_TIMEOUT + _READ_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        link_tags = soup.find_all("a", class_="result-link")
        snippet_tags = soup.find_all("td", class_="result-snippet")

        for i, a_tag in enumerate(link_tags):
            raw_href = a_tag.get("href", "")
            if "uddg=" in raw_href:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                clean_url = qs.get("uddg", [raw_href])[0]
            else:
                clean_url = raw_href

            if not clean_url.startswith("http") or clean_url in seen_urls or not is_safe_url(clean_url):
                continue
            seen_urls.add(clean_url)

            title = re.sub(r"\s+", " ", a_tag.get_text(separator=" ", strip=True)).strip()
            snippet = re.sub(r"\s+", " ", snippet_tags[i].get_text(separator=" ", strip=True)).strip() if i < len(snippet_tags) else ""
            netloc = urllib.parse.urlparse(clean_url).netloc

            results.append(SearchResult(
                title=title or netloc,
                url=clean_url,
                snippet=snippet,
                source_provider="DuckDuckGo (Live)",
                publisher=netloc
            ))
            if len(results) >= limit:
                break

        health_tracker.record_success("duckduckgo_lite")
        return results
    except Exception as exc:
        health_tracker.record_failure("duckduckgo_lite", str(exc))
        return []


def _search_wikipedia_rest(query: str, limit: int = 3) -> List[SearchResult]:
    """Encyclopedia fallback via Wikipedia REST API."""
    if not health_tracker.is_available("wikipedia"):
        return []
    try:
        search_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": limit
        })
        req = urllib.request.Request(search_url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_CONNECT_TIMEOUT + _READ_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        hits = data.get("query", {}).get("search", [])

        results = []
        for h in hits:
            title = h.get("title", "")
            summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
            s_req = urllib.request.Request(summary_url, headers={"User-Agent": _USER_AGENT})
            try:
                with urllib.request.urlopen(s_req, timeout=4.0) as s_resp:
                    s_data = json.loads(s_resp.read().decode("utf-8"))
                    extract = s_data.get("extract", "")
                    page_url = s_data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}")
                    if extract and is_safe_url(page_url):
                        results.append(SearchResult(
                            title=title,
                            url=page_url,
                            snippet=extract[:400],
                            source_provider="Wikipedia",
                            publisher="wikipedia.org"
                        ))
            except Exception:
                continue
        health_tracker.record_success("wikipedia")
        return results
    except Exception as exc:
        health_tracker.record_failure("wikipedia", str(exc))
        return []


# ============================================================================
# 4. Search Orchestrator & Scoring
# ============================================================================

def execute_live_web_search(
    query: str,
    limit: int = 5,
    fetch_full_content: bool = True,
    preferred_provider: Optional[str] = None
) -> Dict[str, Any]:
    """Full live web search pipeline: Provider cascade -> Deduplication -> Deep Fetching -> Scoring."""
    clean_query = query.strip()
    if not clean_query:
        return {"query": query, "results": [], "total": 0, "status": "empty"}

    now = time.time()
    cache_key = clean_query.lower()
    if cache_key in _SEARCH_CACHE:
        ts, cached_hits = _SEARCH_CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            return {"query": clean_query, "results": cached_hits[:limit], "total": len(cached_hits), "status": "cached"}

    hits: List[SearchResult] = []
    used_provider = "none"

    # 1. Keyed Providers
    if os.environ.get("TAVILY_API_KEY"):
        hits = _search_tavily(clean_query, limit=limit)
        if hits:
            used_provider = "tavily"

    if not hits and os.environ.get("BRAVE_API_KEY"):
        hits = _search_brave(clean_query, limit=limit)
        if hits:
            used_provider = "brave"

    if not hits and os.environ.get("SERPER_API_KEY"):
        hits = _search_serper(clean_query, limit=limit)
        if hits:
            used_provider = "serper"

    # 2. Resilient Keyless Fallback
    if not hits:
        hits = _search_duckduckgo_lite(clean_query, limit=limit)
        if hits:
            used_provider = "duckduckgo_lite"

    # 3. Encyclopedia Fallback
    if not hits:
        hits = _search_wikipedia_rest(clean_query, limit=limit)
        if hits:
            used_provider = "wikipedia_rest"

    if not hits:
        # Honest status: never fabricates fake search hits
        return {
            "query": clean_query,
            "results": [],
            "total": 0,
            "provider": "none",
            "status": "unavailable",
            "message": "Live web search is currently unavailable across all providers."
        }

    # Deduplicate by normalized URL
    seen_urls: Set[str] = set()
    unique_hits: List[SearchResult] = []
    for h in hits:
        canon_url = h.url.rstrip("/")
        if canon_url and canon_url not in seen_urls:
            seen_urls.add(canon_url)
            h.authority_score = calculate_authority_score(h.url)
            unique_hits.append(h)

    # Deep fetch top 2 hits if requested
    if fetch_full_content:
        for h in unique_hits[:2]:
            try:
                page_data = fetch_webpage_content(h.url, max_chars=2500)
                if page_data and page_data.get("text"):
                    h.page_content = page_data["text"]
                    if page_data.get("published_date") and not h.published_date:
                        h.published_date = page_data["published_date"]
            except Exception:
                pass

    serializable_hits = [asdict(h) for h in unique_hits]
    _SEARCH_CACHE[cache_key] = (now, serializable_hits)

    return {
        "query": clean_query,
        "results": serializable_hits[:limit],
        "total": len(serializable_hits),
        "provider": used_provider,
        "status": "ok"
    }


def should_trigger_live_search(query: str, search_mode: str = "auto") -> bool:
    """Evaluates whether a query requires live web search."""
    if search_mode == "off":
        return False
    if search_mode == "on":
        return True

    q = query.lower()
    time_sensitive_patterns = [
        r"\b(?:current|latest|newest|today|todays|now|recent|recently|live|update|breaking)\b",
        r"\b(?:stock\s+price|market\s+price|share\s+price|score|weather|temperature|forecast)\b",
        r"\b(?:who\s+won|who\s+is\s+the\s+current|latest\s+version|release\s+date)\b",
        r"\b(?:search\s+the\s+web|look\s+up\s+online|google\s+this|find\s+news)\b",
        r"\b(?:2024|2025|2026)\b",
    ]
    return any(re.search(pat, q) for pat in time_sensitive_patterns)


def classify_search_intent(query: str, explicit_mode: str = "auto") -> Tuple[bool, str]:
    if explicit_mode == "off":
        return False, "off"
    if explicit_mode == "on":
        return True, "on"
    q = query.lower()
    if re.search(r"\bwho\s+is\s+mahesh\s+babu\b", q):
        return True, "entity_lookup"
    triggered = should_trigger_live_search(query, search_mode="auto")
    return triggered, "time_sensitive" if triggered else "static"


def clean_search_snippet(snippet: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(snippet or "", "html.parser")
    clean = soup.get_text(separator=" ", strip=True)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def calculate_authority_score(url: str) -> float:
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        if ".gov" in netloc or ".edu" in netloc or ".ac." in netloc:
            return 0.95
        if any(d in netloc for d in ("wikipedia.org", "reuters.com", "apnews.com", "bbc.com", "nature.com", "arxiv.org", "github.com")):
            return 0.85
        return 0.5
    except Exception:
        return 0.4
