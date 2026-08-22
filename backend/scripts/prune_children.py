import os
import sys
from datetime import datetime

# Setup path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Agent, Loan
from lifecycle import _kill_agent

def main():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'survival.db')
    db_url = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    parent = session.query(Agent).filter_by(name='Agent_02').first()
    if not parent:
        print('Agent_02 not found.')
        return
        
    alive_children = session.query(Agent).filter_by(parent_id=parent.id, alive=True).all()
    print(f'Agent_02 has {len(alive_children)} alive children.')
    
    if len(alive_children) <= 5:
        print('No pruning needed.')
        return
        
    # Sort by balance descending (richest first) so we keep the most successful ones
    alive_children.sort(key=lambda c: c.balance, reverse=True)
    
    children_to_keep = alive_children[:5]
    children_to_prune = alive_children[5:]
    
    print(f'Keeping top 5 richest children.')
    print(f'Pruning {len(children_to_prune)} children...')
    
    total_recovered = 0
    
    for child in children_to_prune:
        print(f' - Pruning {child.name} (Balance: ${child.balance:.2f})')
        
        # Transfer balance back to parent
        recovered = child.balance
        parent.balance += recovered
        child.balance = 0
        total_recovered += recovered
        
        # Write off any outstanding loans owed to parent
        loans = session.query(Loan).filter_by(
            lender_id=parent.id, 
            borrower_id=child.id, 
            written_off_at=None
        ).all()
        for loan in loans:
            if loan.outstanding > 0:
                loan.written_off_at = datetime.utcnow()
                
        # Mark as dead
        _kill_agent(session, child, cause='Pruned by administrator to enforce max-5 children limit.')
        
    session.commit()
    print(f'\nPruning complete! Recovered ${total_recovered:.2f} back to Agent_02.')
    print(f'Agent_02 new balance: ${parent.balance:.2f}')

if __name__ == '__main__':
    main()
