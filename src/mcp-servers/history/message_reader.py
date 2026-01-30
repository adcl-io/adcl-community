# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Message Reader - Handles efficient reading of conversation messages
Responsibilities:
- Efficient message retrieval with pagination
- Use indexes for fast seeks
- Stream messages for real-time updates
- Handle large conversations (1M+ messages)
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncIterator


class MessageReader:
    """Reads messages from JSONL files with pagination and streaming support"""

    def __init__(self, base_path: str = "/app/volumes/conversations"):
        self.base_path = Path(base_path)
        self.active_path = self.base_path / "active"

    def get_messages(self, session_id: str,
                    offset: int = 0,
                    limit: int = 50,
                    reverse: bool = True) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation session with pagination

        Args:
            session_id: Session ID
            offset: Number of messages to skip (from start or end based on reverse)
            limit: Maximum number of messages to return
            reverse: If True, return newest first; if False, oldest first

        Returns:
            List of message dicts
        """
        session_dir = self.active_path / session_id
        messages_file = session_dir / "messages.jsonl"
        index_file = session_dir / "index.json"

        if not messages_file.exists():
            return []

        # Try to use index for fast seeks if available
        if index_file.exists():
            return self._get_messages_indexed(messages_file, index_file, offset, limit, reverse)
        else:
            return self._get_messages_sequential(messages_file, offset, limit, reverse)

    def _get_messages_indexed(self, messages_file: Path, index_file: Path,
                             offset: int, limit: int, reverse: bool) -> List[Dict[str, Any]]:
        """Get messages using byte offset index for O(1) seeks"""
        try:
            index = json.loads(index_file.read_text())
            offsets = index.get("offsets", [])

            if not offsets:
                return self._get_messages_sequential(messages_file, offset, limit, reverse)

            total_messages = len(offsets)

            # Calculate which messages to read
            if reverse:
                # Newest first - read from end
                start_idx = max(0, total_messages - offset - limit)
                end_idx = total_messages - offset
                selected_offsets = offsets[start_idx:end_idx]
                selected_offsets.reverse()
            else:
                # Oldest first - read from start
                start_idx = offset
                end_idx = min(total_messages, offset + limit)
                selected_offsets = offsets[start_idx:end_idx]

            # Read messages using byte offsets
            messages = []
            with open(messages_file, 'r') as f:
                for offset_entry in selected_offsets:
                    byte_offset = offset_entry.get("byte_offset")
                    if byte_offset is not None:
                        f.seek(byte_offset)
                        line = f.readline()
                        if line.strip():
                            try:
                                messages.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

            return messages

        except Exception as e:
            print(f"Index read failed, falling back to sequential: {e}")
            return self._get_messages_sequential(messages_file, offset, limit, reverse)

    def _get_messages_sequential(self, messages_file: Path,
                                 offset: int, limit: int,
                                 reverse: bool) -> List[Dict[str, Any]]:
        """Fallback: sequential read of messages"""
        messages = []

        with open(messages_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        # Apply reverse if needed
        if reverse:
            messages.reverse()

        # Apply offset and limit
        return messages[offset:offset + limit]

    def get_message_by_id(self, session_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific message by ID

        Args:
            session_id: Session ID
            message_id: Message ID

        Returns:
            Message dict or None if not found
        """
        session_dir = self.active_path / session_id
        messages_file = session_dir / "messages.jsonl"
        index_file = session_dir / "index.json"

        if not messages_file.exists():
            return None

        # Try to use index for fast lookup
        if index_file.exists():
            try:
                index = json.loads(index_file.read_text())
                offsets = index.get("offsets", [])

                # Find message in index
                for offset_entry in offsets:
                    if offset_entry.get("id") == message_id:
                        byte_offset = offset_entry.get("byte_offset")

                        # Seek directly to message
                        with open(messages_file, 'r') as f:
                            f.seek(byte_offset)
                            line = f.readline()
                            if line.strip():
                                return json.loads(line)

                        return None

            except Exception:
                pass

        # Fallback: sequential search
        with open(messages_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get("id") == message_id:
                        return msg
                except json.JSONDecodeError:
                    continue

        return None

    def get_context_around(self, session_id: str, message_id: str,
                          before: int = 5, after: int = 5) -> List[Dict[str, Any]]:
        """
        Get messages around a specific message (for context)

        Args:
            session_id: Session ID
            message_id: Target message ID
            before: Number of messages before target
            after: Number of messages after target

        Returns:
            List of messages with target message and surrounding context
        """
        session_dir = self.active_path / session_id
        messages_file = session_dir / "messages.jsonl"
        index_file = session_dir / "index.json"

        if not messages_file.exists():
            return []

        if index_file.exists():
            try:
                index = json.loads(index_file.read_text())
                offsets = index.get("offsets", [])

                # Find target message index
                target_idx = None
                for i, offset_entry in enumerate(offsets):
                    if offset_entry.get("id") == message_id:
                        target_idx = i
                        break

                if target_idx is None:
                    return []

                # Calculate range
                start_idx = max(0, target_idx - before)
                end_idx = min(len(offsets), target_idx + after + 1)

                # Read messages in range
                messages = []
                with open(messages_file, 'r') as f:
                    for offset_entry in offsets[start_idx:end_idx]:
                        byte_offset = offset_entry.get("byte_offset")
                        f.seek(byte_offset)
                        line = f.readline()
                        if line.strip():
                            try:
                                messages.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

                return messages

            except Exception:
                pass

        # Fallback: sequential read
        messages = []
        with open(messages_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        # Find target in sequential list
        target_idx = None
        for i, msg in enumerate(messages):
            if msg.get("id") == message_id:
                target_idx = i
                break

        if target_idx is None:
            return []

        start_idx = max(0, target_idx - before)
        end_idx = min(len(messages), target_idx + after + 1)

        return messages[start_idx:end_idx]

    async def stream_messages(self, session_id: str,
                             from_message_id: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream messages in real-time as they're written

        Args:
            session_id: Session ID
            from_message_id: Optional starting message ID (stream messages after this)

        Yields:
            Message dicts as they're written
        """
        session_dir = self.active_path / session_id
        messages_file = session_dir / "messages.jsonl"

        if not messages_file.exists():
            return

        # Find starting position
        start_position = 0
        if from_message_id:
            # Read file to find message
            with open(messages_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        if msg.get("id") == from_message_id:
                            # Start after this message
                            start_position = f.tell()
                            break
                    except json.JSONDecodeError:
                        continue

        # Stream new messages
        with open(messages_file, 'r') as f:
            # Seek to starting position
            f.seek(start_position)

            while True:
                line = f.readline()

                if line:
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
                else:
                    # No new data, wait a bit
                    await asyncio.sleep(0.1)

                    # Check if session still exists
                    if not messages_file.exists():
                        break

    def get_message_count(self, session_id: str) -> int:
        """
        Get total message count for a session

        Args:
            session_id: Session ID

        Returns:
            Number of messages
        """
        session_dir = self.active_path / session_id
        metadata_file = session_dir / "metadata.json"

        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text())
                return metadata.get("message_count", 0)
            except Exception:
                pass

        # Fallback: count lines in messages.jsonl
        messages_file = session_dir / "messages.jsonl"
        if not messages_file.exists():
            return 0

        count = 0
        with open(messages_file, 'r') as f:
            for line in f:
                if line.strip():
                    count += 1

        return count
