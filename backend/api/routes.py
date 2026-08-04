import logging
import os
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from pydantic import BaseModel

from models import Agent, AgentLog, SystemState, Lesson, BossNote
from api.auth import get_current_user, verify_credentials, create_session_token, COOKIE_NAME
from api.schemas import (
    LoginRequest, LoginResponse, SystemStateResponse, AgentResponse,
    AgentLogResponse, LessonResponse, BossNoteRequest
)

db_url = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'survival.db')}"
)
engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)

# ── Auth Endpoints ────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, response: Response):
    if verify_credentials(req.username, req.password):
        token = create_session_token()
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=30 * 24 * 3600,
        )
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Logged out"}


# ── Protected Endpoints ───────────────────────────────────────────────────────

@router.get("/system/state", response_model=SystemStateResponse)
def get_system_state(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    state = db.query(SystemState).first()
    if not state:
        raise HTTPException(status_code=500, detail="SystemState not initialized")
    
    alive_agents = db.query(Agent).filter(Agent.alive == True).count()
    dead_agents = db.query(Agent).filter(Agent.alive == False).count()
    total_balance = db.query(func.sum(Agent.balance)).filter(Agent.alive == True).scalar() or 0
    total_tax_reserve = db.query(func.sum(Agent.tax_reserve)).filter(Agent.alive == True).scalar() or 0
    
    return {
        "kill_switch": state.kill_switch,
        "kill_switch_set_at": state.kill_switch_set_at,
        "updated_by": state.updated_by,
        "alive_agents": alive_agents,
        "dead_agents": dead_agents,
        "total_balance": total_balance,
        "total_tax_reserve": total_tax_reserve,
    }


class KillSwitchToggle(BaseModel):
    engaged: bool

@router.post("/system/kill-switch")
def toggle_kill_switch(req: KillSwitchToggle, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    state = db.query(SystemState).first()
    if not state:
        raise HTTPException(status_code=500, detail="SystemState not initialized")
    
    state.kill_switch = req.engaged
    state.kill_switch_set_at = datetime.utcnow() if req.engaged else None
    state.updated_by = current_user
    db.commit()
    return {"status": "success", "kill_switch": state.kill_switch}


@router.get("/agents", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return db.query(Agent).order_by(Agent.generation.asc(), Agent.born_at.asc()).all()


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: UUID, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/agents/{agent_id}/logs", response_model=List[AgentLogResponse])
def get_agent_logs(agent_id: UUID, limit: int = 50, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    logs = db.query(AgentLog).filter(AgentLog.agent_id == agent_id).order_by(AgentLog.cycle_at.desc()).limit(limit).all()
    return logs


@router.post("/agents/{agent_id}/pause")
def toggle_pause(agent_id: UUID, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.alive:
        raise HTTPException(status_code=400, detail="Cannot pause a dead agent")
    
    agent.paused = not agent.paused
    db.commit()
    return {"status": "success", "paused": agent.paused}


@router.get("/memory", response_model=List[LessonResponse])
def get_memory(limit: int = 50, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return db.query(Lesson).order_by(Lesson.created_at.desc()).limit(limit).all()


@router.post("/notes")
@router.post("/agents/{agent_id}/notes")
def add_boss_note(req: BossNoteRequest, agent_id: Optional[UUID] = None, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    note = BossNote(
        agent_id=agent_id,
        text=req.text,
    )
    db.add(note)
    db.commit()
    return {"status": "success", "note_id": note.id}
