# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Index Builder - Builds and maintains indexes for fast message access
Responsibilities:
- Build byte offset indexes for fast seeks
- Maintain search indexes
- Run as background job
- Rebuild corrupted indexes
"""
import json
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, UTC


class IndexBuilder:
    """Builds indexes for fast message access"""

    def __init__(self, base_path: str = "/app/volumes/conversations"):
        self.base_path = Path(base_path)
        self.active_path = self.base_path / "active"

    def build_message_index(self, session_id: str) -> Dict[str, Any]:
        """
        Build byte offset index for a session

        Args:
            session_id: Session ID

        Returns:
            Index metadata
        """
        session_dir = self.active_path / session_id
        messages_file = session_dir / "messages.jsonl"
        index_file = session_dir / "index.json"

        if not messages_file.exists():
            raise FileNotFoundError(f"Messages file not found for {session_id}")

        # Build index by reading file
        index = {
            "version": 1,
            "message_count": 0,
            "offsets": [],
            "checkpoints": {},
            "built_at": datetime.now(UTC).isoformat()
        }

        line_number = 0
        byte_offset = 0

        with open(messages_file, 'r') as f:
            while True:
                current_offset = f.tell()
                line = f.readline()

                if not line:
                    break

                if line.strip():
                    line_number += 1

                    try:
                        msg = json.loads(line)
                        msg_id = msg.get("id", f"msg_{line_number}")

                        # Add to offsets
                        index["offsets"].append({
                            "id": msg_id,
                            "byte_offset": current_offset,
                            "line": line_number
                        })

                        # Create checkpoint every 100 messages
                        if line_number % 100 == 0:
                            checkpoint_key = f"message_{line_number}"
                            index["checkpoints"][checkpoint_key] = {
                                "offset": current_offset,
                                "timestamp": msg.get("timestamp")
                            }

                    except json.JSONDecodeError:
                        pass

                byte_offset = f.tell()

        index["message_count"] = line_number

        # Write index atomically
        self._write_atomic(index_file, index)

        return index

    def rebuild_all_indexes(self) -> Dict[str, Any]:
        """
        Rebuild indexes for all active sessions

        Returns:
            Summary of rebuild operation
        """
        rebuilt = []
        errors = []

        for session_dir in self.active_path.iterdir():
            if not session_dir.is_dir():
                continue

            session_id = session_dir.name

            try:
                self.build_message_index(session_id)
                rebuilt.append(session_id)
            except Exception as e:
                errors.append({
                    "session_id": session_id,
                    "error": str(e)
                })

        return {
            "rebuilt_count": len(rebuilt),
            "error_count": len(errors),
            "rebuilt": rebuilt,
            "errors": errors
        }

    def _write_atomic(self, file_path: Path, data: Dict[str, Any]):
        """Write JSON file atomically"""
        temp_file = file_path.parent / f".{file_path.name}.tmp"

        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        temp_file.rename(file_path)
