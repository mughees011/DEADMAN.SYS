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
| `litellm` | Provider-agnostic LLM interface — wraps OpenAI, Anthropic, Gemini, Groq, etc. | Default model: `claude-sonnet-4-6`. Configured via `LLM_MODEL` + provider API key in `.env`. Do not hardcode a provider. |
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
- **LLM provider** — configured via `LLM_MODEL` in `.env` (e.g. `claude-sonnet-4-6`,
  `gpt-4o`, `gemini/gemini-2.5-pro`). The matching provider API key must also be set
  (e.g. `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`). `litellm` handles routing; the agent
  core never imports a provider SDK directly. Default ships as `claude-sonnet-4-6`.
- **Alpaca** (or equivalent broker with a REST/SDK API) — `APCA_API_KEY_ID`,
  `APCA_API_SECRET_KEY`. Start in **paper trading mode** (`APCA_PAPER=true`) until the
  Boss explicitly flips it to live. This flag lives in `.env`, never in code.
- (Future channel) whatever payment/content platform is chosen when a second channel
  is added — deferred until that channel is actually scoped.

## 4a. Capital architecture (single account, virtual ledger)
- **One real Alpaca account**, funded directly by the Boss, holds all actual capital
  and executes all real orders for every agent in the system.
- **Per-agent capital is tracked virtually** in `agents.balance` (already in the
  schema) — this is bookkeeping the application enforces, not something Alpaca itself
  is aware of. Alpaca only sees one account's aggregate position and equity.
- **Order attribution**: every order placed via `TradingChannel.execute()` must be
  tagged (e.g. via Alpaca's `client_order_id`) with the initiating agent's ID, so P&L
  from that order can be correctly attributed back to that agent's ledger row. Without
  this, there is no way to know which agent's trade caused which real gain or loss.
- **Reconciliation risk to design against**: because multiple agents share one real
  account, it is possible for the sum of all agents' virtual balances to drift from the
  account's actual real equity (e.g. due to fees, slippage, or an attribution bug).
  Phase 1/2 verification must include checking that `sum(agents.balance)` reconciles
  against real Alpaca account equity, not just that individual trades look correct in
  isolation.
- **Explicitly out of scope for v1**: per-agent real sub-accounts via Alpaca's Broker
  API. Revisit only if/when the shared-ledger model's reconciliation risk becomes
  unacceptable at scale — this is a deliberate, documented simplification, not an
  oversight.

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

## 12. Error handling & outage policy
This section is non-negotiable — it governs what happens when infrastructure (LLM API
or broker API) fails mid-cycle, to prevent ambiguous money state.

**When the LLM call fails (timeout, rate-limit, API error):**
- Write one row to `agent_logs` with `error` set to the exception string.
- Do NOT touch `agents.balance`.
- Do NOT update `agents.last_income_at`.
- Abort the rest of that agent's cycle for that tick. The agent is treated as having
  taken no action (equivalent to an implicit "wait").

**When the broker/channel call fails after the LLM has already chosen an action:**
- Same rules: log the error, do not touch balance, do not update `last_income_at`.
- The legality justification and plan text are still written to the log row so the
  audit trail shows what the agent *intended* even if execution failed.

**Outages and the 7-day dead-man timer:**
- The 7-day timer is computed from real wall-clock elapsed time:
  `datetime.utcnow() - agent.last_income_at >= timedelta(days=7)`.
- It is NOT a cycle count. Switching from hourly to daily scheduling does not
  change what "7 days" means.
- API outages do **not** pause or extend the timer. A run of outages that prevents
  income for 7 real days still triggers death. This is an explicit design choice:
  the timer measures real survival, not supervised uptime. If the Boss wants to
  protect an agent during known outages, they should use the per-agent `paused` flag
  (noting that pausing also does not extend the timer — see App Flow §3).

**Death audit trail:**
- When an agent dies, `agents.balance` is floored to `0` in the database (per schema
  integrity rules in Backend Schema §4).
- However, the true negative net result (e.g. `-$42.00`) MUST be written to the
  final `agent_logs.net_result` row before the death transaction completes, so the
  audit trail accurately reflects what actually happened, not just what the floor rule
  produces. `agent_logs.net_result` may go negative; `agents.balance` may not.

**Spawn constants (v1):**
- Spawn threshold: **$500.00** — agent must hold at least this in spendable balance.
- Spawn seed cost: **$100.00** — debited atomically from parent, credited to child.
- These are `.env`-configurable (`SPAWN_THRESHOLD`, `SPAWN_SEED`) but the defaults
  above are the shipped values.
