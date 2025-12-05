# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
History MCP Server
Provides conversation history management as MCP tools
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for base_server import
sys.path.insert(0, str(Path(__file__).parent.parent))

from base_server import BaseMCPServer
from session_manager import SessionManager
from message_writer import MessageWriter
from message_reader import MessageReader
from search import SearchEngine
from indexer import IndexBuilder
from wal import WALManager


class HistoryMCPServer(BaseMCPServer):
    """
    History MCP Server
    Tools: create_session, append_message, get_messages, search_history, etc.
    """

    def __init__(self, port: int = 7004, storage_path: str = "/app/volumes/conversations"):
        super().__init__(
            name="history",
            port=port,
            description="Conversation History MCP Server - Store and retrieve chat history"
        )

        self.storage_path = storage_path

        # Initialize modules
        self.session_manager = SessionManager(storage_path)
        self.message_writer = MessageWriter(storage_path)
        self.message_reader = MessageReader(storage_path)
        self.search_engine = SearchEngine(storage_path)
        self.index_builder = IndexBuilder(storage_path)
        self.wal_manager = WALManager(storage_path)

        # Recover from WAL on startup
        recovery_result = self.wal_manager.recover_from_wal()
        if recovery_result["recovered_count"] > 0:
            print(f"[{self.name}] Recovered {recovery_result['recovered_count']} entries from WAL")

        # Register history tools
        self._register_history_tools()

    def _register_history_tools(self):
        """Register all history management tools"""

        # Session management tools
        self.register_tool(
            name="create_session",
            handler=self.create_session,
            description="Create a new conversation session",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Optional session title"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata (tags, etc.)"
                    }
                }
            }
        )

        self.register_tool(
            name="get_session",
            handler=self.get_session,
            description="Get session metadata",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    }
                },
                "required": ["session_id"]
            }
        )

        self.register_tool(
            name="list_sessions",
            handler=self.list_sessions,
            description="List conversation sessions",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max number of sessions (default: 50)"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of sessions to skip (default: 0)"
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status: 'active' or 'archived'"
                    }
                }
            }
        )

        # Message management tools
        self.register_tool(
            name="append_message",
            handler=self.append_message,
            description="Append a message to a conversation",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    },
                    "message_type": {
                        "type": "string",
                        "description": "Message type (user, agent, tool, system)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata (agent name, tools used, etc.)"
                    }
                },
                "required": ["session_id", "message_type", "content"]
            }
        )

        self.register_tool(
            name="get_messages",
            handler=self.get_messages,
            description="Get messages from a conversation with pagination",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max messages to return (default: 50)"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Messages to skip (default: 0)"
                    },
                    "reverse": {
                        "type": "boolean",
                        "description": "Return newest first (default: true)"
                    }
                },
                "required": ["session_id"]
            }
        )

        self.register_tool(
            name="get_message",
            handler=self.get_message,
            description="Get a specific message by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message ID"
                    }
                },
                "required": ["session_id", "message_id"]
            }
        )

        # Search tools
        self.register_tool(
            name="search_titles",
            handler=self.search_titles,
            description="Search conversation titles",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default: 50)"
                    }
                },
                "required": ["query"]
            }
        )

        self.register_tool(
            name="search_messages",
            handler=self.search_messages,
            description="Full-text search across messages",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional - limit to specific session"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default: 100)"
                    }
                },
                "required": ["query"]
            }
        )

        # Maintenance tools
        self.register_tool(
            name="rebuild_index",
            handler=self.rebuild_index,
            description="Rebuild message index for a session",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    }
                },
                "required": ["session_id"]
            }
        )

        self.register_tool(
            name="cleanup_empty_sessions",
            handler=self.cleanup_empty_sessions,
            description="Archive empty sessions (0 messages) older than specified hours",
            input_schema={
                "type": "object",
                "properties": {
                    "max_age_hours": {
                        "type": "integer",
                        "description": "Maximum age in hours for empty sessions (default: 1)"
                    }
                }
            }
        )

    # Tool implementations

    async def create_session(self, title: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create new conversation session"""
        try:
            session_id = self.session_manager.create_session(title, metadata)
            return {
                "success": True,
                "session_id": session_id,
                "title": title or f"Conversation {session_id[:8]}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session metadata"""
        session = self.session_manager.get_session(session_id)
        if session:
            return {"success": True, "session": session}
        return {"success": False, "error": "Session not found"}

    async def list_sessions(self, limit: int = 50, offset: int = 0,
                          status: Optional[str] = None) -> Dict[str, Any]:
        """List conversation sessions"""
        try:
            sessions = self.session_manager.list_sessions(limit, offset, status)
            return {
                "success": True,
                "count": len(sessions),
                "sessions": sessions
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def append_message(self, session_id: str, message_type: str,
                           content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Append message to conversation"""
        try:
            # Auto-create session if it doesn't exist (graceful degradation)
            session = self.session_manager.get_session(session_id)
            if not session:
                self.session_manager.create_session(
                    title=f"Session {session_id[:8]}",
                    metadata=metadata or {},
                    session_id=session_id
                )
            
            message = {
                "type": message_type,
                "content": content
            }
            if metadata:
                message.update(metadata)

            message_id = self.message_writer.append_message(session_id, message)

            return {
                "success": True,
                "message_id": message_id,
                "session_id": session_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_messages(self, session_id: str, limit: int = 50,
                         offset: int = 0, reverse: bool = True) -> Dict[str, Any]:
        """Get messages from conversation"""
        try:
            messages = self.message_reader.get_messages(session_id, offset, limit, reverse)
            formatted = self._format_messages(messages)
            return {
                "success": True,
                "count": len(messages),
                "messages": messages,
                "formatted": formatted,
                "session_id": session_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages as text for agent prompts"""
        if not messages:
            return ""
        
        lines = []
        for msg in messages:
            role = msg.get("type", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines) + "\n"

    async def get_message(self, session_id: str, message_id: str) -> Dict[str, Any]:
        """Get specific message"""
        message = self.message_reader.get_message_by_id(session_id, message_id)
        if message:
            return {"success": True, "message": message}
        return {"success": False, "error": "Message not found"}

    async def search_titles(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search conversation titles"""
        try:
            results = self.search_engine.search_titles(query, limit)
            return {
                "success": True,
                "count": len(results),
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def search_messages(self, query: str, session_id: Optional[str] = None,
                            limit: int = 100) -> Dict[str, Any]:
        """Full-text search messages"""
        try:
            results = self.search_engine.search_messages(query, session_id=session_id, limit=limit)
            return {
                "success": True,
                "count": len(results),
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def rebuild_index(self, session_id: str) -> Dict[str, Any]:
        """Rebuild message index"""
        try:
            index = self.index_builder.build_message_index(session_id)
            return {
                "success": True,
                "message_count": index.get("message_count", 0)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def cleanup_empty_sessions(self, max_age_hours: int = 1) -> Dict[str, Any]:
        """Clean up empty sessions older than specified hours"""
        try:
            result = self.session_manager.cleanup_empty_sessions(max_age_hours)
            return {
                "success": True,
                **result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    storage = os.getenv("HISTORY_STORAGE", "/app/volumes/conversations")
    port = int(os.getenv("HISTORY_PORT", "7004"))
    server = HistoryMCPServer(port=port, storage_path=storage)
    server.run()
