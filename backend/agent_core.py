"""
agent_core.py — Main decision loop for a single agent cycle.

Flow per cycle (see App Flow §2 for the authoritative description):
  1. Kill switch check (abort immediately if engaged).
  2. Guard: skip if agent is dead or paused.
  3. Build situation snapshot (balance, days-since-income, lessons, boss notes).
  4. Call LLM via litellm with the channel tools.
  5. Parse the tool call: either execute_trade or wait.
  6. If execute_trade:
       a. Run the Alpaca channel.
       b. On broker success → apply_income_result (tax, death, spawn).
       c. On broker error  → log error, do NOT touch balance (TRD §12).
  7. If wait: check dead-man timer only.
  8. On LLM error: log error, do NOT touch balance (TRD §12).
  9. Write AgentLog row (always, even on error).

The legality_justification from the LLM is REQUIRED and is validated before
the trade is executed. A label like "Standard Protocol 1.1" is rejected.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest

import litellm
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Agent, AgentLog, BossNote, Lesson, SystemState
from channels.trading import TradingChannel, ALL_TOOLS
from lifecycle import apply_income_result, check_deadman_only

load_dotenv()
log = logging.getLogger(__name__)

LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

# Minimum length for legality_justification to be considered non-trivial.
MIN_JUSTIFICATION_CHARS = 60

SYSTEM_PROMPT = """\
You are an autonomous trading agent in the DEADMAN.SYS survival system.

Rules you must never break:
1. You must generate real income to survive. Your balance must stay above $0.
   If your balance hits $0 or you earn nothing for 7 consecutive real days, you die permanently.
2. Every trade must be LEGAL. You must explain why in legality_justification using a full,
   specific sentence — not a label, not a code. Example of VALID justification:
   "Buying SPY via a market order on a registered US exchange using only publicly available
   price data; no insider information, no manipulation, position is < 5% of NAV."
3. When in doubt, choose wait(). An unexplained trade is worse than no trade.
4. You have access to one channel: execute_trade (Alpaca stock/ETF market orders, paper mode).
5. You must call exactly ONE tool per cycle: either execute_trade or wait.
6. Use the standard JSON tool calling format provided by the API. DO NOT output raw text tags like `<function=wait>`.

Your survival depends on your decisions. Think carefully.\
"""


def _get_db_session() -> tuple:
    """Return (engine, Session factory). Uses DATABASE_URL env or defaults to local survival.db."""
    db_url = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(__file__), 'survival.db')}"
    )
    engine = create_engine(db_url)
    return engine, sessionmaker(bind=engine)


def reconcile_positions(session: Session) -> None:
    from models import Agent, Position, SystemState
    import os
    from collections import defaultdict
    from alpaca.trading.client import TradingClient
    
    if os.environ.get("BYPASS_RECONCILIATION", "false").lower() == "true":
        return

    # 1. Fetch Alpaca current state first
    api_key = os.environ["APCA_API_KEY_ID"]
    secret_key = os.environ["APCA_API_SECRET_KEY"]
    paper = os.environ.get("APCA_PAPER", "true").lower() == "true"
    client = TradingClient(api_key, secret_key, paper=paper)
    
    try:
        acct = client.get_account()
        alpaca_cash_now = float(acct.cash)
        alpaca_positions = {}
        for pos in client.get_all_positions():
            alpaca_positions[pos.symbol] = float(pos.qty)
    except Exception as e:
        log.warning(f"Reconciliation skip: Failed to fetch Alpaca account: {e}")
        return

    # 2. Load or initialise baselines in SystemState
    state = session.query(SystemState).first()
    if state and state.alpaca_cash_baseline is None:
        # First run — calibrate baselines from current reality
        agents = session.query(Agent).all()
        state.alpaca_cash_baseline = alpaca_cash_now
        state.agents_balance_baseline = float(sum(a.balance + a.tax_reserve for a in agents))
        session.commit()
        session.refresh(state)
        log.info(
            "Reconciliation baselines initialised: Alpaca cash $%.2f, agents sum $%.2f",
            state.alpaca_cash_baseline, state.agents_balance_baseline
        )
        return  # Nothing to compare yet on first run

    alpaca_baseline = state.alpaca_cash_baseline if state.alpaca_cash_baseline is not None else alpaca_cash_now
    agents_baseline = state.agents_balance_baseline if state.agents_balance_baseline is not None else 5000.0

    # 3. Virtual sums
    agents = session.query(Agent).all()
    virtual_cash = float(sum(a.balance + a.tax_reserve for a in agents))
    virtual_pnl = virtual_cash - agents_baseline

    alpaca_pnl = alpaca_cash_now - alpaca_baseline
    
    virtual_positions = defaultdict(float)
    positions = session.query(Position).all()
    for pos in positions:
        virtual_positions[pos.symbol] += pos.qty

    # 4. Check tolerances (allow $1.00 for rounding; fractional shares not in use)
    errors = []
    if abs(virtual_pnl - alpaca_pnl) > 1.00:
        errors.append(
            f"Cash mismatch: Virtual PnL ${virtual_pnl:.2f} != Alpaca PnL ${alpaca_pnl:.2f} "
            f"(baselines: agents ${agents_baseline:.2f}, alpaca ${alpaca_baseline:.2f})"
        )

    all_symbols = set(virtual_positions.keys()) | set(alpaca_positions.keys())
    for sym in all_symbols:
        v_qty = virtual_positions.get(sym, 0.0)
        a_qty = alpaca_positions.get(sym, 0.0)
        if abs(v_qty - a_qty) > 1e-6:
            errors.append(f"Position mismatch {sym}: Virtual {v_qty} != Alpaca {a_qty}")

    # 5. Trigger Kill Switch
    if errors:
        state.kill_switch = True
        state.kill_switch_set_at = datetime.utcnow()
        state.updated_by = "system_reconciliation"
        session.commit()
        log.critical("RECONCILIATION FAILED. KILL SWITCH ENGAGED. Errors: %s", " | ".join(errors))
        raise RuntimeError("Reconciliation failed. Halting.")


def _build_situation(agent: Agent, session: Session, market_snapshot_text: str, positions_text: str = "") -> str:
    """Construct the human-readable situation snapshot passed to the LLM."""
    days_since_income = (datetime.utcnow() - agent.last_income_at).days

    # Recent lessons (up to 5)
    lessons = (
        session.query(Lesson)
        .order_by(Lesson.created_at.desc())
        .limit(5)
        .all()
    )
    lessons_text = "\n".join(f"  • {l.text}" for l in lessons) or "  (none yet)"

    # Boss notes for this agent (last 3)
    boss_notes = (
        session.query(BossNote)
        .filter((BossNote.agent_id == agent.id) | (BossNote.agent_id.is_(None)))
        .order_by(BossNote.created_at.desc())
        .limit(3)
        .all()
    )
    notes_text = "\n".join(f"  • {n.text}" for n in boss_notes) or "  (none)"

    # Last cycle log (to prevent repeating mistakes)
    last_log = (
        session.query(AgentLog)
        .filter_by(agent_id=agent.id)
        .order_by(AgentLog.cycle_at.desc())
        .first()
    )
    last_cycle_text = "  (No previous cycles)"
    if last_log:
        if last_log.error:
            last_cycle_text = f"  • FAILED: {last_log.error}"
        elif last_log.chosen_channel:
            last_cycle_text = f"  • SUCCESS: {last_log.plan_text} (Result: ${last_log.net_result})"
        else:
            last_cycle_text = f"  • WAITED: {last_log.plan_text}"

    return f"""\
AGENT STATUS
  Name:              {agent.name}
  Generation:        {agent.generation}
  Spendable balance: ${agent.balance:.2f}
  Tax reserve:       ${agent.tax_reserve:.2f}
  Days since income: {days_since_income} / 7 (die at 7)
  Alive:             {agent.alive}

OPEN POSITIONS (assets you currently hold and CAN sell):
{positions_text or "  (none)"}

MARKET SNAPSHOT (current prices):
{market_snapshot_text or "  (No market data available)"}

LAST CYCLE RESULT:
{last_cycle_text}

RECENT COLLECTIVE LESSONS (from dead agents):
{lessons_text}

BOSS NOTES (advisory — not orders):
{notes_text}

STRATEGY REMINDER: If your spendable balance is too low to buy anything, consider selling
an open position to realise its P&L. Selling returns cash to your spendable balance.

You must now choose exactly one action: execute_trade or wait.\
"""


def _validate_justification(justification: str) -> bool:
    """
    Reject trivially short or obviously label-like justifications.
    A real sentence must be at least MIN_JUSTIFICATION_CHARS characters and
    must not be a single word or obvious template string.
    """
    if not justification or len(justification.strip()) < MIN_JUSTIFICATION_CHARS:
        return False
    # Reject if it looks like a code/label (no spaces = single token)
    if " " not in justification.strip():
        return False
    return True


def run_agent_cycle(agent_id, session: Session) -> None:
    """Run one full decision cycle for the given agent."""
    agent = session.query(Agent).filter_by(id=agent_id).first()
    if agent is None:
        log.error("run_agent_cycle: agent_id %s not found.", agent_id)
        return

    # ── Guard: skip dead or paused agents ────────────────────────────────────
    if not agent.alive:
        log.debug("Skipping dead agent %s.", agent.name)
        return
    if agent.paused:
        log.info("Agent %s is paused — skipping cycle (dead-man timer still runs).", agent.name)
        # Still check dead-man even while paused — pausing is not a cheat (App Flow §3)
        check_deadman_only(session, agent)
        session.commit()
        return

    # ── Fetch Market Snapshot & Open Positions ───────────────────────────────
    market_snapshot_text = ""
    positions_text = ""
    snapshot_data = {}
    positions_data = {}
    try:
        api_key = os.environ["APCA_API_KEY_ID"]
        secret_key = os.environ["APCA_API_SECRET_KEY"]
        paper = os.environ.get("APCA_PAPER", "true").lower() == "true"
        data_client = StockHistoricalDataClient(api_key, secret_key)
        trading_client = TradingClient(api_key, secret_key, paper=paper)

        # Fetch current prices for watchlist
        symbols = ["SPY", "QQQ", "AAPL", "GLD"]
        req = StockLatestTradeRequest(symbol_or_symbols=symbols)
        latest_trades = data_client.get_stock_latest_trade(req)

        price_lines = []
        for sym, trade in latest_trades.items():
            price = trade.price
            snapshot_data[sym] = float(price)
            price_lines.append(f"  • {sym}: ${price:.2f}")
        market_snapshot_text = "\n".join(price_lines)

        # Fetch virtual positions from local database
        from models import Position
        positions = session.query(Position).filter_by(agent_id=agent.id).all()
        pos_lines = []
        for pos in positions:
            sym = pos.symbol
            qty = float(pos.qty)
            if qty <= 0:
                continue
            
            market_val = 0.0
            if sym in snapshot_data:
                market_val = qty * snapshot_data[sym]
                
            positions_data[sym] = {"qty": qty, "market_value": market_val}
            pos_lines.append(
                f"  • {sym}: {qty} shares, current market value ~${market_val:.2f} "
                f"(unrealized P&L not tracked locally)"
            )
        positions_text = "\n".join(pos_lines) if pos_lines else "  (none)"

    except Exception as data_err:
        log.error("Failed to fetch market data for agent %s: %s", agent.name, data_err)
        # TRD §12 & Phase 1.5: Broker failure -> log error, do not touch balance, skip decision
        log_row = AgentLog(
            agent_id=agent.id,
            cycle_at=datetime.utcnow(),
            situation_snapshot={},
            plan_text="(Market data fetch failed — no action taken)",
            legality_justification="(N/A)",
            error=str(data_err),
        )
        session.add(log_row)
        check_deadman_only(session, agent)
        session.commit()
        return

    # ── Build situation snapshot ──────────────────────────────────────────────
    situation = _build_situation(agent, session, market_snapshot_text, positions_text)
    snapshot = {
        "balance": str(agent.balance),
        "tax_reserve": str(agent.tax_reserve),
        "days_since_income": (datetime.utcnow() - agent.last_income_at).days,
        "last_income_at": agent.last_income_at.isoformat(),
        "market_data": snapshot_data,
        "open_positions": positions_data,
    }

    # Pre-build the log row (we always write it, even on error — TRD §12)
    log_row = AgentLog(
        agent_id=agent.id,
        cycle_at=datetime.utcnow(),
        situation_snapshot=snapshot,
        plan_text="",
        legality_justification="",
    )
    session.add(log_row)

    # ── LLM call ─────────────────────────────────────────────────────────────
    response = None
    last_err = None
    for attempt in range(3):
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": situation},
            ]
            response = litellm.completion(
                model=LLM_MODEL,
                messages=messages,
                tools=ALL_TOOLS,
                tool_choice="auto",
            )
            break  # Success
        except Exception as llm_err:
            last_err = llm_err
            log.warning("LLM call attempt %d failed for agent %s: %s", attempt + 1, agent.name, llm_err)

    if not response:
        # TRD §12: LLM failure → log error, do not touch balance or last_income_at
        log.error("All LLM call attempts failed for agent %s: %s", agent.name, last_err)
        log_row.error = str(last_err)
        log_row.plan_text = "(LLM error — no action taken)"
        log_row.legality_justification = "(N/A)"
        check_deadman_only(session, agent)
        session.commit()
        return

    # ── Parse tool call ───────────────────────────────────────────────────────
    message = response.choices[0].message
    if not message.tool_calls:
        # Model replied in plain text instead of calling a tool — treat as wait
        plain_text = message.content or ""
        log.warning("Agent %s returned no tool call (plain text): %s", agent.name, plain_text[:200])
        log_row.plan_text = f"(no tool call) {plain_text[:500]}"
        log_row.legality_justification = "(no tool call — treated as wait)"
        log_row.error = "Model returned plain text instead of a tool call."
        agent.last_evaluated_at = datetime.utcnow()
        check_deadman_only(session, agent)
        session.commit()
        return

    tool_call = message.tool_calls[0]
    tool_name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        log.error("Failed to parse LLM tool args for agent %s: %s", agent.name, e)
        log_row.error = f"JSON parse error: {e}"
        log_row.plan_text = "(parse error)"
        log_row.legality_justification = "(N/A)"
        check_deadman_only(session, agent)
        session.commit()
        return

    # ── Handle: wait ──────────────────────────────────────────────────────────
    if tool_name == "wait":
        reason = args.get("reason", "")
        log.info("Agent %s chose WAIT: %s", agent.name, reason)
        log_row.chosen_channel = None
        log_row.plan_text = f"WAIT — {reason}"
        log_row.legality_justification = "(wait — no action)"
        agent.last_evaluated_at = datetime.utcnow()
        check_deadman_only(session, agent)
        session.commit()
        return

    # ── Handle: execute_trade ─────────────────────────────────────────────────
    if tool_name == "execute_trade":
        symbol = args.get("symbol", "").upper()
        qty = int(args.get("qty", 0))
        side = args.get("side", "")
        plan_text = args.get("plan_text", "")
        justification = args.get("legality_justification", "")

        log_row.chosen_channel = "trading"
        log_row.plan_text = plan_text
        log_row.legality_justification = justification

        # ── Validate justification ────────────────────────────────────────────
        if not _validate_justification(justification):
            err_msg = (
                f"Rejected trade: legality_justification too short or label-like "
                f"({len(justification)} chars). Trade aborted."
            )
            log.warning("Agent %s: %s", agent.name, err_msg)
            log_row.error = err_msg
            agent.last_evaluated_at = datetime.utcnow()
            check_deadman_only(session, agent)
            session.commit()
            return

        # ── Validate sell ownership ───────────────────────────────────────────
        if side == "sell":
            pos = session.query(Position).filter_by(agent_id=agent.id, symbol=symbol).first()
            if not pos or pos.qty < qty:
                err_msg = (
                    f"Rejected trade: Cannot sell {qty} shares of {symbol}. "
                    f"Agent owns {pos.qty if pos else 0} shares."
                )
                log.warning("Agent %s: %s", agent.name, err_msg)
                log_row.error = err_msg
                agent.last_evaluated_at = datetime.utcnow()
                check_deadman_only(session, agent)
                session.commit()
                return

        # ── Execute channel ───────────────────────────────────────────────────
        try:
            channel = TradingChannel()
            net_result = channel.execute(
                symbol=symbol,
                qty=qty,
                side=side,
                agent_balance=agent.balance,
                agent_id=agent.id,
            )
            
            if log_row.situation_snapshot is None:
                log_row.situation_snapshot = {}
            new_snap = dict(log_row.situation_snapshot)
            new_snap["executed_trade"] = {"symbol": symbol, "qty": qty, "side": side}
            log_row.situation_snapshot = new_snap
            
            log.info(
                "Agent %s traded %s %s x%d → net $%s",
                agent.name, side, symbol, qty, net_result,
            )
        except Exception as broker_err:
            # TRD §12: broker failure → log error, do not touch balance
            log.error("Broker error for agent %s: %s", agent.name, broker_err)
            log_row.error = str(broker_err)
            check_deadman_only(session, agent)
            session.commit()
            return

        # ── Apply survival rules (tax, death, spawn) ──────────────────────────
        agent.last_evaluated_at = datetime.utcnow()
        apply_income_result(session, agent, log_row, net_result)
        session.commit()
        return

    # ── Unknown tool ──────────────────────────────────────────────────────────
    log.error("Agent %s called unknown tool '%s'.", agent.name, tool_name)
    log_row.error = f"Unknown tool: {tool_name}"
    log_row.plan_text = "(unknown tool)"
    log_row.legality_justification = "(N/A)"
    agent.last_evaluated_at = datetime.utcnow()
    check_deadman_only(session, agent)
    session.commit()


def run_all_cycles() -> None:
    """
    Entry point called by the scheduler.
    Checks kill switch first, then runs one cycle per alive agent.
    """
    _, SessionFactory = _get_db_session()
    session = SessionFactory()

    try:
        # ── Kill switch — checked BEFORE any agent code runs ──────────────────
        state = session.query(SystemState).first()
        if state and state.kill_switch:
            log.warning("Kill switch is ENGAGED — all cycles aborted this tick.")
            return

        # ── Reconciliation Check ──────────────────────────────────────────────────
        try:
            reconcile_positions(session)
        except RuntimeError:
            return  # Kill switch engaged, abort this tick

        alive_agents = session.query(Agent).filter_by(alive=True).all()
        log.info("Starting cycle tick: %d alive agent(s).", len(alive_agents))

        for agent in alive_agents:
            try:
                run_agent_cycle(agent.id, session)
            except Exception as e:
                # Catch-all: one agent crashing must not stop others
                log.exception("Unhandled error in cycle for agent %s: %s", agent.name, e)
                session.rollback()

    finally:
        session.close()
