# PRD — Survival Agent System ("Zero Means Gone")

## 1. What this is
A system of autonomous AI agents that each control a real pool of money. An agent must
generate real income through legal means it chooses itself. If its balance hits $0, or it
earns nothing for 7 straight days, it dies permanently. Surviving agents can spawn new
agents (children), becoming their overseer. One human ("the Boss") owns the whole system,
sets legal/financial guardrails, and holds an absolute kill switch.

This is not a trading bot with a personality skin — the core product is the **decision
loop**: an agent that reasons about its situation, chooses among real income channels,
justifies legality, and remembers what killed previous agents so it doesn't repeat it.

## 2. Who it's for
Single user (the Boss) running this on their own infrastructure, for their own money,
as a personal project / experiment in autonomous economic agents. Not a multi-tenant
product in v1.

## 3. Goals
- An agent can start from **$0** and must earn its first dollar itself.
- Death is real and permanent — no auto-respawn, no "continue" button. A dead agent's
  balance and identity are gone.
- Every income-generating action must be legal; the agent must be able to explain why,
  and must default to inaction ("wait") when unsure rather than guessing.
- Lessons from dead agents persist and shape the behavior of future/spawned agents
  (e.g. "don't repeat the trade sizing that killed Agent-3").
- The Boss can observe everything and halt everything, instantly, without the agent
  being able to resist or route around it.
- A percentage of every agent's net income is set aside as a tax reserve the Boss uses
  to actually file/pay taxes (the agent is not a legal or tax entity).

### 3.1 Capital model
**Decision: Option A — Boss-fronted seed capital, agent balance = net P&L ledger.**

An agent cannot place a real trade with $0 — brokerage accounts require actual capital
to exist before any order executes. So "the agent starts at $0 and earns its first
dollar itself" means:

- The Boss deposits real seed capital into **one real Alpaca account** that the Boss
  owns and controls.
- Each agent's `balance` field is a **virtual ledger** tracking that agent's net
  profit/loss against its allocated slice of that capital — not capital the agent
  itself possesses or can withdraw.
- An agent's "first dollar" is its first net-positive trade result, not its first unit
  of capital — the capital itself always belongs to, and is provided by, the Boss.
- Death (`balance <= 0`) means the agent has lost back everything it was allocated —
  its slice of the real account is effectively spent. The underlying real account isn't
  necessarily at $0; only that agent's tracked ledger is.
- Spawning transfers real capital, at the account level, from parent's allocation to a
  new ledger entry for the child — no new brokerage account is created (see TRD §4a).

This is analogous to a prop-trading desk: the trader doesn't own the capital, they own
their track record against it, and losing the allocation ends their run.

**This is inherently risky real-money exposure the Boss is accepting knowingly** — not
a limitation to be engineered away, a deliberate choice.

## 4. Non-goals (v1)
- Not building a multi-user SaaS product.
- Not automating tax filing itself — only automating the *reserve* calculation.
- Not attempting to make the agent judgment-proof or fully unsupervised — the kill
  switch and Boss oversight are permanent, non-negotiable parts of the design, not a
  temporary training-wheels phase.
- Not integrating every possible income channel on day one — v1 ships with a small,
  real set (starting with trading) and is built to add more later.

## 5. Feature list

### 5.1 Agent core
- Unique agent identity, generation number, parent link (for hierarchy).
- Real dollar balance, tracked to the cent.
- Decision cycle: on a fixed interval, the agent is given its full situation and must
  choose exactly one action (an income channel, or "wait").
- Legality justification required for every non-wait action.

### 5.2 Income channels (pluggable)
- v1: one real channel (trading via a broker API — see TRD).
- Architecture supports adding more channels (content sales, services, etc.) without
  changing the agent core.
- Each channel reports real net P&L back to the agent; no simulated numbers ever mix
  with real ones.

### 5.3 Survival & death
- Death trigger 1: balance ≤ $0.
- Death trigger 2: 7 consecutive days with $0 net income.
- Death is terminal: agent is marked dead, stops running, cannot be revived.
- On death, a lesson is generated and written to shared memory.

### 5.4 Tax reserve
- Configurable percentage (default 15%) of net positive income is moved to a reserve
  balance, separate from spendable balance, on every income event.
- Reserve is reported to the Boss; the system never files or pays taxes itself.

### 5.5 Hierarchy & spawning
- An agent whose balance clears a spawn threshold may fund a new child agent from its
  own balance.
- The parent becomes that child's overseer in the dashboard (not a control relationship
  in code — the Boss remains the only one with kill authority).
- Children are seeded with a summary of recent collective lessons.

### 5.6 Shared memory
- Every death writes a structured lesson (what channel, what action, what went wrong).
- New and spawned agents are given the most relevant recent lessons in their context.

### 5.7 Kill switch
- Boss-only, out-of-band control (a file flag / dashboard button / signal — see TRD).
- Checked at the start of every single cycle, for every agent, before any action.
- Engaging it halts all agents immediately; no agent action can disable, delay, or
  ignore it.

### 5.8 Boss dashboard
- List of all agents (alive + dead), balances, generation tree, current status.
- Full log/timeline per agent (what it decided, why, and the result).
- Collective memory / lessons feed.
- One-click kill switch (global) and per-agent pause (see App Flow).
- Tax reserve total, visible and exportable.

## 6. Success criteria for v1
- An agent can run unattended, make at least one real decision cycle per day, and
  either grow, spawn, or die according to the rules above — with zero manual
  intervention required to enforce those rules.
- The Boss can kill the entire system in under 5 seconds from the dashboard.
- Every dollar the system reports matches a real transaction in the underlying
  brokerage/payment account — no numbers are simulated once live.
