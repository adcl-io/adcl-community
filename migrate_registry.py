#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Migrate packages from old registry-server/registries/ structure to new registry/ structure.

Old structure: registry-server/registries/{type}/{name}-{version}.json
New structure: registry/{type}s/{name}/{version}/{type}.json
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import re


def parse_old_filename(filename):
    """
    Parse old filename format: {name}-{version}.json

    Returns: (name, version) or None if invalid
    """
    # Remove .json extension
    stem = filename.replace('.json', '')

    # Try to match {name}-{version} pattern
    # Version typically looks like X.Y.Z
    match = re.match(r'^(.+?)-(\d+\.\d+\.\d+.*)$', stem)
    if match:
        return match.group(1), match.group(2)

    return None, None


def create_metadata(package_type, name, version, config_data):
    """Create metadata.json for a package"""
    return {
        "package_type": package_type,
        "name": name,
        "version": version,
        "created_at": datetime.now().isoformat(),
        "publisher": "unknown",  # Will be set when signing
        "description": config_data.get("description", ""),
        "checksum": {
            "sha256": "",  # Will be calculated when signing
            "md5": ""
        },
        "signature": {
            "signed": False,
            "signer": None,
            "timestamp": None
        },
        "migrated_from": "registry-server/registries"
    }


def migrate_package(old_path, package_type, registry_root):
    """
    Migrate a single package file to new structure.

    Args:
        old_path: Path to old package file
        package_type: 'team' or 'mcp'
        registry_root: Path to new registry root
    """
    # Parse filename
    filename = old_path.name
    name, version = parse_old_filename(filename)

    if not name or not version:
        print(f"  ⚠️  Skipping {filename}: Could not parse name/version")
        return False

    # Read old config
    try:
        with open(old_path, 'r') as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"  ❌ Error reading {filename}: {e}")
        return False

    # Create new directory structure
    plural_type = package_type + 's'  # team -> teams, mcp -> mcps
    new_dir = registry_root / plural_type / name / version
    new_dir.mkdir(parents=True, exist_ok=True)

    # Write config file with new name
    config_file = new_dir / f"{package_type}.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)

    # Create metadata file
    metadata = create_metadata(package_type, name, version, config_data)
    metadata_file = new_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  ✅ Migrated: {name} v{version} -> {new_dir}")
    return True


def main():
    """Main migration function"""
    print("=" * 70)
    print("Registry Migration: Old Structure → New Structure")
    print("=" * 70)

    old_registry_root = Path("registry-server/registries")
    new_registry_root = Path("registry")

    if not old_registry_root.exists():
        print(f"❌ Old registry not found: {old_registry_root}")
        return

    if not new_registry_root.exists():
        print(f"❌ New registry not found: {new_registry_root}")
        print("   Please create it first with: mkdir -p registry/{publishers,agents,mcps,teams}")
        return

    total_migrated = 0

    # Migrate teams
    print("\n📦 Migrating Teams...")
    teams_dir = old_registry_root / "teams"
    if teams_dir.exists():
        for old_file in teams_dir.glob("*.json"):
            if migrate_package(old_file, "team", new_registry_root):
                total_migrated += 1

    # Migrate MCPs
    print("\n📦 Migrating MCPs...")
    mcps_dir = old_registry_root / "mcps"
    if mcps_dir.exists():
        for old_file in mcps_dir.glob("*.json"):
            if migrate_package(old_file, "mcp", new_registry_root):
                total_migrated += 1

    # Migrate agents if they exist
    print("\n📦 Migrating Agents...")
    agents_dir = old_registry_root / "agents"
    if agents_dir.exists():
        for old_file in agents_dir.glob("*.json"):
            if migrate_package(old_file, "agent", new_registry_root):
                total_migrated += 1

    print("\n" + "=" * 70)
    print(f"✅ Migration Complete: {total_migrated} packages migrated")
    print("=" * 70)

    print("\n📋 Next Steps:")
    print("  1. Review migrated packages in registry/")
    print("  2. Sign packages with GPG (see docs/GPG_PASSPHRASE_SETUP.md)")
    print("  3. Update backend to use new registry/ path")
    print("  4. Test package loading and verification")
    print("\n⚠️  Note: Old registry-server/registries/ is still intact")
    print("   You can delete it after verifying the migration.")


if __name__ == "__main__":
    main()
