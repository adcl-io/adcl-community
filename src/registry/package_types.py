# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Package Type Definitions for Agent Registry

Defines data structures for agents, MCPs, and teams with GPG signature support.
Implements YUM-style package format with dependencies and metadata.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class PackageType(str, Enum):
    """Package types supported by the registry"""
    AGENT = "agent"
    MCP = "mcp"
    TEAM = "team"
    TRIGGER = "trigger"


@dataclass
class Dependency:
    """
    Represents a package dependency with exact version requirement.

    Used by Team packages to specify required agents and MCPs.
    """
    type: str  # 'agent' or 'mcp'
    name: str
    version: str  # Exact version required (e.g., "1.0.0")

    def __post_init__(self):
        """Validate dependency fields"""
        if self.type not in ['agent', 'mcp']:
            raise ValueError(f"Invalid dependency type: {self.type}. Must be 'agent' or 'mcp'")

        if not self.name:
            raise ValueError("Dependency name cannot be empty")

        if not self.version:
            raise ValueError("Dependency version cannot be empty")

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'version': self.version
        }

    @classmethod
    def from_dict(cls, data: Dict, dep_type: str) -> 'Dependency':
        """Create Dependency from dictionary"""
        return cls(
            type=dep_type,
            name=data['name'],
            version=data['version']
        )

    def __str__(self) -> str:
        return f"{self.type}/{self.name}@{self.version}"


@dataclass
class SignatureInfo:
    """GPG signature metadata"""
    algorithm: str = "GPG"
    key_id: Optional[str] = None
    fingerprint: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> 'SignatureInfo':
        """Create SignatureInfo from dictionary"""
        return cls(
            algorithm=data.get('algorithm', 'GPG'),
            key_id=data.get('key_id'),
            fingerprint=data.get('fingerprint'),
            created_at=data.get('created_at')
        )


@dataclass
class PackageMetadata:
    """
    Package metadata stored in metadata.json.

    Contains signature info, checksums, and publication details.
    """
    type: str
    name: str
    version: str
    publisher: str
    description: str = ""
    signature: Optional[SignatureInfo] = None
    checksums: Dict[str, str] = field(default_factory=dict)
    published_at: Optional[str] = None
    dependencies: Optional[Dict[str, List[Dict]]] = None  # Only for teams

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {
            'type': self.type,
            'name': self.name,
            'version': self.version,
            'publisher': self.publisher,
            'description': self.description,
            'checksums': self.checksums,
            'published_at': self.published_at or datetime.now().isoformat()
        }

        if self.signature:
            result['signature'] = self.signature.to_dict()

        if self.dependencies:
            result['dependencies'] = self.dependencies

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> 'PackageMetadata':
        """Create PackageMetadata from dictionary"""
        signature = None
        if 'signature' in data:
            signature = SignatureInfo.from_dict(data['signature'])

        return cls(
            type=data['type'],
            name=data['name'],
            version=data['version'],
            publisher=data['publisher'],
            description=data.get('description', ''),
            signature=signature,
            checksums=data.get('checksums', {}),
            published_at=data.get('published_at'),
            dependencies=data.get('dependencies')
        )


@dataclass
class Package:
    """
    Base package class representing an agent, MCP, or team.

    Contains the package configuration, metadata, and dependencies.
    """
    type: PackageType
    name: str
    version: str
    publisher: str
    config: Dict[str, Any]  # The actual JSON content (agent.json, mcp.json, or team.json)
    dependencies: List[Dependency] = field(default_factory=list)
    metadata: Optional[PackageMetadata] = None

    def __post_init__(self):
        """Validate package fields"""
        if not self.name:
            raise ValueError("Package name cannot be empty")

        if not self.version:
            raise ValueError("Package version cannot be empty")

        if not self.publisher:
            raise ValueError("Package publisher cannot be empty")

        if not self.config:
            raise ValueError("Package config cannot be empty")

        # For team packages, extract dependencies from config
        if self.type == PackageType.TEAM and not self.dependencies:
            self._extract_team_dependencies()

    def _extract_team_dependencies(self):
        """Extract dependencies from team config"""
        if 'dependencies' not in self.config:
            return

        deps_config = self.config['dependencies']

        # Extract agent dependencies
        for agent_dep in deps_config.get('agents', []):
            self.dependencies.append(
                Dependency(
                    type='agent',
                    name=agent_dep['name'],
                    version=agent_dep['version']
                )
            )

        # Extract MCP dependencies
        for mcp_dep in deps_config.get('mcps', []):
            self.dependencies.append(
                Dependency(
                    type='mcp',
                    name=mcp_dep['name'],
                    version=mcp_dep['version']
                )
            )

    def calculate_checksums(self, config_content: str) -> Dict[str, str]:
        """
        Calculate checksums for package content.

        Args:
            config_content: The JSON content as string

        Returns:
            Dictionary with sha256 and md5 checksums
        """
        content_bytes = config_content.encode('utf-8')

        return {
            'sha256': hashlib.sha256(content_bytes).hexdigest(),
            'md5': hashlib.md5(content_bytes).hexdigest()
        }

    def to_config_dict(self) -> Dict:
        """Return the package config (for writing to agent.json, mcp.json, or team.json)"""
        return self.config

    def to_metadata_dict(self) -> Dict:
        """Return metadata dictionary (for writing to metadata.json)"""
        if self.metadata:
            return self.metadata.to_dict()

        # Create metadata from package info
        metadata = PackageMetadata(
            type=self.type.value,
            name=self.name,
            version=self.version,
            publisher=self.publisher,
            description=self.config.get('description', ''),
            published_at=datetime.now().isoformat()
        )

        # Add dependencies for teams
        if self.type == PackageType.TEAM and self.dependencies:
            deps_by_type = {'agents': [], 'mcps': []}
            for dep in self.dependencies:
                if dep.type == 'agent':
                    deps_by_type['agents'].append(dep.to_dict())
                elif dep.type == 'mcp':
                    deps_by_type['mcps'].append(dep.to_dict())
            metadata.dependencies = deps_by_type

        return metadata.to_dict()

    @classmethod
    def from_files(
        cls,
        package_dir: Path,
        package_type: PackageType
    ) -> 'Package':
        """
        Load package from directory containing config and metadata files.

        Args:
            package_dir: Path to package directory
            package_type: Type of package (agent, mcp, or team)

        Returns:
            Package instance

        Raises:
            FileNotFoundError: If required files don't exist
            ValueError: If package structure is invalid
        """
        # Determine config filename
        if package_type == PackageType.AGENT:
            config_file = package_dir / 'agent.json'
        elif package_type == PackageType.MCP:
            config_file = package_dir / 'mcp.json'
        elif package_type == PackageType.TEAM:
            config_file = package_dir / 'team.json'
        elif package_type == PackageType.TRIGGER:
            config_file = package_dir / 'trigger.json'
        else:
            raise ValueError(f"Unknown package type: {package_type}")

        if not config_file.exists():
            raise FileNotFoundError(f"Package config not found: {config_file}")

        # Load config
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Load metadata if exists
        metadata_file = package_dir / 'metadata.json'
        metadata = None
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata_dict = json.load(f)
                metadata = PackageMetadata.from_dict(metadata_dict)

        # Extract package info from config
        name = config.get('name')
        version = config.get('version')
        publisher = config.get('publisher')

        if not all([name, version, publisher]):
            raise ValueError(
                f"Package config missing required fields: name, version, or publisher. "
                f"Found: name={name}, version={version}, publisher={publisher}"
            )

        return cls(
            type=package_type,
            name=name,
            version=version,
            publisher=publisher,
            config=config,
            metadata=metadata
        )

    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        package_type: PackageType
    ) -> 'Package':
        """
        Create package from configuration dictionary.

        Args:
            config: Package configuration dictionary
            package_type: Type of package (agent, mcp, or team)

        Returns:
            Package instance

        Raises:
            ValueError: If config is missing required fields
        """
        name = config.get('name')
        version = config.get('version')
        publisher = config.get('publisher')

        if not all([name, version, publisher]):
            raise ValueError(
                f"Package config missing required fields: name, version, or publisher"
            )

        return cls(
            type=package_type,
            name=name,
            version=version,
            publisher=publisher,
            config=config
        )

    def get_dependency_tree(self) -> Dict[str, List[str]]:
        """
        Get dependency tree organized by type.

        Returns:
            Dictionary with 'agents' and 'mcps' lists
        """
        tree = {'agents': [], 'mcps': []}

        for dep in self.dependencies:
            if dep.type == 'agent':
                tree['agents'].append(str(dep))
            elif dep.type == 'mcp':
                tree['mcps'].append(str(dep))

        return tree

    def __str__(self) -> str:
        return f"{self.type.value}/{self.name}@{self.version}"


def validate_package_structure(package_dir: Path, package_type: PackageType) -> bool:
    """
    Validate that a package directory has the correct structure.

    Args:
        package_dir: Path to package directory
        package_type: Expected package type

    Returns:
        True if valid, False otherwise

    Raises:
        ValueError: If validation fails with details
    """
    if not package_dir.exists():
        raise ValueError(f"Package directory does not exist: {package_dir}")

    # Check for config file
    if package_type == PackageType.AGENT:
        config_file = package_dir / 'agent.json'
    elif package_type == PackageType.MCP:
        config_file = package_dir / 'mcp.json'
    elif package_type == PackageType.TEAM:
        config_file = package_dir / 'team.json'
    elif package_type == PackageType.TRIGGER:
        config_file = package_dir / 'trigger.json'
    else:
        raise ValueError(f"Unknown package type: {package_type}")

    if not config_file.exists():
        raise ValueError(f"Missing config file: {config_file}")

    # Check for signature
    signature_file = config_file.with_suffix(config_file.suffix + '.asc')
    if not signature_file.exists():
        raise ValueError(f"Missing signature file: {signature_file}")

    # Validate JSON structure
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Check required fields
        required_fields = ['name', 'version', 'publisher']
        missing_fields = [f for f in required_fields if f not in config]

        if missing_fields:
            raise ValueError(f"Config missing required fields: {', '.join(missing_fields)}")

        # For teams, validate dependencies
        if package_type == PackageType.TEAM:
            if 'dependencies' not in config:
                raise ValueError("Team config missing 'dependencies' field")

            deps = config['dependencies']
            if 'agents' not in deps and 'mcps' not in deps:
                raise ValueError("Team dependencies must include 'agents' or 'mcps'")

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")

    return True
