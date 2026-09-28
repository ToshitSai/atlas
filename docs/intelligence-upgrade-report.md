# Intelligence Upgrade Report

**Date:** 2026-09-26  
**Scope:** Phase 2 capability orchestration, answer-quality controls, and regression verification.

## Audit of the post-repair system

| Capability | Observed implementation | Verification status |
| --- | --- | --- |
| Intent and multi-part routing | `backend/intent_router.py` plus structural decomposition/coverage checks | Hermetic tests passed. |
| Mathematics | Calculator + SymPy engine with symbolic verification | Existing capability tests passed. |
| Current information | Current-fact verifier and configurable multi-provider search | Hermetic tests passed; no live provider credential was used. |
| Memory | Persisted turns/session context; Postgres/pgvector semantic-memory primitives; JSON fallback | Hermetic conversation tests passed. |
| Research | Background orchestrator, SSE project events, literature/web synthesis | Code inspected; no live research workload run in this pass. |
| Sandbox | Docker-aware runner plus restricted process fallback | Unit tests passed; Docker CLI is not installed on this host. |
| PostgreSQL | PostgreSQL processes were present on the host; the application only uses it when `DATABASE_URL` is configured | Connection/migration was not executed against an unknown user database. |

## Intelligence changes

Added `backend/intelligence.py` and integrated it at the public chat-router boundary. Each response now has an `intelligence` object containing only safe, structured metadata:

- `task_type`, `difficulty`, required capabilities, selected tools/model category
- verification status
- total/completed explicit requirements

The layer is intentionally not a chain-of-thought log. It scores difficulty from request structure, requirement count, constraints, length, and tool/domain need; it selects the existing math, current-information, research, coding, retrieval, or general capability path; and it maintains a compact per-conversation summary (`topics`, last task/intent, turns seen). The full transcript is not copied into that summary.

An ambiguity guard now asks for sport and year for underspecified “Who won the World Cup?” queries, rather than choosing a tournament. Named or dated requests continue through normal current-information handling.

## Quality and verification behavior

| Task | Tool/verification classification |
| --- | --- |
| Math | calculator/SymPy; verified when a result is returned |
| Current fact | verifier + web search; verified status is reported without inventing a source |
| Deep research | web, literature, and source synthesis |
| Coding | generator + sandbox; marked `pending_execution` unless execution evidence exists |
| File/data | parser/retrieval; marked `source_required` until actual retrieved evidence is present |

This prevents generated code or unprocessed files from being presented as verified work.

## Tests actually run

| Command | Result |
| --- | --- |
| `py -m pytest tests/test_intelligence_orchestrator.py tests/test_intent_router.py tests/test_qa_regression.py tests/test_repair_capabilities.py -q` | **122 passed** in 3.15 s |
| `py -m pytest tests/test_current_information.py tests/test_llm_latency.py tests/test_backend_reliability.py tests/test_intelligence_orchestrator.py -q` | **72 passed** in 2.39 s; 28 deprecation warnings |
| `npm run build` | **Passed** |

## Benchmarks

The earlier black-box baseline remains **429 submitted / 51 completed / 378 unavailable**. No updated 350+ test dataset or live benchmark result is claimed: the repository does not include an executable 429-case fixture, and no LLM/search provider credentials were validated during this pass. Creating nominal test cases without a real evaluation oracle would not be meaningful benchmarking.

## Remaining limitations

### Model limitation

- The quality of open-ended explanation, coding, and deep synthesis still depends on the configured provider; the system does not claim frontier-model parity.

### System limitation

- The coding answer path can identify that execution is needed, but a general interactive code-execution API and automatic repair loop are not yet wired through chat.
- File parsing/chunk retrieval needs end-to-end upload-to-chat provenance before file claims can be verified.
- Conversation summaries are compact deterministic metadata; LLM-generated semantic summaries and explicit user-controlled long-term memory are not yet implemented.

### Tool limitation

- Search and research cannot verify live facts when no configured provider returns evidence.
- Docker hardening has not been container-tested because Docker is unavailable on this host.

### Infrastructure limitation

- Redis/worker and Postgres/pgvector were not integration-tested against configured services. The bounded local executor remains the development fallback.
- The full performance matrix (1/5/10/20/50 concurrent requests) and the complete benchmark require a runnable server and provider setup.
