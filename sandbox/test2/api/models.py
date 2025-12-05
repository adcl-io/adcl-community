# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class CampaignMode(str, Enum):
    """Campaign execution mode"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class CampaignStatus(str, Enum):
    """Campaign execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(str, Enum):
    """Vulnerability severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Persona Configuration Models

class PersonaConfig(BaseModel):
    """Configuration for an agent persona"""
    system_prompt: str
    mcp_servers: List[str]
    llm_model: str = "claude-sonnet-4"
    temperature: float = 0.5
    max_tasks: int = 10
    timeout_minutes: int = 30


class TeamMember(BaseModel):
    """Team member definition for a campaign"""
    persona: str
    count: int = 1
    config: PersonaConfig


class SafetyConfig(BaseModel):
    """Safety configuration for campaign"""
    require_approval_for: List[str] = Field(default_factory=list)
    max_concurrent_agents: int = 5
    global_timeout_hours: int = 8


# Campaign Models

class CampaignCreate(BaseModel):
    """Request model for creating a campaign"""
    name: str
    target: str
    mode: CampaignMode = CampaignMode.SEQUENTIAL
    team: List[TeamMember]
    safety: Optional[SafetyConfig] = None


class Campaign(BaseModel):
    """Campaign data model"""
    id: UUID = Field(default_factory=uuid4)
    name: str
    target: str
    mode: CampaignMode
    status: CampaignStatus = CampaignStatus.PENDING
    team: List[TeamMember]
    safety: Optional[SafetyConfig]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class CampaignResponse(BaseModel):
    """Response model for campaign"""
    id: UUID
    name: str
    target: str
    status: CampaignStatus
    mode: CampaignMode
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


# Agent Models

class AgentCreate(BaseModel):
    """Request model for creating an agent"""
    campaign_id: UUID
    persona: str
    config: PersonaConfig


class Agent(BaseModel):
    """Agent data model"""
    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    persona: str
    config: PersonaConfig
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tasks_completed: int = 0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class AgentResponse(BaseModel):
    """Response model for agent"""
    id: UUID
    campaign_id: UUID
    persona: str
    status: AgentStatus
    created_at: datetime
    tasks_completed: int


# Finding Models

class FindingCreate(BaseModel):
    """Request model for creating a finding"""
    campaign_id: UUID
    agent_id: UUID
    title: str
    description: str
    severity: FindingSeverity
    target_host: str
    target_port: Optional[int] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    remediation: Optional[str] = None


class Finding(BaseModel):
    """Finding/vulnerability data model"""
    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID
    agent_id: UUID
    title: str
    description: str
    severity: FindingSeverity
    target_host: str
    target_port: Optional[int] = None
    evidence: Dict[str, Any]
    remediation: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class FindingResponse(BaseModel):
    """Response model for finding"""
    id: UUID
    campaign_id: UUID
    agent_id: UUID
    title: str
    description: str
    severity: FindingSeverity
    target_host: str
    target_port: Optional[int]
    discovered_at: datetime


# WebSocket Message Models

class WSMessageType(str, Enum):
    """WebSocket message types"""
    CAMPAIGN_STATUS = "campaign_status"
    AGENT_STATUS = "agent_status"
    FINDING = "finding"
    LOG = "log"
    ERROR = "error"


class WSMessage(BaseModel):
    """WebSocket message structure"""
    type: WSMessageType
    campaign_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]


# Task Queue Models

class TaskType(str, Enum):
    """Types of tasks for agents"""
    RECON = "recon"
    EXPLOIT = "exploit"
    POST_EXPLOIT = "post_exploit"
    REPORT = "report"


class AgentTask(BaseModel):
    """Task for an agent to execute"""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    campaign_id: UUID
    task_type: TaskType
    target: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
