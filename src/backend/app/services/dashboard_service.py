# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Dashboard Service - KPI calculation and activity tracking
Following ADCL principle: Backend service (Tier 2) - no MCP
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.models.red_team import (
    KPIData,
    VulnerabilitySeverityCounts,
    ActivityEvent,
    TopHost,
)


class DashboardService:
    """
    Service for dashboard KPI calculation and activity tracking.

    This is a Tier 2 backend service - uses direct Python imports and file I/O,
    NOT MCP protocol.
    """

    def __init__(self, base_dir: str = "volumes/recon"):
        """
        Initialize dashboard service.

        Args:
            base_dir: Base directory for scan and vulnerability data
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Activity log file
        self.activity_log_file = self.base_dir / "activity.jsonl"

    async def get_kpis(self) -> KPIData:
        """
        Calculate dashboard KPIs from stored scan data.

        Returns:
            KPIData with current metrics
        """
        # Count discovered hosts from scan files
        hosts_discovered = await self._count_discovered_hosts()

        # Count vulnerabilities by severity
        vuln_counts = await self._count_vulnerabilities()

        # Count active attacks
        active_attacks = await self._count_active_attacks()

        # Calculate success rate
        success_rate = await self._calculate_success_rate()

        return KPIData(
            hosts_discovered=hosts_discovered,
            vulnerabilities=vuln_counts,
            active_attacks=active_attacks,
            success_rate=success_rate,
        )

    async def get_activity(self, limit: int = 50) -> List[ActivityEvent]:
        """
        Get recent activity events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent activity events
        """
        if not self.activity_log_file.exists():
            return []

        events = []

        # Read activity log (JSONL format - one event per line)
        with open(self.activity_log_file, "r") as f:
            lines = f.readlines()

        # Get last N lines (most recent events)
        recent_lines = lines[-limit:] if len(lines) > limit else lines

        for line in reversed(recent_lines):  # Newest first
            try:
                event_data = json.loads(line.strip())
                events.append(ActivityEvent(**event_data))
            except (json.JSONDecodeError, ValueError) as e:
                # Skip malformed lines
                continue

        return events

    async def get_top_hosts(self, limit: int = 10) -> List[TopHost]:
        """
        Get top hosts by risk score.

        Args:
            limit: Maximum number of hosts to return

        Returns:
            List of top hosts sorted by risk score
        """
        # Aggregate vulnerability data by host
        host_data = await self._aggregate_host_vulnerabilities()

        # Calculate risk scores
        top_hosts = []
        for host, data in host_data.items():
            risk_score = self._calculate_host_risk_score(data)

            top_hosts.append(
                TopHost(
                    host=host,
                    hostname=data.get("hostname"),
                    vulnerability_count=data["total"],
                    critical_vulns=data["critical"],
                    high_vulns=data["high"],
                    risk_score=risk_score,
                    last_scanned=data.get("last_scanned"),
                )
            )

        # Sort by risk score descending
        top_hosts.sort(key=lambda h: h.risk_score, reverse=True)

        return top_hosts[:limit]

    async def log_activity(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log an activity event.

        Args:
            event_type: Type of event (scan, vulnerability, attack, system)
            severity: Event severity (info, warning, error, success)
            message: Human-readable message
            details: Additional event details

        Returns:
            Event ID
        """
        import uuid

        event_id = str(uuid.uuid4())
        event = ActivityEvent(
            event_id=event_id,
            timestamp=datetime.now(),
            event_type=event_type,
            severity=severity,
            message=message,
            details=details,
        )

        # Append to activity log (JSONL format)
        with open(self.activity_log_file, "a") as f:
            f.write(event.model_dump_json() + "\n")

        return event_id

    # ========================================================================
    # Private helper methods
    # ========================================================================

    async def _count_discovered_hosts(self) -> int:
        """Count unique hosts from scan results."""
        hosts = set()

        # Search for scan result files
        scan_dirs = list(self.base_dir.glob("scan_*"))

        for scan_dir in scan_dirs:
            result_file = scan_dir / "result.json"
            if result_file.exists():
                try:
                    with open(result_file, "r") as f:
                        result = json.load(f)

                    # Extract hosts from different result formats
                    if "hosts_discovered" in result:
                        for host in result["hosts_discovered"]:
                            hosts.add(host.get("ip", host.get("host")))
                    elif "hosts" in result:
                        for host in result["hosts"]:
                            hosts.add(host.get("ip", host.get("host")))

                except (json.JSONDecodeError, KeyError):
                    continue

        return len(hosts)

    async def _count_vulnerabilities(self) -> VulnerabilitySeverityCounts:
        """Count vulnerabilities by severity."""
        counts = {
            "total": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        # Search for vulnerability files
        vuln_files = list(self.base_dir.glob("**/vulnerabilities.json"))

        for vuln_file in vuln_files:
            try:
                with open(vuln_file, "r") as f:
                    vulns = json.load(f)

                if isinstance(vulns, list):
                    for vuln in vulns:
                        severity = vuln.get("severity", "").lower()
                        counts["total"] += 1
                        if severity in counts:
                            counts[severity] += 1

            except (json.JSONDecodeError, KeyError):
                continue

        return VulnerabilitySeverityCounts(**counts)

    async def _count_active_attacks(self) -> int:
        """Count currently running attacks."""
        active = 0

        # Search for attack status files
        attack_dirs = list(self.base_dir.glob("attack_*"))

        for attack_dir in attack_dirs:
            status_file = attack_dir / "status.json"
            if status_file.exists():
                try:
                    with open(status_file, "r") as f:
                        status = json.load(f)

                    if status.get("status") in ["running", "pending"]:
                        active += 1

                except (json.JSONDecodeError, KeyError):
                    continue

        return active

    async def _calculate_success_rate(self) -> float:
        """Calculate attack success rate."""
        total = 0
        successful = 0

        # Search for attack result files
        attack_dirs = list(self.base_dir.glob("attack_*"))

        for attack_dir in attack_dirs:
            result_file = attack_dir / "result.json"
            if result_file.exists():
                try:
                    with open(result_file, "r") as f:
                        result = json.load(f)

                    total += 1
                    if result.get("status") == "success":
                        successful += 1

                except (json.JSONDecodeError, KeyError):
                    continue

        if total == 0:
            return 0.0

        return (successful / total) * 100

    async def _aggregate_host_vulnerabilities(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate vulnerability counts by host."""
        host_data = {}

        # Search for vulnerability files
        vuln_files = list(self.base_dir.glob("**/vulnerabilities.json"))

        for vuln_file in vuln_files:
            try:
                with open(vuln_file, "r") as f:
                    vulns = json.load(f)

                if isinstance(vulns, list):
                    for vuln in vulns:
                        host = vuln.get("host")
                        if not host:
                            continue

                        if host not in host_data:
                            host_data[host] = {
                                "total": 0,
                                "critical": 0,
                                "high": 0,
                                "medium": 0,
                                "low": 0,
                                "hostname": vuln.get("hostname"),
                                "last_scanned": None,
                            }

                        severity = vuln.get("severity", "").lower()
                        host_data[host]["total"] += 1
                        if severity in host_data[host]:
                            host_data[host][severity] += 1

                        # Update last scanned time
                        discovered = vuln.get("discovered_at")
                        if discovered:
                            try:
                                discovered_dt = datetime.fromisoformat(discovered)
                                if (
                                    host_data[host]["last_scanned"] is None
                                    or discovered_dt > host_data[host]["last_scanned"]
                                ):
                                    host_data[host]["last_scanned"] = discovered_dt
                            except ValueError:
                                pass

            except (json.JSONDecodeError, KeyError):
                continue

        return host_data

    def _calculate_host_risk_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate risk score for a host.

        Formula: Weighted sum of vulnerabilities by severity.
        Critical: 10 points, High: 5 points, Medium: 2 points, Low: 1 point
        Max score capped at 100.
        """
        score = (
            data.get("critical", 0) * 10
            + data.get("high", 0) * 5
            + data.get("medium", 0) * 2
            + data.get("low", 0) * 1
        )

        # Cap at 100
        return min(score, 100.0)
