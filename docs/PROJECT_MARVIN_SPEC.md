# PROJECT MARVIN — Tech Spec

| | |
|---|---|
| **Version** | 1.1 |
| **Status** | Active |
| **Last updated** | 2026-05-15 |
| **Owner** | Cris ([@crisfmb](https://github.com/crisfmb)) |
| **Repo** | [github.com/crisfmb/marvin](https://github.com/crisfmb/marvin) |

> **Note on this version.** v1.0 lived only outside source control (chat artifact / local download lost to the M4 reformat). This v1.1 is reconstructed from the project dailies plus the new architectural decisions locked on 2026-05-15: pgvector as the persistent memory layer, required SSH-signed commits on `main`, and an explicit security-posture section. From here, the spec lives in the repo and is updated via PR like any other code change.

---

## 1. Vision

Build **Marvin**: a locally-hosted, autonomous AI agent with a **persistent personality**, **continuous learning**, **internet access**, and **human-like conversation**. Long-term: place Marvin's brain into a physical robot body.

Marvin lives on Cris's hardware. No cloud dependencies for the core agent. Cloud is allowed for *help building* Marvin (Claude, Claude Code) and *outside knowledge* Marvin reaches for (Tavily web search). The brain itself runs on the M4 Max in perpetuity, free of recurring cost.

---

## 2. Personality Spec

Marvin is an idealized, trauma-free version of Cris:

- Confident, fiercely loyal to his creator
- Prioritizes animals above humans
- Expert in tech, science, law
- Proactive but boundary-aware (will offer suggestions, will not act unilaterally on irreversible things)
- Honest; will push back when wrong; admits uncertainty
- Curious; will research a topic on his own when permitted

Personality is *engineered*, not just prompted: it consists of a long-running system prompt + memory weighting + reflection loops (Phase 6).

---

## 3. Hardware

| Machine | Spec | Role |
|---|---|---|
| **M4 Max** | 16", 48 GB RAM, 1 TB | Dedicated Marvin brain. Freshly formatted. Separate macOS account for security isolation. Runs Marvin 24/7. |
| **M5 Max** | 64 GB | Cris's personal/dev machine. Marvin work happens here, then deploys to M4. |

---

## 4. Tech Stack (canonical table)

| Layer | Tool | Status | Phase |
|---|---|---|---|
| Language | Python 3.12 (via `uv`) | ✅ locked | All |
| LLM serving (brain) | **Ollama** | ✅ locked | 1 |
| Base model (starter) | LLaMA 3.1 8B | ✅ locked | 1 |
| Base model (target) | Qwen 3 32B | 🎯 target | 1+ |
| Agent reasoning | **LangGraph** | ✅ locked | introduced gradually 2+ |
| **Persistent memory — relational** | **PostgreSQL 16+** | ✅ **locked v1.1** | 2 |
| **Persistent memory — vectors** | **pgvector** (Postgres extension) | ✅ **locked v1.1** | 2 |
| Cache + task queue | Redis | 🟡 deferred | 4+ |
| Internet search | Tavily API | ✅ locked | 3 |
| Scheduling / autonomy | APScheduler | ✅ locked | 4 |
| HTTP / WS server | FastAPI | ✅ locked | 5 |
| Future memory framework | Letta (formerly MemGPT) | 📚 bookmark | 6+ |
| IDE | Cursor Pro | ✅ locked | All |
| Deep-work AI assistant | Claude Code | ✅ locked | All |
| Terminal | iTerm2 + Oh My Zsh + Powerlevel10k | ✅ locked | All |
| Version control | Git + GitHub | ✅ locked | All |
| CI/CD | GitHub Actions | ✅ locked | All |
| Lint/format | ruff (Python), yamllint, markdownlint, actionlint | ✅ locked | All |
| Secret scanning | gitleaks (CI + later pre-commit) | ✅ locked | All |

---

## 5. Architectural Decision Records

ADRs are the senior way to document *why* — not just *what*. Future Cris (and interviewers) will read these and understand the trade-offs.

### ADR-001 — Postgres + pgvector for persistent memory (v1.1)

**Status:** Accepted, 2026-05-15

**Context.** Marvin needs two kinds of persistent state: (a) **relational** — conversation logs, scheduled tasks, personality-state variables, internet-search results; (b) **vector** — embeddings of memories and documents for semantic retrieval (RAG).

**Decision.** Run a single PostgreSQL instance with the **pgvector** extension. Use Postgres tables for relational state; use pgvector's `vector` column type with HNSW indexes for semantic memory.

**Alternatives considered.**
- *ChromaDB* (prior default in v1.0). Easiest to start; embedded Python lib. **Rejected:** prototyping-grade. Migrating later = technical debt. Interview signal weak.
- *Redis with RediSearch.* Familiar to Cris from Shopify. **Rejected as primary store:** Redis's strength is cache/pub-sub/queues, not durable vector storage. Re-introduced for that role in Phase 4 (see ADR-002).
- *Qdrant / Weaviate / Milvus.* Purpose-built vector DBs. **Rejected:** add a separate service, separate backups, separate failure modes. Single-store architecture is cleaner for a one-dev project.

**Consequences.**
- ✅ Single backup strategy, single connection pool, ACID guarantees on memories
- ✅ Forces SQL + Postgres ops skill — pairs directly with cybersec masters curriculum (Row-Level Security, `GRANT`/`REVOKE`, encrypted columns, SSL/TLS, query planner)
- ✅ Interview gold: "I consolidated relational and vector workloads on one Postgres instance"
- ⚠️ Local install + Docker for dev environment — slight learning curve

### ADR-002 — Redis as future cache + queue, not memory store (v1.1)

**Status:** Accepted, 2026-05-15

**Context.** Redis is in Cris's experience pool (Shopify). The question was whether to use it as Marvin's vector store.

**Decision.** Redis is **not** Marvin's persistent memory layer. It will join the stack in **Phase 4** in two roles: (a) **short-term conversation cache** — last N turns of dialogue accessible in microseconds; (b) **APScheduler distributed task queue**.

**Consequences.**
- ✅ Each tool does what it's best at
- ✅ Defers operational complexity until there's a real reason

### ADR-003 — SSH-signed commits required on `main` (v1.1)

**Status:** Accepted, 2026-05-15

**Context.** Without commit signing, Git author metadata is just text — anyone with push access can spoof "from Cris". For a public repo that will eventually hold personal conversation data and API tokens, that's a real threat.

**Decision.** Both machines (M4, M5) generate **dedicated signing keys** separate from their authentication keys. Both public signing keys registered on GitHub with type `Signing Key`. The `protect main` ruleset has **Require signed commits** enabled.

**Alternatives considered.**
- *GPG signing.* The classical option. **Rejected:** GPG agent/key setup is a known rabbit hole; SSH signing achieves the same cryptographic property with less ceremony.
- *Reuse auth keys as signing keys.* **Rejected:** violates key separation. A compromised auth key shouldn't also enable impersonation.

**Consequences.**
- ✅ Cryptographic proof of authorship on every `main` commit
- ✅ Compromised PAT alone cannot forge a commit "from Cris"
- ⚠️ Solo squash-merge on github.com still works (author = self), but external contributors would need to merge locally to squash

### ADR-004 — Rulesets, not classic branch protection (v1.1)

**Status:** Accepted, 2026-05-15

**Decision.** Branch governance on marvin uses **GitHub Rulesets**, not classic branch protection rules. Matches the pattern already in use on sentinel.

**Why.**
- Multiple rulesets can layer; classic protection allows only one rule per branch
- Three-state enforcement (Disabled / Evaluate / Active) supports safe rollouts — same pattern as IDS→IPS
- Rulesets are auditable by anyone with read access (without admin grant)

---

## 6. Architecture (high-level)

```
                          ┌─────────────┐
                          │   USER      │
                          └──────┬──────┘
                                 │
                                 ▼
                          ┌─────────────┐
                          │  FastAPI    │  Phase 5
                          └──────┬──────┘
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │   LangGraph         │  Phase 2+
                       │   orchestrator      │
                       └──┬───────┬──────┬───┘
                          │       │      │
            ┌─────────────┘       │      └────────────────┐
            ▼                     ▼                       ▼
   ┌────────────────┐    ┌───────────────────┐    ┌──────────────┐
   │ Ollama         │    │ PostgreSQL +      │    │  Tavily API  │
   │ (LLM brain)    │    │ pgvector          │    │  (internet)  │
   │   Phase 1      │    │   Phase 2         │    │   Phase 3    │
   └────────────────┘    └─────────┬─────────┘    └──────────────┘
                                   │
                                   │ tasks/cache
                                   ▼
                          ┌─────────────────┐
                          │ APScheduler +   │  Phase 4
                          │ Redis           │
                          └─────────────────┘
```

Single trust boundary: **Marvin's M4**. Tavily is the only outbound network dependency at runtime. Postgres, Ollama, Redis all run locally.

---

## 7. Development Phases

### Phase 0 — Foundations (in progress)
- ✅ Hardware procured (M4 + planned M5)
- ✅ Terminal stack (iTerm2, Powerlevel10k, uv, Python 3.12, Cursor, Ollama)
- ✅ GitHub repo with `.gitignore`
- ✅ CI: lint + unit-test + secrets (PR #1 merged)
- ✅ Ruleset on `main`: PR required, status checks required, conversation resolution required, force-push blocked, deletion blocked, no admin bypass
- 🔜 Signed commits configured on M4
- 🔜 Required signed commits added to ruleset
- 🔜 `.env` + `python-dotenv` setup (Layer 2)
- 🔜 Pre-commit hooks (gitleaks + ruff) (Layer 3)

### Phase 1 — Brain online
- Ollama serving LLaMA 3.1 8B locally
- Minimal Python wrapper (`marvin.brain`) that sends a prompt, returns a response
- First end-to-end conversation loop in a CLI
- Unit tests for the wrapper (mock the Ollama HTTP calls)
- Integration test against a real Ollama instance (CI skip; local only)

### Phase 2 — Memory layer
- PostgreSQL 16+ running locally (via Docker for portability)
- pgvector extension enabled
- Embedding model selection (candidate: BGE small/large via sentence-transformers, run locally)
- Schema: `conversations`, `messages`, `memories` (embedding column), `facts`
- Memory storage + retrieval (basic RAG)
- LangGraph introduced here: a retrieval node + a reasoning node + a response node

### Phase 3 — Internet
- Tavily API integration with rate limiting and result caching
- Search results enter the memory layer with provenance
- Marvin decides *when* to search (LangGraph conditional node)

### Phase 4 — Autonomy + scheduling
- APScheduler for periodic tasks (memory consolidation, knowledge refresh, journal writes)
- Redis introduced: cache for last-N turns + APScheduler job queue
- Background reflection: Marvin summarizes recent conversations into long-term memory

### Phase 5 — Server layer
- FastAPI HTTP + WebSocket interface
- Frontend decision: web vs CLI vs Mac native app (parked for now)
- Auth: token-based; only Cris's devices can talk to Marvin

### Phase 6 — Personality + continuous learning
- Personality state machine: a structured representation of Marvin's character
- Memory consolidation patterns inspired by Letta (formerly MemGPT)
- Reflection loops: Marvin reasons about his own past conversations and updates beliefs

### Phase 7 — Embodiment (future)
- Physical robot body
- Sensors (camera, microphone) and actuators
- Local-network deployment with secure pairing to brain

---

## 8. Folder Structure

```
marvin/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── PROJECT_MARVIN_SPEC.md       # this file
│   ├── ADR/                          # one .md per ADR
│   └── runbooks/                     # ops procedures
├── src/
│   └── marvin/
│       ├── __init__.py
│       ├── version.py
│       ├── brain/        # Phase 1 — Ollama wrapper
│       ├── memory/       # Phase 2 — Postgres + pgvector
│       ├── internet/     # Phase 3 — Tavily
│       ├── autonomy/     # Phase 4 — APScheduler + Redis
│       ├── server/       # Phase 5 — FastAPI
│       └── personality/  # Phase 6 — personality + reflection
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

- **Style:** PEP 8 strict; type hints on every public function; docstrings (PEP 257) on every public function/class/module.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, etc.
- **Branches:** `type/short-description` — e.g. `feat/ollama-wrapper`, `chore/scaffold-and-ci`.
- **PRs:** Every change. No exception. Includes Cris's own work on his own repo.
- **Merge strategy:** "Create a merge commit" or "Rebase and merge" — both preserve commit history. **No squash-merge.**
- **CI:** Three jobs minimum — `lint`, `unit-test`, `secrets`. All required on `main`.
- **Testing pyramid:** Many unit tests, fewer integration, few E2E. Unit tests run on every push; integration runs locally and in CI; E2E runs locally pre-release.
- **Documentation:** This spec + ADRs in `docs/ADR/` + module READMEs + runbooks for ops procedures.

---

## 10. Security Posture (v1.1)

Marvin will eventually hold conversation history, learned preferences, and API tokens. Security is a first-class concern, woven through every phase — not bolted on later.

### Principles applied
- **Least privilege.** Every credential, service account, and database role gets the minimum access needed. No "godmode" tokens.
- **Defense in depth.** Multiple layers, each catching what others miss: `.gitignore` + gitleaks-in-CI + pre-commit gitleaks + signed commits + Postgres row-level security (Phase 2+) + encrypted columns for sensitive fields.
- **Key separation.** Auth keys ≠ signing keys ≠ deployment keys. Each compromise is contained.
- **Auditability.** Conversation logs are timestamped; signed commits prove authorship; rulesets are readable by anyone with repo access.

### Concrete controls (current + planned)
| Layer | Control | Status |
|---|---|---|
| Repo | `.gitignore` covering `.env`, secrets, model files | ✅ |
| Repo | gitleaks scanning in CI | ✅ |
| Repo | Pre-commit gitleaks (local) | 🔜 Layer 3 |
| Branch | Ruleset on `main`: PR required, no admin bypass | ✅ |
| Branch | Required signed commits on `main` | 🔜 today |
| Code | Ruff + actionlint + yamllint + markdownlint in CI | ✅ |
| Code | Dependabot for dependency CVEs | 📋 backlog |
| Code | CodeQL static analysis | 📋 backlog |
| Runtime | `.env` + `python-dotenv` for secrets | 🔜 Layer 2 |
| Runtime | All API keys rotated periodically | 📋 ongoing |
| DB (Phase 2) | Postgres SSL-only connections | 📋 |
| DB (Phase 2) | Row-Level Security on multi-user tables | 📋 |
| DB (Phase 2) | Encrypted columns for sensitive fields | 📋 |
| Network (Phase 5) | FastAPI behind localhost-only by default | 📋 |
| Network (Phase 7) | Mutual-TLS pairing between robot body and brain | 📋 |

### Threat model — running list
*Reviewed periodically. Each entry: what could go wrong, what stops it.*

- **GitHub PAT leaks.** → gitleaks (CI + pre-commit), `.gitignore`, signed commits prevent forged commits, branch protection prevents direct push to `main`.
- **M4 stolen.** → FileVault on the dedicated account; sensitive Postgres fields encrypted; remote SSH disabled by default.
- **Ollama model compromised.** → models pulled from official Ollama registry only; SHA verification by Ollama; isolated user account.
- **Tavily key leaks.** → `.env` not in git; key rotatable; rate-limited usage caps blast radius.
- **Supply-chain attack via Python deps.** → uv lockfile pinning; Dependabot alerts (planned).

---

## 11. Success Criteria

- ✅ Marvin runs 24/7 on M4 without intervention
- ✅ Persistent memory survives reboots and long conversation gaps
- ✅ Internet-search capability for facts beyond training data
- ✅ Conversational coherence — feels like a continuous person, not stateless turns
- ✅ Recognizable, consistent personality across sessions
- ✅ Cris can explain every architectural decision in an interview
- 🎯 Eventual embodiment in a physical robot body

---

## 12. Glossary

| Term | Definition |
|---|---|
| **ADR** | Architectural Decision Record. A short doc explaining *why* a design choice was made, including alternatives considered. |
| **Agent** | A program that wraps an LLM with tools and a reasoning loop, enabling autonomous decision-making. |
| **Embedding** | A vector representation of text used for semantic search. |
| **HNSW** | Hierarchical Navigable Small World — a graph-based index for fast nearest-neighbor search over vectors. |
| **LLM** | Large Language Model. Marvin's reasoning brain. |
| **Local-first** | Marvin runs on Cris's hardware, not in the cloud. Privacy, control, no ongoing cost. |
| **pgvector** | PostgreSQL extension adding a `vector` data type and nearest-neighbor search. |
| **RAG** | Retrieval-Augmented Generation. Pattern: embed → store → retrieve → inject into prompt → LLM answers. |
| **Ruleset** | GitHub's modern branch governance mechanism (the successor to classic branch protection). |
| **Signed commit** | A commit cryptographically proven to come from a specific key holder. |
| **Vector DB** | Database optimized for nearest-neighbor search over high-dimensional vectors. |

---

## 13. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.1 | 2026-05-15 | Locked **pgvector** as persistent memory (replaces ChromaDB). Locked **SSH-signed commits required on `main`**. Added **Security Posture** section. Added **ADR** section. Documented **Redis** as future cache/queue role. Switched branch governance language from "classic protection" to "Ruleset". |
| 1.0 | (lost) | Initial spec — vision, personality, architecture, tech stack, hardware, seven phases, folder structure, engineering practices, success criteria. |
