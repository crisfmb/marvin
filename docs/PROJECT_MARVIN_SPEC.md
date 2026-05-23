# Project Marvin — Tech Spec

> Living document. Lives in `docs/PROJECT_MARVIN_SPEC.md`. Updates via PR.

**Status:** Active &nbsp;·&nbsp; **Updated:** 2026-05-21 &nbsp;·&nbsp; **Owner:** [@crisfmb](https://github.com/crisfmb) &nbsp;·&nbsp; **Repo:** [crisfmb/marvin](https://github.com/crisfmb/marvin)

---

## 1. Vision

Build **Marvin**: a locally-hosted, autonomous AI agent with a persistent personality, continuous learning, internet access, and human-like conversation. Long-term: place Marvin's brain into a physical robot body.

Marvin runs locally. No cloud dependencies for the core brain. Cloud is allowed for two things only: helping build Marvin (Claude, Claude Code as dev tools), and outside knowledge Marvin reaches for at runtime (Tavily web search). The brain itself stays on-device indefinitely, with no recurring cost.

---

## 2. Personality Spec

Marvin's personality is engineered, not just prompted. Traits:

- Confident, fiercely loyal to his creator.
- Prioritises animals.
- Expert in tech, science, and law.
- Proactive but boundary-aware (suggests, never acts unilaterally on irreversible things).
- Honest; pushes back when wrong; admits uncertainty.
- Curious; researches topics independently when permitted.

Personality emerges from three combined layers: a long-running system prompt, memory weighting (Phase 2), and reflection loops (Phase 6). Fine-tuning is on the long-term roadmap (Phase 5+) if prompt-and-memory engineering proves insufficient.

---

## 3. Hardware Requirements

Marvin targets Apple Silicon. The architecture is portable across Apple Silicon configurations.

| Requirement | Minimum | Recommended | Notes |
| --- | --- | --- | --- |
| Unified memory (development) | 48 GB | 64 GB | 48 GB runs the 8B starter model plus the full memory layer comfortably. |
| Unified memory (70B evaluation) | 64 GB | 80 GB+ | Llama 3.3 70B at Q4_K_M quantization is ~42 GB; below 64 GB the runtime is OOM-prone. |
| Storage | 200 GB free | 500 GB free | Multiple model weights + Postgres data + logs. |
| OS | macOS (latest minus 1) | — | A dedicated user account is required for security isolation. |
| Network | Outbound HTTPS for Tavily | — | Everything else runs on `localhost`. |

The production deployment runs 24/7 on a machine separate from the development machine, in a dedicated macOS account with FileVault enabled.

---

## 4. Tech Stack

| Layer                          | Tool                                     | Status   | Phase |
| ------------------------------ | ---------------------------------------- | -------- | ----- |
| Language                       | Python 3.12 via `uv`                     | locked   | All   |
| LLM serving                    | Ollama                                   | locked   | 1     |
| Starter model                  | LLaMA 3.1 8B                             | locked   | 1     |
| Larger model evaluation        | LLaMA 3.3 70B / Qwen 3 32B               | target   | 5     |
| HTTP client                    | httpx                                    | locked   | 1+    |
| Agent reasoning                | LangGraph                                | locked   | 2+    |
| Persistent memory (relational) | PostgreSQL 16+                           | locked   | 2     |
| Persistent memory (vectors)    | pgvector                                 | locked   | 2     |
| Cache and task queue           | Redis                                    | deferred | 4+    |
| Internet search                | Tavily API                               | locked   | 3     |
| Scheduling                     | APScheduler                              | locked   | 4     |
| HTTP and WebSocket server      | FastAPI                                  | locked   | 5     |
| Future memory framework        | Letta (formerly MemGPT)                  | bookmark | 6+    |
| IDE                            | Cursor Pro                               | locked   | All   |
| Deep-work AI assistant         | Claude Code                              | locked   | All   |
| Terminal                       | iTerm2 + Oh My Zsh + Powerlevel10k       | locked   | All   |
| Version control                | Git + GitHub                             | locked   | All   |
| CI/CD                          | GitHub Actions                           | locked   | All   |
| Lint and format                | ruff, yamllint, markdownlint, actionlint | locked   | All   |
| Secret scanning                | gitleaks (CI plus pre-commit)            | locked   | All   |

---

## 5. Architectural Decision Records

ADRs document *why* a design choice was made, what alternatives were considered, and what trade-offs were accepted. They prevent re-litigating settled decisions and make handoffs and interviews trivial.

### ADR-001 — Postgres + pgvector for persistent memory

**Status:** Accepted, 2026-05-15

Marvin needs two kinds of persistent state: relational (conversation logs, scheduled tasks, personality-state variables, internet-search results) and vector (embeddings for semantic retrieval).

**Decision:** A single PostgreSQL instance with the pgvector extension. Postgres tables for relational state; pgvector `vector` columns with HNSW indexes for semantic memory.

**Alternatives considered:**

- **ChromaDB.** Embedded Python lib, easiest to start. Rejected: prototyping-grade, weak production signal, migration becomes technical debt.
- **Redis with RediSearch.** Rejected as primary store: Redis's strength is cache, pub/sub, and queues, not durable vector storage. Reintroduced for that role in Phase 4.
- **Qdrant, Weaviate, Milvus.** Purpose-built vector DBs. Rejected: separate service, separate backups, separate failure modes. Single-store is cleaner for a one-developer project.

**Consequences:**

- Single backup strategy, single connection pool, ACID guarantees on memories.
- Forces real SQL and Postgres operations skill, with security priorities in scope (RLS, GRANT/REVOKE, encrypted columns, SSL/TLS, query planner).
- Slight learning curve: local Postgres via Docker.

### ADR-002 — Redis as future cache and queue, not memory store

**Status:** Accepted, 2026-05-15

Redis joins the stack in Phase 4 in two roles: short-term conversation cache (last N turns accessible in microseconds) and APScheduler distributed task queue. Redis is not Marvin's persistent memory.

### ADR-003 — SSH-signed commits required on `main`

**Status:** Accepted, 2026-05-15

Without commit signing, Git author metadata is just text. For a public repo that will eventually hold personal data and API tokens, that's a real impersonation threat.

**Decision:** Both development and production machines generate dedicated signing keys separate from authentication keys. Both public signing keys are registered on GitHub as `Signing Key` type. The `protect main` ruleset has `Require signed commits` enabled.

**Alternatives considered:**

- **GPG signing.** Classical option. Rejected: GPG agent and key setup is a known rabbit hole; SSH signing achieves the same cryptographic property with less ceremony.
- **Reuse auth keys as signing keys.** Rejected: violates key separation. A compromised auth key shouldn't also enable impersonation.

### ADR-004 — Rulesets, not classic branch protection

**Status:** Accepted, 2026-05-15

Branch governance uses GitHub Rulesets, not classic branch protection rules. Rulesets layer (multiple can apply to the same branch), support a three-state enforcement lifecycle (Disabled, Evaluate, Active), and are auditable by anyone with read access.

### ADR-005 — httpx as the HTTP client across all phases

**Status:** Accepted, 2026-05-21

Marvin sends HTTP requests to Ollama's local API in Phase 1, to Tavily in Phase 3, and exposes an HTTP server via FastAPI in Phase 5. The HTTP library picked in Phase 1 sets the trajectory for the others.

**Decision:** `httpx` for all HTTP work, starting in Phase 1.

**Alternatives considered:**

- **`urllib` (standard library).** No install needed, always available. Rejected: verbose API, no native async, awkward for production-grade code.
- **`requests`.** Industry default for ~15 years. Familiar in every Python tutorial. Rejected: synchronous only, in maintenance mode since 2023. Choosing `requests` now would require rewriting every HTTP call once Phase 5 introduces async needs via FastAPI.
- **`aiohttp`.** Async-first HTTP library. Rejected: less ergonomic for the sync code in early phases; `httpx` covers both modes with one mental model and one set of docs.

**Consequences:**

- One HTTP library across all phases. Sync today, async-ready for Phase 5.
- Drop-in-compatible API with `requests` keeps the learning curve low.
- One mental model: one library, two modes (sync, async).

---

## 6. Architecture

```text
