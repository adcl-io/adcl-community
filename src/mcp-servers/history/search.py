# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Search Engine - Handles searching across conversation history
Responsibilities:
- Title search (fast, from sessions.jsonl)
- Full-text search (slower, scans messages)
- Agent-based filtering
- Date range queries
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class SearchEngine:
    """Search conversation history"""

    def __init__(self, base_path: str = "/app/volumes/conversations"):
        self.base_path = Path(base_path)
        self.active_path = self.base_path / "active"
        self.sessions_file = self.base_path / "sessions.jsonl"

    def search_titles(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search conversation titles (fast)

        Args:
            query: Search query string
            limit: Max results

        Returns:
            List of matching session summaries
        """
        if not self.sessions_file.exists():
            return []

        query_lower = query.lower()
        matches = []

        with open(self.sessions_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    session = json.loads(line)
                    title = session.get("title", "").lower()
                    preview = session.get("preview", "").lower()

                    # Simple fuzzy match on title and preview
                    if query_lower in title or query_lower in preview:
                        # Calculate relevance score
                        score = 0
                        if query_lower in title:
                            score += 10
                        if title.startswith(query_lower):
                            score += 5
                        if query_lower in preview:
                            score += 1

                        matches.append({
                            "session": session,
                            "score": score
                        })

                except json.JSONDecodeError:
                    continue

        # Sort by relevance score
        matches.sort(key=lambda x: x["score"], reverse=True)

        return [m["session"] for m in matches[:limit]]

    def search_messages(self, query: str,
                       session_id: Optional[str] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None,
                       message_type: Optional[str] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """
        Full-text search across messages

        Args:
            query: Search query string
            session_id: Optional - limit to specific session
            date_from: Optional - ISO date string
            date_to: Optional - ISO date string
            message_type: Optional - filter by message type
            limit: Max results

        Returns:
            List of matching messages with context
        """
        query_lower = query.lower()
        matches = []

        # Determine which sessions to search
        if session_id:
            sessions_to_search = [session_id]
        else:
            sessions_to_search = self._get_all_active_sessions()

        # Search each session
        for sid in sessions_to_search:
            session_dir = self.active_path / sid
            messages_file = session_dir / "messages.jsonl"

            if not messages_file.exists():
                continue

            with open(messages_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        msg = json.loads(line)

                        # Apply filters
                        if message_type and msg.get("type") != message_type:
                            continue

                        # Date range filter
                        if date_from or date_to:
                            msg_timestamp = msg.get("timestamp")
                            if msg_timestamp:
                                if date_from and msg_timestamp < date_from:
                                    continue
                                if date_to and msg_timestamp > date_to:
                                    continue

                        # Text search
                        content = str(msg.get("content", "")).lower()
                        if query_lower in content:
                            # Calculate relevance
                            score = content.count(query_lower)

                            matches.append({
                                "session_id": sid,
                                "message": msg,
                                "score": score
                            })

                            if len(matches) >= limit:
                                break

                    except json.JSONDecodeError:
                        continue

            if len(matches) >= limit:
                break

        # Sort by relevance
        matches.sort(key=lambda x: x["score"], reverse=True)

        return matches[:limit]

    def search_by_agent(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find conversations where a specific agent participated

        Args:
            agent_name: Agent name/type
            limit: Max results

        Returns:
            List of session summaries
        """
        matching_sessions = []

        for session_dir in self.active_path.iterdir():
            if not session_dir.is_dir():
                continue

            metadata_file = session_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                metadata = json.loads(metadata_file.read_text())
                participants = metadata.get("participants", {})

                if agent_name in participants:
                    matching_sessions.append(metadata)

                if len(matching_sessions) >= limit:
                    break

            except Exception:
                continue

        return matching_sessions

    def _get_all_active_sessions(self) -> List[str]:
        """Get list of all active session IDs"""
        sessions = []

        if not self.active_path.exists():
            return sessions

        for session_dir in self.active_path.iterdir():
            if session_dir.is_dir():
                sessions.append(session_dir.name)

        return sessions
