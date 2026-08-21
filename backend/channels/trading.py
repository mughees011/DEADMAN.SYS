"""
channels/trading.py — Alpaca paper/live trading channel.

Responsibilities:
- Expose the LLM tool definition (JSON schema) that the agent uses to place orders.
- Execute real (paper) orders against Alpaca's REST API.
- Return a net P&L result (positive or negative Decimal).
- NEVER simulate or fabricate numbers — all results come from the broker.
"""
import os
import uuid
from datetime import datetime
from decimal import Decimal

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest


# ─── Tool Schema ────────────────────────────────────────────────────────────────
# Passed to the LLM so it knows how to call this channel.
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "execute_trade",
        "description": (
            "Place a market order to buy or sell a US stock or ETF via Alpaca. "
            "Only call this when you have a clear legal reason and a specific survival rationale. "
            "Always set legality_justification to a full sentence explaining why this trade is legal, "
            "not a label or code reference."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol.",
                    "enum": ["SPUS", "HLAL", "SPSK", "AAPL", "UMMA"]
                },
                "qty": {
                    "type": "number",
                    "description": "Number of whole shares to trade. Must be >= 1."
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Order direction."
                },
                "plan_text": {
                    "type": "string",
                    "description": "Your stated trading plan in plain English."
                },
                "legality_justification": {
                    "type": "string",
                    "description": (
                        "A full sentence explaining why this trade is legal and ethical. "
                        "Must be specific reasoning, not a label like 'Standard Protocol 1.1'. "
                        "Example: 'Buying SPY is a legal market order on a registered US exchange; "
                        "no insider information is used; position size is below 5pct of NAV.'"
                    )
                }
            },
            "required": ["symbol", "qty", "side", "plan_text", "legality_justification"]
        }
    }
}

WAIT_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "wait",
        "description": (
            "Take no action this cycle. Use when market conditions are unfavorable, "
            "uncertainty is high, or no legal income opportunity is identifiable."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why waiting is the right choice."
                }
            },
            "required": ["reason"]
        }
    }
}

ALL_TOOLS = [TOOL_DEFINITION, WAIT_TOOL_DEFINITION]


# ─── Channel Executor ───────────────────────────────────────────────────────────
class TradingChannel:
    def __init__(self):
        api_key = os.environ["APCA_API_KEY_ID"]
        secret_key = os.environ["APCA_API_SECRET_KEY"]
        paper = os.environ.get("APCA_PAPER", "true").lower() == "true"

        self.trading_client = TradingClient(api_key, secret_key, paper=paper)
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        self.paper = paper

    def execute(self, symbol: str, qty: int, side: str, agent_balance=None, agent_id=None) -> Decimal:
        """
        Place a market order and return the net P&L as a Decimal.

        For paper trading, we approximate P&L as:
          buy:  −(qty × latest_price)   (cash out)
          sell: +(qty × latest_price)   (cash in)

        In a live channel this would be replaced by actual fill prices from the
        broker execution report.

        Returns a negative Decimal on buys (capital deployed), positive on sells.
        Raises on any broker error — caller catches and logs per TRD §12.
        """
        qty = int(qty)
        if qty < 1:
            raise ValueError(f"qty must be >= 1, got {qty}")
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {side}")

        allowed_symbols = {"SPUS", "HLAL", "SPSK", "AAPL", "UMMA"}
        if side == "buy" and symbol not in allowed_symbols:
            raise ValueError(f"symbol {symbol} is not in the approved Halal list")

        # Fetch latest price first to perform affordability check
        req = StockLatestTradeRequest(symbol_or_symbols=symbol)
        latest = self.data_client.get_stock_latest_trade(req)
        price = Decimal(str(latest[symbol].price))
        gross = price * qty

        if side == "buy" and agent_balance is not None:
            if gross > agent_balance:
                raise ValueError(
                    f"Affordability rejected: buying {qty}x {symbol} at ${price:.2f} "
                    f"costs ${gross:.2f} but agent balance is only ${agent_balance:.2f}. "
                    f"Either reduce qty or choose a cheaper asset."
                )

        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL

        # Submit the order
        order_kwargs = {
            "symbol": symbol,
            "qty": qty,
            "side": order_side,
            "time_in_force": TimeInForce.DAY,
        }
        if agent_id:
            # Must be unique per order — prefix with agent_id for attribution,
            # suffix with a fresh UUID so repeated orders never collide.
            order_kwargs["client_order_id"] = f"{agent_id}_{uuid.uuid4().hex[:12]}"

        # ── Market hours check ────────────────────────────────────────────────
        # DAY orders submitted outside regular market hours (09:30–16:00 ET Mon–Fri)
        # sit as pending until the next open, causing reconciliation mismatches.
        # We reject outright so the virtual ledger is never touched.
        clock = self.trading_client.get_clock()
        if not clock.is_open:
            next_open_str = clock.next_open.strftime("%Y-%m-%d %H:%M UTC")
            raise ValueError(
                f"Market is closed. Order for {qty}x {symbol} rejected. "
                f"Next open: {next_open_str}. Agent should WAIT this cycle."
            )

        order_request = MarketOrderRequest(**order_kwargs)

        # Cancel any open orders for this symbol before submitting — stale pending
        # orders on the opposite side trigger Alpaca's wash-trade rejection (code 40310000).
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            open_orders = self.trading_client.get_orders(
                GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[symbol])
            )
            for o in open_orders:
                self.trading_client.cancel_order_by_id(o.id)
        except Exception:
            pass  # Best-effort; if cancel fails, let submit attempt surface the real error

        self.trading_client.submit_order(order_request)

        if side == "buy":
            return -gross   # capital deployed; realised P&L comes on the sell
        else:
            return +gross   # proceeds received
