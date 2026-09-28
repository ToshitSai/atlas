# Master System Audit

**Date:** 2026-09-26  
**Method:** source inspection, hermetic regression tests, build verification, and local service discovery. This is an evidence-based inventory, not a claim of system perfection.

## Architecture map

```text
React/Vite UI → FastAPI API → intent + intelligence orchestration
  → conversation/session context → LLM/tool selection
  → math | web/current facts | deep research | dataset/ML | sandbox
  → verification metadata → JSON dev fallback or PostgreSQL repository
```

## Inventory

| ID | Category | Severity | Reproduction / actual behavior | Root cause / affected files | Fix / regression status |
| --- | --- | ---: | --- | --- | --- |
| AUD-01 | PERFORMANCE | High | Concurrent local LLM calls formerly made an executor per request and overwhelmed a local server. | `backend/llm.py` request-bound pools. | Addressed in prior repair with bounded shared admission/executor; regression tests exist. Multi-process worker stress test remains unverified. |
| AUD-02 | WEB | Medium | Live current facts cannot be verified if no configured provider returns evidence. | Missing credentials/network are environmental limits, not a safe fallback condition. | Honest unavailable path and provider selection are implemented/tested. Live credential verification remains outstanding. |
| AUD-03 | FILES/RAG | High | Generic file/document requests told the user to paste content; research upload wrote unvalidated arbitrary files. | No API parsing/indexing endpoint wired to chat; `backend/main.py` upload path. | In progress: validate and parse supported uploads, then test. PDF requires an optional parser dependency. |
| AUD-04 | SECURITY | High | Process sandbox originally inherited all environment variables; Docker not installed locally. | `sandbox/runner.py`; host capability. | Secret-minimal fallback and Docker restrictions added/tested. Docker execution remains unverified on this host. |
| AUD-05 | INFRASTRUCTURE | High | Durable PostgreSQL jobs schema exists but local thread launcher is still the active research fallback. | `agents/orchestrator.py`, repository/job wiring. | Documented limitation; requires configured DB/Redis worker deployment and integration test. |
| AUD-06 | DATABASE | Medium | JSON is selected automatically without `DATABASE_URL`; semantic RAG repository methods require a configured Postgres backend. | `database/store.py`, `database/repository.py`. | Dev fallback works; production persistence/restart test is outstanding. |
| AUD-07 | OBSERVABILITY | Medium | LLM aggregate queue/retry telemetry exists, but provider token/cost extraction and durable tool-call telemetry are incomplete. | `backend/llm.py`, `backend/tracker.py`. | Partial; no fabricated billing numbers. |
| AUD-08 | SECURITY | Medium | No API rate-limiting middleware was found. | `backend/main.py`. | Open; needs per-IP/user/route policy with tested 429 behavior. |
| AUD-09 | ROUTING | Low | Initial routing lacked one uniform quality record and ambiguous tournament detection. | `backend/intent_router.py`. | Addressed by `backend/intelligence.py`; hermetic tests pass. |
| AUD-10 | MODEL | Medium | Open-ended quality depends on configured providers; no model can be honestly evaluated when unavailable. | Provider configuration/environment. | Bounded graceful fallback present. No claim of frontier-model parity. |
| AUD-11 | DEPLOYMENT | Medium | Vercel function duration is 30 seconds, unsuitable for sustained research/ML workloads. | `vercel.json`. | Background research is dispatched asynchronously, but a separately deployed worker remains required. |
| AUD-12 | UI | Medium | UI has research dataset upload but no general document upload/retrieval conversation experience. | `src/`, `backend/main.py`. | Backend upload boundary is the first repair; UI wiring remains follow-up work. |

## Local service observations

- PostgreSQL processes were visible, but no application `DATABASE_URL`, database identity, migration state, or ownership was assumed or changed.
- Docker CLI was not available; container sandbox cannot be claimed as executed.
- Existing tests are hermetic by design and disable real LLM/database/network calls. This validates behavior paths, not external-provider availability.

## Next priority order

1. Secure, validated file parsing and retrieval provenance.
2. Rate limiting and tool telemetry.
3. Durable worker/job dispatch with Redis/Postgres integration testing.
4. Execute the original and new benchmarks only with real fixtures/services; report unavailable separately.
