# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Data models for Red Team Dashboard
Following ADCL principle: Clear contracts between backend and frontend
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


# ============================================================================
# Dashboard Models
# ============================================================================

class VulnerabilitySeverityCounts(BaseModel):
    """Vulnerability counts by severity level"""
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class KPIData(BaseModel):
    """Dashboard KPI metrics"""
    hosts_discovered: int = Field(description="Total hosts discovered")
    vulnerabilities: VulnerabilitySeverityCounts = Field(description="Vulnerability counts by severity")
    active_attacks: int = Field(description="Number of currently running attacks")
    success_rate: float = Field(description="Attack success rate percentage (0-100)")


class ActivityEvent(BaseModel):
    """Activity feed event"""
    event_id: str = Field(description="Unique event identifier")
    timestamp: datetime = Field(description="When the event occurred")
    event_type: Literal["scan", "vulnerability", "attack", "system"] = Field(description="Type of event")
    severity: Literal["info", "warning", "error", "success"] = Field(description="Event severity")
    message: str = Field(description="Human-readable event message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional event details")


class TopHost(BaseModel):
    """Top host by vulnerability or importance"""
    host: str = Field(description="IP address or hostname")
    hostname: Optional[str] = Field(default=None, description="Resolved hostname")
    vulnerability_count: int = Field(description="Number of vulnerabilities")
    critical_vulns: int = Field(description="Number of critical vulnerabilities")
    high_vulns: int = Field(description="Number of high vulnerabilities")
    risk_score: float = Field(description="Calculated risk score (0-100)")
    last_scanned: Optional[datetime] = Field(default=None, description="Last scan timestamp")


# ============================================================================
# Scanner Models
# ============================================================================

class ScanType(str, Enum):
    """Types of scans available"""
    DISCOVERY = "discovery"
    DEEP = "deep"
    VULN = "vuln"


class ScanStatus(str, Enum):
    """Scan execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanResults(BaseModel):
    """Scan execution results summary"""
    hosts_found: int = Field(default=0, description="Number of hosts discovered")
    ports_found: int = Field(default=0, description="Total ports found across all hosts")
    vulnerabilities_found: int = Field(default=0, description="Number of vulnerabilities identified")
    scan_duration: Optional[float] = Field(default=None, description="Scan duration in seconds")


class Scan(BaseModel):
    """Scan record"""
    scan_id: str = Field(description="Unique scan identifier")
    target: str = Field(description="Target network or host")
    type: ScanType = Field(description="Type of scan")
    status: ScanStatus = Field(description="Current scan status")
    created_at: datetime = Field(description="When scan was created")
    started_at: Optional[datetime] = Field(default=None, description="When scan started executing")
    completed_at: Optional[datetime] = Field(default=None, description="When scan completed")
    results: ScanResults = Field(default_factory=ScanResults, description="Scan results summary")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    raw_output: Optional[str] = Field(default=None, description="Raw scan output")


class ScanCreateRequest(BaseModel):
    """Request to create a new scan"""
    target: str = Field(description="Target network or host (e.g., 192.168.1.0/24)")
    type: ScanType = Field(default=ScanType.DISCOVERY, description="Type of scan to perform")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Additional scan options")


# ============================================================================
# Vulnerability Models
# ============================================================================

class VulnerabilitySeverity(str, Enum):
    """Vulnerability severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Vulnerability(BaseModel):
    """Vulnerability record"""
    vuln_id: str = Field(description="Unique vulnerability identifier")
    cve: Optional[str] = Field(default=None, description="CVE identifier if applicable")
    title: str = Field(description="Vulnerability title")
    severity: VulnerabilitySeverity = Field(description="Severity level")
    cvss: Optional[float] = Field(default=None, description="CVSS score (0-10)")
    host: str = Field(description="Affected host IP/hostname")
    port: Optional[int] = Field(default=None, description="Affected port")
    service: Optional[str] = Field(default=None, description="Affected service")
    description: Optional[str] = Field(default=None, description="Vulnerability description")
    exploitable: bool = Field(default=False, description="Whether vulnerability is exploitable")
    exploit_available: bool = Field(default=False, description="Whether exploit is publicly available")
    discovered_at: datetime = Field(description="When vulnerability was discovered")
    scan_id: Optional[str] = Field(default=None, description="Scan that discovered this vulnerability")


class VulnerabilityFilters(BaseModel):
    """Filters for vulnerability list endpoint"""
    severity: Optional[VulnerabilitySeverity] = Field(default=None, description="Filter by severity")
    host: Optional[str] = Field(default=None, description="Filter by host")
    exploitable: Optional[bool] = Field(default=None, description="Filter by exploitable status")
    cve: Optional[str] = Field(default=None, description="Filter by CVE")
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


# ============================================================================
# Chat Models
# ============================================================================

class ChatMessageRole(str, Enum):
    """Chat message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Chat message"""
    role: ChatMessageRole = Field(description="Message role")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")


class ChatRequest(BaseModel):
    """Chat request for AI interaction"""
    session_id: str = Field(description="WebSocket session ID")
    message: str = Field(description="User message")
    context: Optional[str] = Field(default=None, description="Context identifier (scanner, vulnerabilities, attack-console)")


class ChatStreamEvent(BaseModel):
    """Streaming chat event"""
    type: Literal["status", "thinking", "tool_use", "response", "complete", "error"] = Field(description="Event type")
    content: Optional[str] = Field(default=None, description="Event content")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional event data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")


# ============================================================================
# Attack Console Models (Reuse existing WorkflowEngine)
# ============================================================================

class AttackTarget(BaseModel):
    """Attack target information"""
    host: str = Field(description="Target host")
    port: Optional[int] = Field(default=None, description="Target port")
    service: Optional[str] = Field(default=None, description="Target service")
    vulnerabilities: List[str] = Field(default_factory=list, description="Associated vulnerability IDs")


class AttackRequest(BaseModel):
    """Request to execute an attack workflow"""
    workflow_id: str = Field(description="Workflow ID to execute")
    target: AttackTarget = Field(description="Attack target")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")
