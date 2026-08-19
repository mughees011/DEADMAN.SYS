"""
reset_baselines.py — Reset SystemState baselines to match current live reality.
Run this any time the kill switch has been manually reviewed and cleared,
or whenever the DB and Alpaca account have been manually reconciled.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import SystemState, Agent
from alpaca.trading.client import TradingClient

db_url = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'survival.db'))
session = sessionmaker(bind=create_engine(db_url))()

# 1. Fetch real Alpaca state
api_key = os.environ['APCA_API_KEY_ID']
secret_key = os.environ['APCA_API_SECRET_KEY']
paper = os.environ.get('APCA_PAPER', 'true').lower() == 'true'
client = TradingClient(api_key, secret_key, paper=paper)
acct = client.get_account()
alpaca_cash = float(acct.cash)
alpaca_positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
print(f"Alpaca cash: ${alpaca_cash:.2f}")
print(f"Alpaca open positions: {alpaca_positions or 'None'}")

# 2. Fetch virtual state
agents = session.query(Agent).all()
virtual_sum = float(sum(float(a.balance) + float(a.tax_reserve) for a in agents))
print(f"Virtual sum (balance+tax_reserve): ${virtual_sum:.2f}")
for a in agents:
    print(f"  {a.name}: balance=${float(a.balance):.2f}, tax_reserve=${float(a.tax_reserve):.2f}, alive={a.alive}")

# 3. Check positions match
from models import Position
from collections import defaultdict
virtual_pos = defaultdict(float)
for pos in session.query(Position).all():
    virtual_pos[pos.symbol] += pos.qty
print(f"Virtual positions: {dict(virtual_pos) or 'None'}")

# 4. Sanity check before committing
errors = []
all_symbols = set(virtual_pos.keys()) | set(alpaca_positions.keys())
for sym in all_symbols:
    v = virtual_pos.get(sym, 0.0)
    a = alpaca_positions.get(sym, 0.0)
    if abs(v - a) > 1e-6:
        errors.append(f"Position mismatch {sym}: Virtual={v} Alpaca={a}")

if errors:
    print("\nCANNOT reset baselines — position mismatch detected:")
    for e in errors:
        print(f"  {e}")
    print("Resolve this first (flatten or correct position rows), then re-run.")
    sys.exit(1)

# 5. Commit new baselines
state = session.query(SystemState).first()
state.kill_switch = False
state.updated_by = 'boss'
state.alpaca_cash_baseline = alpaca_cash
state.agents_balance_baseline = virtual_sum
session.commit()
print(f"\nBaselines reset:")
print(f"  alpaca_cash_baseline    = ${alpaca_cash:.2f}")
print(f"  agents_balance_baseline = ${virtual_sum:.2f}")
print("Kill switch: OFF")
print("Done.")
