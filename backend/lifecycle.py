"""
lifecycle.py — Survival rule enforcement for the agent system.

Responsibilities (all run AFTER a cycle's channel result is known):
  1. Tax reserve deduction on any positive net income.
  2. Death check A: balance <= 0 after result.
  3. Death check B: 7 real days elapsed since last_income_at.
  4. Spawn check: balance >= SPAWN_THRESHOLD.

All monetary operations that touch multiple rows use a single DB transaction.
See TRD §12 for the full rules (balance floor, audit trail, spawn constants).
"""
import os
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from models import Agent, AgentLog, Lesson

log = logging.getLogger(__name__)

SPAWN_THRESHOLD = Decimal(os.environ.get("SPAWN_THRESHOLD", "500.00"))
SPAWN_SEED = Decimal(os.environ.get("SPAWN_SEED", "100.00"))
DEAD_MAN_DAYS = 7


def apply_income_result(
    session: Session,
    agent: Agent,
    log_row: AgentLog,
    net_result: Decimal,
) -> None:
    """
    Apply a completed channel result to the agent.
    Handles tax reserve, balance update, death and spawn checks atomically.

    Args:
        session:    Active SQLAlchemy session (caller owns commit/rollback).
        agent:      The Agent ORM object (already loaded in session).
        log_row:    The AgentLog row for this cycle (already added to session,
                    not yet committed). We set net_result and tax_deducted here.
        net_result: Real net P&L from the channel (may be negative).
    """
    # ── 1. Tax reserve ────────────────────────────────────────────────────────
    tax_deducted = Decimal("0.00")
    if net_result > 0:
        tax_deducted = (net_result * Decimal(str(agent.tax_rate))).quantize(Decimal("0.01"))
        agent.tax_reserve += tax_deducted
        net_after_tax = net_result - tax_deducted
    else:
        net_after_tax = net_result

    # ── 2. Write true P&L to audit trail BEFORE applying the floor ────────────
    # TRD §12: net_result in agent_logs may go negative; agents.balance may not.
    log_row.net_result = net_result
    log_row.tax_deducted = tax_deducted

    # ── 3. Update balance ─────────────────────────────────────────────────────
    new_balance = agent.balance + net_after_tax

    # ── 4. Update last_income_at if positive income ───────────────────────────
    if net_result > 0:
        agent.last_income_at = datetime.utcnow()

    # ── 5. Death check A: balance <= 0 ────────────────────────────────────────
    if new_balance <= 0:
        agent.balance = Decimal("0.00")  # floor per schema rule
        _kill_agent(session, agent, cause=f"Balance hit {new_balance:.2f} after trade.")
        return

    agent.balance = new_balance

    # ── 6. Death check B: 7-day dead-man (strict wall-clock) ────────────────────
    days_since_income = datetime.utcnow() - agent.last_income_at
    if days_since_income >= timedelta(days=DEAD_MAN_DAYS):
        _kill_agent(
            session,
            agent,
            cause=f"No income for {days_since_income.days} real days (dead-man threshold: {DEAD_MAN_DAYS}).",
        )
        return

    # ── 7. Spawn check ────────────────────────────────────────────────────────
    if agent.balance >= SPAWN_THRESHOLD:
        _try_spawn(session, agent)


def check_deadman_only(session: Session, agent: Agent) -> bool:
    """
    Run only the 7-day dead-man check (used on cycles where the agent chose 'wait'
    or an error occurred — no balance change, but death can still trigger).
    Returns True if agent was killed.
    """
    days_since_income = datetime.utcnow() - agent.last_income_at
    if days_since_income >= timedelta(days=DEAD_MAN_DAYS):
        _kill_agent(
            session,
            agent,
            cause=f"No income for {days_since_income.days} real days (dead-man threshold: {DEAD_MAN_DAYS}).",
        )
        return True
    return False


def _kill_agent(session: Session, agent: Agent, cause: str) -> None:
    """
    Atomically mark an agent dead and write its final lesson.
    Called within an existing session; caller must commit.
    """
    if not agent.alive:
        return  # guard: never write twice

    log.warning("Agent %s DIED: %s", agent.name, cause)

    agent.alive = False
    agent.died_at = datetime.utcnow()
    agent.cause_of_death = cause

    lesson = Lesson(
        source_agent_id=agent.id,
        text=(
            f"Agent {agent.name} (Gen {agent.generation}) died. Cause: {cause} "
            f"Final balance was ${agent.balance:.2f}. "
            f"Last income: {agent.last_income_at.strftime('%Y-%m-%d %H:%M UTC')}."
        ),
    )
    session.add(lesson)
    log.info("Lesson written for dead agent %s.", agent.name)


def _try_spawn(session: Session, parent: Agent) -> None:
    """
    Spawn a child agent funded from the parent's balance.
    Parent balance is debited and child is created in one atomic block.
    """
    if parent.balance < SPAWN_THRESHOLD:
        return  # race guard

    # Debit parent first — if anything below fails, SQLAlchemy rolls back
    parent.balance -= SPAWN_SEED

    # Gather recent lessons for the seed context
    recent_lessons = (
        session.query(Lesson)
        .order_by(Lesson.created_at.desc())
        .limit(10)
        .all()
    )
    lesson_summary = "\n".join(f"- {l.text}" for l in recent_lessons) or "No lessons yet."

    child_name = f"{parent.name}_C{int(datetime.utcnow().timestamp())}"
    child = Agent(
        generation=parent.generation + 1,
        parent_id=parent.id,
        name=child_name,
        balance=SPAWN_SEED,
        tax_reserve=Decimal("0.00"),
        tax_rate=parent.tax_rate,
        alive=True,
        paused=False,
        born_at=datetime.utcnow(),
        last_income_at=datetime.utcnow(),
        last_evaluated_at=datetime.utcnow(),
    )
    session.add(child)

    log.info(
        "Agent %s spawned child %s with seed $%s. Parent balance now $%s.",
        parent.name, child_name, SPAWN_SEED, parent.balance,
    )
