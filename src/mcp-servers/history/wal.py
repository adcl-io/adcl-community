# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
WAL Manager - Write-Ahead Log for crash recovery
Responsibilities:
- Ensure durability of writes
- Recover from crashes
- Periodic checkpoint flushing
"""
import json
import os
import fcntl
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class WALManager:
    """Manages write-ahead log for crash recovery"""

    def __init__(self, base_path: str = "/app/volumes/conversations"):
        self.base_path = Path(base_path)
        self.wal_path = self.base_path / "wal"
        self.wal_file = self.wal_path / "pending.jsonl"
        self.active_path = self.base_path / "active"

        # Ensure WAL directory exists
        self.wal_path.mkdir(parents=True, exist_ok=True)

        # Ensure WAL file exists
        if not self.wal_file.exists():
            self.wal_file.touch()

    def write_entry(self, entry: Dict[str, Any]):
        """
        Write entry to WAL with fsync for durability

        Args:
            entry: WAL entry dict
        """
        with open(self.wal_file, 'a') as f:
            # Acquire exclusive lock
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + '\n')
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def recover_from_wal(self) -> Dict[str, Any]:
        """
        Recover uncommitted writes from WAL

        Returns:
            Recovery summary
        """
        if not self.wal_file.exists() or self.wal_file.stat().st_size == 0:
            return {
                "recovered_count": 0,
                "errors": []
            }

        recovered = 0
        errors = []

        # Read WAL entries
        wal_entries = []
        with open(self.wal_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    wal_entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    errors.append(f"Corrupt WAL entry: {str(e)}")

        # Replay entries
        for entry in wal_entries:
            try:
                self._replay_entry(entry)
                recovered += 1
            except Exception as e:
                errors.append({
                    "entry": entry,
                    "error": str(e)
                })

        # Clear WAL after successful recovery
        if recovered > 0:
            self._clear_wal()

        return {
            "recovered_count": recovered,
            "error_count": len(errors),
            "errors": errors
        }

    def _replay_entry(self, entry: Dict[str, Any]):
        """
        Replay a WAL entry

        Args:
            entry: WAL entry to replay
        """
        from .message_writer import MessageWriter

        session_id = entry.get("session_id")
        if not session_id:
            raise ValueError("WAL entry missing session_id")

        writer = MessageWriter(str(self.base_path))

        if entry.get("bulk"):
            # Bulk append
            messages = entry.get("messages", [])
            # Don't write to WAL again during replay
            writer.bulk_append(session_id, messages)
        else:
            # Single message
            message = entry.get("message")
            if message:
                writer.append_message(session_id, message)

    def _clear_wal(self):
        """Clear WAL after successful recovery"""
        # Truncate WAL file
        with open(self.wal_file, 'w') as f:
            f.truncate(0)
            f.flush()
            os.fsync(f.fileno())

    def checkpoint(self) -> Dict[str, Any]:
        """
        Force a checkpoint (flush pending writes)

        Returns:
            Checkpoint summary
        """
        return self.recover_from_wal()

    def get_wal_size(self) -> int:
        """Get WAL file size in bytes"""
        if not self.wal_file.exists():
            return 0
        return self.wal_file.stat().st_size

    def has_pending_writes(self) -> bool:
        """Check if WAL has pending writes"""
        return self.get_wal_size() > 0
