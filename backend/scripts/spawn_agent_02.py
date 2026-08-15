import os
import sys
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Adjust path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Agent

db_url = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(__file__)), 'survival.db')}"
)
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

# Check if Agent_02 already exists
agent = session.query(Agent).filter_by(name="Agent_02").first()
if agent:
    print("Agent_02 already exists!")
else:
    new_agent = Agent(
        name="Agent_02",
        generation=0,
        parent_id=None,
        balance=Decimal("5000.00"),
        tax_reserve=Decimal("0.00"),
        alive=True,
        born_at=datetime.utcnow(),
        last_income_at=datetime.utcnow(),
        last_evaluated_at=datetime.utcnow(),
        paused=False
    )
    session.add(new_agent)
    session.commit()
    print(f"Successfully provisioned Agent_02 (ID: {new_agent.id}, Generation: {new_agent.generation}, Parent: {new_agent.parent_id})")

session.close()
