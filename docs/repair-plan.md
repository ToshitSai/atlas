# Repair Plan — AI Scientist

**Audit date:** 2026-09-26  
**Baseline evidence:** `AI_SCIENTIST_BLACKBOX_EVALUATION_REPORT.md` reports 429 submitted scenarios, 51 completed responses, and 378 infrastructure timeouts. The 100% figure applies only to completed responses and is not a whole-benchmark accuracy result.

## Audit summary

The application is a FastAPI backend (`backend/main.py`), React/Vite client (`src/`), research orchestrator (`agents/orchestrator.py`), multi-provider LLM client (`backend/llm.py`), and persistence facade (`database/store.py`). It already includes a PostgreSQL/pgvector schema and repository, a JSON development fallback, multi-provider web-search adapters, a SymPy engine, Hugging Face dataset inspection/ranking, Docker-aware experiment execution, SSE research progress, and a substantial hermetic test suite.

The main production blocker is execution control: chat requests call the router synchronously; each automatic LLM request creates a new `ThreadPoolExecutor`; provider attempts are raced without a process-wide concurrency bound; and there is no durable, observable job abstraction for regular LLM work. This explains why a local single-model server can be overwhelmed even though individual request timeouts exist.

## Phased repair backlog

| Priority | Issue / root cause | Affected modules | Proposed fix | Tests required |
| --- | --- | --- | --- | --- |
| P0 | Local LLM overload and request timeouts: a new executor is created per request and there is no global admission control, bounded retry, or queue telemetry. | `backend/llm.py`, `backend/main.py`, `database/repository.py`, `database/store.py` | Add a process-wide bounded LLM executor/semaphore, configurable `LLM_TIMEOUT_SECONDS`, `MAX_CONCURRENT_LLM_REQUESTS`, `MAX_RETRIES`, and exponential backoff. Return explicit overload/timeout outcomes; record queue/execution telemetry. Keep a safe in-process fallback when Redis is absent. | Unit tests for bounded concurrency, retry/backoff, timeout, and overload. Sequential and controlled-parallel benchmark runner results. |
| P0 | Deep research executes inside a normal chat request and can hold the request open. | `backend/deep_research.py`, `backend/main.py`, `database/repository.py` | Create durable research jobs, return `job_id`, expose status/SSE progress, and execute through a bounded worker path. | API tests for submit/status/progress/failure recovery. |
| P0 | Benchmark reporting cannot yet execute the supplied 429-case battery as a reliable job and must not imply unavailable cases passed. | `scripts/`, `tests/`, `reports/` | Preserve existing tests; add a runner/report format that records submitted, completed, unavailable, pass, partial, fail, and latency percentiles. | One sequential and 5/10/20 controlled-parallel dry-run; only report measurements actually run. |
| P1 | Current-information providers exist but provider choice is fixed-order rather than explicitly configurable; source quality metadata is limited. | `backend/web_search.py`, `backend/current_info.py`, `backend/intent_router.py` | Respect `SEARCH_PROVIDER=auto|…`, validate configured providers, retain an honest no-verification result, and prioritize/filter sources by authority/relevance/recency. | Provider-selection and unavailable-path tests; current-information acceptance run with configured credentials. |
| P1 | Generated code uses an experiment sandbox; it is not yet a general-purpose coding execution service. Process fallback inherits broad host environment. | `sandbox/runner.py`, `backend/intent_router.py`, `backend/main.py` | Harden Docker defaults (non-root, read-only filesystem, PID/output limits) and make subprocess fallback opt-in with a minimal allowlist environment. Add a bounded code-run job endpoint. | Sandbox argv/security tests, output-limit test, and language-specific coding tests. |
| P1 | File analysis/RAG is partially scaffolded in schema/repository but upload parsing and retrieval are not fully wired through chat. | `backend/main.py`, `database/file_store.py`, `database/repository.py`, `database/vector_memory.py` | Validate upload type/size; parse PDF/TXT/CSV/JSON/code; persist metadata; chunk and embed through configured embedding provider; retrieve traceable chunks for file questions. | Parser tests with page/schema assertions, retrieval provenance tests, oversized/invalid upload tests. |
| P1 | Production persistence is available only when `DATABASE_URL` is configured; JSON fallback is currently implicit. | `database/store.py`, `database/repository.py`, `migrations/`, deployment docs | Require explicit development fallback in production configuration, surface backend status honestly, and complete migrations/deployment checks. | Postgres integration tests and migration smoke test; JSON-dev fallback test. |
| P1 | HF discovery uses expansion/ranking but needs broader semantic relevance where API metadata is sparse. | `backend/hf_datasets.py` | Audit expansion candidates and rank with task/features/license/size/splits/recency; retain zero-result truthfulness. | Fraud, churn, house-price search fixtures and direct-reference tests. |
| P1 | Research orchestration uses threads for background research and lacks a separated worker deployment contract. | `agents/orchestrator.py`, `backend/main.py`, `docker-compose.yml`, deployment docs | Route research through durable jobs/workers; retain planner/dataset/experiment/critic/report evidence flow without adding needless agents. | Job cancellation/restart/reconciliation and end-to-end small-data run. |
| P2 | Token/model/tool telemetry and rates are incomplete at the API boundary. | `backend/llm.py`, `backend/tracker.py`, `database/repository.py`, `backend/main.py` | Capture provider/model/token usage where returned, duration, queue time, tool status; add per-IP/user/route limiter with Redis adapter and safe local fallback. | Telemetry persistence and HTTP 429 limiter tests. |
| P2 | Export and technical result visuals are incomplete. | `backend/report_generator.py`, `backend/main.py`, `src/views/` | Add non-blocking Markdown/JSON/CSV and practical PDF exports; show experiment metrics, confusion matrices, timelines, and comparison data in advanced views. | Export-format and frontend-build tests. |
| P3 | Voice and localization. | frontend | Defer until the P0/P1 acceptance suite is reliable. | Feature-specific tests after core acceptance is green. |

## Safety and verification rules

- Preserve the existing modified `database/research_store.json` and untracked black-box report; neither is a repair artifact to overwrite.
- Do not claim that the 429 benchmark is repaired until all 429 cases have a terminal, recorded outcome.
- Treat missing credentials, unavailable Docker/Redis/Postgres, and provider failures as explicit states, never as successful model answers.
- Run unit tests after each phase and integration/e2e tests where the required services are available. Record environment limitations in the final report.

## Implementation order

1. P0 LLM admission control, retry policy, timeout configuration, and telemetry.
2. P0 durable async research execution and benchmark accounting.
3. P1 web provider configuration, sandbox hardening, and file/RAG wiring.
4. P1 deployment-grade persistence and worker contract.
5. P1 HF/research improvements.
6. P2 telemetry/rate limiting, exports, and visualizations.
7. Full benchmark only after the above tests are green.
