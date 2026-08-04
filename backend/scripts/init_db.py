"""
scripts/init_db.py — One-time setup: create the first agent and seed the DB.

Run once after Phase 0 migrations have been applied:
    python scripts/init_db.py

Creates:
  - One SystemState row (kill_switch=False)
  - One "trading" Channel row
  - One Generation-0 agent named "Agent_01" with balance $0
"""
import os
import sys
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Agent, Channel, SystemState

load_dotenv()

db_url = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'survival.db')}"
)
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

# ── SystemState ───────────────────────────────────────────────────────────────
if not session.query(SystemState).first():
    session.add(SystemState(kill_switch=False, updated_by="boss"))
    print("[OK] SystemState created (kill_switch=False)")
else:
    print("[SKIP] SystemState already exists")

# ── Channels ──────────────────────────────────────────────────────────────────
if not session.query(Channel).filter_by(id="trading").first():
    session.add(Channel(
        id="trading",
        description="Alpaca stock/ETF market orders (paper mode until APCA_PAPER=false).",
        enabled=True,
    ))
    print("[OK] Channel 'trading' created")
else:
    print("[SKIP] Channel 'trading' already exists")

# ── First Agent ───────────────────────────────────────────────────────────────
if not session.query(Agent).first():
    agent = Agent(
        generation=0,
        parent_id=None,
        name="Agent_01",
        balance=Decimal("0.00"),
        tax_reserve=Decimal("0.00"),
        tax_rate=Decimal(os.environ.get("TAX_RATE", "0.150")),
        alive=True,
        paused=False,
        born_at=datetime.utcnow(),
        last_income_at=datetime.utcnow(),
    )
    session.add(agent)
    print(f"[OK] Agent_01 (Gen 0) created with balance $0.00")
    print(f"     7-day timer starts now. It has {7} days to earn its first dollar.")
else:
    print("[SKIP] Agents already exist")

session.commit()
session.close()
print("\nDone. Run `python main.py` to start the scheduler.")
