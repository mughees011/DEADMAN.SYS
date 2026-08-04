# App Flow — Survival Agent System

Describes every user (Boss) journey and what happens on each action. No feature exists
in the app unless it's mapped here to a trigger and a result.

## 1. First-time setup (one-time, CLI/manual — no UI needed for this part)
1. Boss provisions a VPS.
2. Boss creates `.env` with `ANTHROPIC_API_KEY`, `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`,
   `APCA_PAPER=true`.
3. Boss runs a one-time init script: creates the SQLite DB, creates tables (see Backend
   Schema), inserts the first agent (generation 0, "the Boss's first agent") with
   balance = $0.
4. Boss starts the scheduler process (`systemd` service or `screen`/`tmux` session
   running `main.py`).
5. Dashboard is started separately (`uvicorn` + built React app) and Boss logs in.

## 2. Daily automated cycle (no Boss action required — this is the core loop)
1. Scheduler wakes up for a due agent.
2. **Kill switch check.** If engaged → cycle aborts immediately, nothing else in this
   list happens, log entry written ("skipped: kill switch engaged").
3. Agent's current state loaded (balance, days since income, recent memory/lessons).
4. Agent core calls Anthropic API with full situation + available channel tools.
5. Agent returns exactly one action: a channel + plan + legality justification, or "wait".
6. If a channel action:
   a. Channel executes the real API call (e.g. Alpaca order).
   b. Real net result recorded.
   c. Tax reserve % deducted from any positive net, moved to `tax_reserve` balance.
   d. Balance updated.
   e. If net > 0, `last_income_at` reset to now.
7. **Death check A**: balance ≤ 0 → agent marked dead, lesson generated and written to
   shared memory, all future cycles for this agent skipped permanently.
8. **Death check B**: 7 days since `last_income_at` → same as above.
9. **Spawn check**: balance ≥ spawn threshold → new child agent row created, seeded
   with recent lessons, funded from parent's balance; parent's balance decreased
   accordingly.
10. Full cycle (situation, decision, result, any death/spawn) written to `agent_logs`.

## 3. Boss opens the dashboard
1. Boss logs in (single-user auth, §Backend Schema).
2. **Home view**: list of all agents — alive first, then dead — each showing name,
   generation, balance, tax reserve, days since income, status badge.
3. Clicking an agent → **Agent detail view**: full chronological log of every cycle
   (situation summary → decision → justification → real result), a balance-over-time
   chart, and (if dead) the lesson it generated.
4. **Family tree view**: agents rendered by generation/parent link, so the Boss can see
   who spawned whom.
5. **Memory view**: full list of lessons from all dead agents, most recent first.
6. **Kill switch**: a single, unmissable control (not buried in a menu). Clicking it:
   a. Shows a confirmation ("This stops every agent immediately. Continue?").
   b. On confirm, flips `system_state.kill_switch` to true via one API call.
   c. Dashboard immediately shows a persistent banner: "SYSTEM HALTED" until Boss
      turns it back off from the same control.
7. **Per-agent pause** (lighter than global kill switch): Boss can pause one agent
   without stopping the whole system — sets that agent's `paused` flag, scheduler
   skips only that agent until unpaused. This does not extend its 7-day timer — a
   paused agent that runs out of the dead-man window still dies, so pausing is not a
   way to cheat the survival rule; it's for the Boss to freeze-and-inspect only.

## 4. Boss adds Boss notes (guidance, not override)
1. From an agent's detail view, Boss can add a short text note.
2. Note is stored and included in that agent's next decision-cycle context (as seen in
   the `boss_notes` parameter already in `agent_core.py`).
3. This is advisory only — it cannot force a specific action; it shapes the agent's
   reasoning the same way a lesson does.

## 5. Agent dies
1. Death triggers per §2 steps 7–8, no Boss action needed.
2. Dashboard reflects the status change on next load/poll; dead agents are visually
   distinct (see UI/UX brief) and cannot be reactivated by anyone, including the Boss —
   that's a deliberate design constraint, not a missing feature.

## 6. Agent spawns a child
1. Trigger per §2 step 9, no Boss action needed.
2. New agent appears in the dashboard's list and family tree on next load.
3. Boss can view it exactly like any other agent going forward.
