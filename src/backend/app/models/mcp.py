# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""MCP server data models."""

from pydantic import BaseModel
from typing import Optional


class MCPServerInfo(BaseModel):
    name: str
    endpoint: str
    description: Optional[str] = ""
    version: str = "1.0.0"
