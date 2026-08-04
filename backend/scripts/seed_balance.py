"""
scripts/seed_balance.py — One-time Boss action to seed Agent_01 with starting capital.

Run ONCE before the verification week starts:
    python scripts/seed_balance.py

This is the Boss's initial deposit into the system — equivalent to the spawn seed
but for the Gen-0 agent who has no parent to fund it.
"""
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Agent, AgentLog
from datetime import datetime

load_dotenv()

SEED_AMOUNT = Decimal("200.00")

db_url = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'survival.db')}"
)
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

agent = session.query(Agent).filter_by(generation=0, alive=True).first()
if not agent:
    print("[ERROR] No alive Gen-0 agent found. Run init_db.py first.")
    sys.exit(1)

if agent.balance > 0:
    print(f"[SKIP] Agent '{agent.name}' already has balance ${agent.balance:.2f}. Not re-seeding.")
    sys.exit(0)

# Credit balance
agent.balance = SEED_AMOUNT

# Log it as a boss deposit so the audit trail is complete
log_row = AgentLog(
    agent_id=agent.id,
    cycle_at=datetime.utcnow(),
    situation_snapshot={"event": "boss_seed", "amount": str(SEED_AMOUNT)},
    chosen_channel=None,
    plan_text=f"Boss deposited initial seed capital of ${SEED_AMOUNT:.2f} to start the paper-trading verification week.",
    legality_justification="Boss action — not a trade. No legality check required.",
    net_result=SEED_AMOUNT,
    tax_deducted=Decimal("0.00"),
    error=None,
)
session.add(log_row)
session.commit()

# Capture values before closing the session
agent_name = agent.name
final_balance = agent.balance
session.close()

print(f"[OK] Agent '{agent_name}' seeded with ${SEED_AMOUNT:.2f}")
print(f"     Verification week clock starts NOW ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})")
print(f"     The agent has 7 real days to earn income before the dead-man timer fires.")
print(f"\n     Run: python main.py")
