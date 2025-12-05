# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit Tests for Package Type Definitions

Tests package structures, dependency handling, and metadata management
for agents, MCPs, and teams.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from src.registry.package_types import (
    PackageType,
    Dependency,
    SignatureInfo,
    PackageMetadata,
    Package,
    validate_package_structure
)


class TestDependency:
    """Test suite for Dependency class"""

    def test_create_agent_dependency(self):
        """Test creating an agent dependency"""
        dep = Dependency(
            type='agent',
            name='security-analyst',
            version='1.0.0'
        )

        assert dep.type == 'agent'
        assert dep.name == 'security-analyst'
        assert dep.version == '1.0.0'
        assert str(dep) == 'agent/security-analyst@1.0.0'

    def test_create_mcp_dependency(self):
        """Test creating an MCP dependency"""
        dep = Dependency(
            type='mcp',
            name='nmap_recon',
            version='2.1.0'
        )

        assert dep.type == 'mcp'
        assert dep.name == 'nmap_recon'
        assert dep.version == '2.1.0'

    def test_invalid_dependency_type(self):
        """Test that invalid dependency type raises error"""
        with pytest.raises(ValueError, match="Invalid dependency type"):
            Dependency(
                type='invalid',
                name='test',
                version='1.0.0'
            )

    def test_empty_dependency_name(self):
        """Test that empty name raises error"""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Dependency(
                type='agent',
                name='',
                version='1.0.0'
            )

    def test_empty_dependency_version(self):
        """Test that empty version raises error"""
        with pytest.raises(ValueError, match="version cannot be empty"):
            Dependency(
                type='agent',
                name='test',
                version=''
            )

    def test_dependency_to_dict(self):
        """Test converting dependency to dictionary"""
        dep = Dependency(
            type='agent',
            name='security-analyst',
            version='1.0.0'
        )

        dep_dict = dep.to_dict()

        assert dep_dict == {
            'name': 'security-analyst',
            'version': '1.0.0'
        }

    def test_dependency_from_dict(self):
        """Test creating dependency from dictionary"""
        dep_dict = {
            'name': 'nmap_recon',
            'version': '2.1.0'
        }

        dep = Dependency.from_dict(dep_dict, 'mcp')

        assert dep.type == 'mcp'
        assert dep.name == 'nmap_recon'
        assert dep.version == '2.1.0'


class TestSignatureInfo:
    """Test suite for SignatureInfo class"""

    def test_create_signature_info(self):
        """Test creating signature info"""
        sig_info = SignatureInfo(
            algorithm='GPG',
            key_id='ABC123',
            fingerprint='1234 5678 9ABC DEF0',
            created_at='2025-10-17T12:00:00Z'
        )

        assert sig_info.algorithm == 'GPG'
        assert sig_info.key_id == 'ABC123'
        assert sig_info.fingerprint == '1234 5678 9ABC DEF0'
        assert sig_info.created_at == '2025-10-17T12:00:00Z'

    def test_signature_info_defaults(self):
        """Test signature info with defaults"""
        sig_info = SignatureInfo()

        assert sig_info.algorithm == 'GPG'
        assert sig_info.key_id is None
        assert sig_info.fingerprint is None
        assert sig_info.created_at is None

    def test_signature_info_to_dict(self):
        """Test converting signature info to dictionary"""
        sig_info = SignatureInfo(
            algorithm='GPG',
            key_id='ABC123',
            fingerprint='1234 5678'
        )

        sig_dict = sig_info.to_dict()

        assert sig_dict['algorithm'] == 'GPG'
        assert sig_dict['key_id'] == 'ABC123'
        assert sig_dict['fingerprint'] == '1234 5678'
        # created_at should not be in dict if None
        assert 'created_at' not in sig_dict

    def test_signature_info_from_dict(self):
        """Test creating signature info from dictionary"""
        sig_dict = {
            'algorithm': 'GPG',
            'key_id': 'XYZ789',
            'fingerprint': 'ABCD EFGH'
        }

        sig_info = SignatureInfo.from_dict(sig_dict)

        assert sig_info.algorithm == 'GPG'
        assert sig_info.key_id == 'XYZ789'
        assert sig_info.fingerprint == 'ABCD EFGH'


class TestPackageMetadata:
    """Test suite for PackageMetadata class"""

    def test_create_agent_metadata(self):
        """Test creating agent metadata"""
        metadata = PackageMetadata(
            type='agent',
            name='security-analyst',
            version='1.0.0',
            publisher='jason@adcl',
            description='Security analysis agent'
        )

        assert metadata.type == 'agent'
        assert metadata.name == 'security-analyst'
        assert metadata.version == '1.0.0'
        assert metadata.publisher == 'jason@adcl'

    def test_metadata_with_signature(self):
        """Test metadata with signature info"""
        sig_info = SignatureInfo(
            algorithm='GPG',
            key_id='ABC123'
        )

        metadata = PackageMetadata(
            type='mcp',
            name='nmap_recon',
            version='2.0.0',
            publisher='security-team@company.com',
            signature=sig_info
        )

        assert metadata.signature is not None
        assert metadata.signature.key_id == 'ABC123'

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary"""
        metadata = PackageMetadata(
            type='agent',
            name='test-agent',
            version='1.0.0',
            publisher='test@example.com',
            description='Test agent',
            checksums={'sha256': 'abc123'}
        )

        meta_dict = metadata.to_dict()

        assert meta_dict['type'] == 'agent'
        assert meta_dict['name'] == 'test-agent'
        assert meta_dict['version'] == '1.0.0'
        assert meta_dict['publisher'] == 'test@example.com'
        assert meta_dict['checksums']['sha256'] == 'abc123'
        assert 'published_at' in meta_dict

    def test_metadata_from_dict(self):
        """Test creating metadata from dictionary"""
        meta_dict = {
            'type': 'mcp',
            'name': 'file_tools',
            'version': '1.0.0',
            'publisher': 'tools@example.com',
            'description': 'File management tools',
            'checksums': {'md5': 'def456'},
            'published_at': '2025-10-17T12:00:00Z'
        }

        metadata = PackageMetadata.from_dict(meta_dict)

        assert metadata.type == 'mcp'
        assert metadata.name == 'file_tools'
        assert metadata.checksums['md5'] == 'def456'


class TestPackage:
    """Test suite for Package class"""

    def test_create_agent_package(self):
        """Test creating an agent package"""
        config = {
            'name': 'security-analyst',
            'version': '1.0.0',
            'publisher': 'jason@adcl',
            'description': 'Security analysis agent',
            'prompt': 'You are a security analyst...'
        }

        package = Package(
            type=PackageType.AGENT,
            name='security-analyst',
            version='1.0.0',
            publisher='jason@adcl',
            config=config
        )

        assert package.type == PackageType.AGENT
        assert package.name == 'security-analyst'
        assert package.version == '1.0.0'
        assert package.dependencies == []
        assert str(package) == 'agent/security-analyst@1.0.0'

    def test_create_mcp_package(self):
        """Test creating an MCP package"""
        config = {
            'name': 'nmap_recon',
            'version': '2.1.0',
            'publisher': 'security-team@company.com',
            'description': 'Nmap reconnaissance tools',
            'tools': ['network_discovery', 'port_scan']
        }

        package = Package(
            type=PackageType.MCP,
            name='nmap_recon',
            version='2.1.0',
            publisher='security-team@company.com',
            config=config
        )

        assert package.type == PackageType.MCP
        assert package.name == 'nmap_recon'

    def test_create_team_package_with_dependencies(self):
        """Test creating a team package with dependencies"""
        config = {
            'name': 'pentest',
            'version': '1.0.0',
            'publisher': 'jason@adcl',
            'description': 'Penetration testing team',
            'dependencies': {
                'agents': [
                    {'name': 'security-analyst', 'version': '1.0.0'},
                    {'name': 'reporter', 'version': '1.2.0'}
                ],
                'mcps': [
                    {'name': 'nmap_recon', 'version': '2.1.0'},
                    {'name': 'file_tools', 'version': '1.0.0'}
                ]
            },
            'workflow': {}
        }

        package = Package(
            type=PackageType.TEAM,
            name='pentest',
            version='1.0.0',
            publisher='jason@adcl',
            config=config
        )

        assert package.type == PackageType.TEAM
        assert len(package.dependencies) == 4

        # Check agent dependencies
        agent_deps = [d for d in package.dependencies if d.type == 'agent']
        assert len(agent_deps) == 2
        assert any(d.name == 'security-analyst' for d in agent_deps)

        # Check MCP dependencies
        mcp_deps = [d for d in package.dependencies if d.type == 'mcp']
        assert len(mcp_deps) == 2
        assert any(d.name == 'nmap_recon' for d in mcp_deps)

    def test_package_missing_required_fields(self):
        """Test that missing required fields raise error"""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Package(
                type=PackageType.AGENT,
                name='',
                version='1.0.0',
                publisher='test@example.com',
                config={}
            )

    def test_package_calculate_checksums(self):
        """Test calculating package checksums"""
        config = {
            'name': 'test-agent',
            'version': '1.0.0',
            'publisher': 'test@example.com'
        }

        package = Package(
            type=PackageType.AGENT,
            name='test-agent',
            version='1.0.0',
            publisher='test@example.com',
            config=config
        )

        config_str = json.dumps(config, sort_keys=True, indent=2)
        checksums = package.calculate_checksums(config_str)

        assert 'sha256' in checksums
        assert 'md5' in checksums
        assert len(checksums['sha256']) == 64  # SHA256 hex length
        assert len(checksums['md5']) == 32  # MD5 hex length

    def test_package_to_config_dict(self):
        """Test converting package to config dictionary"""
        config = {
            'name': 'test-agent',
            'version': '1.0.0',
            'publisher': 'test@example.com',
            'prompt': 'Test prompt'
        }

        package = Package(
            type=PackageType.AGENT,
            name='test-agent',
            version='1.0.0',
            publisher='test@example.com',
            config=config
        )

        config_dict = package.to_config_dict()

        assert config_dict == config

    def test_package_to_metadata_dict(self):
        """Test converting package to metadata dictionary"""
        config = {
            'name': 'test-agent',
            'version': '1.0.0',
            'publisher': 'test@example.com',
            'description': 'Test agent'
        }

        package = Package(
            type=PackageType.AGENT,
            name='test-agent',
            version='1.0.0',
            publisher='test@example.com',
            config=config
        )

        meta_dict = package.to_metadata_dict()

        assert meta_dict['type'] == 'agent'
        assert meta_dict['name'] == 'test-agent'
        assert meta_dict['version'] == '1.0.0'
        assert meta_dict['publisher'] == 'test@example.com'
        assert 'published_at' in meta_dict

    def test_team_package_metadata_includes_dependencies(self):
        """Test that team metadata includes dependencies"""
        config = {
            'name': 'test-team',
            'version': '1.0.0',
            'publisher': 'test@example.com',
            'dependencies': {
                'agents': [{'name': 'agent1', 'version': '1.0.0'}],
                'mcps': [{'name': 'mcp1', 'version': '1.0.0'}]
            }
        }

        package = Package(
            type=PackageType.TEAM,
            name='test-team',
            version='1.0.0',
            publisher='test@example.com',
            config=config
        )

        meta_dict = package.to_metadata_dict()

        assert 'dependencies' in meta_dict
        assert 'agents' in meta_dict['dependencies']
        assert 'mcps' in meta_dict['dependencies']

    def test_package_from_config(self):
        """Test creating package from config dictionary"""
        config = {
            'name': 'test-agent',
            'version': '1.0.0',
            'publisher': 'test@example.com',
            'prompt': 'Test prompt'
        }

        package = Package.from_config(config, PackageType.AGENT)

        assert package.name == 'test-agent'
        assert package.version == '1.0.0'
        assert package.publisher == 'test@example.com'
        assert package.config == config

    def test_package_from_config_missing_fields(self):
        """Test that from_config fails with missing fields"""
        config = {
            'name': 'test-agent'
            # Missing version and publisher
        }

        with pytest.raises(ValueError, match="missing required fields"):
            Package.from_config(config, PackageType.AGENT)

    def test_package_get_dependency_tree(self):
        """Test getting dependency tree"""
        config = {
            'name': 'test-team',
            'version': '1.0.0',
            'publisher': 'test@example.com',
            'dependencies': {
                'agents': [
                    {'name': 'agent1', 'version': '1.0.0'},
                    {'name': 'agent2', 'version': '1.1.0'}
                ],
                'mcps': [
                    {'name': 'mcp1', 'version': '2.0.0'}
                ]
            }
        }

        package = Package(
            type=PackageType.TEAM,
            name='test-team',
            version='1.0.0',
            publisher='test@example.com',
            config=config
        )

        tree = package.get_dependency_tree()

        assert len(tree['agents']) == 2
        assert len(tree['mcps']) == 1
        assert 'agent/agent1@1.0.0' in tree['agents']
        assert 'mcp/mcp1@2.0.0' in tree['mcps']


class TestPackageFromFiles:
    """Test suite for loading packages from filesystem"""

    @pytest.fixture
    def temp_package_dir(self):
        """Create temporary directory for package files"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_load_agent_from_files(self, temp_package_dir):
        """Test loading agent package from files"""
        config = {
            'name': 'test-agent',
            'version': '1.0.0',
            'publisher': 'test@example.com',
            'description': 'Test agent'
        }

        # Write config file
        config_file = temp_package_dir / 'agent.json'
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # Write metadata file
        metadata = {
            'type': 'agent',
            'name': 'test-agent',
            'version': '1.0.0',
            'publisher': 'test@example.com',
            'published_at': '2025-10-17T12:00:00Z'
        }

        metadata_file = temp_package_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Load package
        package = Package.from_files(temp_package_dir, PackageType.AGENT)

        assert package.name == 'test-agent'
        assert package.version == '1.0.0'
        assert package.type == PackageType.AGENT
        assert package.metadata is not None

    def test_load_team_from_files(self, temp_package_dir):
        """Test loading team package from files"""
        config = {
            'name': 'test-team',
            'version': '1.0.0',
            'publisher': 'test@example.com',
            'dependencies': {
                'agents': [{'name': 'agent1', 'version': '1.0.0'}],
                'mcps': []
            }
        }

        # Write config file
        config_file = temp_package_dir / 'team.json'
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # Load package
        package = Package.from_files(temp_package_dir, PackageType.TEAM)

        assert package.name == 'test-team'
        assert package.type == PackageType.TEAM
        assert len(package.dependencies) == 1

    def test_load_package_missing_file(self, temp_package_dir):
        """Test that loading fails when config file is missing"""
        with pytest.raises(FileNotFoundError):
            Package.from_files(temp_package_dir, PackageType.AGENT)

    def test_load_package_invalid_config(self, temp_package_dir):
        """Test that loading fails with invalid config"""
        config = {
            'name': 'test-agent'
            # Missing version and publisher
        }

        config_file = temp_package_dir / 'agent.json'
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        with pytest.raises(ValueError, match="missing required fields"):
            Package.from_files(temp_package_dir, PackageType.AGENT)


class TestValidatePackageStructure:
    """Test suite for package structure validation"""

    @pytest.fixture
    def temp_package_dir(self):
        """Create temporary directory for package files"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_validate_valid_agent_package(self, temp_package_dir):
        """Test validating a valid agent package"""
        config = {
            'name': 'test-agent',
            'version': '1.0.0',
            'publisher': 'test@example.com'
        }

        # Write config file
        config_file = temp_package_dir / 'agent.json'
        with open(config_file, 'w') as f:
            json.dump(config, f)

        # Write signature file
        signature_file = temp_package_dir / 'agent.json.asc'
        signature_file.write_text('-----BEGIN PGP SIGNATURE-----\nfake signature\n-----END PGP SIGNATURE-----')

        # Validate
        result = validate_package_structure(temp_package_dir, PackageType.AGENT)
        assert result is True

    def test_validate_missing_config_file(self, temp_package_dir):
        """Test validation fails when config file is missing"""
        with pytest.raises(ValueError, match="Missing config file"):
            validate_package_structure(temp_package_dir, PackageType.AGENT)

    def test_validate_missing_signature_file(self, temp_package_dir):
        """Test validation fails when signature file is missing"""
        config = {
            'name': 'test-agent',
            'version': '1.0.0',
            'publisher': 'test@example.com'
        }

        config_file = temp_package_dir / 'agent.json'
        with open(config_file, 'w') as f:
            json.dump(config, f)

        # No signature file

        with pytest.raises(ValueError, match="Missing signature file"):
            validate_package_structure(temp_package_dir, PackageType.AGENT)

    def test_validate_invalid_json(self, temp_package_dir):
        """Test validation fails with invalid JSON"""
        config_file = temp_package_dir / 'agent.json'
        config_file.write_text('{ invalid json }')

        signature_file = temp_package_dir / 'agent.json.asc'
        signature_file.write_text('signature')

        with pytest.raises(ValueError, match="Invalid JSON"):
            validate_package_structure(temp_package_dir, PackageType.AGENT)

    def test_validate_missing_required_fields(self, temp_package_dir):
        """Test validation fails with missing required fields"""
        config = {
            'name': 'test-agent'
            # Missing version and publisher
        }

        config_file = temp_package_dir / 'agent.json'
        with open(config_file, 'w') as f:
            json.dump(config, f)

        signature_file = temp_package_dir / 'agent.json.asc'
        signature_file.write_text('signature')

        with pytest.raises(ValueError, match="missing required fields"):
            validate_package_structure(temp_package_dir, PackageType.AGENT)

    def test_validate_team_missing_dependencies(self, temp_package_dir):
        """Test validation fails for team without dependencies"""
        config = {
            'name': 'test-team',
            'version': '1.0.0',
            'publisher': 'test@example.com'
            # Missing dependencies
        }

        config_file = temp_package_dir / 'team.json'
        with open(config_file, 'w') as f:
            json.dump(config, f)

        signature_file = temp_package_dir / 'team.json.asc'
        signature_file.write_text('signature')

        with pytest.raises(ValueError, match="missing 'dependencies' field"):
            validate_package_structure(temp_package_dir, PackageType.TEAM)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
