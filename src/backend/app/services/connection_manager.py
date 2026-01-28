# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""WebSocket Connection Manager Service."""

from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.cancellation_flags: Dict[str, bool] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.cancellation_flags[session_id] = False
        print(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Disconnect a WebSocket client"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.cancellation_flags:
            del self.cancellation_flags[session_id]
        print(f"WebSocket disconnected: {session_id}")

    def cancel_execution(self, session_id: str):
        """Mark execution as cancelled"""
        self.cancellation_flags[session_id] = True
        print(f"Execution cancelled for session: {session_id}")

    def is_cancelled(self, session_id: str) -> bool:
        """Check if execution is cancelled"""
        return self.cancellation_flags.get(session_id, False)

    async def send_update(self, session_id: str, message: dict):
        """Send update to specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                print(f"Error sending to {session_id}: {e}")
                self.disconnect(session_id)
