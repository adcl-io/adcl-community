# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Registry Service - Modular Composition

Composes focused modules into unified registry service.
Each module does one thing well, following Unix philosophy.
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.models.registry_models import (
    RegistryConfig,
    PackageInfo,
    PackageSearchResult,
    InstallOptions,
    TransactionRecord,
    InstallationRecord
)
from app.mcp_manager import MCPManager

from .config import RegistryConfigLoader
from .index import PackageIndexManager
from .resolver import DependencyResolver
from .transactions import TransactionLogger
from .operations import PackageOperations
from .failover import FailoverConfig

logger = logging.getLogger(__name__)


class RegistryService:
    """
    Unified registry service (modular composition).

    Composes:
    - RegistryConfigLoader: Load registries.conf
    - PackageIndexManager: Search, refresh index
    - DependencyResolver: Resolve dependencies
    - TransactionLogger: Log transactions
    - PackageOperations: Install/update/remove
    """

    def __init__(
        self, 
        base_dir: str = "/app", 
        configs_dir: Optional[str] = None, 
        mcp_manager: Optional[MCPManager] = None,
        failover_config: Optional[FailoverConfig] = None
    ):
        """
        Initialize Registry Service.

        Args:
            base_dir: Base directory for ADCL installation
            configs_dir: Optional configs directory (defaults to base_dir/configs or /configs if it exists)
            mcp_manager: MCPManager instance for container lifecycle
            failover_config: Optional failover configuration
        """
        self.base_dir = Path(base_dir)

        # Auto-detect configs directory: prefer /configs if it exists, else use base_dir/configs
        if configs_dir:
            self.configs_dir = Path(configs_dir)
        elif Path("/configs").exists() and Path("/configs").is_dir():
            self.configs_dir = Path("/configs")
        else:
            self.configs_dir = self.base_dir / "configs"

        self.registries_dir = self.configs_dir / "registries.d"
        self.keys_dir = self.configs_dir / "keys"
        self.packages_dir = self.base_dir / "packages"
        self.mcp_servers_dir = self.base_dir / "mcp_servers"

        # File paths
        self.registries_file = self.configs_dir / "registries.conf"
        self.package_index_file = self.configs_dir / "package-index.json"
        self.installed_packages_file = self.configs_dir / "installed-packages.json"
        self.transactions_log = self.configs_dir / "transactions.jsonl"

        # Ensure directories exist
        self.configs_dir.mkdir(exist_ok=True)
        self.registries_dir.mkdir(exist_ok=True)
        self.keys_dir.mkdir(exist_ok=True)
        self.packages_dir.mkdir(exist_ok=True)

        # MCP Manager for container operations
        self.mcp_manager = mcp_manager or MCPManager(str(base_dir))

        # Initialize modular components
        self.config_loader = RegistryConfigLoader(self.registries_file)
        self.index_manager = PackageIndexManager(
            self.package_index_file, 
            base_dir=self.base_dir,
            failover_config=failover_config
        )
        self.transaction_logger = TransactionLogger(self.transactions_log)

        # Load registries
        self.registries = self.config_loader.load()

        # Initialize resolver with current index
        self.resolver = DependencyResolver(self.index_manager.index)

        # Initialize operations
        self.operations = PackageOperations(
            self.installed_packages_file,
            self.mcp_manager,
            self.resolver,
            self.transaction_logger
        )

        # Reconcile runtime state (container IDs) on startup
        self.reconcile_runtime_state()

        logger.info(f"RegistryService initialized with {len(self.registries)} registries")

    def reconcile_runtime_state(self):
        """
        Reconcile declared state (installed-packages.json) with runtime state (Docker).

        Updates in-memory InstallationRecords with current container IDs/names
        WITHOUT persisting them to disk. This keeps installed-packages.json portable
        across deployments while maintaining runtime tracking.
        """
        logger.info("Reconciling runtime state with declared packages...")

        for pkg_name, record in self.operations.installed_packages.items():
            try:
                # Query Docker for current container status
                status = self.mcp_manager.get_status(pkg_name)

                if status and status.get("running"):
                    # Update in-memory record with runtime state
                    record.container_id = status.get("container_id")
                    record.container_name = status.get("container_name")
                    logger.debug(f"Reconciled {pkg_name}: container_name={record.container_name}")
                else:
                    # Package is declared as installed but container not running
                    logger.warning(f"Package {pkg_name} is installed but container not running")
                    record.container_id = None
                    record.container_name = None

            except Exception as e:
                logger.warning(f"Failed to reconcile runtime state for {pkg_name}: {e}")
                record.container_id = None
                record.container_name = None

        logger.info(f"Runtime reconciliation complete: {len(self.operations.installed_packages)} packages checked")

    async def install_from_local_path(
        self,
        local_path: str,
        options: Optional[InstallOptions] = None
    ) -> TransactionRecord:
        """
        Install a package directly from a local directory (air-gapped mode).

        Args:
            local_path: Path to local package directory containing mcp.json
            options: Installation options

        Returns:
            Transaction record
        """
        local_dir = Path(local_path).resolve()
        
        # Security: Validate path is within reasonable bounds
        if not local_dir.exists() or not local_dir.is_dir():
            raise ValueError(f"Local package directory not found: {local_path}")
        
        # Prevent extremely long paths that could cause issues
        if len(str(local_dir)) > 4096:
            raise ValueError("Package path too long")
        
        mcp_json_path = local_dir / "mcp.json"
        if not mcp_json_path.exists():
            raise ValueError(f"Package metadata file not found: {mcp_json_path}")
        
        try:
            # Load package metadata from mcp.json with size limit
            if mcp_json_path.stat().st_size > 1024 * 1024:  # 1MB limit
                raise ValueError("Package metadata file too large (max 1MB)")
            
            import json
            with open(mcp_json_path, encoding='utf-8') as f:
                metadata_dict = json.load(f)
            
            # Comprehensive metadata validation
            validation_errors = self._validate_package_metadata(metadata_dict)
            if validation_errors:
                raise ValueError(f"Invalid package metadata: {'; '.join(validation_errors)}")
            
            # Add type field if missing
            if "type" not in metadata_dict:
                metadata_dict["type"] = "mcp"
            
            # Create PackageMetadata object
            from app.models.registry_models import PackageMetadata
            package = PackageMetadata(**metadata_dict)
            
            logger.info(f"Installing package from local path: {package.name}@{package.version} from {local_path}")
            
            return await self.operations.install_from_local(
                package,
                local_dir,
                "local",  # registry_name for tracking
                options
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {mcp_json_path}: {e}")
            raise ValueError(f"Invalid JSON in package metadata: {e}")
        except Exception as e:
            logger.error(f"Failed to install from local path {local_path}: {e}")
            raise ValueError(f"Failed to load package from {local_path}: {e}")
    
    async def discover_local_packages(self, directory: str) -> List[PackageInfo]:
        """
        Discover all packages in a local directory (for air-gapped browsing).
        
        Args:
            directory: Directory to scan for packages
            
        Returns:
            List of discovered packages
        """
        packages = []
        scan_dir = Path(directory).resolve()
        
        if not scan_dir.exists() or not scan_dir.is_dir():
            logger.warning(f"Directory does not exist: {directory}")
            return []
        
        logger.info(f"Discovering packages in: {scan_dir}")
        
        # Scan each subdirectory for mcp.json
        for item in scan_dir.iterdir():
            if not item.is_dir():
                continue
                
            mcp_json = item / "mcp.json"
            if not mcp_json.exists():
                continue
                
            try:
                import json
                with open(mcp_json) as f:
                    metadata_dict = json.load(f)
                
                # Ensure required fields
                if "name" not in metadata_dict or "version" not in metadata_dict:
                    logger.warning(f"Invalid mcp.json in {item.name}: missing name or version")
                    continue
                
                # Add type field if missing
                if "type" not in metadata_dict:
                    metadata_dict["type"] = "mcp"
                
                from app.models.registry_models import PackageMetadata
                package_metadata = PackageMetadata(**metadata_dict)
                
                packages.append(PackageInfo(
                    metadata=package_metadata,
                    registry_name="local-discovery",
                    registry_url=f"file://{item}"
                ))
                
                logger.debug(f"Discovered package: {metadata_dict['name']} v{metadata_dict['version']}")
                
            except Exception as e:
                logger.warning(f"Failed to load package from {item}: {e}")
                continue
        
        logger.info(f"Discovered {len(packages)} packages in {scan_dir}")
        return packages
    
    def _validate_package_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Validate package metadata structure and content.
        
        Args:
            metadata: Package metadata dictionary
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = ["name", "version"]
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")
        
        # Validate name format (alphanumeric, hyphens, underscores)
        if "name" in metadata:
            name = metadata["name"]
            if not isinstance(name, str) or not name:
                errors.append("Package name must be a non-empty string")
            elif not re.match(r'^[a-zA-Z0-9_-]+$', name):
                errors.append("Package name contains invalid characters")
            elif len(name) > 100:
                errors.append("Package name too long (max 100 characters)")
        
        # Validate version format (basic semver check)
        if "version" in metadata:
            version = metadata["version"]
            if not isinstance(version, str) or not version:
                errors.append("Package version must be a non-empty string")
            elif not re.match(r'^\d+\.\d+\.\d+', version):
                errors.append("Package version must follow semver format (e.g., 1.0.0)")
        
        # Validate type
        if "type" in metadata:
            valid_types = ["mcp", "agent", "team"]
            if metadata["type"] not in valid_types:
                errors.append(f"Invalid package type (must be one of: {', '.join(valid_types)})")
        
        # Validate deployment configuration
        if "deployment" in metadata:
            deployment = metadata["deployment"]
            if not isinstance(deployment, dict):
                errors.append("Deployment configuration must be an object")
            elif "image" not in deployment and "build" not in deployment:
                errors.append("Deployment must specify either 'image' or 'build' configuration")
        
        return errors

    @property
    def installed_packages(self) -> Dict[str, InstallationRecord]:
        """Get currently installed packages"""
        return self.operations.installed_packages

    async def close(self):
        """Close resources and cleanup"""
        logger.info("RegistryService closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    # Registry Configuration Methods
    def enable_registry(self, name: str):
        """
        Enable a registry and persist to config.

        Args:
            name: Registry name
        """
        if name not in self.registries:
            raise ValueError(f"Registry not found: {name}")

        self.registries[name].enabled = True
        self.config_loader.save(self.registries)
        logger.info(f"Enabled registry: {name}")

    def disable_registry(self, name: str):
        """
        Disable a registry and persist to config.

        Args:
            name: Registry name
        """
        if name not in self.registries:
            raise ValueError(f"Registry not found: {name}")

        self.registries[name].enabled = False
        self.config_loader.save(self.registries)
        logger.info(f"Disabled registry: {name}")

    # Package Index Methods
    async def refresh_index(self, registry_name: Optional[str] = None):
        """
        Refresh package index from registries.

        Args:
            registry_name: Optional specific registry to refresh
        """
        await self.index_manager.refresh(self.registries, registry_name)

        # Update resolver with new index
        self.resolver.package_index = self.index_manager.index

    async def search_packages(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[PackageSearchResult]:
        """
        Search packages across all enabled registries.

        Args:
            query: Search query for name/description
            filters: Optional filters (type, tags, etc.)

        Returns:
            List of matching packages
        """
        return self.index_manager.search(
            query=query,
            filters=filters,
            installed_packages=self.operations.installed_packages
        )

    async def get_package_info(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[PackageInfo]:
        """
        Get detailed package information with failover support.

        Args:
            name: Package name
            version: Optional specific version

        Returns:
            Package info or None if not found
        """
        # First try local index
        result = self.index_manager.get_package(name, version)
        if result:
            return result
        
        # If not in local index, try live lookup with failover
        return await self.index_manager.get_package_with_failover(
            name, version, self.registries
        )

    # Package Operation Methods
    async def install_package(
        self,
        name: str,
        version: Optional[str] = None,
        options: Optional[InstallOptions] = None,
        local_path: Optional[str] = None
    ) -> TransactionRecord:
        """
        Install a package with dependencies.

        Args:
            name: Package name
            version: Optional specific version (defaults to latest)
            options: Installation options
            local_path: Optional local directory path for air-gapped installation

        Returns:
            Transaction record
        """
        # Handle local path installation (air-gapped mode)
        if local_path:
            return await self.install_from_local_path(local_path, options)

        # Get package info from registry
        pkg_info = await self.get_package_info(name, version)
        if not pkg_info:
            raise ValueError(f"Package not found: {name}@{version or 'latest'}")

        return await self.operations.install(
            pkg_info.metadata,
            pkg_info.registry_name,
            options
        )

    async def update_package(
        self,
        name: str,
        to_version: Optional[str] = None
    ) -> TransactionRecord:
        """
        Update a package to a new version.

        Args:
            name: Package name
            to_version: Target version (defaults to latest)

        Returns:
            Transaction record
        """
        # Get new package info
        pkg_info = await self.get_package_info(name, to_version)
        if not pkg_info:
            raise ValueError(f"Package version not found: {name}@{to_version or 'latest'}")

        return await self.operations.update(name, pkg_info.metadata)

    async def remove_package(
        self,
        name: str,
        force: bool = False
    ) -> TransactionRecord:
        """
        Remove a package.

        Args:
            name: Package name
            force: Force removal even if other packages depend on it

        Returns:
            Transaction record
        """
        return await self.operations.remove(name, force)

    # Transaction Methods
    def list_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent transactions from log.

        Args:
            limit: Maximum number of transactions to return

        Returns:
            List of transaction records
        """
        return self.transaction_logger.list_transactions(limit)

    async def rollback_transaction(self, transaction_id: str) -> bool:
        """
        Rollback a specific transaction.

        Args:
            transaction_id: Transaction ID to rollback

        Returns:
            True if successful
        """
        return await self.operations.rollback(transaction_id)

    # GPG Verification (kept in service for now)
    def _gpg_verify(self, file_path: Path, signature: str, gpgkey: str) -> bool:
        """
        Verify GPG signature of a package.

        Args:
            file_path: Path to package file
            signature: GPG signature string
            gpgkey: Path to GPG public key (must be file:// URL)

        Returns:
            True if signature is valid
        """
        # Validate gpgkey is a file:// URL
        if not gpgkey.startswith("file://"):
            logger.error(f"Invalid gpgkey format (must start with file://): {gpgkey}")
            return False

        # Extract and validate key path
        key_path_str = gpgkey[7:]  # Remove "file://" prefix
        key_path = Path(key_path_str)

        # Security: Ensure key path is absolute and exists
        if not key_path.is_absolute():
            logger.error(f"GPG key path must be absolute: {key_path}")
            return False

        if not key_path.exists():
            logger.error(f"GPG key file not found: {key_path}")
            return False

        if not key_path.is_file():
            logger.error(f"GPG key path is not a file: {key_path}")
            return False

        # Validate file_path
        if not file_path.exists() or not file_path.is_file():
            logger.error(f"Package file not found or not a file: {file_path}")
            return False

        # Write signature to temp file
        sig_file = file_path.with_suffix(".sig")
        sig_file.write_text(signature)

        try:
            # Import GPG key - use list for args to prevent injection
            import_result = subprocess.run(
                ["gpg", "--import", str(key_path.resolve())],
                check=False,  # Don't raise on non-zero exit
                capture_output=True,
                text=True
            )
            if import_result.returncode != 0:
                logger.warning(f"GPG key import failed: {import_result.stderr}")

            # Verify signature - use list for args to prevent injection
            verify_result = subprocess.run(
                ["gpg", "--verify", str(sig_file.resolve()), str(file_path.resolve())],
                check=False,
                capture_output=True,
                text=True
            )

            if verify_result.returncode == 0:
                logger.info(f"GPG signature verified successfully for {file_path.name}")
                return True
            else:
                logger.error(f"GPG signature verification failed: {verify_result.stderr}")
                return False

        except Exception as e:
            logger.error(f"GPG verification failed with exception: {e}")
            return False
        finally:
            sig_file.unlink(missing_ok=True)

    # Registry Health and Failover Methods
    def get_registry_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive health summary for all registries.
        
        Returns:
            Registry health summary with status and metrics
        """
        return self.index_manager.get_registry_health()

    async def run_health_checks(self):
        """
        Run health checks on all enabled registries.
        
        This updates the internal health metrics and circuit breaker states.
        """
        await self.index_manager.failover_manager.run_health_checks(self.registries)

    def get_failover_config(self) -> FailoverConfig:
        """
        Get current failover configuration.
        
        Returns:
            Failover configuration settings
        """
        return self.index_manager.failover_manager.config

    def update_failover_config(self, config: FailoverConfig):
        """
        Update failover configuration.
        
        Args:
            config: New failover configuration
        """
        self.index_manager.failover_manager.config = config
        logger.info(f"Updated failover configuration: {config}")

    def get_ordered_registries(self, operation: str = "general") -> List[str]:
        """
        Get list of registry names ordered by priority and health.
        
        Args:
            operation: Operation type for context
            
        Returns:
            List of registry names in optimal order
        """
        ordered = self.index_manager.failover_manager.get_ordered_registries(
            self.registries, operation
        )
        return [r.name for r in ordered]

    def reset_circuit_breaker(self, registry_name: str) -> bool:
        """
        Manually reset circuit breaker for a registry.
        
        Args:
            registry_name: Registry name
            
        Returns:
            True if reset successfully
        """
        if registry_name not in self.registries:
            return False
        
        if registry_name in self.index_manager.failover_manager.circuit_breakers:
            del self.index_manager.failover_manager.circuit_breakers[registry_name]
            
        # Reset health metrics
        health = self.index_manager.failover_manager.get_registry_health(registry_name)
        health.consecutive_failures = 0
        health.status = health.status.HEALTHY
        
        logger.info(f"Circuit breaker reset for registry: {registry_name}")
        return True
