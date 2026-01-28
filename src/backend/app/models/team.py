# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Team and agent coordination data models."""

from pydantic import BaseModel
from typing import List, Optional


class TeamAgent(BaseModel):
    """Agent reference in a team - references autonomous agent by ID"""

    agent_id: str
    role: str
    responsibilities: Optional[List[str]] = []
    mcp_access: Optional[List[str]] = []  # Optional MCP restrictions


class Coordination(BaseModel):
    """Team coordination configuration"""

    mode: str = "sequential"  # sequential, parallel, collaborative
    share_context: bool = True
    task_distribution: str = "automatic"


class Team(BaseModel):
    """Multi-agent team with shared MCP pool"""

    name: str
    description: Optional[str] = ""
    version: str = "1.0.0"
    available_mcps: List[str]  # Team MCP pool
    agents: List[TeamAgent]
    coordination: Optional[Coordination] = None
    tags: Optional[List[str]] = []
    author: Optional[str] = ""


class TeamUpdate(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    version: str = "1.0.0"
    available_mcps: List[str]
    agents: List[TeamAgent]
    coordination: Optional[Coordination] = None
    tags: Optional[List[str]] = []
    author: Optional[str] = ""
