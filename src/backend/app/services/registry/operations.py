# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Package Operations

Single responsibility: Install, update, and remove packages
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, UTC

from app.models.registry_models import (
    PackageMetadata,
    InstallationRecord,
    InstallOptions,
    TransactionRecord,
    TransactionOperation,
    TransactionStatus,
    BackupState
)
from app.mcp_manager import MCPManager

from .resolver import DependencyResolver
from .transactions import TransactionLogger

logger = logging.getLogger(__name__)


class PackageOperations:
    """Handles package installation, updates, and removal"""

    def __init__(
        self,
        installed_packages_file: Path,
        mcp_manager: MCPManager,
        resolver: DependencyResolver,
        transaction_logger: TransactionLogger
    ):
        """
        Initialize package operations.

        Args:
            installed_packages_file: Path to installed-packages.json
            mcp_manager: MCP Manager for container operations
            resolver: Dependency resolver
            transaction_logger: Transaction logger
        """
        self.installed_packages_file = installed_packages_file
        self.mcp_manager = mcp_manager
        self.resolver = resolver
        self.transaction_logger = transaction_logger

        # Load installed packages
        self.installed_packages = self._load_installed_packages()

    def _load_installed_packages(self) -> Dict[str, InstallationRecord]:
        """
        Load installed packages from disk.

        Returns:
            Dictionary of installation records keyed by package name
        """
        if not self.installed_packages_file.exists():
            return {}

        try:
            data = json.loads(self.installed_packages_file.read_text())
            records = {}
            for name, record in data.get("packages", {}).items():
                # Convert ISO datetime strings to datetime objects
                record["installed_at"] = datetime.fromisoformat(record["installed_at"])
                records[name] = InstallationRecord(**record)
            return records
        except Exception as e:
            logger.error(f"Failed to load installed packages: {e}")
            return {}

    def _save_installed_packages(self):
        """
        Save installed packages to disk.

        IMPORTANT: Excludes runtime state (container_id, container_name) to keep
        the file declarative and portable across deployments. These IDs change
        on every deploy and should not be version controlled.
        """
        data = {
            "version": "2.0",
            "packages": {}
        }
        for name, record in self.installed_packages.items():
            pkg_data = record.model_dump(exclude={"container_id", "container_name"})
            pkg_data["installed_at"] = record.installed_at.isoformat()
            data["packages"][name] = pkg_data

        self.installed_packages_file.write_text(json.dumps(data, indent=2))

    def _create_backup_state(self) -> BackupState:
        """
        Create backup of current state for rollback.

        Returns:
            Backup state snapshot
        """
        container_states = {}
        container_ids = []

        for name, record in self.installed_packages.items():
            if record.container_id:
                container_ids.append(record.container_id)
                status = self.mcp_manager.get_status(name)
                container_states[name] = status.get("state", "unknown")

        return BackupState(
            installed_packages=json.loads(self.installed_packages_file.read_text()) if self.installed_packages_file.exists() else {},
            container_ids=container_ids,
            container_states=container_states,
            files_backed_up=[str(self.installed_packages_file)]
        )

    def _restore_backup_state(self, backup: BackupState):
        """
        Restore system to backup state (rollback).

        Args:
            backup: Backup state to restore
        """
        logger.info("Rolling back to backup state...")

        # Restore installed-packages.json
        if backup.installed_packages:
            self.installed_packages_file.write_text(
                json.dumps(backup.installed_packages, indent=2)
            )
            self.installed_packages = self._load_installed_packages()

        # Restore container states
        for name, state in backup.container_states.items():
            try:
                if state == "running":
                    self.mcp_manager.start(name)
                elif state == "stopped":
                    self.mcp_manager.stop(name)
            except Exception as e:
                logger.error(f"Failed to restore container {name}: {e}")

        logger.info("Rollback completed")

    async def install(
        self,
        package: PackageMetadata,
        registry_name: str,
        options: Optional[InstallOptions] = None
    ) -> TransactionRecord:
        """
        Install a package with dependencies.

        Args:
            package: Package metadata
            registry_name: Registry name (for tracking)
            options: Installation options

        Returns:
            Transaction record
        """
        options = options or InstallOptions()
        transaction = self.transaction_logger.create_transaction(
            TransactionOperation.INSTALL,
            package.name,
            package.version
        )

        try:
            transaction.status = TransactionStatus.IN_PROGRESS
            self.transaction_logger.log(transaction)

            # Create backup
            if not options.no_rollback:
                transaction.backup_state = self._create_backup_state()

            # Check if already installed
            if package.name in self.installed_packages:
                existing_version = self.installed_packages[package.name].version
                if existing_version == package.version:
                    transaction.status = TransactionStatus.COMPLETED
                    transaction.completed_at = datetime.now(UTC)
                    self.transaction_logger.log(transaction)
                    return transaction

            # Resolve dependencies
            deps = []
            if not options.skip_dependencies:
                deps = self.resolver.resolve(package, self.installed_packages)
                transaction.dependencies_installed = [f"{d.name}@{d.version}" for d in deps]

            # Install dependencies first
            for dep in deps:
                logger.info(f"Installing dependency: {dep.name}@{dep.version}")
                dep_result = self.mcp_manager.install(dep.model_dump())
                if dep_result.get("status") not in ["installed", "already_installed"]:
                    raise Exception(f"Failed to install dependency {dep.name}: {dep_result.get('error')}")

                # Record installation
                self.installed_packages[dep.name] = InstallationRecord(
                    name=dep.name,
                    version=dep.version,
                    installed_at=datetime.now(UTC),
                    installed_from=registry_name,
                    container_id=dep_result.get("container_id"),
                    container_name=dep_result.get("container_name"),
                    transaction_id=transaction.id,
                    metadata=dep
                )

            # Install main package
            logger.info(f"Installing package: {package.name}@{package.version}")
            install_result = self.mcp_manager.install(package.model_dump())

            if install_result.get("status") not in ["installed", "already_installed"]:
                raise Exception(f"Installation failed: {install_result.get('error')}")

            # Record installation
            self.installed_packages[package.name] = InstallationRecord(
                name=package.name,
                version=package.version,
                installed_at=datetime.now(UTC),
                installed_from=registry_name,
                container_id=install_result.get("container_id"),
                container_name=install_result.get("container_name"),
                transaction_id=transaction.id,
                metadata=package
            )

            # Save state
            self._save_installed_packages()

            # Mark transaction complete
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.now(UTC)
            self.transaction_logger.log(transaction)

            logger.info(f"Package {package.name}@{package.version} installed successfully")
            return transaction

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            transaction.status = TransactionStatus.FAILED
            transaction.error = str(e)
            transaction.completed_at = datetime.now(UTC)
            self.transaction_logger.log(transaction)

            # Rollback if enabled
            if not options.no_rollback and transaction.backup_state:
                self._restore_backup_state(transaction.backup_state)
                transaction.status = TransactionStatus.ROLLED_BACK
                self.transaction_logger.log(transaction)

            raise

    async def update(
        self,
        name: str,
        new_package: PackageMetadata
    ) -> TransactionRecord:
        """
        Update a package to a new version.

        Args:
            name: Package name
            new_package: New package metadata

        Returns:
            Transaction record
        """
        transaction = self.transaction_logger.create_transaction(
            TransactionOperation.UPDATE,
            name,
            new_package.version
        )

        try:
            transaction.status = TransactionStatus.IN_PROGRESS
            self.transaction_logger.log(transaction)

            # Check if installed
            if name not in self.installed_packages:
                raise ValueError(f"Package not installed: {name}")

            current_version = self.installed_packages[name].version

            if current_version == new_package.version:
                transaction.status = TransactionStatus.COMPLETED
                transaction.completed_at = datetime.now(UTC)
                self.transaction_logger.log(transaction)
                return transaction

            # Create backup
            transaction.backup_state = self._create_backup_state()

            # Update via MCP manager
            update_result = self.mcp_manager.update(name, new_package.model_dump())

            if update_result.get("status") != "updated":
                raise Exception(f"Update failed: {update_result.get('error')}")

            # Update installation record
            self.installed_packages[name].version = new_package.version
            self.installed_packages[name].installed_at = datetime.now(UTC)
            self.installed_packages[name].transaction_id = transaction.id
            self._save_installed_packages()

            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.now(UTC)
            self.transaction_logger.log(transaction)

            logger.info(f"Package {name} updated from {current_version} to {new_package.version}")
            return transaction

        except Exception as e:
            logger.error(f"Update failed: {e}")
            transaction.status = TransactionStatus.FAILED
            transaction.error = str(e)
            transaction.completed_at = datetime.now(UTC)
            self.transaction_logger.log(transaction)

            # Rollback
            if transaction.backup_state:
                self._restore_backup_state(transaction.backup_state)
                transaction.status = TransactionStatus.ROLLED_BACK
                self.transaction_logger.log(transaction)

            raise

    async def remove(
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
        transaction = self.transaction_logger.create_transaction(
            TransactionOperation.REMOVE,
            name
        )

        try:
            transaction.status = TransactionStatus.IN_PROGRESS
            self.transaction_logger.log(transaction)

            # Check if installed
            if name not in self.installed_packages:
                raise ValueError(f"Package not installed: {name}")

            # Check for dependents (if not forcing)
            if not force:
                dependents = []
                for pkg_name, pkg_record in self.installed_packages.items():
                    if pkg_record.metadata:
                        for dep in pkg_record.metadata.dependencies.mcps:
                            if dep.name == name:
                                dependents.append(pkg_name)

                if dependents:
                    raise ValueError(f"Cannot remove {name}: required by {', '.join(dependents)}")

            # Create backup
            transaction.backup_state = self._create_backup_state()

            # Remove via MCP manager
            remove_result = self.mcp_manager.uninstall(name)

            if remove_result.get("status") != "uninstalled":
                raise Exception(f"Removal failed: {remove_result.get('error')}")

            # Remove from installed packages
            del self.installed_packages[name]
            self._save_installed_packages()

            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.now(UTC)
            self.transaction_logger.log(transaction)

            logger.info(f"Package {name} removed successfully")
            return transaction

        except Exception as e:
            logger.error(f"Removal failed: {e}")
            transaction.status = TransactionStatus.FAILED
            transaction.error = str(e)
            transaction.completed_at = datetime.now(UTC)
            self.transaction_logger.log(transaction)

            # Rollback
            if transaction.backup_state:
                self._restore_backup_state(transaction.backup_state)
                transaction.status = TransactionStatus.ROLLED_BACK
                self.transaction_logger.log(transaction)

            raise

    async def rollback(self, transaction_id: str) -> bool:
        """
        Rollback a specific transaction.

        Args:
            transaction_id: Transaction ID to rollback

        Returns:
            True if successful
        """
        txn_data = self.transaction_logger.get_transaction(transaction_id)

        if not txn_data:
            raise ValueError(f"Transaction not found: {transaction_id}")

        if not txn_data.get("backup_state"):
            raise ValueError(f"No backup state for transaction: {transaction_id}")

        # Restore backup
        backup = BackupState(**txn_data["backup_state"])
        self._restore_backup_state(backup)

        # Log rollback transaction
        rollback_txn = self.transaction_logger.create_transaction(
            TransactionOperation.ROLLBACK,
            txn_data["package_name"],
            txn_data.get("version")
        )
        rollback_txn.status = TransactionStatus.COMPLETED
        rollback_txn.completed_at = datetime.now(UTC)
        self.transaction_logger.log(rollback_txn)

        logger.info(f"Rolled back transaction: {transaction_id}")
        return True
    
    async def install_from_local(
        self,
        package: PackageMetadata,
        local_path: Path,
        registry_name: str,
        options: Optional[InstallOptions] = None
    ) -> TransactionRecord:
        """
        Install a package directly from a local directory (air-gapped mode).
        
        Args:
            package: Package metadata
            local_path: Local directory containing the package
            registry_name: Registry name for tracking
            options: Installation options
            
        Returns:
            Transaction record
        """
        options = options or InstallOptions()
        transaction = self.transaction_logger.create_transaction(
            TransactionOperation.INSTALL,
            package.name,
            package.version
        )
        
        try:
            transaction.status = TransactionStatus.IN_PROGRESS
            self.transaction_logger.log(transaction)
            
            # Create backup
            if not options.no_rollback:
                transaction.backup_state = self._create_backup_state()
            
            # Check if already installed
            if package.name in self.installed_packages:
                existing_version = self.installed_packages[package.name].version
                if existing_version == package.version:
                    transaction.status = TransactionStatus.COMPLETED
                    transaction.completed_at = datetime.now(UTC)
                    self.transaction_logger.log(transaction)
                    return transaction
            
            # Resolve dependencies (try to find them locally if possible)
            deps = []
            if not options.skip_dependencies:
                deps = self.resolver.resolve(package, self.installed_packages)
                transaction.dependencies_installed = [f"{d.name}@{d.version}" for d in deps]
            
            # Install dependencies first
            for dep in deps:
                logger.info(f"Installing dependency: {dep.name}@{dep.version}")
                
                # Try to find dependency in local parent directory first
                parent_dir = local_path.parent
                dep_local_path = parent_dir / dep.name
                
                if dep_local_path.exists() and (dep_local_path / "mcp.json").exists():
                    # Validate local dependency version matches requirement
                    try:
                        import json
                        with open(dep_local_path / "mcp.json", encoding='utf-8') as f:
                            local_dep_metadata = json.load(f)
                        
                        local_version = local_dep_metadata.get('version')
                        if local_version != dep.version:
                            logger.warning(
                                f"Local dependency {dep.name} version mismatch: "
                                f"required {dep.version}, found {local_version}"
                            )
                            # Continue with local version but log warning
                        
                        logger.info(f"Installing dependency {dep.name} from local path: {dep_local_path}")
                        dep_result = self.mcp_manager.install_from_local(dep.model_dump(), str(dep_local_path))
                        
                    except Exception as e:
                        logger.error(f"Failed to validate local dependency {dep.name}: {e}")
                        # Fallback to regular installation
                        logger.warning(f"Local dependency validation failed for {dep.name}, trying regular installation")
                        dep_result = self.mcp_manager.install(dep.model_dump())
                else:
                    # Fallback to regular installation (may fail in air-gapped)
                    logger.warning(f"Local dependency not found for {dep.name}, trying regular installation")
                    dep_result = self.mcp_manager.install(dep.model_dump())
                
                if dep_result.get("status") not in ["installed", "already_installed"]:
                    raise Exception(f"Failed to install dependency {dep.name}: {dep_result.get('error')}")
                
                # Record installation
                self.installed_packages[dep.name] = InstallationRecord(
                    name=dep.name,
                    version=dep.version,
                    installed_at=datetime.now(UTC),
                    installed_from=registry_name,
                    container_id=dep_result.get("container_id"),
                    container_name=dep_result.get("container_name"),
                    transaction_id=transaction.id,
                    metadata=dep
                )
            
            # Install main package from local path
            logger.info(f"Installing package: {package.name}@{package.version} from {local_path}")
            install_result = self.mcp_manager.install_from_local(package.model_dump(), str(local_path))
            
            if install_result.get("status") not in ["installed", "already_installed"]:
                raise Exception(f"Local installation failed: {install_result.get('error')}")
            
            # Record installation
            self.installed_packages[package.name] = InstallationRecord(
                name=package.name,
                version=package.version,
                installed_at=datetime.now(UTC),
                installed_from=registry_name,
                container_id=install_result.get("container_id"),
                container_name=install_result.get("container_name"),
                transaction_id=transaction.id,
                metadata=package
            )
            
            # Save state
            self._save_installed_packages()
            
            # Mark transaction complete
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.now(UTC)
            self.transaction_logger.log(transaction)
            
            logger.info(f"Package {package.name}@{package.version} installed successfully from local path")
            return transaction
            
        except Exception as e:
            logger.error(f"Local installation failed: {e}")
            transaction.status = TransactionStatus.FAILED
            transaction.error = str(e)
            transaction.completed_at = datetime.now(UTC)
            self.transaction_logger.log(transaction)
            
            # Rollback if enabled
            if not options.no_rollback and transaction.backup_state:
                self._restore_backup_state(transaction.backup_state)
                transaction.status = TransactionStatus.ROLLED_BACK
                self.transaction_logger.log(transaction)
            
            raise
