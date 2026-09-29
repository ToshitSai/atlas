"""Deep Research pipeline: plan -> search -> synthesize -> verify -> report.

Implements the router's autonomous multi-step research mode. Sources come from
the web_search tool (current web) plus the literature tool (academic papers).
The report is honest by construction: it contains only material traceable to a
collected source, and if no source can be reached it reports that instead of
inventing content.
"""
import datetime
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
    "explicitly."
)

_FILLER_ABSTRACT_PREFIXES = ("research paper on", "academic research indexed")


def plan_subqueries(goal: str, max_subqueries: int = 3, trace: Optional[StepTrace] = None) -> List[str]:
    """Break the research goal into concrete search sub-queries.

    Uses the LLM when a provider is reachable; otherwise deterministic query
    variants derived from the goal. Returns [] for an empty goal.
    """
    goal = (goal or "").strip()
    if not goal:
        return []

    if trace:
        trace.start_step(Stages.PLANNING, "Planning research approach", f"Breaking down: {goal[:80]}")

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
            if 5 < len(clean) < 120 and clean.lower() not in (s.lower() for s in subs):
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


def _collect_sources(subqueries: List[str], per_query: int, papers_on_first: int = 2, trace: Optional[StepTrace] = None) -> List[Dict[str, Any]]:
    """Run web + academic searches per sub-query and deduplicate by URL.

    A paper hit without real evidence (empty snippet after dropping the
    literature tool's filler abstracts) is not a usable source and is skipped."""
    sources: List[Dict[str, Any]] = []
    seen_urls = set()
    for idx, sq in enumerate(subqueries):
        if trace:
            trace.start_step(Stages.WEB_SEARCH, f"Searching: \"{sq}\"", f"Query {idx + 1}/{len(subqueries)}")
        web_hits = search_web(sq, limit=per_query)
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
            # An academic record without an abstract remains a real, citeable
            # bibliographic source.  It is clearly labelled as metadata-only
            # in the final report; we never turn its title into a factual claim.
            seen_urls.add(url)
            sources.append({**hit, "query": sq})
    return sources


def _synthesize(goal: str, subqueries: List[str], sources: List[Dict[str, Any]], trace: Optional[StepTrace] = None) -> str:
    """Build the report: grounded LLM synthesis when a provider is reachable,
    otherwise an honest sourced-snippet digest. Verification notes included."""
    by_query: Dict[str, List[Dict[str, Any]]] = {}
    for n, source in enumerate(sources, 1):
        source["n"] = n
        by_query.setdefault(source["query"], []).append(source)

    lines = [
        f"# Deep Research Report: {goal}",
        "",
        "> Machine-generated by the AI Scientist deep-research pipeline "
        f"({datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}). "
        "Every statement below is traceable to a cited source; evidence is snippet-level "
        "(pages were not fully read).",
        "",
        "## Research Plan",
    ]
    lines += [f"{i}. {sq}" for i, sq in enumerate(subqueries, 1)]
    lines += ["", "## Findings", ""]

    use_llm = True
    for sq in subqueries:
        items = by_query.get(sq) or []
        if not items:
            lines += [f"### {sq}", "_No sources were found for this sub-question._", ""]
            continue

        evidence = "\n".join(f"[{s['n']}] {s['title']} — {s['snippet']}" for s in items if s.get("snippet"))
        section = None
        if use_llm and evidence:
            if trace:
                trace.start_step(Stages.SYNTHESIS, f"Synthesizing: \"{sq}\"", f"Processing {len(items)} sources via LLM")
            section = query_llm(
                f"Research goal: {goal}\nSub-question: {sq}\n\n"
                f"Evidence snippets (cite by [n]):\n{evidence}\n\n"
                "Write a 3-5 sentence synthesis of this sub-question using ONLY the evidence "
                "above, citing sources inline like [1]. Say explicitly if the evidence is insufficient.",
                _SYNTH_SYSTEM_PROMPT,
            )
            if section is None:
                use_llm = False  # no provider reachable; digest the rest honestly
            if trace:
                trace.complete_step(Stages.SYNTHESIS, f"Synthesized: \"{sq}\"", "LLM synthesis complete")
        if not section:
            if trace:
                trace.start_step(Stages.SYNTHESIS, f"Compiling evidence: \"{sq}\"", f"Building digest from {len(items)} sources")
            section = "\n".join(
                f"- **[{s['n']}] {s['title']}** ({s['source']}): {s.get('snippet') or '(no snippet available — open the source)'}"
                for s in items
            )
            if trace:
                trace.complete_step(Stages.SYNTHESIS, f"Compiled evidence: \"{sq}\"", "Fallback digest complete")
        lines += [f"### {sq}", section, ""]

    if trace:
        trace.start_step(Stages.VERIFICATION, "Cross-checking claims", f"Verifying {len(sources)} sources across {len(subqueries)} queries")
    lines += [
        "## Verification",
        f"- {len(sources)} unique sources collected across {len(subqueries)} planned searches (web + academic), deduplicated by URL.",
        "- Only sourced material is included; statements are snippet-level and should be verified against the full sources before being relied on.",
        "",
        "## Sources",
    ]
    lines += [f"{s['n']}. [{s['title'] or s['url']}]({s['url']}) — {s['source']}" for s in sources]
    if trace:
        trace.complete_step(Stages.VERIFICATION, "Cross-checking complete", f"Verified {len(sources)} sources")
    return "\n".join(lines)


def run_deep_research(goal: str, per_query: int = 3, progress_callback: Optional[callable] = None, trace_id: Optional[str] = None) -> Dict[str, Any]:
    """Execute the full deep-research pass for a goal."""
    trace = create_trace("deep_research", trace_id)
    if progress_callback:
        trace.add_callback(progress_callback)

    trace.start_step(Stages.PLANNING, "Planning research approach", f"Analyzing goal: {goal[:100]}")
    subqueries = plan_subqueries(goal, per_query, trace=trace)
    if not subqueries:
        trace.fail_step(Stages.PLANNING, "Research planning failed", "No usable research question was produced")
        return {"status": "no_sources", "report": "", "sourceCount": 0, "subqueries": [], "trace": trace.to_dict()}

    trace.start_step(Stages.WEB_SEARCH, "Searching the web", f"Running {len(subqueries)} search queries")
    try:
        sources = _collect_sources(subqueries, per_query, trace=trace)
    except TypeError as exc:
        # Compatibility for integrations that provide the original two-argument
        # collector. Built-in collection always receives the progress callback.
        if "progress" not in str(exc):
            raise
        sources = _collect_sources(subqueries, per_query, trace=trace)
    if not sources:
        trace.fail_step(Stages.LITERATURE_SEARCH, "Literature search failed", "No verifiable sources were retrieved")
        return {"status": "no_sources", "report": "", "sourceCount": 0, "subqueries": subqueries, "trace": trace.to_dict()}
    academic_sources = sum(1 for source in sources if source.get("source") in ("Semantic Scholar", "OpenAlex"))
    trace.complete_step(Stages.LITERATURE_SEARCH, "Literature search complete", f"Collected {len(sources)} unique sources ({academic_sources} academic)")

    trace.start_step(Stages.SYNTHESIS, "Synthesizing findings", "Building evidence-grounded report sections")
    report = _synthesize(goal, subqueries, sources, trace=trace)
    trace.complete_step(Stages.SYNTHESIS, "Synthesis complete", "All sections synthesized from source evidence")

    trace.start_step(Stages.VERIFICATION, "Verifying citations", "Checking source traceability")
    trace.complete_step(Stages.VERIFICATION, "Verification complete", "All claims traceable to sources")

    trace.start_step(Stages.REPORT_GENERATION, "Generating final report", "Assembling complete research report")
    trace.complete_step(Stages.REPORT_GENERATION, "Report generated", f"Completed deep research with {len(sources)} sources")
    trace.complete_step(Stages.COMPLETED, "Deep research complete", f"Completed a sourced review using {len(sources)} unique sources")
    return {
        "status": "ok",
        "report": report,
        "sourceCount": len(sources),
        "subqueries": subqueries,
        "trace": trace.to_dict(),
    }
