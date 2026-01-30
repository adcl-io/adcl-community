# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Session Context Service - Manages conversation context for sessions.

Single responsibility: Load/save/summarize session context.
Follows ADCL principle: Disk-first, no hidden state.
"""

import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

from app.core.logging import get_service_logger
from app.utils.token_counter import get_token_counter

logger = get_service_logger("session_context")


def _validate_session_id(session_id: str) -> None:
    """
    Validate session_id to prevent path traversal attacks.

    Args:
        session_id: Session identifier to validate

    Raises:
        ValueError: If session_id contains invalid characters
    """
    # Allow only alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        raise ValueError(
            f"Invalid session_id '{session_id}'. "
            "Only alphanumeric characters, hyphens, and underscores are allowed."
        )


class SessionContextService:
    """
    Manages conversation context for sessions.

    Responsibilities:
    - Load context from disk (volumes/conversations/active/{session_id}/context.json)
    - Update context with execution summaries
    - Summarize and prune context to prevent token bloat
    - Clear session context

    Follows Unix philosophy: Simple text files, one directory per session.
    """

    def __init__(
        self,
        conversations_dir: Path,
        max_context_items: int = 5,
        max_context_tokens: int = 4000,
        default_model: str = "claude-sonnet-4"
    ) -> None:
        """
        Initialize SessionContextService.

        Args:
            conversations_dir: Directory for conversation persistence (volumes/conversations)
            max_context_items: Maximum number of execution summaries to keep
            max_context_tokens: Maximum total tokens allowed in context
            default_model: Model to use for token counting (default: claude-sonnet-4)
        """
        self.conversations_dir = conversations_dir
        self.max_context_items = max_context_items
        self.max_context_tokens = max_context_tokens
        self.default_model = default_model
        logger.info(f"SessionContextService initialized with directory: {conversations_dir}")

    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        Load context from disk for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with recent execution summaries and conversation history

        Example:
            >>> service = SessionContextService(Path("volumes/conversations"))
            >>> context = await service.get_context("session-123")
            >>> # Returns: {"executions": [...], "total_items": 3}

        Raises:
            ValueError: If session_id contains invalid characters
        """
        # Validate session_id to prevent path traversal
        _validate_session_id(session_id)

        context_file = self.conversations_dir / "active" / session_id / "context.json"

        # Check if context file exists
        exists = await asyncio.to_thread(context_file.exists)
        if not exists:
            logger.debug(f"No context file for session {session_id}, returning empty context")
            return {"executions": [], "total_items": 0}

        try:
            # Load context from disk
            async with aiofiles.open(context_file, "r") as f:
                content = await f.read()
                context = json.loads(content)

            logger.debug(f"Loaded context for session {session_id}: {context.get('total_items', 0)} items")
            return context

        except json.JSONDecodeError as e:
            # Backup corrupted file and return empty context
            logger.error(f"Corrupted JSON in context file for session {session_id}: {e}")
            backup_file = context_file.with_suffix(f".corrupted_{datetime.now().timestamp()}.json")
            try:
                await asyncio.to_thread(context_file.rename, backup_file)
                logger.warning(f"Backed up corrupted context to {backup_file}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted context: {backup_error}")
            return {"executions": [], "total_items": 0}

        except Exception as e:
            logger.error(f"Failed to load context for session {session_id}: {e}")
            return {"executions": [], "total_items": 0}

    async def update_context(
        self,
        session_id: str,
        execution_result: Dict[str, Any],
        user_message: str
    ) -> None:
        """
        Update context with a new execution summary.
        Automatically prunes old entries to stay within token limits.

        Args:
            session_id: Session identifier
            execution_result: Full execution result from team runtime
            user_message: Original user message that triggered this execution

        Raises:
            ValueError: If session_id contains invalid characters
            Exception: If context update fails
        """
        # Validate session_id to prevent path traversal
        _validate_session_id(session_id)

        # Ensure session directory exists
        session_dir = self.conversations_dir / "active" / session_id
        await asyncio.to_thread(session_dir.mkdir, parents=True, exist_ok=True)

        # Load existing context
        context = await self.get_context(session_id)

        # Create execution summary (not full result - too large)
        summary = self._summarize_execution(execution_result, user_message)

        # Append new summary
        executions = context.get("executions", [])
        executions.append(summary)

        # Prune to max items
        if len(executions) > self.max_context_items:
            executions = executions[-self.max_context_items:]
            logger.debug(f"Pruned context for session {session_id} to {self.max_context_items} items")

        # Prune by token count if necessary
        executions = self._prune_by_tokens(executions)

        # Update context
        updated_context = {
            "executions": executions,
            "total_items": len(executions),
            "last_updated": datetime.now().isoformat()
        }

        # Save to disk
        context_file = session_dir / "context.json"
        async with aiofiles.open(context_file, "w") as f:
            await f.write(json.dumps(updated_context, indent=2))

        logger.info(f"Updated context for session {session_id}: {len(executions)} items")

    async def clear_context(self, session_id: str) -> None:
        """
        Clear all context for a session.

        Args:
            session_id: Session identifier

        Raises:
            ValueError: If session_id contains invalid characters
        """
        # Validate session_id to prevent path traversal
        _validate_session_id(session_id)

        context_file = self.conversations_dir / "active" / session_id / "context.json"

        exists = await asyncio.to_thread(context_file.exists)
        if exists:
            await asyncio.to_thread(context_file.unlink)
            logger.info(f"Cleared context for session {session_id}")
        else:
            logger.debug(f"No context to clear for session {session_id}")

    def _summarize_execution(self, result: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """
        Create a compact summary of execution result.
        Extract key information without full reasoning/tool details.

        Args:
            result: Full execution result from team runtime
            user_message: Original user message

        Returns:
            Summarized execution data
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "status": result.get("status", "unknown"),
        }

        # Extract answer (truncate if too long)
        answer = result.get("answer", "")
        if isinstance(answer, str):
            token_counter = get_token_counter()
            # Limit each answer to 1000 tokens
            answer = token_counter.truncate_to_token_limit(answer, 1000, self.default_model)
            summary["answer"] = answer

        # Extract agent results summary (not full details)
        agent_results = result.get("agent_results", [])
        if agent_results:
            summary["agents_used"] = [
                {
                    "agent_id": ar.get("agent_id"),
                    "role": ar.get("role"),
                    "status": ar.get("status"),
                    "tools_count": len(ar.get("tools_used", []))
                }
                for ar in agent_results
            ]

        # Extract key findings (for recon/attack results)
        # Look for structured data like hosts, vulnerabilities, etc.
        if "hosts" in str(answer)[:500] or "vulnerabilities" in str(answer)[:500]:
            summary["contains_technical_findings"] = True

        return summary

    def _prune_by_tokens(self, executions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prune executions list to stay within token budget.
        Removes oldest executions first.

        Args:
            executions: List of execution summaries

        Returns:
            Pruned list within token limits
        """
        token_counter = get_token_counter()

        # Calculate total tokens
        total_text = json.dumps(executions)
        total_tokens = token_counter.count_tokens(total_text, self.default_model)

        # If within budget, return as-is
        if total_tokens <= self.max_context_tokens:
            return executions

        # Remove oldest until we're under budget
        while executions and total_tokens > self.max_context_tokens:
            executions = executions[1:]  # Remove oldest
            total_text = json.dumps(executions)
            total_tokens = token_counter.count_tokens(total_text, self.default_model)
            logger.debug(f"Pruned context: {total_tokens} tokens remaining")

        return executions

    def format_context_for_agent(self, context: Dict[str, Any]) -> str:
        """
        Format context as human-readable text for agent consumption.

        Args:
            context: Context dict from get_context()

        Returns:
            Formatted context string
        """
        executions = context.get("executions", [])

        if not executions:
            return ""

        lines = ["Previous conversation context:", ""]

        for i, exec_summary in enumerate(executions, 1):
            user_msg = exec_summary.get("user_message", "")
            answer = exec_summary.get("answer", "")
            status = exec_summary.get("status", "unknown")

            lines.append(f"## Turn {i}")
            lines.append(f"User: {user_msg}")
            lines.append(f"Status: {status}")
            if answer:
                lines.append(f"Result: {answer}")
            lines.append("")

        return "\n".join(lines)
