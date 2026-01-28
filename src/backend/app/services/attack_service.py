# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Attack Service - Orchestrates attack workflows against discovered hosts
Follows ADCL principle: "Configuration is Code" - all state in text files

Thread-safe with async file locking to prevent race conditions
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json
import asyncio
import aiofiles
from uuid import uuid4


class AttackService:
    """
    Orchestrate and track attack operations.
    
    Storage structure:
        volumes/recon/{scan_id}/attacks/
        └── {attack_id}.json        # Attack execution results
    
    Attacks are stored within their corresponding scan directory.
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

    async def create_attack(
        self,
        scan_id: str,
        target_host: str,
        attack_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new attack operation.
        
        Args:
            scan_id: Parent scan identifier
            target_host: Target host IP address
            attack_type: Type of attack (vulnerability_scan, exploit, etc.)
            options: Additional attack options
        
        Returns:
            attack_id: Unique attack identifier
        """
        scan_dir = self.base_dir / scan_id
        if not scan_dir.exists():
            raise ValueError(f"Scan {scan_id} not found")
        
        attacks_dir = scan_dir / "attacks"
        attacks_dir.mkdir(exist_ok=True)
        
        attack_id = f"attack_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        
        # Initialize attack metadata
        attack_data = {
            "attack_id": attack_id,
            "scan_id": scan_id,
            "target_host": target_host,
            "attack_type": attack_type,
            "options": options or {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "vulnerabilities": [],
            "errors": []
        }
        
        attack_file = attacks_dir / f"{attack_id}.json"
        async with aiofiles.open(attack_file, 'w') as f:
            await f.write(json.dumps(attack_data, indent=2))
        
        return attack_id

    async def start_attack(
        self,
        scan_id: str,
        attack_id: str,
        agent_runtime,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Start an attack operation using agent runtime.
        
        Args:
            scan_id: Parent scan identifier
            attack_id: Attack identifier
            agent_runtime: AgentRuntime instance for executing attacks
            progress_callback: Optional callback for progress updates
        
        Returns:
            Attack result dictionary
        """
        attack_file = self.base_dir / scan_id / "attacks" / f"{attack_id}.json"
        if not attack_file.exists():
            raise ValueError(f"Attack {attack_id} not found in scan {scan_id}")
        
        # Load attack data
        async with aiofiles.open(attack_file, 'r') as f:
            content = await f.read()
            attack_data = json.loads(content)
        
        # Update status to running
        attack_data["status"] = "running"
        attack_data["started_at"] = datetime.now().isoformat()
        await self._save_attack(scan_id, attack_id, attack_data)
        
        if progress_callback:
            await progress_callback({
                "type": "attack_started",
                "attack_id": attack_id,
                "scan_id": scan_id,
                "target_host": attack_data["target_host"],
                "attack_type": attack_data["attack_type"]
            })
        
        # TODO: Execute attack using agent_runtime
        # For now, this is a placeholder - actual implementation will
        # call appropriate MCP servers (ZAP, metasploit, etc.) via agent runtime
        
        return {"status": "running", "attack_id": attack_id}

    async def update_attack_progress(
        self,
        scan_id: str,
        attack_id: str,
        progress_data: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ):
        """
        Update attack progress.
        
        Args:
            scan_id: Parent scan identifier
            attack_id: Attack identifier
            progress_data: Progress update data
            progress_callback: Optional callback for progress updates
        """
        attack_file = self.base_dir / scan_id / "attacks" / f"{attack_id}.json"
        
        # Thread-safe update
        lock = self._get_lock(str(attack_file))
        async with lock:
            async with aiofiles.open(attack_file, 'r') as f:
                content = await f.read()
                attack_data = json.loads(content)
            
            # Update progress
            attack_data.setdefault("progress", []).append({
                **progress_data,
                "timestamp": datetime.now().isoformat()
            })
            
            async with aiofiles.open(attack_file, 'w') as f:
                await f.write(json.dumps(attack_data, indent=2))
        
        # Stream update via WebSocket
        if progress_callback:
            await progress_callback({
                "type": "attack_progress",
                "attack_id": attack_id,
                "scan_id": scan_id,
                "progress": progress_data
            })

    async def complete_attack(
        self,
        scan_id: str,
        attack_id: str,
        result: Dict[str, Any],
        vulnerabilities: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ):
        """
        Mark attack as completed.
        
        Args:
            scan_id: Parent scan identifier
            attack_id: Attack identifier
            result: Attack result data
            vulnerabilities: List of discovered vulnerabilities
            progress_callback: Optional callback for progress updates
        """
        attack_file = self.base_dir / scan_id / "attacks" / f"{attack_id}.json"
        
        async with aiofiles.open(attack_file, 'r') as f:
            content = await f.read()
            attack_data = json.loads(content)
        
        attack_data["status"] = "completed"
        attack_data["completed_at"] = datetime.now().isoformat()
        attack_data["result"] = result
        attack_data["vulnerabilities"] = vulnerabilities
        
        await self._save_attack(scan_id, attack_id, attack_data)
        
        if progress_callback:
            await progress_callback({
                "type": "attack_complete",
                "attack_id": attack_id,
                "scan_id": scan_id,
                "vulnerabilities_count": len(vulnerabilities),
                "result": result
            })

    async def fail_attack(
        self,
        scan_id: str,
        attack_id: str,
        error: str,
        progress_callback: Optional[Callable] = None
    ):
        """
        Mark attack as failed.
        
        Args:
            scan_id: Parent scan identifier
            attack_id: Attack identifier
            error: Error message
            progress_callback: Optional callback for progress updates
        """
        attack_file = self.base_dir / scan_id / "attacks" / f"{attack_id}.json"
        
        async with aiofiles.open(attack_file, 'r') as f:
            content = await f.read()
            attack_data = json.loads(content)
        
        attack_data["status"] = "failed"
        attack_data["completed_at"] = datetime.now().isoformat()
        attack_data["errors"].append({
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
        await self._save_attack(scan_id, attack_id, attack_data)
        
        if progress_callback:
            await progress_callback({
                "type": "attack_error",
                "attack_id": attack_id,
                "scan_id": scan_id,
                "error": error
            })

    async def _save_attack(
        self,
        scan_id: str,
        attack_id: str,
        attack_data: Dict[str, Any]
    ):
        """Save attack data (internal use)"""
        attack_file = self.base_dir / scan_id / "attacks" / f"{attack_id}.json"
        lock = self._get_lock(str(attack_file))
        
        async with lock:
            async with aiofiles.open(attack_file, 'w') as f:
                await f.write(json.dumps(attack_data, indent=2))

    def list_attacks(
        self,
        scan_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List attacks for a scan.
        
        Args:
            scan_id: Parent scan identifier
            status: Filter by status (pending, running, completed, failed)
        
        Returns:
            List of attack data
        """
        attacks_dir = self.base_dir / scan_id / "attacks"
        if not attacks_dir.exists():
            return []
        
        attacks = []
        
        for attack_file in sorted(attacks_dir.glob("attack_*.json"), reverse=True):
            try:
                with open(attack_file, 'r') as f:
                    attack_data = json.load(f)
                
                # Apply status filter
                if status and attack_data.get("status") != status:
                    continue
                
                attacks.append(attack_data)
            except Exception as e:
                print(f"Warning: Failed to load attack {attack_file.name}: {e}")
        
        return attacks

    def get_attack(self, scan_id: str, attack_id: str) -> Optional[Dict[str, Any]]:
        """Get attack by ID (synchronous)"""
        attack_file = self.base_dir / scan_id / "attacks" / f"{attack_id}.json"
        if not attack_file.exists():
            return None
        
        with open(attack_file, 'r') as f:
            return json.load(f)
