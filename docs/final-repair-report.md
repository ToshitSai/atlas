# Repair Report — P0 Foundation

**Date:** 2026-09-26  
**Status:** partial implementation; this is not a claim that the full production-upgrade backlog or the 429-scenario benchmark is complete.

## Problems found and root causes

| Problem | Evidence / root cause | Status |
| --- | --- | --- |
| Local-LLM overload | The original LLM dispatcher created a fresh thread pool for every request and had no process-wide request admission bound. A single local inference process could be overwhelmed by concurrent HTTP requests. | Addressed for in-process execution. |
| Blocking research start | `POST /api/research` invoked the synchronous research pipeline before responding. | Addressed: now dispatches the existing async runner. |
| Search-provider ambiguity | Search adapters existed, but no explicit `SEARCH_PROVIDER` contract governed which source could answer a current-information request. | Addressed. |
| Sandbox secret inheritance | The subprocess fallback copied the full process environment into generated code. | Addressed for the fallback; Docker hardening also added. |

## Changes implemented

- Added [`docs/repair-plan.md`](repair-plan.md), based on repository inspection and the supplied black-box evidence.
- Added a bounded, process-wide LLM admission gate and shared executor. Configuration is read at startup:
  - `LLM_TIMEOUT_SECONDS` (legacy `LLM_TIMEOUT` remains supported)
  - `LLM_QUEUE_TIMEOUT_SECONDS`
  - `MAX_CONCURRENT_LLM_REQUESTS`
  - `MAX_RETRIES`
  - `LLM_RETRY_BACKOFF_SECONDS`
- Added bounded exponential retry, timeout/overload/queue telemetry, and exposed secret-free execution telemetry in `/api/health` and `/api/config`.
- Changed research submission to launch the existing async pipeline rather than execute it in the request.
- Added strict `SEARCH_PROVIDER=auto|tavily|serper|brave|duckduckgo`; an explicit unavailable provider no longer silently switches sources.
- Hardened Docker execution with a non-root user, no-new-privileges, PID limit, read-only base filesystem, restricted network, and a temporary filesystem. The process fallback now passes only minimal OS variables plus required task inputs, rather than application secrets.

## Verification actually run

| Check | Result |
| --- | --- |
| `py -m pytest tests/test_current_information.py tests/test_llm_latency.py tests/test_backend_reliability.py -q` | **67 passed** (2.45 s); 28 FastAPI/Python deprecation warnings. |
| `py -m pytest tests/test_llm_latency.py tests/test_repair_capabilities.py tests/test_backend_reliability.py -q` | **64 passed** (3.05 s); same deprecation warnings. |
| Hermetic non-live suite (`test_database`, `test_store_conversation`, `test_store_db`, `test_intent_router`, `test_qa_regression`, `test_general_assistant`, `test_hf_parsing`) | **169 passed, 6 skipped** (11.10 s). |
| `npm run build` | **Passed**; Vite production build generated `dist/`. |

## Benchmark accounting

No full 429-case benchmark was run during this repair pass because the repository does not contain the supplied 429-case executable fixture and no live local LLM/search credentials were validated. The baseline remains:

| Total | Completed | Unavailable | Pass | Partial | Fail |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 429 | 51 | 378 | Not separately reported | Not separately reported | Not separately reported |

The supplied report's 100% pass rate applies only to its 51 completed responses. It must not be used as an overall benchmark result.

## Remaining production limitations

- The in-process bounded executor is a safe local fallback, not a Redis-backed multi-process worker queue. The PostgreSQL `jobs` schema exists, but durable LLM/research job dispatch and a separately deployed worker still need wiring.
- File/PDF/CSV ingestion, embedding generation, and source-aware RAG retrieval remain incomplete end-to-end.
- Postgres/pgvector, Redis, object storage, and Docker were not available to validate in this workspace; their integration and migrations have not been claimed as production-tested.
- API rate limiting, provider token/cost capture, complete code-execution API, full exports, and benchmark execution/reporting remain planned work.
- Docker hardening is implemented but not container-tested on this host.

## Next required verification

Run the full hermetic unit suite, then start the backend with real but non-production test credentials and execute the complete benchmark sequentially and at 5, 10, and 20 controlled concurrent submissions. Record each terminal outcome and latency percentiles; do not reclassify unavailable work as pass.
