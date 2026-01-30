# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Recon Service - Orchestrates reconnaissance workflows
Follows ADCL principle: "Configuration is Code" - all state in text files

Thread-safe with async file locking to prevent race conditions
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json
import asyncio
import aiofiles
import aiofiles.os
from uuid import uuid4


class ReconService:
    """
    Orchestrate and track reconnaissance scans.
    
    Storage structure:
        volumes/recon/
        └── {scan_id}/
            ├── metadata.json      # Scan configuration and status
            ├── hosts.json         # Discovered hosts (source of truth)
            ├── progress.jsonl     # Event log for real-time streaming
            └── attacks/
                └── {attack_id}.json
    
    Each scan is completely self-contained in its directory.
    All state persisted to disk - NO hidden state in memory.
    """

    def __init__(self, base_dir: str = "volumes/recon"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Async locks for thread-safe file operations
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def _get_lock(self, file_path: str) -> asyncio.Lock:
        """Get or create lock for a specific file"""
        if file_path not in self._locks:
            self._locks[file_path] = asyncio.Lock()
        return self._locks[file_path]

    async def create_scan(
        self,
        target: str,
        scan_type: str = "network_discovery",
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new reconnaissance scan.
        
        Args:
            target: Target network/host (e.g., "192.168.1.0/24")
            scan_type: Type of scan (network_discovery, port_scan, etc.)
            options: Additional scan options
        
        Returns:
            scan_id: Unique scan identifier
        """
        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        scan_dir = self.base_dir / scan_id
        scan_dir.mkdir(parents=True, exist_ok=True)
        
        # Create attacks subdirectory
        (scan_dir / "attacks").mkdir(exist_ok=True)
        
        # Initialize metadata
        metadata = {
            "scan_id": scan_id,
            "target": target,
            "scan_type": scan_type,
            "options": options or {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None
        }
        
        async with aiofiles.open(scan_dir / "metadata.json", 'w') as f:
            await f.write(json.dumps(metadata, indent=2))
        
        # Initialize empty hosts file
        async with aiofiles.open(scan_dir / "hosts.json", 'w') as f:
            await f.write(json.dumps({"hosts": [], "total_discovered": 0}, indent=2))
        
        # Initialize progress log
        await self.log_event(scan_id, {
            "type": "scan_created",
            "message": f"Scan created for target: {target}",
            "target": target,
            "scan_type": scan_type
        })
        
        return scan_id

    async def start_scan(
        self,
        scan_id: str,
        agent_runtime,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Start a reconnaissance scan using agent runtime.
        
        Args:
            scan_id: Scan identifier
            agent_runtime: AgentRuntime instance for executing scans
            progress_callback: Optional callback for progress updates
        
        Returns:
            Scan result dictionary
        """
        scan_dir = self.base_dir / scan_id
        if not scan_dir.exists():
            raise ValueError(f"Scan {scan_id} not found")
        
        # Update status to running
        metadata = await self.get_metadata(scan_id)
        metadata["status"] = "running"
        metadata["started_at"] = datetime.now().isoformat()
        await self._save_metadata(scan_id, metadata)
        
        await self.log_event(scan_id, {
            "type": "scan_started",
            "message": "Reconnaissance scan started"
        })
        
        if progress_callback:
            await progress_callback({
                "type": "scan_progress",
                "scan_id": scan_id,
                "status": "running",
                "message": "Starting reconnaissance scan..."
            })
        
        # TODO: Execute scan using agent_runtime
        # For now, this is a placeholder - actual implementation will
        # call nmap_recon MCP via agent runtime
        
        return {"status": "running", "scan_id": scan_id}

    async def update_hosts(
        self,
        scan_id: str,
        hosts: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ):
        """
        Update discovered hosts for a scan.
        
        Args:
            scan_id: Scan identifier
            hosts: List of discovered host dictionaries
            progress_callback: Optional callback for progress updates
        """
        scan_dir = self.base_dir / scan_id
        hosts_file = scan_dir / "hosts.json"
        
        # Thread-safe update
        lock = self._get_lock(str(hosts_file))
        async with lock:
            hosts_data = {
                "hosts": hosts,
                "total_discovered": len(hosts),
                "last_updated": datetime.now().isoformat()
            }
            
            async with aiofiles.open(hosts_file, 'w') as f:
                await f.write(json.dumps(hosts_data, indent=2))
        
        # Log event
        await self.log_event(scan_id, {
            "type": "hosts_updated",
            "count": len(hosts),
            "message": f"Discovered {len(hosts)} hosts"
        })
        
        # Stream update via WebSocket
        if progress_callback:
            await progress_callback({
                "type": "host_discovered",
                "scan_id": scan_id,
                "hosts_count": len(hosts),
                "hosts": hosts[:10]  # Send first 10 for real-time display
            })

    async def complete_scan(
        self,
        scan_id: str,
        result: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ):
        """
        Mark scan as completed.
        
        Args:
            scan_id: Scan identifier
            result: Scan result data
            progress_callback: Optional callback for progress updates
        """
        metadata = await self.get_metadata(scan_id)
        metadata["status"] = "completed"
        metadata["completed_at"] = datetime.now().isoformat()
        metadata["result"] = result
        await self._save_metadata(scan_id, metadata)
        
        await self.log_event(scan_id, {
            "type": "scan_completed",
            "message": "Reconnaissance scan completed",
            "result": result
        })
        
        if progress_callback:
            await progress_callback({
                "type": "scan_complete",
                "scan_id": scan_id,
                "status": "completed",
                "result": result
            })

    async def fail_scan(
        self,
        scan_id: str,
        error: str,
        progress_callback: Optional[Callable] = None
    ):
        """
        Mark scan as failed.
        
        Args:
            scan_id: Scan identifier
            error: Error message
            progress_callback: Optional callback for progress updates
        """
        metadata = await self.get_metadata(scan_id)
        metadata["status"] = "failed"
        metadata["completed_at"] = datetime.now().isoformat()
        metadata["error"] = error
        await self._save_metadata(scan_id, metadata)
        
        await self.log_event(scan_id, {
            "type": "scan_failed",
            "message": f"Scan failed: {error}",
            "error": error
        })
        
        if progress_callback:
            await progress_callback({
                "type": "scan_error",
                "scan_id": scan_id,
                "status": "failed",
                "error": error
            })

    async def get_metadata(self, scan_id: str) -> Dict[str, Any]:
        """Get scan metadata"""
        metadata_file = self.base_dir / scan_id / "metadata.json"
        if not metadata_file.exists():
            raise ValueError(f"Scan {scan_id} not found")
        
        async with aiofiles.open(metadata_file, 'r') as f:
            content = await f.read()
            return json.loads(content)

    async def _save_metadata(self, scan_id: str, metadata: Dict[str, Any]):
        """Save scan metadata (internal use)"""
        metadata_file = self.base_dir / scan_id / "metadata.json"
        lock = self._get_lock(str(metadata_file))
        
        async with lock:
            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))

    async def get_hosts(self, scan_id: str) -> Dict[str, Any]:
        """Get discovered hosts for a scan"""
        hosts_file = self.base_dir / scan_id / "hosts.json"
        if not hosts_file.exists():
            return {"hosts": [], "total_discovered": 0}
        
        async with aiofiles.open(hosts_file, 'r') as f:
            content = await f.read()
            return json.loads(content)

    async def log_event(self, scan_id: str, event: Dict[str, Any]):
        """
        Log event to progress file (REQUIRED - source of truth for streaming)
        
        Args:
            scan_id: Scan identifier
            event: Event data to log
        """
        progress_file = self.base_dir / scan_id / "progress.jsonl"
        event_with_timestamp = {
            **event,
            "timestamp": datetime.now().isoformat()
        }
        
        lock = self._get_lock(str(progress_file))
        async with lock:
            async with aiofiles.open(progress_file, 'a') as f:
                await f.write(json.dumps(event_with_timestamp) + "\n")

    def list_scans(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List reconnaissance scans.
        
        Args:
            status: Filter by status (pending, running, completed, failed)
            limit: Max results to return
        
        Returns:
            List of scan metadata
        """
        scans = []
        
        for scan_dir in sorted(self.base_dir.glob("scan_*"), reverse=True):
            if not scan_dir.is_dir():
                continue
            
            metadata_file = scan_dir / "metadata.json"
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Apply status filter
                if status and metadata.get("status") != status:
                    continue
                
                scans.append(metadata)
                
                if len(scans) >= limit:
                    break
            except Exception as e:
                print(f"Warning: Failed to load scan {scan_dir.name}: {e}")
        
        return scans

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get scan by ID (synchronous)"""
        metadata_file = self.base_dir / scan_id / "metadata.json"
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r') as f:
            return json.load(f)
