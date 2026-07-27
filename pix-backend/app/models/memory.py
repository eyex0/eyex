"""SQLAlchemy models for memory system."""
from __future__ import annotations

from sqlalchemy import Uuid, JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.types import JSONBCompat
from app.models.base import Base


class AgentMemoryRecord(Base):
    __tablename__ = "agent_memory_records"
    org_id = Column(Uuid, nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONBCompat, default={})
    importance = Column(Float, default=0.5)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    org_id = Column(Uuid, nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONBCompat, default={})


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"
    org_id = Column(Uuid, nullable=False, index=True)
    agent_id = Column(String(255), nullable=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSONBCompat, default=None)
    importance = Column(Float, default=0.5)
    memory_type = Column(String(50), default="long_term")
    metadata_ = Column("metadata", JSONBCompat, default={})
