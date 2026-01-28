# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Package Index Manager

Single responsibility: Manage package index (search, refresh, query)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
import httpx

from app.models.registry_models import (
    RegistryConfig,
    PackageMetadata,
    PackageInfo,
    PackageSearchResult,
    InstallationRecord
)
from .failover import RegistryFailoverManager, FailoverConfig

logger = logging.getLogger(__name__)


class PackageIndexManager:
    """Manages searchable package index from all registries"""

    def __init__(
        self, 
        index_file: Path, 
        base_dir: Path = Path("/app"),
        failover_config: Optional[FailoverConfig] = None
    ):
        """
        Initialize package index manager.

        Args:
            index_file: Path to package-index.json
            base_dir: Base directory for resolving relative paths (default: /app)
            failover_config: Optional failover configuration
        """
        self.index_file = index_file
        self.base_dir = base_dir
        self.index = self._load_index()
        self.failover_manager = RegistryFailoverManager(failover_config)

    def _load_index(self) -> Dict[str, Any]:
        """
        Load package index from disk.

        Returns:
            Package index dictionary
        """
        if not self.index_file.exists():
            return {"last_updated": None, "registries": {}}

        try:
            return json.loads(self.index_file.read_text())
        except Exception as e:
            logger.error(f"Failed to load package index: {e}")
            return {"last_updated": None, "registries": {}}

    def _save_index(self):
        """Save package index to disk"""
        self.index_file.write_text(json.dumps(self.index, indent=2))

    async def refresh(
        self,
        registries: Dict[str, RegistryConfig],
        registry_name: Optional[str] = None
    ):
        """
        Refresh package index from registries with failover support.

        Args:
            registries: Dictionary of registry configurations
            registry_name: Optional specific registry to refresh
        """
        logger.info("Refreshing package index...")
        
        # Run health checks before refresh
        await self.failover_manager.run_health_checks(registries)

        registries_to_refresh = []
        if registry_name:
            if registry_name not in registries:
                raise ValueError(f"Registry not found: {registry_name}")
            registries_to_refresh = [registries[registry_name]]
        else:
            # Get ordered registries for optimal performance
            registries_to_refresh = self.failover_manager.get_ordered_registries(
                registries, "refresh"
            )

        new_index = {
            "last_updated": datetime.now(UTC).isoformat(),
            "registries": {},
            "failover_summary": self.failover_manager.get_health_summary()
        }

        async with httpx.AsyncClient(timeout=self.failover_manager.config.timeout) as client:
            for registry in registries_to_refresh:
                try:
                    logger.info(f"Fetching packages from {registry.name}...")
                    
                    # Use retry logic for individual registries
                    packages = await self.failover_manager.execute_with_retry(
                        self._fetch_from_registry_with_client,
                        registry,
                        "fetch_packages",
                        client=client
                    )
                    
                    new_index["registries"][registry.name] = {
                        "url": registry.url,
                        "packages": [pkg.model_dump() for pkg in packages],
                        "last_updated": datetime.now(UTC).isoformat()
                    }
                    logger.info(f"Fetched {len(packages)} packages from {registry.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to fetch from {registry.name} after retries: {e}")
                    # Continue with other registries - partial failure is acceptable

        # Only update if we got data from at least one registry
        if new_index["registries"]:
            self.index = new_index
            self._save_index()
            logger.info(f"Package index refreshed successfully from {len(new_index['registries'])} registries")
        else:
            logger.warning("No registries available - keeping existing index")
            raise Exception("All registries failed - package index not updated")

    async def _fetch_from_registry_with_client(
        self,
        registry: RegistryConfig,
        client: httpx.AsyncClient
    ) -> List[PackageMetadata]:
        """
        Wrapper for _fetch_from_registry that matches failover manager signature.
        
        Args:
            registry: Registry configuration
            client: HTTP client
            
        Returns:
            List of package metadata
        """
        return await self._fetch_from_registry(client, registry)

    async def _fetch_from_registry(
        self,
        client: httpx.AsyncClient,
        registry: RegistryConfig
    ) -> List[PackageMetadata]:
        """
        Fetch package list from a registry.

        Supports both HTTP and local file:// repositories (YUM-style).

        Args:
            client: HTTP client (unused for file:// repos)
            registry: Registry configuration

        Returns:
            List of package metadata
        """
        # Handle local file:// repositories (like local YUM repos)
        if registry.url.startswith("file://"):
            return await self._scan_local_directory(registry)

        # Handle HTTP/HTTPS remote repositories
        response = await client.get(f"{registry.url}/api/v2/packages")
        response.raise_for_status()
        data = response.json()
        return [PackageMetadata(**pkg) for pkg in data.get("packages", [])]

    async def _scan_local_directory(self, registry: RegistryConfig) -> List[PackageMetadata]:
        """
        Scan local directory for MCP packages (like createrepo for YUM).

        Reads mcp.json from each subdirectory to build package list.
        Supports both absolute paths (file:///absolute/path) and
        relative paths (file://./relative/path) resolved from base_dir.

        Args:
            registry: Registry configuration with file:// URL

        Returns:
            List of package metadata
        """
        packages = []

        # Extract path from file:// URL
        local_path = registry.url.replace("file://", "")

        # Resolve relative paths from base_dir
        # If path starts with ./ or ../, it's relative
        if local_path.startswith("./") or local_path.startswith("../"):
            directory = (self.base_dir / local_path).resolve()
        else:
            # Absolute path
            directory = Path(local_path)

        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Local registry directory does not exist: {directory}")
            return []

        logger.info(f"Scanning local directory: {directory}")

        # Scan each subdirectory for mcp.json
        for item in directory.iterdir():
            if not item.is_dir():
                continue

            mcp_json = item / "mcp.json"
            if not mcp_json.exists():
                continue

            try:
                with open(mcp_json, "r") as f:
                    import json
                    metadata = json.load(f)

                # Ensure it has required fields
                if "name" not in metadata or "version" not in metadata:
                    logger.warning(f"Invalid mcp.json in {item.name}: missing name or version")
                    continue

                # Add type field if missing
                if "type" not in metadata:
                    metadata["type"] = "mcp"

                packages.append(PackageMetadata(**metadata))
                logger.debug(f"Found package: {metadata['name']} v{metadata['version']}")

            except Exception as e:
                logger.warning(f"Failed to load {mcp_json}: {e}")
                continue

        logger.info(f"Scanned {len(packages)} packages from {directory}")
        return packages

    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        installed_packages: Optional[Dict[str, InstallationRecord]] = None
    ) -> List[PackageSearchResult]:
        """
        Search packages in index.

        Args:
            query: Search query for name/description
            filters: Optional filters (type, tags, etc.)
            installed_packages: Optional installed packages for checking

        Returns:
            List of matching packages
        """
        results = []
        filters = filters or {}
        installed_packages = installed_packages or {}

        for reg_name, reg_data in self.index.get("registries", {}).items():
            for pkg in reg_data.get("packages", []):
                # Apply query filter
                if query:
                    if query.lower() not in pkg["name"].lower() and \
                       query.lower() not in pkg.get("description", "").lower():
                        continue

                # Apply type filter
                if "type" in filters and pkg.get("type") != filters["type"]:
                    continue

                # Apply tags filter
                if "tags" in filters:
                    pkg_tags = set(pkg.get("tags", []))
                    filter_tags = set(filters["tags"])
                    if not filter_tags.intersection(pkg_tags):
                        continue

                # Check if installed
                installed = pkg["name"] in installed_packages
                installed_version = None
                if installed:
                    installed_version = installed_packages[pkg["name"]].version

                results.append(PackageSearchResult(
                    name=pkg["name"],
                    version=pkg["version"],
                    description=pkg.get("description", ""),
                    registry=reg_name,
                    tags=pkg.get("tags", []),
                    installed=installed,
                    installed_version=installed_version
                ))

        return results

    def get_package(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[PackageInfo]:
        """
        Get detailed package information.

        Args:
            name: Package name
            version: Optional specific version

        Returns:
            Package info or None if not found
        """
        for reg_name, reg_data in self.index.get("registries", {}).items():
            for pkg in reg_data.get("packages", []):
                if pkg["name"] == name:
                    if version is None or pkg["version"] == version:
                        metadata = PackageMetadata(**pkg)
                        return PackageInfo(
                            metadata=metadata,
                            registry_name=reg_name,
                            registry_url=reg_data["url"],
                            available_versions=[pkg["version"]]
                        )

        return None

    def get_registry_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health summary for all registries.
        
        Returns:
            Registry health summary
        """
        return self.failover_manager.get_health_summary()

    async def get_package_with_failover(
        self,
        name: str,
        version: Optional[str] = None,
        registries: Optional[Dict[str, RegistryConfig]] = None
    ) -> Optional[PackageInfo]:
        """
        Get package information with registry failover support.
        
        Args:
            name: Package name
            version: Optional specific version
            registries: Optional registries to search (will try in priority order)
            
        Returns:
            Package info from first available registry, or None if not found
        """
        # First try local index
        local_result = self.get_package(name, version)
        if local_result:
            return local_result
        
        # If not in local index and registries provided, try live lookup with failover
        if not registries:
            return None
        
        try:
            async def search_registry(registry: RegistryConfig, client: httpx.AsyncClient):
                packages = await self._fetch_from_registry(client, registry)
                for pkg in packages:
                    if pkg.name == name and (version is None or pkg.version == version):
                        return PackageInfo(
                            metadata=pkg,
                            registry_name=registry.name,
                            registry_url=registry.url,
                            available_versions=[pkg.version]
                        )
                return None
            
            async with httpx.AsyncClient(timeout=self.failover_manager.config.timeout) as client:
                result = await self.failover_manager.execute_with_failover(
                    lambda reg: search_registry(reg, client),
                    registries,
                    f"search_package_{name}"
                )
                return result
                
        except Exception as e:
            logger.warning(f"Failover search failed for package {name}: {e}")
            return None
