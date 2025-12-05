# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Session Manager - Handles conversation session lifecycle
Responsibilities:
- Create new sessions with ULID IDs
- Update session metadata atomically
- Handle concurrent writes with file locks
- Rebuild corrupted metadata from messages
"""
import json
import fcntl
import os
import tarfile
import shutil
from pathlib import Path
from datetime import datetime, UTC, timedelta
from typing import Optional, Dict, Any, List
from ulid import ULID


class SessionManager:
    """Manages conversation sessions using filesystem as storage"""

    def __init__(self, base_path: str = "/app/volumes/conversations"):
        self.base_path = Path(base_path)
        self.active_path = self.base_path / "active"
        self.archive_path = self.base_path / "archive"
        self.sessions_file = self.base_path / "sessions.jsonl"

        # Ensure directories exist
        self.active_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Ensure sessions.jsonl exists
        if not self.sessions_file.exists():
            self.sessions_file.touch()

    def create_session(self, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None) -> str:
        """
        Create a new conversation session

        Args:
            title: Optional session title
            metadata: Optional additional metadata
            session_id: Optional custom session ID (defaults to ULID)

        Returns:
            session_id (ULID string or custom ID)
        """
        # Use provided session_id or generate ULID
        if not session_id:
            session_id = str(ULID())
        timestamp = datetime.now(UTC).isoformat()

        # Create session directory
        session_dir = self.active_path / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize session metadata
        session_metadata = {
            "id": session_id,
            "title": title or f"Conversation {session_id[:8]}",
            "created_at": timestamp,
            "updated_at": timestamp,
            "message_count": 0,
            "byte_size": 0,
            "participants": {},
            "mcp_servers_used": [],
            "tags": metadata.get("tags", []) if metadata else [],
            "auto_summary": "",
            "last_message": None,
            "index_version": 1,
            "archived": False
        }

        # Merge additional metadata
        if metadata:
            session_metadata.update({k: v for k, v in metadata.items() if k not in session_metadata})

        # Write metadata.json
        metadata_file = session_dir / "metadata.json"
        self._write_atomic(metadata_file, session_metadata)

        # Initialize messages.jsonl
        messages_file = session_dir / "messages.jsonl"
        messages_file.touch()

        # Initialize index.json
        index_file = session_dir / "index.json"
        index_data = {
            "version": 1,
            "message_count": 0,
            "offsets": [],
            "checkpoints": {}
        }
        self._write_atomic(index_file, index_data)

        # Append to master sessions.jsonl
        session_entry = {
            "id": session_id,
            "title": session_metadata["title"],
            "created": timestamp,
            "updated": timestamp,
            "message_count": 0,
            "status": "active",
            "preview": ""
        }
        self._append_to_jsonl(self.sessions_file, session_entry)

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata

        Args:
            session_id: Session ID

        Returns:
            Session metadata dict or None if not found
        """
        metadata_file = self.active_path / session_id / "metadata.json"

        if not metadata_file.exists():
            # Check if archived
            metadata_file = self._find_archived_session(session_id)
            if not metadata_file:
                return None

        try:
            return json.loads(metadata_file.read_text())
        except Exception as e:
            print(f"Error reading metadata for {session_id}: {e}")
            return None

    def update_metadata(self, session_id: str, updates: Dict[str, Any]):
        """
        Update session metadata atomically with file locking

        Args:
            session_id: Session ID
            updates: Dictionary of fields to update
        """
        session_dir = self.active_path / session_id
        metadata_file = session_dir / "metadata.json"
        lock_file = session_dir / ".lock"

        if not metadata_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        # Acquire lock
        with self._file_lock(lock_file):
            # Read current metadata
            current = json.loads(metadata_file.read_text())

            # Merge updates
            current.update(updates)
            current["updated_at"] = datetime.now(UTC).isoformat()

            # Write atomically
            self._write_atomic(metadata_file, current)

            # Update sessions.jsonl entry
            self._update_session_entry(session_id, current)

    def list_sessions(self, limit: int = 50, offset: int = 0,
                     status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List conversation sessions from master file

        Args:
            limit: Max number of sessions to return
            offset: Number of sessions to skip
            status: Filter by status ('active' or 'archived')

        Returns:
            List of session summaries
        """
        sessions = []

        if not self.sessions_file.exists():
            return sessions

        # Read sessions.jsonl in reverse (newest first)
        with open(self.sessions_file, 'r') as f:
            lines = f.readlines()

        # Reverse for newest first
        lines.reverse()

        skipped = 0
        for line in lines:
            if not line.strip():
                continue

            try:
                session = json.loads(line)

                # Apply status filter
                if status and session.get("status") != status:
                    continue

                # Apply offset
                if skipped < offset:
                    skipped += 1
                    continue

                sessions.append(session)

                # Apply limit
                if len(sessions) >= limit:
                    break

            except json.JSONDecodeError:
                continue

        return sessions

    def archive_session(self, session_id: str):
        """
        Archive a completed session

        Args:
            session_id: Session ID to archive
        """
        session_dir = self.active_path / session_id
        if not session_dir.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        # Get metadata for date
        metadata = self.get_session(session_id)
        if not metadata:
            raise ValueError(f"Cannot read metadata for {session_id}")

        # Create date-based archive directory
        created_date = metadata["created_at"][:10]  # YYYY-MM-DD
        archive_dir = self.archive_path / created_date
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Create tar.gz
        archive_file = archive_dir / f"{session_id}.tar.gz"
        with tarfile.open(archive_file, "w:gz") as tar:
            tar.add(session_dir, arcname=session_id)

        # Update metadata to mark as archived
        metadata["archived"] = True
        metadata["archived_at"] = datetime.now(UTC).isoformat()
        metadata["archive_path"] = str(archive_file)

        # Write updated metadata before removing
        metadata_file = session_dir / "metadata.json"
        self._write_atomic(metadata_file, metadata)

        # Update sessions.jsonl
        self._update_session_entry(session_id, {"status": "archived"})

        # Remove from active
        shutil.rmtree(session_dir)

        print(f"Archived session {session_id} to {archive_file}")

    def cleanup_empty_sessions(self, max_age_hours: int = 1) -> Dict[str, Any]:
        """
        Clean up empty sessions (0 messages) older than max_age_hours

        Args:
            max_age_hours: Maximum age in hours for empty sessions (default: 1)

        Returns:
            Dictionary with cleanup stats
        """
        cleaned = []
        errors = []
        current_time = datetime.now(UTC)
        max_age = timedelta(hours=max_age_hours)

        # List all active sessions
        all_sessions = self.list_sessions(limit=1000, status='active')

        for session in all_sessions:
            # Check if session is empty and old enough
            message_count = session.get('message_count', 0)
            if message_count > 0:
                continue

            # Parse created timestamp
            try:
                created_at = datetime.fromisoformat(session['created'].replace('Z', '+00:00'))
                age = current_time - created_at

                if age > max_age:
                    session_id = session['id']
                    try:
                        self.archive_session(session_id)
                        cleaned.append(session_id)
                        print(f"[Cleanup] Archived empty session {session_id} (age: {age})")
                    except Exception as e:
                        errors.append({"session_id": session_id, "error": str(e)})
                        print(f"[Cleanup] Failed to archive {session_id}: {e}")

            except (ValueError, KeyError) as e:
                errors.append({"session_id": session.get('id'), "error": f"Parse error: {e}"})
                continue

        return {
            "cleaned_count": len(cleaned),
            "cleaned_sessions": cleaned,
            "error_count": len(errors),
            "errors": errors
        }

    def rebuild_metadata(self, session_id: str) -> Dict[str, Any]:
        """
        Rebuild corrupted metadata from messages.jsonl

        Args:
            session_id: Session ID

        Returns:
            Rebuilt metadata
        """
        session_dir = self.active_path / session_id
        messages_file = session_dir / "messages.jsonl"

        if not messages_file.exists():
            raise FileNotFoundError(f"Messages file not found for {session_id}")

        # Analyze messages
        message_count = 0
        byte_size = 0
        participants = {}
        first_timestamp = None
        last_timestamp = None
        last_message = None

        with open(messages_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    msg = json.loads(line)
                    message_count += 1
                    byte_size += len(line)

                    # Track timestamps
                    timestamp = msg.get("timestamp")
                    if not first_timestamp:
                        first_timestamp = timestamp
                    last_timestamp = timestamp

                    # Track participants
                    participant = msg.get("type", "unknown")
                    if participant not in participants:
                        participants[participant] = {
                            "message_count": 0,
                            "first": timestamp
                        }
                    participants[participant]["message_count"] += 1

                    # Keep last message
                    last_message = {
                        "id": msg.get("id"),
                        "type": msg.get("type"),
                        "preview": msg.get("content", "")[:100],
                        "timestamp": timestamp
                    }

                except json.JSONDecodeError:
                    continue

        # Rebuild metadata
        metadata = {
            "id": session_id,
            "title": f"Recovered Conversation {session_id[:8]}",
            "created_at": first_timestamp or datetime.now(UTC).isoformat(),
            "updated_at": last_timestamp or datetime.now(UTC).isoformat(),
            "message_count": message_count,
            "byte_size": byte_size,
            "participants": participants,
            "mcp_servers_used": [],
            "tags": ["recovered"],
            "auto_summary": "",
            "last_message": last_message,
            "index_version": 1,
            "archived": False
        }

        # Write rebuilt metadata
        metadata_file = session_dir / "metadata.json"
        self._write_atomic(metadata_file, metadata)

        return metadata

    def _write_atomic(self, file_path: Path, data: Dict[str, Any]):
        """Write JSON file atomically using temp file + rename"""
        temp_file = file_path.parent / f".{file_path.name}.tmp"

        # Write to temp file
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename
        temp_file.rename(file_path)

    def _append_to_jsonl(self, file_path: Path, data: Dict[str, Any]):
        """Append entry to JSONL file"""
        with open(file_path, 'a') as f:
            f.write(json.dumps(data) + '\n')
            f.flush()
            os.fsync(f.fileno())

    def _file_lock(self, lock_file: Path):
        """Context manager for file-based locking"""
        class FileLock:
            def __init__(self, lock_path: Path):
                self.lock_path = lock_path
                self.fd = None

            def __enter__(self):
                # Create lock file if it doesn't exist
                self.lock_path.touch()

                # Open and acquire exclusive lock
                self.fd = open(self.lock_path, 'r+')
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX)
                return self

            def __exit__(self, *args):
                if self.fd:
                    fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
                    self.fd.close()

        return FileLock(lock_file)

    def _update_session_entry(self, session_id: str, updates: Dict[str, Any]):
        """Update entry in sessions.jsonl"""
        if not self.sessions_file.exists():
            return

        # Read all lines
        with open(self.sessions_file, 'r') as f:
            lines = f.readlines()

        # Update matching entry
        updated_lines = []
        for line in lines:
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                if entry.get("id") == session_id:
                    entry.update(updates)
                    entry["updated"] = datetime.now(UTC).isoformat()
                updated_lines.append(json.dumps(entry) + '\n')
            except json.JSONDecodeError:
                updated_lines.append(line)

        # Write back atomically
        temp_file = self.sessions_file.parent / ".sessions.jsonl.tmp"
        with open(temp_file, 'w') as f:
            f.writelines(updated_lines)
            f.flush()
            os.fsync(f.fileno())

        temp_file.rename(self.sessions_file)

    def _find_archived_session(self, session_id: str) -> Optional[Path]:
        """Find archived session metadata file"""
        # Would need to search archive directories
        # For now, return None
        return None
