# ATLAS AI GEN-3.3.4 — PERMANENT DATABASE, PRIVATE OBJECT STORAGE & MULTIMODAL RAG PERSISTENCE REPORT

**Project:** Atlas AI / AI Scientist  
**Production URL:** [https://atlas-scientist.vercel.app](https://atlas-scientist.vercel.app)  
**Production Deployment:** `dpl_CKhZT8ntwMAkaEtQFxtGGuLbkdiF`  
**Current Production Commit:** `44c549d` (synced on `main`, `master`, and `origin`)  
**Release Classification:** Gen-3.3.4 Production Infrastructure Hardening  
**Verification Date:** November 12, 2026  

---

## EXECUTIVE CERTIFICATION

Atlas AI has completed the Gen-3.3.4 infrastructure upgrade. The application is now permanently backed by **Neon PostgreSQL 18.6** with the **`pgvector` 0.8.6 extension** and a **Private Vercel Blob object store** (`atlas-private-storage`).

Every requirement from Section 18 has been implemented, audited, deployed, and verified against live production endpoints. The cross-instance battery (`scripts/verify_gen334_cross_instance.py`) achieved a **100% pass rate** across all persistence, security, and multimodal retrieval tests.

```text
========================================================
ATLAS GEN-3.3.4 CROSS-INSTANCE PERSISTENCE BATTERY
Target URL: https://atlas-scientist.vercel.app
========================================================
[TEST 1] Verifying /api/health and /api/ready... PASSED (HTTP 200)
[TEST 2] Ingesting ATLAS-PERSISTENCE-2026...     PASSED (id=580e1227-b5b2-5a3b-8580-428958d51b0c, persistent=True)
[TEST 3] Ingesting ATLAS-IMAGE-2026...           PASSED (id=4f0f60fe-4467-5d1c-977d-355af7e7d6ac, OCR=Verified)
[TEST 4] Authorized Download (Session A)...      PASSED (HTTP 200, Hash Match=True, Cache-Control=private, no-store)
[TEST 5] Cross-Session Isolation (Session B)...  PASSED (Download Blocked=403, Delete Blocked=403)
[TEST 6] Cross-Instance Grounded RAG Query...   PASSED (Token=PERSIST-88421, Director=Dr. Evelyn Stone)
[TEST 7] Cleaning Up Test Artifacts...           PASSED (Doc Deleted=HTTP 200, Image Deleted=HTTP 200)
========================================================
BATTERY COMPLETE: ALL PASSED
========================================================
```

---

## A. PRODUCTION DATABASE ARCHITECTURE

| Attribute | Production Configuration |
|---|---|
| **Database Provider** | Neon Serverless PostgreSQL (managed via Vercel Marketplace `atlas-db`, resource `store_aaaktZwsPOH9ESeH`) |
| **Engine & Version** | `PostgreSQL 18.6 (ac70818) on aarch64-unknown-linux-gnu` |
| **Compiler** | `gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, 64-bit` |
| **Primary Host** | `ep-holy-salad-bcp77f8p-pooler.c-16.us-east-1.aws.neon.tech` |
| **Region** | AWS `us-east-1` (co-located with Vercel Production Function runtime in `iad1`) |
| **Connection Pooling** | PgBouncer transaction-mode pooler on port `5432` with connection retry and backoff |
| **DNS Fallback** | DNS-over-HTTPS via Google DNS with `hostaddr` resolution in [database/repository.py](file:///C:/Users/Toshit/Desktop/Atlas/database/repository.py) |
| **Durability Classification** | `durability: "durable"`, `persistent: true` |

---

## B. PGVECTOR CONFIGURATION

- **Extension Status:** Enabled in PostgreSQL `public` schema.
- **Extension Version:** `0.8.6`.
- **Vector Columns:**
  - `document_chunks.embedding`: `USER-DEFINED (vector, 1536)`
  - `memories.embedding`: `USER-DEFINED (vector, 1536)`
- **Indexing Strategy:** HNSW and IVFFlat cosine distance indexing using `<=>` operators.
- **Embedding Provider:** Google Gemini `gemini-embedding-001` producing 1536-dimensional normalized vectors with fallback to BM25 lexical rankers if network quota is reached.

---

## C. OBJECT STORAGE ARCHITECTURE

- **Provider:** Private Vercel Blob store (`atlas-private-storage`, resource `store_IwpyWGiUGAmA6dgS`).
- **Access Level:** Strictly `private` (`x-vercel-blob-access: private`).
- **Base Host:** `iwpywgiugama6dgs.private.blob.vercel-storage.com`.
- **Token Configuration:** `PRIVATE_READ_WRITE_TOKEN` injected via Vercel environment variables.
- **Security Boundary:**
  - Direct unauthenticated browser requests return `HTTP 403 Forbidden`.
  - Zero raw public URLs or upload tokens exposed to clients.
  - Authenticated fetches execute server-side via `FileStore.get()` with Bearer authentication.
- **Serverless Resilience:** [backend/rag_service.py](file:///C:/Users/Toshit/Desktop/Atlas/backend/rag_service.py) prioritizes object store writes, ensuring read-only serverless filesystems (`/var/task`) cannot abort document ingestion. Local cache gracefully utilizes `/tmp` when running on Vercel.

---

## D. MIGRATION 001–009 STATUS

All 9 migrations have been executed in sequence and verified in the Neon PostgreSQL `schema_migrations` audit table:

| ID | Migration Name | Applied Timestamp (UTC) | Status |
|---|---|---|---|
| `1` | `001_initial_schema.sql` | 2026-11-12 14:10:52.555818 GMT | Verified |
| `2` | `002_indexes.sql` | 2026-11-12 14:10:54.868090 GMT | Verified |
| `3` | `003_pgvector.sql` | 2026-11-12 14:10:56.629854 GMT | Verified |
| `4` | `004_legacy_compat.sql` | 2026-11-12 14:10:58.387952 GMT | Verified |
| `5` | `005_supabase_rls.sql` | 2026-11-12 14:11:52.968765 GMT | Verified |
| `7` | `006_plain_postgres_auth_ownership.sql` | 2026-11-12 14:11:55.422887 GMT | Verified |
| `8` | `007_rag_documents.sql` | 2026-11-12 14:11:57.755230 GMT | Verified |
| `9` | `008_rag_knowledge_graph_memory.sql` | 2026-11-12 14:11:59.513920 GMT | Verified |
| `10` | `009_user_memories.sql` | 2026-11-12 14:12:01.271031 GMT | Verified |

---

## E. TABLE INVENTORY

The Neon PostgreSQL database contains exactly **33 active relational tables** in the `public` schema:

1. `artifacts`
2. `citations`
3. `conversation_context`
4. `conversations`
5. `dataset_files`
6. `dataset_versions`
7. `datasets`
8. `document_chunks`
9. `document_embeddings`
10. `document_metadata`
11. `documents`
12. `experiment_metrics`
13. `experiment_relationships`
14. `experiments`
15. `files`
16. `hypotheses`
17. `jobs`
18. `knowledge_graph_edges`
19. `memories`
20. `messages`
21. `papers`
22. `project_payloads`
23. `reports`
24. `research_events`
25. `research_memory`
26. `research_projects`
27. `research_sessions`
28. `research_sources`
29. `schema_migrations`
30. `settings`
31. `tool_calls`
32. `user_memories`
33. `users`

---

## F. BLOB MIGRATION RESULTS

- **Migration Tool:** [scripts/migrate_public_to_private_blobs.py](file:///C:/Users/Toshit/Desktop/Atlas/scripts/migrate_public_to_private_blobs.py)
- **Report Location:** [migration_reports/public_to_private_blob_migration.json](file:///C:/Users/Toshit/Desktop/Atlas/migration_reports/public_to_private_blob_migration.json)
- **Summary:**
  - Total legacy public blobs detected: `0`
  - Total files migrated: `0`
  - Failed migrations: `0`
  - Checksum mismatches: `0`
  - Old blobs preserved (no destructive deletions): `0`

---

## G. DOCUMENT INGESTION TEST

- **Test Artifact:** `ATLAS-PERSISTENCE-2026.txt`
- **Verification Token:** `PERSIST-88421`
- **Location & Director:** Europa, Dr. Evelyn Stone
- **Ingested Document ID:** `580e1227-b5b2-5a3b-8580-428958d51b0c`
- **Ingestion Result:**
  - HTTP Status: `200 OK`
  - Chunks generated: `1`
  - Durability: `durable`
  - Storage Backend: `postgres_pgvector`
  - Object Store Persistence: Private Vercel Blob authenticated key written

---

## H. IMAGE INGESTION TEST

- **Test Artifact:** `ATLAS-IMAGE-2026.png`
- **Verification Token:** `VISION-72819`
- **Location:** Titan
- **Ingested Document ID:** `4f0f60fe-4467-5d1c-977d-355af7e7d6ac`
- **Ingestion Result:**
  - HTTP Status: `200 OK`
  - OCR Text Extracted: `ATLAS-IMAGE-2026\nImage Token: VISION-72819\nTarget Location: Titan\nSubsurface Exploration Mission\nAtmospheric Methane Analysis`
  - Durability: `durable`
  - Object Store Persistence: Private Vercel Blob verified

---

## I. CROSS-INSTANCE VERIFICATION

- **Protocol:** Ingestion, retrieval, download, security isolation, and deletion were executed across independent HTTP request contexts against the live production serverless deployment.
- **Outcome:** The application successfully retrieved documents, verified embeddings, and returned file contents across distinct container instances without relying on shared local disk or container memory.

---

## J. RAG RETRIEVAL VERIFICATION

- **Query:** `"What is the verification token and research director for ATLAS-PERSISTENCE-2026 on Europa?"`
- **Session ID:** `test_owner_1794494338`
- **Retrieved Evidence:**
  - Token verified: `PERSIST-88421`
  - Director verified: `Dr. Evelyn Stone`
- **Model Answer:**
  > *"For the ATLAS-PERSISTENCE-2026 project on Europa, the verification token is **PERSIST-88421** and the research director is Dr. Evelyn Stone."*

---

## K. SECURITY AND SESSION ISOLATION

Session isolation was strictly enforced between Authorized Session A (`test_owner_1794494338`) and Unauthorized Session B (`unauth_intruder_1794494338`):

1. **Unauthorized Download Check:** Session B attempted to download Document `580e1227-b5b2-5a3b-8580-428958d51b0c`.
   - **Result:** `HTTP 403 Forbidden` (`{"detail": "Forbidden: You do not have permission to access this private document."}`)
2. **Unauthorized Deletion Check:** Session B attempted to delete Document `580e1227-b5b2-5a3b-8580-428958d51b0c`.
   - **Result:** `HTTP 403 Forbidden` (`{"detail": "Forbidden: You cannot delete another session's private document."}`)

---

## L. FILE DOWNLOAD ENDPOINTS

- **Endpoints:** `GET /api/documents/{file_id}/download` and `GET /api/files/{file_id}/download`
- **Authorization:** Verified against anonymous session cookie and `X-Anonymous-ID` header.
- **Security Response Headers:**
  - `Cache-Control: private, no-store`
  - `X-Content-Type-Options: nosniff`
- **Data Integrity:** Byte-for-byte SHA-256 hash comparison matched the uploaded file with 100% fidelity.

---

## M. DOCUMENT DELETION ENDPOINTS

- **Endpoints:** `DELETE /api/documents/{file_id}` and `DELETE /api/files/{file_id}`
- **Operation:**
  1. Authorizes session ownership.
  2. Issues authenticated delete call to Private Vercel Blob (`https://blob.vercel-storage.com/delete`).
  3. Purges metadata, chunks, and embeddings from PostgreSQL in a single transaction.
- **Test Cleanup:** Both test document `580e1227-b5b2-5a3b-8580-428958d51b0c` and test image `4f0f60fe-4467-5d1c-977d-355af7e7d6ac` returned `HTTP 200 OK` on deletion.

---

## N. HEALTH AND DIAGNOSTICS ENDPOINTS

### 1. `/api/health` Response (Live Production)
```json
{
  "status": "healthy",
  "api": true,
  "database": true,
  "databaseType": "postgresql",
  "pgvector": true,
  "durability": "durable",
  "persistent": true,
  "objectStorage": {
    "provider": "vercel_blob",
    "access": "private",
    "connected": true
  },
  "semanticEmbeddings": {
    "provider": "gemini",
    "model": "gemini-embedding-001",
    "dimensions": 1536,
    "available": true
  },
  "databaseDetails": {
    "configured": true,
    "connected": true,
    "host": "ep-holy-salad-bcp77f8p-pooler.c-16.us-east-1.aws.neon.tech",
    "port": 5432,
    "pgvector": true,
    "last_error": null,
    "type": "postgresql",
    "durability": "durable"
  },
  "llm": true
}
```

### 2. `/api/ready` Response (Live Production)
```json
{
  "ready": true,
  "status": "ready",
  "api": true,
  "database": true,
  "databaseType": "postgresql",
  "pgvector": true,
  "durability": "durable",
  "persistent": true,
  "objectStorage": {
    "provider": "vercel_blob",
    "access": "private",
    "connected": true
  },
  "semanticEmbeddings": {
    "provider": "gemini",
    "model": "gemini-embedding-001",
    "dimensions": 1536,
    "available": true
  },
  "llmReady": true,
  "reason": "Production ready: all critical dependencies (LLM + durable database + object storage) connected."
}
```

---

## O. CURRENT PRODUCTION COMMIT

- **Production Commit Hash:** `44c549d`
- **Commit Message:** `fix(storage): prioritize durable FileStore write and handle serverless read-only filesystem`
- **Branches:** `main` and `master` synchronized at `origin`.
- **Live Vercel Deployment ID:** `dpl_CKhZT8ntwMAkaEtQFxtGGuLbkdiF`
- **Aliased URL:** [https://atlas-scientist.vercel.app](https://atlas-scientist.vercel.app)

---

## P. REMAINING WORK

**None.**
- Permanent Neon PostgreSQL database is connected, pooled, and durable.
- `pgvector` 0.8.6 is active and handling 1536-dimensional embeddings.
- Private Vercel Blob object store is securely integrated with zero public data exposure.
- All 9 schema migrations are applied and verified.
- Cross-instance persistence, authenticated downloads, session isolation, and grounded RAG retrieval have all passed automated verification with 100% green status.
