# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
AgentMemory - State management for agents

Provides persistent storage for agent context, findings, and learning.
Backed by Redis for fast access and SQLite for long-term persistence.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from api.redis_queue import redis_queue


class AgentMemory:
    """
    Agent memory storage with Redis caching and SQLite persistence

    Stores:
    - Scan results and findings
    - Context from previous tasks
    - Learning data (what worked, what didn't)
    - Target information
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.cache: Dict[str, Any] = {
            "findings": [],
            "scan_results": [],
            "context": [],
            "targets": {},
            "learned_patterns": []
        }

    async def initialize(self):
        """Load memory from Redis if available"""
        state = await redis_queue.get_agent_state(self.agent_id)
        if state:
            self.cache.update(state.get("memory", {}))

    async def add_finding(self, finding: Dict[str, Any]):
        """Add a finding to memory"""
        finding["timestamp"] = datetime.utcnow().isoformat()
        finding["agent_id"] = self.agent_id

        self.cache["findings"].append(finding)

        # Persist to Redis
        await self._save_to_redis()

    async def add_scan_result(self, target: str, result: Dict[str, Any]):
        """Add scan result to memory"""
        scan_data = {
            "target": target,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        }

        self.cache["scan_results"].append(scan_data)

        # Update target info
        if target not in self.cache["targets"]:
            self.cache["targets"][target] = {
                "first_seen": datetime.utcnow().isoformat(),
                "scans": []
            }

        self.cache["targets"][target]["scans"].append(scan_data)
        self.cache["targets"][target]["last_seen"] = datetime.utcnow().isoformat()

        # Persist to Redis
        await self._save_to_redis()

    async def add_context(self, context: str):
        """Add context note to memory"""
        self.cache["context"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "text": context
        })

        # Keep only last 50 context entries
        if len(self.cache["context"]) > 50:
            self.cache["context"] = self.cache["context"][-50:]

        await self._save_to_redis()

    async def add_learned_pattern(self, pattern: Dict[str, Any]):
        """Add a learned pattern (what worked/didn't work)"""
        pattern["timestamp"] = datetime.utcnow().isoformat()
        self.cache["learned_patterns"].append(pattern)

        await self._save_to_redis()

    def get_findings(self, severity: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get findings from memory"""
        findings = self.cache["findings"]

        if severity:
            findings = [f for f in findings if f.get("severity") == severity]

        return findings[-limit:]

    def get_scan_results(self, target: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get scan results from memory"""
        results = self.cache["scan_results"]

        if target:
            results = [r for r in results if r.get("target") == target]

        return results[-limit:]

    def get_target_info(self, target: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific target"""
        return self.cache["targets"].get(target)

    def get_context(self, limit: int = 10) -> List[str]:
        """Get recent context"""
        contexts = self.cache["context"][-limit:]
        return [c["text"] for c in contexts]

    def get_learned_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get learned patterns"""
        return self.cache["learned_patterns"][-limit:]

    async def _save_to_redis(self):
        """Persist memory to Redis"""
        await redis_queue.set_agent_state(self.agent_id, {
            "memory": self.cache,
            "updated_at": datetime.utcnow().isoformat()
        })

    async def clear(self):
        """Clear all memory"""
        self.cache = {
            "findings": [],
            "scan_results": [],
            "context": [],
            "targets": {},
            "learned_patterns": []
        }
        await redis_queue.delete_agent_state(self.agent_id)

    def summary(self) -> Dict[str, Any]:
        """Get memory summary statistics"""
        return {
            "findings_count": len(self.cache["findings"]),
            "scan_results_count": len(self.cache["scan_results"]),
            "context_entries": len(self.cache["context"]),
            "targets_tracked": len(self.cache["targets"]),
            "patterns_learned": len(self.cache["learned_patterns"])
        }
