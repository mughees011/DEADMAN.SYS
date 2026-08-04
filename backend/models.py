import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UUID, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Agent(Base):
    __tablename__ = 'agents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation = Column(Integer, nullable=False, default=0)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=True)
    name = Column(String, nullable=False)
    balance = Column(Numeric(12, 2), nullable=False)
    tax_reserve = Column(Numeric(12, 2), nullable=False, default=0)
    tax_rate = Column(Numeric(4, 3), nullable=False, default=0.150)
    alive = Column(Boolean, nullable=False, default=True)
    paused = Column(Boolean, nullable=False, default=False)
    born_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    died_at = Column(DateTime, nullable=True)
    cause_of_death = Column(Text, nullable=True)
    last_income_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    parent = relationship("Agent", remote_side=[id], backref="children")
    logs = relationship("AgentLog", back_populates="agent")
    lessons = relationship("Lesson", back_populates="source_agent")
    notes = relationship("BossNote", back_populates="agent")


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String, primary_key=True)
    description = Column(Text, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)


class AgentLog(Base):
    __tablename__ = 'agent_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False)
    cycle_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    situation_snapshot = Column(JSON, nullable=False)
    chosen_channel = Column(String, ForeignKey('channels.id'), nullable=True)
    plan_text = Column(Text, nullable=False)
    legality_justification = Column(Text, nullable=False)
    net_result = Column(Numeric(12, 2), nullable=True)
    tax_deducted = Column(Numeric(12, 2), nullable=True)
    error = Column(Text, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="logs")
    channel = relationship("Channel")


class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    text = Column(Text, nullable=False)

    # Relationships
    source_agent = relationship("Agent", back_populates="lessons")


class BossNote(Base):
    __tablename__ = 'boss_notes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    text = Column(Text, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="notes")


class SystemState(Base):
    __tablename__ = 'system_state'

    id = Column(Integer, primary_key=True)  # single-row sentinel
    kill_switch = Column(Boolean, nullable=False, default=False)
    kill_switch_set_at = Column(DateTime, nullable=True)
    updated_by = Column(String, nullable=False, default="boss")