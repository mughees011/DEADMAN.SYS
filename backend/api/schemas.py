from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str

class SystemStateResponse(BaseModel):
    kill_switch: bool
    kill_switch_set_at: Optional[datetime]
    updated_by: str
    alive_agents: int
    dead_agents: int
    total_balance: Decimal
    total_tax_reserve: Decimal

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    generation: int
    parent_id: Optional[UUID]
    name: str
    balance: Decimal
    tax_reserve: Decimal
    tax_rate: Decimal
    alive: bool
    paused: bool
    born_at: datetime
    died_at: Optional[datetime]
    last_income_at: datetime
    last_evaluated_at: Optional[datetime]
    cause_of_death: Optional[str]

class AgentLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agent_id: UUID
    cycle_at: datetime
    situation_snapshot: dict
    chosen_channel: Optional[str]
    plan_text: str
    legality_justification: str
    net_result: Optional[Decimal]
    tax_deducted: Optional[Decimal]
    error: Optional[str]

class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_agent_id: Optional[UUID]
    text: str
    created_at: datetime

class BossNoteRequest(BaseModel):
    text: str
