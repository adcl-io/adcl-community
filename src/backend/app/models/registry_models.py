# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Registry Data Models

Defines data structures for the YUM-style registry system including
packages, dependencies, transactions, and installation records.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from enum import Enum


class PackageType(str, Enum):
    """Type of package"""
    MCP = "mcp"
    AGENT = "agent"
    TEAM = "team"
    TRIGGER = "trigger"


class DependencyType(str, Enum):
    """Type of dependency"""
    MCP = "mcps"
    AGENT = "agents"


class TransactionStatus(str, Enum):
    """Transaction status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class TransactionOperation(str, Enum):
    """Type of transaction operation"""
    INSTALL = "install"
    UPDATE = "update"
    REMOVE = "remove"
    ROLLBACK = "rollback"


class TrustLevel(str, Enum):
    """Registry trust level"""
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    UNKNOWN = "unknown"


class VersionConstraint(BaseModel):
    """
    Version constraint for dependencies.

    ADCL uses exact version matching only (no semver ranges).
    Example: "1.0.0" means exactly version 1.0.0
    """
    name: str
    version: str  # Exact version (e.g., "1.0.0")
    required: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "name": "file_tools",
                "version": "1.0.0",
                "required": True
            }
        }


class PackageDependencies(BaseModel):
    """Package dependencies"""
    mcps: List[VersionConstraint] = Field(default_factory=list)
    agents: List[VersionConstraint] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "mcps": [{"name": "file_tools", "version": "^1.0.0", "required": True}],
                "agents": []
            }
        }


class CompatibilityInfo(BaseModel):
    """Compatibility information"""
    min_adcl_version: Optional[str] = None
    max_adcl_version: Optional[str] = None
    python_version: Optional[str] = None
    os_requirements: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "min_adcl_version": "0.5.0",
                "max_adcl_version": "1.x.x",
                "python_version": ">=3.11",
                "os_requirements": ["linux"]
            }
        }


class ResourceRequirements(BaseModel):
    """Resource requirements for package"""
    min_memory: Optional[str] = None
    min_cpu: Optional[str] = None
    min_disk: Optional[str] = None
    api_keys: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "min_memory": "512M",
                "min_cpu": "0.5",
                "min_disk": "100M",
                "api_keys": ["ANTHROPIC_API_KEY"]
            }
        }


class DeploymentConfig(BaseModel):
    """Deployment configuration for Docker containers"""
    image: str
    container_name: str
    ports: List[Dict[str, str]] = Field(default_factory=list)
    volumes: List[Dict[str, str]] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)
    networks: List[str] = Field(default_factory=list)
    restart: str = "unless-stopped"
    network_mode: Optional[str] = None
    cap_add: List[str] = Field(default_factory=list)
    build: Optional[Dict[str, str]] = None


class PackageMetadata(BaseModel):
    """Complete package metadata"""
    name: str
    version: str
    description: str
    type: PackageType
    dependencies: PackageDependencies = Field(default_factory=PackageDependencies)
    compatibility: CompatibilityInfo = Field(default_factory=CompatibilityInfo)
    requirements: ResourceRequirements = Field(default_factory=ResourceRequirements)
    deployment: DeploymentConfig
    tools: List[Dict[str, str]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    license: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    checksum: Optional[str] = None  # SHA256 checksum
    signature: Optional[str] = None  # GPG signature

    class Config:
        json_schema_extra = {
            "example": {
                "name": "nmap-recon",
                "version": "1.0.0",
                "description": "Network reconnaissance using Nmap",
                "type": "mcp",
                "dependencies": {
                    "mcps": [{"name": "file_tools", "version": "^1.0.0", "required": True}],
                    "agents": []
                }
            }
        }


class PackageInfo(BaseModel):
    """Package information from registry"""
    metadata: PackageMetadata
    registry_name: str
    registry_url: str
    available_versions: List[str] = Field(default_factory=list)
    last_updated: Optional[datetime] = None


class InstallationRecord(BaseModel):
    """Record of an installed package"""
    name: str
    version: str
    installed_at: datetime
    installed_from: str  # Registry name
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    dependencies_installed: List[str] = Field(default_factory=list)
    transaction_id: str
    metadata: Optional[PackageMetadata] = None


class BackupState(BaseModel):
    """Backup state for rollback"""
    installed_packages: Dict[str, Any]
    container_ids: List[str] = Field(default_factory=list)
    container_states: Dict[str, str] = Field(default_factory=dict)
    files_backed_up: List[str] = Field(default_factory=list)


class TransactionRecord(BaseModel):
    """Transaction record for operations"""
    id: str
    operation: TransactionOperation
    package_name: str
    version: Optional[str] = None
    dependencies_installed: List[str] = Field(default_factory=list)
    dependencies_updated: List[str] = Field(default_factory=list)
    dependencies_removed: List[str] = Field(default_factory=list)
    status: TransactionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    backup_state: Optional[BackupState] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "operation": self.operation.value,
            "package_name": self.package_name,
            "version": self.version,
            "dependencies_installed": self.dependencies_installed,
            "dependencies_updated": self.dependencies_updated,
            "dependencies_removed": self.dependencies_removed,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "backup_state": self.backup_state.model_dump() if self.backup_state else None
        }


class RegistryConfig(BaseModel):
    """Registry configuration from registries.conf"""
    name: str
    display_name: str
    url: str
    enabled: bool = True
    priority: int = 50  # Lower number = higher priority
    gpgcheck: bool = False
    gpgkey: Optional[str] = None
    trust_level: TrustLevel = TrustLevel.UNKNOWN
    type: str = "adcl-v2"


class InstallOptions(BaseModel):
    """Options for package installation"""
    skip_dependencies: bool = False
    verify_signature: bool = False
    force: bool = False
    registry: Optional[str] = None  # Specific registry to use
    no_rollback: bool = False  # Disable automatic rollback on failure


class DependencyConflict(BaseModel):
    """Dependency conflict information"""
    package_name: str
    required_by: List[str]
    conflicting_versions: Dict[str, str]
    resolution: Optional[str] = None


class PackageSearchResult(BaseModel):
    """Search result for package"""
    name: str
    version: str
    description: str
    registry: str
    tags: List[str] = Field(default_factory=list)
    installed: bool = False
    installed_version: Optional[str] = None


class DependencyNode(BaseModel):
    """Node in dependency graph"""
    name: str
    version: str
    required_by: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    depth: int = 0


class DependencyGraph(BaseModel):
    """Complete dependency graph"""
    root: str
    nodes: Dict[str, DependencyNode]
    installation_order: List[str] = Field(default_factory=list)
    conflicts: List[DependencyConflict] = Field(default_factory=list)
