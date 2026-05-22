# Marvin

A locally-hosted, autonomous AI agent with a persistent personality, continuous learning, and internet access. Built from scratch on Apple Silicon.

---

## What is Marvin?

Marvin is a locally-hosted AI agent I'm building from scratch. Not a chatbot, not a wrapper around an API — a full system with its own persistent personality, memory that survives reboots, the ability to search the internet, and (eventually) a physical robot body to live in.

The core idea: everything runs on my own hardware. No cloud, no monthly bills, no data leaving my machine. Cloud is allowed only for two things: AI assistants helping me build Marvin (Claude, Claude Code as development tools), and Marvin reaching out to the internet when he needs to look something up (Tavily web search). The brain itself stays local, indefinitely, for free.

I want Marvin to feel like a continuous person — not a stateless assistant that forgets every conversation. Same personality across sessions. Real opinions. Real preferences. Real memory of what we talked about last week.

---

## Why I'm building this

I'm a junior engineer with strong fundamentals and ambitious goals. After my first developer role, I wanted to build something serious from the ground up — using the same engineering practices a senior at a large company would use, but on a project I fully own.

Marvin is that project. It forces me to learn the things juniors usually don't get exposed to:

- **System architecture across multiple layers** — LLM serving, vector memory, scheduling, HTTP APIs.
- **Real version control discipline** — signed commits, PR-only workflow, branch protection rulesets, CI/CD with required status checks.
- **Database design with security priorities** — row-level security, encrypted columns, least-privilege roles.
- **Long-term planning broken into phases**, each with clear acceptance criteria.

The goal isn't just to ship Marvin. It's to be able to walk into any technical interview and explain — in depth — every architectural decision I made and why. Every choice has an Architectural Decision Record (ADR). Every alternative I rejected is documented with reasons. If a senior engineer asks "why Postgres + pgvector and not a dedicated vector database?" — I can give the alternatives I considered and the trade-offs I accepted, in five minutes.

---

## Architecture

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

The whole system has one outbound network dependency at runtime: Tavily, for web search. Everything else — the LLM, the database, the cache, the task queue — runs locally on the deployment machine. That's a deliberate choice for privacy, control, and cost.

I'm building this in seven phases, not all at once. Phase 1 is just the brain (LLM serving + a Python wrapper). Each subsequent phase adds one layer: memory, internet, autonomy, server, personality, embodiment.

---

## Tech stack

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
| Version control                | Git + GitHub                             | locked   | All   |
| CI/CD                          | GitHub Actions                           | locked   | All   |
| Lint and format                | ruff, yamllint, markdownlint, actionlint | locked   | All   |
| Secret scanning                | gitleaks (CI + pre-commit)               | locked   | All   |

Picking these tools wasn't random. Each one is documented in [`docs/PROJECT_MARVIN_SPEC.md`](docs/PROJECT_MARVIN_SPEC.md) with the alternatives I considered. Some highlights:

- **`uv` over pip/pyenv:** modern dependency resolution, lockfile-based, dramatically faster.
- **`httpx` over `requests`:** sync today, async-ready for Phase 5 — same library, no rewrite needed when FastAPI comes in.
- **PostgreSQL + pgvector over a dedicated vector DB (Chroma, Qdrant, Weaviate):** one database, ACID guarantees, real SQL skills, single backup strategy.
- **SSH-signed commits over GPG:** same cryptographic property, far less setup ceremony.

For full reasoning on every decision, see the spec.

---

## More

The full technical specification lives at [`docs/PROJECT_MARVIN_SPEC.md`](docs/PROJECT_MARVIN_SPEC.md). It covers:

- The personality specification.
- All seven development phases in detail.
- Engineering practices (CI/CD, testing pyramid, conventional commits, branch protection rulesets).
- Security posture (threat model, controls, layered defenses).
- Architectural Decision Records for every major choice.
