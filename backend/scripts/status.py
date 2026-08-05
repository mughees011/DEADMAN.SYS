import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Agent, AgentLog

db_url = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'survival.db')}"
)
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

print("="*60)
print("DEADMAN.SYS - Verification Week Status")
print("="*60)

agent = session.query(Agent).filter_by(alive=True).first()
if not agent:
    print("[!] NO ALIVE AGENT FOUND")
else:
    print(f"Agent:   {agent.name} (Gen {agent.generation})")
    print(f"Balance: ${agent.balance:.2f}")
    
    days_since_income = (datetime.utcnow() - agent.last_income_at).days
    print(f"Status:  {7 - days_since_income} days remaining on Dead-Man timer")
    
    if agent.paused:
        print("State:   PAUSED")
    else:
        print("State:   ACTIVE")

print("\n" + "-"*60)
print("Latest 5 Logs (Most recent at bottom):")
print("-"*60)

logs = session.query(AgentLog).order_by(AgentLog.cycle_at.desc()).limit(5).all()
for log in reversed(logs):
    time_str = log.cycle_at.strftime('%Y-%m-%d %H:%M')
    action = log.chosen_channel or "WAIT"
    
    if log.error:
        print(f"[{time_str}] ERROR: {log.error}")
        continue
        
    if action == "WAIT":
        print(f"[{time_str}] WAIT")
        print(f"    Reason: {log.plan_text}")
    else:
        net = f"+${log.net_result:.2f}" if log.net_result > 0 else f"-${abs(log.net_result):.2f}"
        print(f"[{time_str}] TRADE ({net})")
        print(f"    Plan: {log.plan_text}")
        print(f"    Legality: {log.legality_justification}")
    print("")

session.close()
