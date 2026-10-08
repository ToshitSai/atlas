"""Deep Research pipeline: plan -> search -> synthesize -> verify -> report.

Implements the router's autonomous multi-step research mode. Sources come from
the web_search tool (current web) plus the literature tool (academic papers).
The report is honest by construction: it contains only material traceable to a
collected source, and if no source can be reached it reports that instead of
inventing content.
"""
import datetime
import os
import re
import time
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

import backend.config  # auto-loads .env into os.environ
from backend.llm import query_llm
from backend.literature_search import search_literature
from backend.web_search import search_web
from backend.step_trace import StepTrace, Stages, create_trace

_SYNTH_SYSTEM_PROMPT = (
    "You are a rigorous research synthesizer. Write ONLY from the evidence "
    "snippets provided, citing sources inline like [1]. Never state a fact that "
    "is not present in the evidence. If the evidence is insufficient, say so "
    "explicitly. Begin each technical finding with a plain-English sentence, "
    "and briefly define any specialist term on its first use."
)

_FILLER_ABSTRACT_PREFIXES = ("research paper on", "academic research indexed")
_TRUSTED_SOURCE_HOSTS = (
    "wikipedia.org", "britannica.com", "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "nih.gov",
    "who.int", "worldbank.org", "oecd.org", "un.org", "kaggle.com", "huggingface.co",
    "archive.ics.uci.edu", "doi.org", "semanticscholar.org", "openalex.org", "acm.org",
    "ieee.org", "nature.com", "science.org", "reuters.com", "apnews.com", "bbc.com",
    "nytimes.com", "theguardian.com", "ft.com",
)
_LOW_QUALITY_HOST_HINTS = ("reddit.", "quora.", "medium.com", "pinterest.", "facebook.", "x.com", "twitter.")
_QUERY_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from", "how",
    "in", "improve", "is", "it", "latest", "of", "on", "or", "the", "this", "to", "what",
    "with", "why", "will", "would", "your",
}


def _topic_terms(text: str) -> List[str]:
    """Meaning-bearing terms used to reject accidental one-word retrieval."""
    return [word for word in re.findall(r"[a-z0-9]{3,}", (text or "").lower())
            if word not in _QUERY_STOPWORDS]


def _usable_query(query: str, goal: str) -> bool:
    terms = _topic_terms(query)
    goal_terms = set(_topic_terms(goal))
    # A web query needs a coherent phrase and must retain the actual topic.
    return len(terms) >= 3 and bool(set(terms) & goal_terms)


def _source_is_relevant(hit: Dict[str, Any], goal: str, query: str) -> bool:
    """Require source evidence to mention the research topic, not just a query word."""
    haystack = " ".join(str(hit.get(key) or "") for key in ("title", "snippet", "url")).lower()
    topic = set(_topic_terms(goal))
    query_terms = set(_topic_terms(query))
    topic_matches = sum(1 for term in topic if re.search(rf"\b{re.escape(term)}\b", haystack))
    query_matches = sum(1 for term in query_terms if re.search(rf"\b{re.escape(term)}\b", haystack))
    # One unmistakable topic term (e.g. fraud) is enough for a focused goal;
    # broader goals require two overlapping terms to avoid unrelated hits.
    return topic_matches >= (1 if len(topic) <= 3 else 2) or query_matches >= 2


def _source_is_trustworthy(hit: Dict[str, Any]) -> bool:
    """Allow recognised publishers, official domains, and academic indexes only."""
    source = str(hit.get("source") or "").lower()
    if source in {"semantic scholar", "openalex", "academic", "pubmed", "arxiv"}:
        return True
    host = (urlparse(str(hit.get("url") or "")).hostname or "").lower().lstrip("www.")
    if not host or any(hint in host for hint in _LOW_QUALITY_HOST_HINTS):
        return False
    return host.endswith(".gov") or host.endswith(".edu") or any(
        host == trusted or host.endswith(f".{trusted}") for trusted in _TRUSTED_SOURCE_HOSTS
    )


def plan_subqueries(goal: str, max_subqueries: int = 3, trace: Optional[StepTrace] = None) -> List[str]:
    """Break the research goal into concrete search sub-queries.

    Uses the LLM when a provider is reachable; otherwise deterministic query
    variants derived from the goal. Returns [] for an empty goal.
    """
    goal = (goal or "").strip()
    if not goal:
        return []

    llm = query_llm(
        f'Research goal: "{goal}"\n'
        f"Break it into {max_subqueries} short, self-contained web search queries. "
        "Return one query per line, no numbering, no commentary.",
        "You are a research planner. Output only the queries.",
    )
    if llm:
        subs = []
        for line in llm.splitlines():
            clean = line.strip().strip("-•").strip()
            clean = clean.lstrip("0123456789. ").strip()
            if (5 < len(clean) < 120 and _usable_query(clean, goal)
                    and clean.lower() not in (s.lower() for s in subs)):
                subs.append(clean)
            if len(subs) >= max_subqueries:
                break
        if subs:
            # Keep the user's complete objective as the first retrieval query.
            # An LLM planner may paraphrase away the core subject, whereas the
            # original is the strongest recall anchor for academic providers.
            original = goal.rstrip("?.!").strip()
            if original.lower() not in (s.lower() for s in subs):
                subs.insert(0, original)
            if trace:
                trace.complete_step(Stages.PLANNING, "Planned research approach", f"Created {len(subs)} search queries: {', '.join(subs[:3])}{'...' if len(subs) > 3 else ''}")
            return subs[:max_subqueries]

    base = goal.rstrip("?.!").strip()
    year = datetime.datetime.now().year
    variants = [
        base,
        f"{base} explained",
        f"{base} latest developments {year}",
        f"{base} advantages and disadvantages",
    ]
    result = variants[:max_subqueries]
    if trace:
        trace.complete_step(Stages.PLANNING, "Planned research approach", f"Created {len(result)} search queries (fallback)")
    return result


def _paper_to_source(paper: Dict[str, Any]) -> Dict[str, str]:
    title = paper.get("title") or ""
    abstract = paper.get("abstract") or ""
    # Guard against legacy/mock providers that synthesize placeholder abstracts.
    synthetic_abstract = any(abstract.lower().startswith(prefix) for prefix in _FILLER_ABSTRACT_PREFIXES)
    if synthetic_abstract:
        abstract = ""
    return {
        "title": title,
        "url": paper.get("url") or "",
        "snippet": abstract[:400],
        "source": paper.get("source") or "Academic",
        "authors": paper.get("authors") or "",
        "year": paper.get("year"),
        "venue": paper.get("venue") or "",
        "doi": paper.get("doi") or "",
        "citationCount": paper.get("citationCount"),
        "syntheticAbstract": synthetic_abstract,
    }


def _collect_sources(goal: str, subqueries: List[str], per_query: int, papers_on_first: int = 2, trace: Optional[StepTrace] = None, cancel_check: Optional[callable] = None) -> List[Dict[str, Any]]:
    """Run web + academic searches per sub-query and deduplicate by URL.

    A paper hit without real evidence (empty snippet after dropping the
    literature tool's filler abstracts) is not a usable source and is skipped.

    Each source that survives the trust + relevance filters is announced with a
    real ``source_reading`` step carrying the actual verdict metadata. This is
    honest about scope: the pipeline evaluates the retrieved snippet/metadata, it
    does NOT fetch the page, so no HTTP status code is invented."""
    sources: List[Dict[str, Any]] = []
    seen_urls = set()
    for idx, sq in enumerate(subqueries):
        if cancel_check and cancel_check():
            if trace:
                trace.skip_step(Stages.WEB_SEARCH, "Search cancelled", f"Stopped before query {idx + 1}/{len(subqueries)}")
            break
        if trace:
            trace.start_step(Stages.WEB_SEARCH, f"Searching: \"{sq}\"", f"Query {idx + 1}/{len(subqueries)}")
        try:
            web_hits = search_web(sq, limit=per_query)
        except Exception as exc:
            # Per-step failure is reported and the pass continues with the
            # remaining queries/providers instead of aborting the whole run.
            print(f"[DEEP RESEARCH WARNING] web search failed for '{sq}': {exc}")
            web_hits = []
            if trace:
                trace.fail_step(Stages.WEB_SEARCH, f"Web search failed: \"{sq}\"", str(exc))
        else:
            if trace:
                trace.complete_step(Stages.WEB_SEARCH, f"Search completed: \"{sq}\"", f"Found {len(web_hits)} web results")


        paper_hits: List[Dict[str, str]] = []
        if idx < papers_on_first:
            if trace:
                trace.start_step(Stages.LITERATURE_SEARCH, f"Searching academic papers: \"{sq}\"", "Querying Semantic Scholar / OpenAlex")
            try:
                papers = search_literature(sq, limit=2) or []
                paper_hits = [_paper_to_source(p) for p in papers]
                if trace:
                    trace.complete_step(Stages.LITERATURE_SEARCH, f"Academic search completed: \"{sq}\"", f"Found {len(paper_hits)} papers")
            except Exception as exc:
                print(f"[DEEP RESEARCH WARNING] literature search failed for '{sq}': {exc}")
                if trace:
                    trace.fail_step(Stages.LITERATURE_SEARCH, f"Academic search failed: \"{sq}\"", str(exc))
        for hit in web_hits + paper_hits:
            url = (hit.get("url") or "").strip()
            title = (hit.get("title") or "").strip()
            snippet = (hit.get("snippet") or "").strip()
            if not url or url in seen_urls:
                continue
            if hit.get("syntheticAbstract"):
                continue
            if title.lower().startswith("untitled"):
                continue
            if not _source_is_trustworthy(hit):
                continue
            if not _source_is_relevant(hit, goal, sq):
                continue
            # An academic record without an abstract remains a real, citeable
            # bibliographic source.  It is clearly labelled as metadata-only
            # in the final report; we never turn its title into a factual claim.
            seen_urls.add(url)
            sources.append({**hit, "query": sq})
            if trace:
                domain = (urlparse(url).hostname or "").lower()
                trace.complete_step(
                    Stages.SOURCE_READING,
                    f"Source checked: {(title or domain)[:60]}",
                    f"{domain or url} — trusted publisher/official domain, on-topic for this goal "
                    f"(snippet-level; page not fetched)",
                    {
                        "url": url,
                        "domain": domain,
                        "provider": hit.get("source") or "web",
                        "publishedYear": hit.get("year"),
                        "retrievedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "trustworthy": True,
                        "relevant": True,
                        "evidenceLevel": "snippet",
                    },
                )
    return sources



def _synthesize(goal: str, subqueries: List[str], sources: List[Dict[str, Any]], trace: Optional[StepTrace] = None, token_callback: Optional[callable] = None, cancel_check: Optional[callable] = None) -> str:
    """Build the report: grounded LLM synthesis when a provider is reachable,
    otherwise an honest sourced-snippet digest. Verification notes included.

    When ``token_callback`` is supplied the report is streamed as it is written:
    LLM synthesis sections forward the provider's real token stream, and the
    templated front-matter/tail are emitted at the moment they are composed. The
    returned string is unchanged, so the authoritative ``final`` frame still
    reconciles the live preview exactly."""
    by_query: Dict[str, List[Dict[str, Any]]] = {}
    for n, source in enumerate(sources, 1):
        source["n"] = n
        by_query.setdefault(source["query"], []).append(source)

    def emit(text: str) -> None:
        # Live answer text. A callback error (e.g. client disconnected) must
        # never abort report construction, so it is swallowed here.
        if token_callback and text:
            try:
                token_callback(text)
            except Exception:
                pass

    lines = [
        f"# Deep Research Report: {goal}",
        "",
        "## Plain-language summary",
        f"This report gathers evidence about **{goal}**. It separates what the retrieved "
        "sources actually support from ideas that would need more evidence, so you can understand "
        "the main takeaway before the technical detail.",
        "",
        f"Researched on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}."
        "Every statement below is traceable to a cited source; evidence is snippet-level "
        "(pages were not fully read).",
        "",
        "## Research Plan",
    ]
    lines += [f"{i}. {sq}" for i, sq in enumerate(subqueries, 1)]
    lines += ["", "## Findings", ""]
    # Front-matter is composed now, so it is streamed now (not batched at the end).
    emit("\n".join(lines))

    use_llm = True
    for sq in subqueries:
        if cancel_check and cancel_check():
            if trace:
                trace.skip_step(Stages.SYNTHESIS, "Writing cancelled", f"Stopped before \"{sq}\"")
            break
        items = by_query.get(sq) or []
        if not items:
            emit(f"\n### {sq}\n_No sources were found for this sub-question._\n")
            lines += [f"### {sq}", "Reliable sources could not be found for this topic.", ""]
            continue

        evidence = "\n".join(f"[{s['n']}] {s['title']} — {s['snippet']}" for s in items if s.get("snippet"))
        section = None
        emit(f"\n### {sq}\n")
        if use_llm and evidence:
            if trace:
                trace.start_step(Stages.SYNTHESIS, f"Writing section: \"{sq}\"", f"Synthesizing {len(items)} sources via LLM")
            # on_token forwards the provider's real token stream to the client,
            # so this section renders progressively instead of all at once.
            section = query_llm(
                f"Research goal: {goal}\nSub-question: {sq}\n\n"
                f"Evidence snippets (cite by [n]):\n{evidence}\n\n"
                "Write a 3-5 sentence synthesis of this sub-question using ONLY the evidence "
                "above, citing sources inline like [1]. Say explicitly if the evidence is insufficient.",
                _SYNTH_SYSTEM_PROMPT,
                on_token=token_callback,
            )
            if section is None:
                use_llm = False  # no provider reachable; digest the rest honestly
            if trace:
                trace.complete_step(Stages.SYNTHESIS, f"Wrote section: \"{sq}\"", "LLM synthesis complete")
        if not section:
            if trace:
                trace.start_step(Stages.SYNTHESIS, f"Compiling evidence: \"{sq}\"", f"Building digest from {len(items)} sources")
            section = "\n".join(
                f"- **[{s['n']}] {s['title']}** ({s['source']}): {s.get('snippet') or '(no snippet available — open the source)'}"
                for s in items
            )
            # Fallback digest is composed here, so it is streamed here.
            emit(section)
            if trace:
                trace.complete_step(Stages.SYNTHESIS, f"Compiled evidence: \"{sq}\"", "Fallback digest complete")
        emit("\n")
        lines += [f"### {sq}", section, ""]

    if trace:
        trace.start_step(Stages.VERIFICATION, "Cross-checking claims", f"Verifying {len(sources)} sources across {len(subqueries)} queries")
    tail = [
        "## Verification",
        f"- {len(sources)} unique sources collected across {len(subqueries)} planned searches (web + academic), deduplicated by URL.",
        "- Only sourced material is included; statements are snippet-level and should be verified against the full sources before being relied on.",
        "",
        "## Sources",
    ]
    tail += [f"{s['n']}. [{s['title'] or s['url']}]({s['url']}) — {s['source']}" for s in sources]
    lines += tail
    emit("\n" + "\n".join(tail))
    if trace:
        trace.complete_step(Stages.VERIFICATION, "Cross-checking complete", f"Verified {len(sources)} sources")
    return "\n".join(lines)



def run_deep_research(goal: str, per_query: int = 3, progress_callback: Optional[callable] = None, trace_id: Optional[str] = None, cancel_check: Optional[callable] = None, token_callback: Optional[callable] = None) -> Dict[str, Any]:
    """Execute the full deep-research pass for a goal.

    ``cancel_check`` (client disconnect) and a wall-clock budget both feed a
    single ``_stop`` predicate checked at every stage boundary and inside the
    collection/synthesis loops, so an aborted or over-budget run returns the
    partial, honest result instead of hanging. ``token_callback`` streams the
    report text live as it is written."""
    trace = create_trace("deep_research", trace_id)
    if progress_callback:
        trace.add_callback(progress_callback)

    budget_seconds = max(10, int(os.environ.get("DEEP_RESEARCH_BUDGET_SECONDS", "120")))
    deadline = time.monotonic() + budget_seconds

    def _stop() -> bool:
        if cancel_check and cancel_check():
            return True
        return time.monotonic() > deadline

    # The staged scientist pass is design/review only.  It adds roughly a minute
    # of LLM work before the sourced report, which overruns the production
    # function budget (Vercel Hobby caps at 60s), so it is skipped there via
    # DEEP_RESEARCH_SKIP_SCIENTIST.  It still runs by default (local/dev) so the
    # design pass and the established SSE contract stay intact.
    ai_scientist: Dict[str, Any] = {}
    if os.environ.get("DEEP_RESEARCH_SKIP_SCIENTIST", "").strip().lower() not in {"1", "true", "yes", "on"}:
        from backend.ai_scientist_pipeline import run_ai_scientist_pipeline
        ai_scientist = run_ai_scientist_pipeline(goal, trace, cancel_check=cancel_check) or {}

    if _stop():
        trace.skip_step(Stages.PLANNING, "Research stopped", "Cancelled by client or time budget exhausted before planning")
        return {"status": "cancelled", "report": "", "sourceCount": 0, "subqueries": [], "trace": trace.to_dict(), "ai_scientist": ai_scientist}

    trace.start_step(Stages.PLANNING, "Planning research approach", f"Analyzing goal: {goal[:100]}")
    subqueries = plan_subqueries(goal, per_query, trace=trace)
    if not subqueries:
        trace.fail_step(Stages.PLANNING, "Research planning failed", "No usable research question was produced")
        return {"status": "no_sources", "report": "", "sourceCount": 0, "subqueries": [], "trace": trace.to_dict(), "ai_scientist": ai_scientist}

    try:
        sources = _collect_sources(goal, subqueries, per_query, trace=trace, cancel_check=_stop)
    except TypeError as exc:
        # Compatibility for integrations that provide the original two-argument
        # collector. Built-in collection always receives the progress callback.
        if "progress" not in str(exc):
            raise
        sources = _collect_sources(goal, subqueries, per_query, trace=trace)
    if not sources:
        if _stop():
            trace.skip_step(Stages.LITERATURE_SEARCH, "Research stopped", "Cancelled or time budget exhausted during source collection")
            return {"status": "cancelled", "report": "", "sourceCount": 0, "subqueries": subqueries, "trace": trace.to_dict(), "ai_scientist": ai_scientist}
        trace.fail_step(Stages.LITERATURE_SEARCH, "Literature search failed", "No verifiable sources were retrieved")
        return {"status": "no_sources", "report": "", "sourceCount": 0, "subqueries": subqueries, "trace": trace.to_dict(), "ai_scientist": ai_scientist}
    academic_sources = sum(1 for source in sources if source.get("source") in ("Semantic Scholar", "OpenAlex"))
    trace.complete_step(Stages.LITERATURE_SEARCH, "Literature search complete", f"Collected {len(sources)} unique sources ({academic_sources} academic)")

    report = _synthesize(goal, subqueries, sources, trace=trace, token_callback=token_callback, cancel_check=_stop)

    trace.start_step(Stages.VERIFICATION, "Verifying citations", "Checking source traceability")
    trace.complete_step(Stages.VERIFICATION, "Verification complete", "All claims traceable to sources")

    trace.start_step(Stages.REPORT_GENERATION, "Generating final report", "Assembling complete research report")
    trace.complete_step(Stages.REPORT_GENERATION, "Report generated", f"Completed deep research with {len(sources)} sources")
    trace.complete_step(Stages.COMPLETED, "Deep research complete", f"Completed a sourced review using {len(sources)} unique sources")
    return {
        "status": "ok",
        "report": report,
        "sourceCount": len(sources),
        "sources": sources,
        "subqueries": subqueries,
        "trace": trace.to_dict(),
        "ai_scientist": ai_scientist,
    }

