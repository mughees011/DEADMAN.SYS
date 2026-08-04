import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import SystemState

def toggle():
    # We must use the absolute path or run it from the backend dir so the DB is created in the right place
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'survival.db')
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()

    state = session.query(SystemState).first()
    if not state:
        state = SystemState(kill_switch=False)
        session.add(state)
        session.commit()
    
    # Toggle it
    state.kill_switch = not state.kill_switch
    session.commit()
    
    print(f"Kill switch is now: {'ENGAGED' if state.kill_switch else 'DISENGAGED'}")

if __name__ == "__main__":
    toggle()
