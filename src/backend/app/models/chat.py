# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Chat message data models."""

from pydantic import BaseModel
from typing import List, Dict, Optional


class ChatMessage(BaseModel):
    team_id: str
    message: str
    history: List[Dict[str, str]] = []
    agent_id: Optional[str] = None  # Optional: Select specific agent
    model_id: Optional[str] = None  # Optional: Override model selection
