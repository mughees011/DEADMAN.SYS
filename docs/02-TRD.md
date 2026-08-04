# TRD — Survival Agent System

Everything an implementer (human or AI) needs so no tool, library, or API is guessed.

## 1. Language & runtime
- **Python 3.11+** for the agent core, scheduler, and channel integrations.
- **Node.js 20+** only for the dashboard frontend (see §6).
- Runs on a single Linux server/VPS the Boss controls (e.g. a $5–10/mo VPS is enough
  for v1). Not containerized in v1 unless the Boss wants Docker — optional, not required.

## 2. Core dependencies (Python)
| Package | Purpose | Notes |
|---|---|---|
| `anthropic` | Agent decision-making via Claude, tool-use | Model: `claude-sonnet-4-6` |
| `alpaca-py` | Real stock/ETF trading | Official Alpaca SDK |
| `sqlalchemy` | ORM for the backend schema | See Backend Schema doc |
| `psycopg2-binary` | Postgres driver | Or `sqlite3` (stdlib) for single-VPS v1 |
| `apscheduler` | Running each agent's decision cycle on a schedule | Alternative: system cron |
| `python-dotenv` | Loading API keys/secrets from `.env` | Never hardcode keys |
| `fastapi` + `uvicorn` | Backend API for the dashboard | |
| `pydantic` | Request/response validation for the API | Ships with FastAPI |

## 3. Core dependencies (Dashboard frontend)
| Package | Purpose |
|---|---|
| `react` + `vite` | Dashboard SPA |
| `tailwindcss` | Styling — tokens defined in UI/UX Design Brief |
| `recharts` | Balance/history charts |
| `lucide-react` | Icons |

## 4. External APIs / accounts required
- **Anthropic API** — `ANTHROPIC_API_KEY`. Used for every agent decision cycle
  (tool-use call as already prototyped in `agent_core.py`).
- **Alpaca** (or equivalent broker with a REST/SDK API) — `APCA_API_KEY_ID`,
  `APCA_API_SECRET_KEY`. Start in **paper trading mode** (`paper=True`) until the Boss
  explicitly flips it to live. This flag lives in `.env`, never in code.
- (Future channel) whatever payment/content platform is chosen when a second channel
  is added — deferred until that channel is actually scoped.

## 5. Data storage
- **v1**: SQLite file on the server (`survival.db`). Simple, no extra service to run.
- **Later, if needed**: swap to Postgres via the same SQLAlchemy models — no schema
  redesign required, just a connection string change.
- Full table definitions live in `05-Backend-Schema.md` — this TRD does not duplicate them.

## 6. Process architecture
```
┌─────────────┐      cycle tick       ┌──────────────────┐
│ Scheduler    │ ───────────────────▶ │ Agent Core Loop   │
│ (APScheduler)│                       │ (agent_core.py)   │
└─────────────┘                       └───────┬───────────┘
                                               │ tool-use call
                                               ▼
                                       ┌──────────────────┐
                                       │ Anthropic API      │
                                       │ (decision + reason) │
                                       └───────┬───────────┘
                                               │ chosen action
                                               ▼
                                       ┌──────────────────┐
                                       │ Channel (Alpaca…) │
                                       └───────┬───────────┘
                                               │ real $ result
                                               ▼
                                       ┌──────────────────┐
                                       │ SQLite / Postgres │
                                       └───────┬───────────┘
                                               │
                                               ▼
                                       ┌──────────────────┐
                                       │ FastAPI backend   │◀── Boss dashboard (React)
                                       └──────────────────┘
```

## 7. Kill switch mechanism
- Implemented as a row in the database (`system_state.kill_switch = true/false`),
  not a file flag, once the dashboard exists (the file-flag version in the prototype
  was a placeholder for before the DB existed).
- Checked by the scheduler **before dispatching any cycle** — if true, no agent code
  runs at all that tick, for any agent.
- The dashboard's kill switch button calls a single FastAPI endpoint that flips this
  value; no agent-facing code path can write to it.

## 8. Scheduling
- One cycle per agent per interval — default **daily**, configurable per deployment.
  (The 7-day dead-man timer assumes daily-or-more-frequent cycles; if you space cycles
  further apart than daily, re-check that the timer still makes sense.)
- APScheduler cron trigger in-process, or a system cron job calling a `run_once.py`
  entrypoint — either is acceptable; pick one and be consistent.

## 9. Security & secrets
- All keys in `.env`, loaded via `python-dotenv`, `.env` in `.gitignore`.
- Broker API keys scoped to the minimum permission level Alpaca allows (trading only,
  no withdrawal permission if the broker supports separating those).
- Dashboard behind basic auth or a single hardcoded Boss login for v1 — this is a
  single-user tool, not a public product; do not over-build auth here (see Backend
  Schema §Auth for the actual minimal shape).

## 10. Logging
- Every agent decision (input situation, chosen tool, tool input, real result) written
  to the `agent_logs` table (see Backend Schema) — this is the audit trail, not just
  console output.
- Standard Python `logging` module to stdout/file for operational logs (crashes,
  scheduler issues) — separate from the agent decision audit trail.

## 11. What is explicitly NOT in v1 scope
- No multi-server/distributed deployment.
- No Docker requirement (optional convenience only).
- No additional income channels beyond trading until v1 trading is proven end-to-end
  on paper, then live, with real observed behavior.
