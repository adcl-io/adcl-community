# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Message Writer - Handles appending messages to conversation sessions
Responsibilities:
- Append messages with guaranteed durability
- Handle concurrent writes from multiple agents
- Update indexes asynchronously
- Implement write-ahead log for crash recovery
"""
import json
import os
import hashlib
import fcntl
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional


class MessageWriter:
    """Writes messages to JSONL files with WAL support"""

    def __init__(self, base_path: str = "/app/volumes/conversations"):
        self.base_path = Path(base_path)
        self.active_path = self.base_path / "active"
        self.wal_path = self.base_path / "wal"
        self.wal_file = self.wal_path / "pending.jsonl"

        # Ensure directories exist
        self.wal_path.mkdir(parents=True, exist_ok=True)

        # Ensure WAL file exists
        if not self.wal_file.exists():
            self.wal_file.touch()

    def append_message(self, session_id: str, message: Dict[str, Any]) -> str:
        """
        Append a single message to a conversation session

        Args:
            session_id: Session ID
            message: Message dict with type, content, metadata

        Returns:
            message_id
        """
        session_dir = self.active_path / session_id
        if not session_dir.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        messages_file = session_dir / "messages.jsonl"
        metadata_file = session_dir / "metadata.json"
        index_file = session_dir / "index.json"
        lock_file = session_dir / ".lock"

        # Generate message ID
        timestamp = datetime.now(UTC).isoformat()
        content_hash = hashlib.sha256(
            json.dumps(message, sort_keys=True).encode()
        ).hexdigest()[:8]
        message_id = f"msg_{timestamp.replace(':', '').replace('.', '').replace('-', '')}_{content_hash}"

        # Add message metadata
        message["id"] = message_id
        message["timestamp"] = message.get("timestamp", timestamp)

        # Step 1: Write to WAL first for durability
        self._write_to_wal({
            "session_id": session_id,
            "message": message,
            "wal_timestamp": timestamp
        })

        # Step 2: Acquire session write lock
        with self._file_lock(lock_file):
            # Get current byte offset for index
            byte_offset = messages_file.stat().st_size if messages_file.exists() else 0

            # Append to messages.jsonl
            message_line = json.dumps(message) + '\n'
            with open(messages_file, 'a') as f:
                f.write(message_line)
                f.flush()
                os.fsync(f.fileno())

            # Update metadata
            metadata = json.loads(metadata_file.read_text())
            metadata["message_count"] = metadata.get("message_count", 0) + 1
            metadata["updated_at"] = timestamp
            metadata["byte_size"] = metadata.get("byte_size", 0) + len(message_line)

            # Update participants
            participant_type = message.get("type", "unknown")
            if "participants" not in metadata:
                metadata["participants"] = {}
            if participant_type not in metadata["participants"]:
                metadata["participants"][participant_type] = {
                    "message_count": 0,
                    "first": timestamp
                }
            metadata["participants"][participant_type]["message_count"] += 1

            # Update last message
            metadata["last_message"] = {
                "id": message_id,
                "type": message.get("type"),
                "preview": str(message.get("content", ""))[:100],
                "timestamp": timestamp
            }

            # Track MCP servers used
            if "tools" in message:
                for tool in message.get("tools", []):
                    if tool not in metadata.get("mcp_servers_used", []):
                        metadata.setdefault("mcp_servers_used", []).append(tool)

            # Write metadata atomically
            self._write_atomic(metadata_file, metadata)

            # Update index
            self._update_index(index_file, message_id, byte_offset, metadata["message_count"])

            # Update sessions.jsonl master list
            self._update_session_list(session_id, metadata)

        return message_id

    def bulk_append(self, session_id: str, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Append multiple messages efficiently with single lock acquisition

        Args:
            session_id: Session ID
            messages: List of message dicts

        Returns:
            List of message IDs
        """
        if not messages:
            return []

        session_dir = self.active_path / session_id
        if not session_dir.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        messages_file = session_dir / "messages.jsonl"
        metadata_file = session_dir / "metadata.json"
        index_file = session_dir / "index.json"
        lock_file = session_dir / ".lock"

        message_ids = []
        timestamp = datetime.now(UTC).isoformat()

        # Generate all message IDs first
        enriched_messages = []
        for msg in messages:
            content_hash = hashlib.sha256(
                json.dumps(msg, sort_keys=True).encode()
            ).hexdigest()[:8]
            msg_id = f"msg_{timestamp.replace(':', '').replace('.', '').replace('-', '')}_{content_hash}"

            msg["id"] = msg_id
            msg["timestamp"] = msg.get("timestamp", timestamp)
            enriched_messages.append(msg)
            message_ids.append(msg_id)

        # Write to WAL
        self._write_to_wal({
            "session_id": session_id,
            "messages": enriched_messages,
            "wal_timestamp": timestamp,
            "bulk": True
        })

        # Single lock acquisition for all writes
        with self._file_lock(lock_file):
            # Get starting byte offset
            byte_offset = messages_file.stat().st_size if messages_file.exists() else 0

            # Append all messages
            total_bytes = 0
            offsets = []
            with open(messages_file, 'a') as f:
                for msg in enriched_messages:
                    message_line = json.dumps(msg) + '\n'
                    offsets.append((msg["id"], byte_offset + total_bytes))
                    f.write(message_line)
                    total_bytes += len(message_line)

                f.flush()
                os.fsync(f.fileno())

            # Update metadata
            metadata = json.loads(metadata_file.read_text())
            metadata["message_count"] = metadata.get("message_count", 0) + len(messages)
            metadata["updated_at"] = timestamp
            metadata["byte_size"] = metadata.get("byte_size", 0) + total_bytes

            # Update last message
            last_msg = enriched_messages[-1]
            metadata["last_message"] = {
                "id": last_msg["id"],
                "type": last_msg.get("type"),
                "preview": str(last_msg.get("content", ""))[:100],
                "timestamp": timestamp
            }

            self._write_atomic(metadata_file, metadata)

            # Update index with all new offsets
            self._bulk_update_index(index_file, offsets, metadata["message_count"])

        return message_ids

    def _write_to_wal(self, entry: Dict[str, Any]):
        """Write entry to write-ahead log for crash recovery"""
        with open(self.wal_file, 'a') as f:
            # Acquire exclusive lock on WAL
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + '\n')
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _update_index(self, index_file: Path, message_id: str,
                     byte_offset: int, message_number: int):
        """Update byte offset index for fast seeks"""
        if not index_file.exists():
            index = {
                "version": 1,
                "message_count": 0,
                "offsets": [],
                "checkpoints": {}
            }
        else:
            index = json.loads(index_file.read_text())

        # Add offset entry
        index["offsets"].append({
            "id": message_id,
            "byte_offset": byte_offset,
            "line": message_number
        })

        index["message_count"] = message_number

        # Create checkpoint every 100 messages
        if message_number % 100 == 0:
            checkpoint_key = f"message_{message_number}"
            if "checkpoints" not in index:
                index["checkpoints"] = {}
            index["checkpoints"][checkpoint_key] = {
                "offset": byte_offset,
                "timestamp": datetime.now(UTC).isoformat()
            }

        # Write index atomically
        self._write_atomic(index_file, index)

    def _bulk_update_index(self, index_file: Path, offsets: List[tuple],
                          final_message_count: int):
        """Bulk update index for multiple messages"""
        if not index_file.exists():
            index = {
                "version": 1,
                "message_count": 0,
                "offsets": [],
                "checkpoints": {}
            }
        else:
            index = json.loads(index_file.read_text())

        start_line = index["message_count"] + 1

        # Add all offset entries
        for i, (msg_id, byte_offset) in enumerate(offsets):
            line_num = start_line + i
            index["offsets"].append({
                "id": msg_id,
                "byte_offset": byte_offset,
                "line": line_num
            })

        index["message_count"] = final_message_count

        # Write index atomically
        self._write_atomic(index_file, index)

    def _write_atomic(self, file_path: Path, data: Dict[str, Any]):
        """Write JSON file atomically using temp file + rename"""
        temp_file = file_path.parent / f".{file_path.name}.tmp"

        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        temp_file.rename(file_path)

    def _update_session_list(self, session_id: str, metadata: Dict[str, Any]):
        """Update session entry in sessions.jsonl master list"""
        sessions_file = self.base_path / "sessions.jsonl"
        if not sessions_file.exists():
            return

        # Read all lines
        with open(sessions_file, 'r') as f:
            lines = f.readlines()

        # Update matching entry
        updated_lines = []
        for line in lines:
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                if entry.get("id") == session_id:
                    # Update with latest metadata
                    entry["updated"] = metadata.get("updated_at")
                    entry["message_count"] = metadata.get("message_count", 0)
                    entry["preview"] = metadata.get("last_message", {}).get("preview", "")
                updated_lines.append(json.dumps(entry) + '\n')
            except json.JSONDecodeError:
                updated_lines.append(line)

        # Write back atomically
        temp_file = sessions_file.parent / ".sessions.jsonl.tmp"
        with open(temp_file, 'w') as f:
            f.writelines(updated_lines)
            f.flush()
            os.fsync(f.fileno())

        temp_file.rename(sessions_file)

    def _file_lock(self, lock_file: Path):
        """Context manager for file-based locking"""
        class FileLock:
            def __init__(self, lock_path: Path):
                self.lock_path = lock_path
                self.fd = None

            def __enter__(self):
                self.lock_path.touch()
                self.fd = open(self.lock_path, 'r+')
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX)
                return self

            def __exit__(self, *args):
                if self.fd:
                    fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
                    self.fd.close()

        return FileLock(lock_file)
