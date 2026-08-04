# Implementation Plan — Survival Agent System

Strict build order. Do not start a later phase before the one before it actually works
end-to-end — this project's core risk is real money moving on bad logic, so each phase
must be provably correct before the next one is layered on.

## Phase 0 — Foundations (no money, no live agent yet)
1. Set up repo structure, `.env` handling, `requirements.txt`.
2. Implement the Backend Schema (§05) with SQLAlchemy models + a migration
   tool (Alembic) so schema changes later don't require hand edits.
3. Write the `system_state` kill-switch table and a trivial script to flip it, and
   confirm reads/writes work before anything depends on it.

**Done when:** you can create/read/update every table from a Python shell manually.

## Phase 1 — Agent core loop, no real money (paper only)
1. Port the existing `agent_core.py` prototype logic onto the real DB models instead
   of the in-memory dataclass.
2. Wire the kill-switch check to read from `system_state`, not a file flag.
3. Implement death checks (balance ≤ 0, 7-day dead-man) writing to `lessons` and
   marking `agents.alive = false` atomically.
4. Implement spawn logic writing new `agents` rows with `parent_id` set.
5. Run the full loop with **Alpaca in paper mode** (`APCA_PAPER=true`) so trades are
   simulated by the broker itself but the code path is 100% identical to live.

**Done when:** an agent can run for at least one full week in paper mode, make real
(paper) trades, potentially die or spawn, and every row in `agent_logs` accurately
reflects what happened — checked by hand against Alpaca's paper dashboard.

## Phase 2 — Trading channel, live
1. Flip `APCA_PAPER=false` only after Phase 1's audit trail has been manually verified
   against the broker's own records for at least one full week.
2. Start with the smallest possible real balance you're comfortable fully losing — this
   is a live test of both the code and the agent's judgment, not the moment to fund it
   generously.
3. Watch the dashboard (Phase 4) daily for the first two weeks minimum before trusting
   it to run unattended for longer stretches.

**Done when:** at least one real dollar has moved through the system and the balance
in `agents.balance` matches Alpaca's real account balance to the cent.

## Phase 3 — Backend API (FastAPI)
1. Endpoints: list agents, get agent detail + logs, list lessons, post boss note,
   get/set kill switch, pause/unpause agent.
2. Minimal auth per Backend Schema §3.
3. No agent-facing endpoints write to `kill_switch` — enforce this at the route level,
   not just by convention.

**Done when:** every screen in the App Flow doc can be served by an existing endpoint.

## Phase 4 — Dashboard (React + Tailwind)
1. Build screens in the order the Boss will actually use them: Home/Roster → Kill
   switch control → Agent detail → Family tree → Collective memory.
2. Apply the UI/UX Design Brief tokens from the start — don't ship a default-styled
   version and restyle later.
3. Kill switch button wired last-but-tested-first: write and manually test this control
   before anything else in the dashboard, since it's the single highest-stakes UI
   element in the app.

**Done when:** the Boss can do everything in the App Flow doc through the UI, with no
manual DB queries required for day-to-day monitoring.

## Phase 5 — Hardening & unattended operation
1. Add process supervision (systemd service with auto-restart on crash — but NOT
   auto-resurrection of dead agents, which is a data operation, not a process one).
2. Add basic alerting (e.g. an email/webhook) for: kill switch engaged, any agent death,
   any channel error, scheduler crash.
3. Backup strategy for the SQLite/Postgres file — this is the only record of real
   financial activity the system produces; treat it like financial records, because it is.

**Done when:** the system can run for 30 days with zero manual intervention required
except normal Boss review, and you're confident a crash wouldn't silently lose track of
real money.

## Phase 6 — Second income channel (only after Phase 5 is stable)
1. Scope and build the next channel (content sales, a second trading strategy, etc.)
   as its own `Channel` subclass, following the exact same "paper/test → small live →
   verified → trusted" progression as Phases 1–2.
2. Do not add a second channel to make the agent's "choice" feel more real before the
   first channel has actually proven the death/spawn/memory mechanics work correctly —
   more options before the mechanics are trustworthy just multiplies the ways real
   money can be lost to a logic bug.

## Explicit ordering rules (do not skip ahead)
- No live trading before paper trading has run a full week and been manually audited.
- No dashboard before the API exists and has been tested with a script/Postman, not
  just "the UI looked right."
- No second income channel before Phase 5's 30-day unattended run is complete.
- No removing or loosening the kill switch's non-negotiable check-first-every-cycle
  behavior, at any phase, for any reason.
