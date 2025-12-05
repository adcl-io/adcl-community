# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
from uuid import uuid4
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./redteam.db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Session factory
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


# Enums matching Pydantic models
class CampaignStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatusEnum(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverityEnum(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CampaignModeEnum(str, enum.Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


# Database Models

class CampaignDB(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    target = Column(String, nullable=False)
    mode = Column(SQLEnum(CampaignModeEnum), nullable=False, default=CampaignModeEnum.SEQUENTIAL)
    status = Column(SQLEnum(CampaignStatusEnum), nullable=False, default=CampaignStatusEnum.PENDING)
    team_config = Column(JSON, nullable=False)  # Stores team configuration
    safety_config = Column(JSON, nullable=True)  # Stores safety configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    agents = relationship("AgentDB", back_populates="campaign", cascade="all, delete-orphan")
    findings = relationship("FindingDB", back_populates="campaign", cascade="all, delete-orphan")


class AgentDB(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    persona = Column(String, nullable=False)
    config = Column(JSON, nullable=False)  # Stores PersonaConfig
    status = Column(SQLEnum(AgentStatusEnum), nullable=False, default=AgentStatusEnum.IDLE)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    tasks_completed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Relationships
    campaign = relationship("CampaignDB", back_populates="agents")
    findings = relationship("FindingDB", back_populates="agent", cascade="all, delete-orphan")


class FindingDB(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(FindingSeverityEnum), nullable=False)
    target_host = Column(String, nullable=False)
    target_port = Column(Integer, nullable=True)
    evidence = Column(JSON, default=dict)
    remediation = Column(Text, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("CampaignDB", back_populates="findings")
    agent = relationship("AgentDB", back_populates="findings")


# Database utility functions

async def get_db():
    """Dependency to get database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await engine.dispose()
