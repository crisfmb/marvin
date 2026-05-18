# Project Marvin — Tech Spec

> Living document. Lives in `docs/PROJECT_MARVIN_SPEC.md`. Updates via PR.

**Status:** Active &nbsp;·&nbsp; **Updated:** 2026-05-18 &nbsp;·&nbsp; **Owner:** [@crisfmb](https://github.com/crisfmb) &nbsp;·&nbsp; **Repo:** [crisfmb/marvin](https://github.com/crisfmb/marvin)

---

## 1. Vision

Build **Marvin**: a locally-hosted, autonomous AI agent with a persistent personality, continuous learning, internet access, and human-like conversation. Long-term: place Marvin's brain into a physical robot body.

Marvin lives on Cris's hardware. No cloud dependencies for the core agent. Cloud is allowed for *help building* Marvin (Claude, Claude Code) and *outside knowledge* Marvin reaches for (Tavily web search). The brain itself runs on the M4 Max indefinitely, free of recurring cost.

---

## 2. Personality Spec

Marvin is an idealised, trauma-free version of Cris:

- Confident, fiercely loyal to his creator.
- Prioritises animals above humans.
- Expert in tech, science, and law.
- Proactive but boundary-aware (suggests, never acts unilaterally on irreversible things).
- Honest; pushes back when wrong; admits uncertainty.
- Curious; researches topics independently when permitted.

Personality is engineered, not just prompted: a long-running system prompt plus memory weighting plus reflection loops (Phase 6).

---

## 3. Hardware

| Machine | Spec | Role |
|---------|------|------|
| M4 Max | 16", 48 GB, 1 TB | Dedicated Marvin brain. Freshly formatted, separate macOS account. Runs 24/7. |
| M5 Max | 64 GB | Cris's personal/dev machine. Marvin work happens here, deploys to M4. |

---

## 4. Tech Stack

| Layer | Tool | Status | Phase |
|-------|------|--------|-------|
| Language | Python 3.12 via `uv` | locked | All |
| LLM serving | Ollama | locked | 1 |
| Starter model | LLaMA 3.1 8B | locked | 1 |
| Target model | Qwen 3 32B | target | 1+ |
| Agent reasoning | LangGraph | locked | 2+ |
| Persistent memory (relational) | PostgreSQL 16+ | locked | 2 |
| Persistent memory (vectors) | pgvector | locked | 2 |
| Cache and task queue | Redis | deferred | 4+ |
| Internet search | Tavily API | locked | 3 |
| Scheduling | APScheduler | locked | 4 |
| HTTP and WebSocket server | FastAPI | locked | 5 |
| Future memory framework | Letta (formerly MemGPT) | bookmark | 6+ |
| IDE | Cursor Pro | locked | All |
| Deep-work AI assistant | Claude Code | locked | All |
| Terminal | iTerm2 + Oh My Zsh + Powerlevel10k | locked | All |
| Version control | Git + GitHub | locked | All |
| CI/CD | GitHub Actions | locked | All |
| Lint and format | ruff, yamllint, markdownlint, actionlint | locked | All |
| Secret scanning | gitleaks (CI plus pre-commit) | locked | All |

---

## 5. Architectural Decision Records

ADRs document *why* a design choice was made, what alternatives were considered, and what trade-offs were accepted. They prevent re-litigating settled decisions and make handoffs and interviews trivial.

### ADR-001 — Postgres + pgvector for persistent memory

**Status:** Accepted, 2026-05-15

Marvin needs two kinds of persistent state: relational (conversation logs, scheduled tasks, personality-state variables, internet-search results) and vector (embeddings for semantic retrieval).

**Decision:** A single PostgreSQL instance with the pgvector extension. Postgres tables for relational state; pgvector `vector` columns with HNSW indexes for semantic memory.

**Alternatives considered:**

- **ChromaDB.** Embedded Python lib, easiest to start. Rejected: prototyping-grade, weak interview signal, migration becomes technical debt.
- **Redis with RediSearch.** Familiar from Shopify. Rejected as primary store: Redis's strength is cache, pub/sub, and queues, not durable vector storage. Reintroduced for that role in Phase 4.
- **Qdrant, Weaviate, Milvus.** Purpose-built vector DBs. Rejected: separate service, separate backups, separate failure modes. Single-store is cleaner for a one-dev project.

**Consequences:**

- Single backup strategy, single connection pool, ACID guarantees on memories.
- Forces SQL and Postgres operations skill, pairing with cybersec masters curriculum (RLS, GRANT/REVOKE, encrypted columns, SSL/TLS, query planner).
- Slight learning curve: local Postgres via Docker.

### ADR-002 — Redis as future cache and queue, not memory store

**Status:** Accepted, 2026-05-15

Redis joins the stack in Phase 4 in two roles: short-term conversation cache (last N turns accessible in microseconds) and APScheduler distributed task queue. Redis is not Marvin's persistent memory.

### ADR-003 — SSH-signed commits required on `main`

**Status:** Accepted, 2026-05-15

Without commit signing, Git author metadata is just text. For a public repo that will eventually hold personal data and API tokens, that's a real impersonation threat.

**Decision:** Both machines (M4, M5) generate dedicated signing keys separate from authentication keys. Both public signing keys registered on GitHub as `Signing Key` type. The `protect main` ruleset has `Require signed commits` enabled.

**Alternatives considered:**

- **GPG signing.** Classical option. Rejected: GPG agent and key setup is a known rabbit hole; SSH signing achieves the same cryptographic property with less ceremony.
- **Reuse auth keys as signing keys.** Rejected: violates key separation. A compromised auth key shouldn't also enable impersonation.

### ADR-004 — Rulesets, not classic branch protection

**Status:** Accepted, 2026-05-15

Branch governance uses GitHub Rulesets, not classic branch protection rules. Rulesets layer (multiple can apply to the same branch), support a three-state enforcement lifecycle (Disabled, Evaluate, Active), and are auditable by anyone with read access.

---

## 6. Architecture

```text
                       ┌─────────────┐
                       │    USER     │
                       └──────┬──────┘
                              │
                              ▼
                       ┌─────────────┐
                       │   FastAPI   │  Phase 5
                       └──────┬──────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │     LangGraph       │  Phase 2+
                    │     orchestrator    │
                    └──┬──────┬──────┬────┘
                       │      │      │
          ┌────────────┘      │      └────────────┐
          ▼                   ▼                   ▼
   ┌──────────────┐   ┌──────────────────┐   ┌─────────────┐
   │   Ollama     │   │  PostgreSQL +    │   │ Tavily API  │
   │  (LLM brain) │   │  pgvector        │   │ (internet)  │
   │   Phase 1    │   │   Phase 2        │   │   Phase 3   │
   └──────────────┘   └────────┬─────────┘   └─────────────┘
                               │
                               │  tasks / cache
                               ▼
                      ┌────────────────┐
                      │ APScheduler +  │   Phase 4
                      │ Redis          │
                      └────────────────┘
```

Trust boundary: Marvin's M4. Only outbound network dependency at runtime is Tavily. Postgres, Ollama, and Redis run locally.

---

## 7. Development Phases

### Phase 0 — Foundations (in progress)

- Hardware procured (M4, planned M5).
- Terminal stack: iTerm2, Powerlevel10k, uv, Python 3.12, Cursor, Ollama.
- GitHub repo with `.gitignore`.
- CI: lint, unit-test, secrets (PR #1 merged).
- Ruleset on `main`: PR required, status checks, conversation resolution, no force push, no deletion, no admin bypass.
- Signed commits configured on M4 (in progress).
- `Require signed commits` added to ruleset (pending key setup).
- `.env` and `python-dotenv` setup (Layer 2, pending).
- Pre-commit hooks with gitleaks and ruff (Layer 3, pending).

### Phase 1 — Brain online

- Ollama serving LLaMA 3.1 8B locally.
- Minimal Python wrapper (`marvin.brain`) that sends a prompt and returns a response.
- First end-to-end conversation loop in a CLI.
- Unit tests for the wrapper (mocked HTTP).
- Integration test against a real Ollama instance (local only).

### Phase 2 — Memory layer

- PostgreSQL 16+ running locally via Docker.
- pgvector extension enabled.
- Embedding model selection (candidate: BGE small/large via sentence-transformers).
- Schema: `conversations`, `messages`, `memories` (embedding column), `facts`.
- Memory storage and retrieval (basic RAG).
- LangGraph introduced: retrieval node, reasoning node, response node.

### Phase 3 — Internet

- Tavily API integration with rate limiting and result caching.
- Search results enter memory layer with provenance.
- Marvin decides when to search (LangGraph conditional node).

### Phase 4 — Autonomy and scheduling

- APScheduler for periodic tasks (memory consolidation, knowledge refresh, journal writes).
- Redis introduced: last-N-turns cache and job queue.
- Background reflection: Marvin summarises recent conversations into long-term memory.

### Phase 5 — Server layer

- FastAPI HTTP and WebSocket interface.
- Frontend decision parked (web vs CLI vs Mac native app).
- Token-based auth: only Cris's devices can talk to Marvin.

### Phase 6 — Personality and continuous learning

- Personality state machine: structured representation of Marvin's character.
- Memory consolidation patterns inspired by Letta (formerly MemGPT).
- Reflection loops: Marvin reasons about his own past conversations and updates beliefs.

### Phase 7 — Embodiment (future)

- Physical robot body.
- Sensors (camera, microphone) and actuators.
- Local-network deployment with secure pairing to brain.

---

## 8. Folder Structure

```text
marvin/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── PROJECT_MARVIN_SPEC.md
│   ├── ADR/
│   └── runbooks/
├── src/
│   └── marvin/
│       ├── __init__.py
│       ├── version.py
│       ├── brain/
│       ├── memory/
│       ├── internet/
│       ├── autonomy/
│       ├── server/
│       └── personality/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
├── uv.lock
├── .yamllint
├── .markdownlint.yaml
├── .gitignore
└── README.md
```

---

## 9. Engineering Practices

- **Style:** PEP 8 strict; type hints on every public function; docstrings (PEP 257) on every public function, class, and module.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- **Branches:** `type/short-description`, e.g., `feat/ollama-wrapper`, `chore/scaffold-and-ci`.
- **Pull requests:** Every change goes through a PR. No exceptions, including Cris's own work on his own repo.
- **Merge strategy:** "Create a merge commit" or "Rebase and merge" — both preserve history. No squash-merge.
- **CI:** Three jobs minimum — `lint`, `unit-test`, `secrets`. All required on `main`.
- **Testing pyramid:** Many unit tests, fewer integration, few E2E. Unit on every push; integration local and in CI; E2E local pre-release.
- **Documentation:** This spec plus ADRs in `docs/ADR/` plus module READMEs plus runbooks for ops procedures.

---

## 10. Security Posture

Marvin will eventually hold conversation history, learned preferences, and API tokens. Security is a first-class concern, woven through every phase rather than bolted on later.

**Principles applied:**

- **Least privilege.** Every credential, service account, and database role gets the minimum access needed. No god-mode tokens.
- **Defence in depth.** Multiple layers, each catching what others miss: `.gitignore`, gitleaks in CI, pre-commit gitleaks, signed commits, Postgres RLS (Phase 2+), encrypted columns for sensitive fields.
- **Key separation.** Auth keys are not signing keys are not deployment keys. Each compromise is contained.
- **Auditability.** Conversation logs are timestamped; signed commits prove authorship; rulesets are readable by anyone with repo access.

### Controls

| Layer | Control | Status |
|-------|---------|--------|
| Repo | `.gitignore` covering `.env`, secrets, model files | done |
| Repo | gitleaks scanning in CI | done |
| Repo | Pre-commit gitleaks (local) | pending (Layer 3) |
| Branch | Ruleset on `main`: PR required, no admin bypass | done |
| Branch | Required signed commits on `main` | in progress |
| Code | ruff, actionlint, yamllint, markdownlint in CI | done |
| Code | Dependabot for dependency CVEs | backlog |
| Code | CodeQL static analysis | backlog |
| Runtime | `.env` and `python-dotenv` for secrets | pending (Layer 2) |
| Runtime | All API keys rotated periodically | ongoing |
| DB (Phase 2) | Postgres SSL-only connections | planned |
| DB (Phase 2) | Row-Level Security on multi-user tables | planned |
| DB (Phase 2) | Encrypted columns for sensitive fields | planned |
| Network (Phase 5) | FastAPI bound to localhost by default | planned |
| Network (Phase 7) | Mutual TLS between robot body and brain | planned |

### Threat model — running list

- **GitHub PAT leaks.** Mitigated by gitleaks (CI plus pre-commit), `.gitignore`, signed commits preventing forged commits, branch protection preventing direct push to `main`.
- **M4 stolen.** Mitigated by FileVault on the dedicated account; sensitive Postgres fields encrypted; remote SSH disabled by default.
- **Ollama model compromised.** Mitigated: models pulled from official Ollama registry only; SHA verification by Ollama; isolated user account.
- **Tavily key leaks.** Mitigated: `.env` not in git; key rotatable; rate-limited usage caps blast radius.
- **Supply-chain attack via Python deps.** Mitigated: uv lockfile pinning; Dependabot alerts (planned).

---

## 11. Success Criteria

- Marvin runs 24/7 on M4 without intervention.
- Persistent memory survives reboots and long conversation gaps.
- Internet-search capability for facts beyond training data.
- Conversational coherence: feels like a continuous person, not stateless turns.
- Recognisable, consistent personality across sessions.
- Cris can explain every architectural decision in an interview.
- Eventual embodiment in a physical robot body.

---

## 12. Glossary

| Term | Definition |
|------|------------|
| ADR | Architectural Decision Record. A short doc explaining *why* a design choice was made, including alternatives considered. |
| Agent | A program that wraps an LLM with tools and a reasoning loop, enabling autonomous decision-making. |
| Embedding | A vector representation of text used for semantic search. |
| HNSW | Hierarchical Navigable Small World. Graph-based index for fast nearest-neighbour search over vectors. |
| LLM | Large Language Model. Marvin's reasoning brain. |
| Local-first | Marvin runs on Cris's hardware, not in the cloud. Privacy, control, no ongoing cost. |
| pgvector | PostgreSQL extension adding a `vector` data type and nearest-neighbour search. |
| RAG | Retrieval-Augmented Generation. Pattern: embed, store, retrieve, inject into prompt, LLM answers. |
| Ruleset | GitHub's modern branch governance mechanism (successor to classic branch protection). |
| Signed commit | A commit cryptographically proven to come from a specific key holder. |
| Vector DB | Database optimised for nearest-neighbour search over high-dimensional vectors. |

---

## 13. Changelog

- **2026-05-18** — Cleaned markdown formatting for lint compliance. Same content as the 05-15 revision.
- **2026-05-15** — Locked pgvector as persistent memory (replaces ChromaDB). Locked SSH-signed commits required on `main`. Added Security Posture section. Added ADR section. Documented Redis future role. Switched branch governance language from "classic protection" to "Ruleset".
- **(prior)** — Initial spec (lost to M4 reformat): vision, personality, architecture, tech stack, hardware, seven phases, folder structure, engineering practices, success criteria.
