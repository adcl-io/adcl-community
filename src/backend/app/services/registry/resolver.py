# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Dependency Resolver

Single responsibility: Resolve package dependencies with cycle detection
"""

import logging
from typing import List, Optional, Set, Dict, Any

from app.models.registry_models import PackageMetadata, InstallationRecord

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Resolves package dependencies (exact version matching only)"""

    def __init__(self, package_index: Dict[str, Any]):
        """
        Initialize dependency resolver.

        Args:
            package_index: Package index dictionary
        """
        self.package_index = package_index

    def resolve(
        self,
        package: PackageMetadata,
        installed_packages: Dict[str, InstallationRecord],
        visited: Optional[Set[str]] = None
    ) -> List[PackageMetadata]:
        """
        Resolve dependencies for a package with cycle detection.

        For ADCL, dependencies use exact version matching:
        - Agent X needs MCP Y version Z (exact)
        - Team A needs Agents B,C
        - Exact versions only (no semver ranges)

        Args:
            package: Package to resolve dependencies for
            installed_packages: Currently installed packages
            visited: Set of already-visited packages (for cycle detection)

        Returns:
            List of dependency packages (not yet installed)

        Raises:
            ValueError: If circular dependency detected or required dependency not found
        """
        # Initialize visited set on first call
        if visited is None:
            visited = set()

        # Check for circular dependency
        pkg_key = f"{package.name}@{package.version}"
        if pkg_key in visited:
            raise ValueError(f"Circular dependency detected: {pkg_key} already in dependency chain")

        # Mark this package as visited
        visited.add(pkg_key)

        deps_to_install = []

        # Check MCP dependencies
        for dep in package.dependencies.mcps:
            if dep.name not in installed_packages:
                # Find the dependency in registry
                dep_pkg = self._find_package(dep.name, dep.version)

                if dep_pkg:
                    deps_to_install.append(dep_pkg)
                elif dep.required:
                    raise ValueError(f"Required dependency not found: {dep.name}@{dep.version}")

        # Recursively resolve dependencies of dependencies
        all_deps = list(deps_to_install)
        for dep in deps_to_install:
            # Pass visited set to detect cycles
            sub_deps = self.resolve(dep, installed_packages, visited)
            all_deps.extend(sub_deps)

        # Remove duplicates (keep first occurrence)
        unique_deps = self._deduplicate(all_deps)

        return unique_deps

    def _find_package(self, name: str, version: str) -> Optional[PackageMetadata]:
        """
        Find a package in the index.

        Args:
            name: Package name
            version: Package version (exact)

        Returns:
            PackageMetadata or None if not found
        """
        for reg_data in self.package_index.get("registries", {}).values():
            for pkg in reg_data.get("packages", []):
                if pkg["name"] == name and pkg["version"] == version:
                    return PackageMetadata(**pkg)
        return None

    def _deduplicate(self, packages: List[PackageMetadata]) -> List[PackageMetadata]:
        """
        Remove duplicate packages from list (keep first occurrence).

        Args:
            packages: List of packages

        Returns:
            Deduplicated list
        """
        seen = set()
        unique = []
        for pkg in packages:
            key = f"{pkg.name}@{pkg.version}"
            if key not in seen:
                seen.add(key)
                unique.append(pkg)
        return unique
