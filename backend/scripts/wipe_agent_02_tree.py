import os, sys
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Agent, AgentLog, BossNote, Lesson, Position, SystemState

db_url = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'survival.db'))
engine = create_engine(db_url)
session = sessionmaker(bind=engine)()

root = session.query(Agent).filter(Agent.name == "Agent_02").first()
if not root:
    print("Agent_02 not found!"); sys.exit(1)

def descendants(aid):
    kids = session.query(Agent).filter(Agent.parent_id == aid).all()
    result = []
    for k in kids:
        result.append(k)
        result.extend(descendants(k.id))
    return result

all_agents = [root] + descendants(root.id)
ids = [a.id for a in all_agents]
print(f"Wiping {len(ids)} agents: {[a.name for a in all_agents]}")

session.query(AgentLog).filter(AgentLog.agent_id.in_(ids)).delete(synchronize_session=False)
session.query(BossNote).filter(BossNote.agent_id.in_(ids)).delete(synchronize_session=False)
session.query(Lesson).filter(Lesson.source_agent_id.in_(ids)).delete(synchronize_session=False)
session.query(Position).filter(Position.agent_id.in_(ids)).delete(synchronize_session=False)
session.query(Agent).filter(Agent.id.in_(ids)).delete(synchronize_session=False)
print("Deleted fraudulent tree.")

fresh = Agent(
    name="Agent_02", generation=0, parent_id=None,
    balance=5000.0, tax_reserve=0.0, tax_rate=0.150,
    alive=True, paused=False,
    born_at=datetime.utcnow(), last_income_at=datetime.utcnow(), last_evaluated_at=datetime.utcnow()
)
session.add(fresh)
print("Spawned fresh Agent_02 with $5000.00.")

state = session.query(SystemState).first()
if state:
    state.kill_switch = False
    state.updated_by = "boss"
print("Kill switch disengaged.")

session.commit()
print("Done. DB is clean.")
