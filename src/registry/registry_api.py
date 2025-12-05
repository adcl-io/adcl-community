# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Registry API Client

Client for interacting with package registries, downloading packages,
verifying signatures, and managing trusted publishers.
"""

import os
import json
import httpx
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Import GPG functions for verification
from ..signing import gpg


@dataclass
class RegistryConfig:
    """Registry configuration"""
    name: str
    url: str
    enabled: bool = True
    priority: int = 100


class RegistryClient:
    """
    Client for package registry operations.

    Handles:
    - Package discovery and download
    - Signature verification
    - Publisher trust management
    - Package caching
    """

    def __init__(
        self,
        registries: List[RegistryConfig],
        config_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        keyring_dir: Optional[Path] = None
    ):
        """
        Initialize registry client.

        Args:
            registries: List of registry configurations
            config_dir: Directory for client config (default: ./.agent-cli/)
            cache_dir: Directory for package cache (default: ./.agent-cli/cache/)
            keyring_dir: Directory for GPG keyring (default: ./.agent-cli/keyring/)
        """
        self.registries = sorted(registries, key=lambda r: r.priority)

        self.config_dir = Path(config_dir) if config_dir else Path(".agent-cli")
        self.cache_dir = Path(cache_dir) if cache_dir else (self.config_dir / "cache")
        self.keyring_dir = Path(keyring_dir) if keyring_dir else (self.config_dir / "keyring")

        # Create directories
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.keyring_dir.mkdir(parents=True, exist_ok=True)

        self.client = httpx.Client(timeout=30.0)

    def list_packages(
        self,
        package_type: str,
        registry_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List available packages from registries.

        Args:
            package_type: Type of package ('agent', 'mcp', 'team')
            registry_name: Optional specific registry to query

        Returns:
            List of package metadata
        """
        packages = []
        registries_to_query = self.registries

        if registry_name:
            registries_to_query = [r for r in self.registries if r.name == registry_name]

        for registry in registries_to_query:
            if not registry.enabled:
                continue

            try:
                response = self.client.get(f"{registry.url}/{package_type}s")
                response.raise_for_status()

                registry_packages = response.json()
                for pkg in registry_packages:
                    pkg["registry"] = registry.name
                    packages.append(pkg)

            except Exception as e:
                print(f"Failed to query {registry.name}: {e}")

        return packages

    def get_package(
        self,
        package_type: str,
        name: str,
        version: str,
        registry_name: Optional[str] = None,
        verify_signature: bool = True
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get a specific package from registry.

        Args:
            package_type: Type of package ('agent', 'mcp', 'team')
            name: Package name
            version: Package version
            registry_name: Optional specific registry to query
            verify_signature: Whether to verify package signature

        Returns:
            (package_data, signature_valid) tuple
        """
        registries_to_query = self.registries

        if registry_name:
            registries_to_query = [r for r in self.registries if r.name == registry_name]

        for registry in registries_to_query:
            if not registry.enabled:
                continue

            try:
                # Fetch package
                url = f"{registry.url}/{package_type}s/{name}/{version}"
                response = self.client.get(url)
                response.raise_for_status()

                package_data = response.json()

                # Verify signature if requested
                signature_valid = True
                if verify_signature and package_data.get("has_signature"):
                    signature_valid = self._verify_package_signature(
                        package_data,
                        package_type,
                        name,
                        version
                    )

                return (package_data, signature_valid)

            except Exception as e:
                print(f"Failed to get package from {registry.name}: {e}")
                continue

        raise ValueError(f"Package {name} v{version} not found in any registry")

    def _verify_package_signature(
        self,
        package_data: Dict[str, Any],
        package_type: str,
        name: str,
        version: str
    ) -> bool:
        """
        Verify package GPG signature.

        Args:
            package_data: Package data from registry
            package_type: Type of package
            name: Package name
            version: Package version

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Get package config and metadata
            config = package_data.get("config", {})
            metadata = package_data.get("metadata", {})

            # Get publisher ID
            publisher_id = metadata.get("publisher")
            if not publisher_id or publisher_id == "unknown":
                print(f"⚠️  Package {name} has no publisher - cannot verify")
                return False

            # Check if publisher is in keyring
            # TODO: Import publisher key if not present

            # Create temporary files for verification
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Write config to temp file
                config_file = tmpdir_path / f"{package_type}.json"
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)

                # Get signature (would need to fetch from registry)
                # For now, assume signature is in package_data
                signature = package_data.get("signature")
                if not signature:
                    print(f"⚠️  No signature data for {name}")
                    return False

                # Write signature to temp file
                sig_file = tmpdir_path / f"{package_type}.json.asc"
                with open(sig_file, 'w') as f:
                    f.write(signature)

                # Verify
                is_valid, error_msg = gpg.verify_signature(
                    filepath=str(config_file),
                    signature_path=str(sig_file),
                    keyring_dir=str(self.keyring_dir)
                )

                if not is_valid:
                    print(f"❌ Signature verification failed for {name}: {error_msg}")

                return is_valid

        except Exception as e:
            print(f"Error verifying signature for {name}: {e}")
            return False

    def download_package(
        self,
        package_type: str,
        name: str,
        version: str,
        verify_signature: bool = True,
        force: bool = False
    ) -> Path:
        """
        Download and cache a package.

        Args:
            package_type: Type of package ('agent', 'mcp', 'team')
            name: Package name
            version: Package version
            verify_signature: Whether to verify package signature
            force: Force re-download even if cached

        Returns:
            Path to cached package directory
        """
        # Check cache first
        cache_path = self.cache_dir / f"{package_type}s" / name / version
        if cache_path.exists() and not force:
            print(f"✅ Using cached {package_type} {name} v{version}")
            return cache_path

        # Fetch from registry
        print(f"📥 Downloading {package_type} {name} v{version}...")
        package_data, signature_valid = self.get_package(
            package_type,
            name,
            version,
            verify_signature=verify_signature
        )

        if verify_signature and not signature_valid:
            raise ValueError(f"Package {name} v{version} has invalid signature!")

        # Create cache directory
        cache_path.mkdir(parents=True, exist_ok=True)

        # Write config
        config_file = cache_path / f"{package_type}.json"
        with open(config_file, 'w') as f:
            json.dump(package_data.get("config", {}), f, indent=2)

        # Write metadata
        metadata_file = cache_path / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(package_data.get("metadata", {}), f, indent=2)

        print(f"✅ Downloaded and cached {package_type} {name} v{version}")
        return cache_path

    def trust_publisher(self, publisher_id: str, registry_name: Optional[str] = None):
        """
        Import and trust a publisher's public key.

        Args:
            publisher_id: Publisher ID (fingerprint)
            registry_name: Optional specific registry to query
        """
        registries_to_query = self.registries

        if registry_name:
            registries_to_query = [r for r in self.registries if r.name == registry_name]

        for registry in registries_to_query:
            if not registry.enabled:
                continue

            try:
                # Fetch publisher's public key
                response = self.client.get(f"{registry.url}/publishers/{publisher_id}/pubkey")
                response.raise_for_status()

                pubkey_data = response.json()
                public_key = pubkey_data.get("public_key")

                if not public_key:
                    continue

                # Import to keyring
                imported_key_id = gpg.import_public_key(
                    public_key,
                    keyring_dir=str(self.keyring_dir)
                )

                # Update config to add to trusted list
                config_file = self.config_dir / "config.json"
                if config_file.exists():
                    config = json.loads(config_file.read_text())
                else:
                    config = {"trusted_publishers": []}

                if publisher_id not in config.get("trusted_publishers", []):
                    config.setdefault("trusted_publishers", []).append(publisher_id)

                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=2)

                print(f"✅ Trusted publisher {publisher_id} from {registry.name}")
                return imported_key_id

            except Exception as e:
                print(f"Failed to trust publisher from {registry.name}: {e}")
                continue

        raise ValueError(f"Publisher {publisher_id} not found in any registry")

    def list_trusted_publishers(self) -> List[str]:
        """Get list of trusted publisher IDs"""
        config_file = self.config_dir / "config.json"
        if not config_file.exists():
            return []

        config = json.loads(config_file.read_text())
        return config.get("trusted_publishers", [])

    def close(self):
        """Close HTTP client"""
        self.client.close()


# Helper function to create client from config file
def load_client(config_path: Optional[str] = None) -> RegistryClient:
    """
    Load registry client from config file.

    Args:
        config_path: Path to config.json (default: .agent-cli/config.json)

    Returns:
        Configured RegistryClient instance
    """
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = Path(".agent-cli/config.json")

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    config = json.loads(config_file.read_text())

    # Parse registries
    registries = []
    for reg in config.get("registries", []):
        registries.append(RegistryConfig(
            name=reg["name"],
            url=reg["url"],
            enabled=reg.get("enabled", True),
            priority=reg.get("priority", 100)
        ))

    return RegistryClient(
        registries=registries,
        config_dir=config_file.parent,
        cache_dir=Path(config.get("cache_dir", str(config_file.parent / "cache"))),
        keyring_dir=Path(config.get("keyring_dir", str(config_file.parent / "keyring")))
    )
