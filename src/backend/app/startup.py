# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Orchestrator startup logic - Extracted from main.py (Phase 5 refactoring)"""

import asyncio
import os
import json
import httpx
import docker
from pathlib import Path as _PathForEnv

from app.models import MCPServerInfo
from app.services.model_config_service import load_models_from_config


async def run_startup(app, config, engine, agent_runtime, team_runtime, registry,
                      get_mcp_manager, get_trigger_manager, parse_registries_conf):
    """
    Startup tasks:
    0. Check and perform automatic migration if needed
    1. Store runtime objects in app.state for dependency injection
    2. Discover and register dynamically installed MCPs
    3. Auto-install default MCPs from registry if configured

    Args:
        app: FastAPI application instance
        config: Configuration object
        engine: Workflow engine instance
        agent_runtime: Agent runtime instance
        team_runtime: Team runtime instance
        registry: MCP registry instance
        get_mcp_manager: Function to get MCP manager
        get_trigger_manager: Function to get trigger manager
        parse_registries_conf: Function to parse registries config
    """
    print("🚀 Starting orchestrator...")

    # 0. Check and perform automatic migration if needed (US-011)
    print("🔄 Checking for installation migration...")
    try:
        from app.services.startup_migration_service import StartupMigrationService

        startup_migration_service = StartupMigrationService()
        migration_result = await startup_migration_service.check_and_migrate_on_startup()

        status = migration_result.get("status")
        if status == "migration_completed":
            version = migration_result.get("migrated_to_version", "unknown")
            count = migration_result.get("migrations_completed", 0)
            print(f"✅ Migration completed successfully to version {version} ({count} migrations)")
        elif status == "no_migration_needed":
            version = migration_result.get("current_version", "unknown")
            print(f"✅ Installation is current (version {version}) - no migration needed")
        elif status == "migration_required":
            required = migration_result.get("required_migrations", [])
            print(f"⚠️  Migration required but not automatic: {len(required)} migrations needed")
            print("   Use /api/migration/auto to perform migration")
        elif status == "migration_failed":
            error = migration_result.get("error", "Unknown error")
            print(f"❌ Migration failed: {error}")
            print("   Application will continue but may have compatibility issues")
        elif status == "migration_error":
            error = migration_result.get("error", "Unknown error")
            print(f"⚠️  Migration check failed: {error}")
            print("   Application will continue but migration status unknown")

        # Store migration service for API access
        app.state.startup_migration_service = startup_migration_service

    except Exception as e:
        print(f"⚠️  Failed to check migration status: {str(e)}")
        print("   Application will continue but migration status unknown")

    # Store runtime objects in app.state for proper dependency injection
    app.state.workflow_engine = engine
    app.state.agent_runtime = agent_runtime
    app.state.team_runtime = team_runtime
    app.state.mcp_registry = registry  # Global MCP registry with registered servers
    app.state.mcp_manager = None  # Will be set after MCP manager initializes
    print("✅ Runtime objects stored in app.state")

    # Wait for registry to be ready
    print("⏳ Waiting for registry server...")
    await asyncio.sleep(config.get_polling_interval())

    # 1. Discover already installed MCPs and get MCP network name
    print("🔍 Discovering installed MCPs...")
    try:
        mcp_mgr = get_mcp_manager()
        app.state.mcp_manager = mcp_mgr  # Store in app.state for dependency injection
        installed_mcps = mcp_mgr.list_installed()
        installed_names = {mcp["name"] for mcp in installed_mcps}

        # Get the actual MCP network name (auto-detected with compose prefix)
        mcp_network_name = getattr(mcp_mgr, 'network_name', 'mcp-network')
        print(f"📡 Using MCP network: {mcp_network_name}")
    except Exception as e:
        print(f"⚠️  Could not discover installed MCPs: {e}")
        installed_mcps = []
        installed_names = set()
        mcp_network_name = 'mcp-network'

    # 1.5. Initialize Registry Service for YUM-style package management
    print("📦 Initializing Registry Service...")
    try:
        from app.services.registry import RegistryService

        # base_dir will be loaded from APP_BASE_DIR environment variable
        registry_service = RegistryService(mcp_manager=mcp_mgr)
        # Store in app.state for dependency injection (no global variable)
        app.state.registry_service = registry_service
        print(f"✅ Registry Service initialized with {len(registry_service.registries)} registries")

        # Refresh package index from registries
        await registry_service.refresh_index()
        print(f"✅ Package index refreshed")
    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize Registry Service: {e}")
        print("   Registry features will be disabled.")

    # 2. Initialize Vulhub using MCP network (no separate network needed)
    print(f"🎯 Initializing Vulhub services on {mcp_network_name}...")
    from app.api.vulhub import init_vulhub_services
    try:
        init_vulhub_services(mcp_network_name)
        print(f"✅ Vulhub services initialized on {mcp_network_name}")
    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize Vulhub services: {e}")
        print("   Vulhub features will be disabled.")

    # 3. Start any stopped MCP containers
    if installed_mcps:
        print("🔄 Ensuring MCP containers are running...")
        for mcp in installed_mcps:
            mcp_name = mcp.get("name")
            if not mcp.get("running"):
                try:
                    print(f"  Starting {mcp_name}...")
                    result = mcp_mgr.start(mcp_name)
                    if result.get("status") == "started":
                        print(f"  ✅ Started {mcp_name}")
                    else:
                        print(f"  ⚠️  Failed to start {mcp_name}: {result.get('error', 'Unknown')}")
                except Exception as e:
                    print(f"  ⚠️  Error starting {mcp_name}: {e}")

    # 4. Auto-install default MCPs from registry if not already installed
    def get_auto_install_packages():
        """
        Get list of packages to auto-install.
        Reads from configs/auto-install.json (preferred) or AUTO_INSTALL_MCPS env var (fallback).
        """
        # Prefer JSON configuration file (use ADCL_SYSTEM_CONFIG_DIR for system configs)
        config_dir = _PathForEnv(os.getenv('ADCL_SYSTEM_CONFIG_DIR', '/configs'))
        auto_install_file = config_dir / "auto-install.json"
        if auto_install_file.exists():
            try:
                with open(auto_install_file) as f:
                    config_data = json.load(f)

                if not config_data.get("auto_install", {}).get("enabled", True):
                    print("ℹ️  Auto-install is disabled in configs/auto-install.json")
                    return []

                packages = config_data.get("auto_install", {}).get("packages", {})
                # Filter enabled packages and sort by priority
                enabled_packages = [
                    (name, pkg.get("priority", 99), pkg.get("required", False))
                    for name, pkg in packages.items()
                    if pkg.get("enabled", False)
                ]
                enabled_packages.sort(key=lambda x: x[1])  # Sort by priority

                package_names = [name for name, _, _ in enabled_packages]
                required_count = sum(1 for _, _, req in enabled_packages if req)
                optional_count = len(enabled_packages) - required_count

                print(f"📦 Auto-install from configs/auto-install.json:")
                print(f"   • {required_count} required package(s)")
                print(f"   • {optional_count} optional package(s)")
                print(f"   • Order: {', '.join(package_names)}")

                return package_names
            except Exception as e:
                print(f"⚠️  Failed to read configs/auto-install.json: {e}")
                print("   Falling back to AUTO_INSTALL_MCPS environment variable")

        # Fallback to environment variable (backward compatibility)
        auto_install = os.getenv("AUTO_INSTALL_MCPS", "")
        if auto_install:
            mcps = [name.strip() for name in auto_install.split(",") if name.strip()]
            print(f"📦 Auto-install from environment variable: {', '.join(mcps)}")
            return mcps

        return []

    mcps_to_install = get_auto_install_packages()
    if mcps_to_install:
        print(f"📦 Installing {len(mcps_to_install)} package(s)...")

        for mcp_name in mcps_to_install:
            # Check if already installed with same version
            installed_mcp = next((m for m in installed_mcps if m["name"] == mcp_name), None)

            try:
                # Fetch from registry
                registries = parse_registries_conf()
                enabled_registries = [r for r in registries if r.get("enabled", True)]

                for reg in enabled_registries:
                    try:
                        # Handle file:// registries
                        if reg['url'].startswith('file://'):
                            from pathlib import Path

                            local_path = reg['url'].replace('file://', '')
                            if local_path.startswith('./') or local_path.startswith('../'):
                                base_dir = os.getenv('APP_BASE_DIR', '/app')
                                directory = (Path(base_dir) / local_path).resolve()
                            else:
                                directory = Path(local_path)

                            # Scan all subdirectories to find mcp.json with matching name
                            # (directory name might not match package name)
                            mcp_package = None
                            if directory.exists() and directory.is_dir():
                                for item in directory.iterdir():
                                    if not item.is_dir():
                                        continue
                                    mcp_json_path = item / "mcp.json"
                                    if mcp_json_path.exists():
                                        try:
                                            with open(mcp_json_path) as f:
                                                pkg = json.load(f)
                                            # Match by package name from mcp.json, not directory name
                                            if pkg.get("name") == mcp_name:
                                                mcp_package = pkg
                                                break
                                        except Exception as e:
                                            print(f"  ⚠️  Failed to read {mcp_json_path}: {e}")
                                            continue

                            if not mcp_package:
                                continue

                            # Check if version matches installed version AND container actually exists
                            if installed_mcp:
                                installed_version = installed_mcp.get("version")
                                package_version = mcp_package.get("version")
                                # Verify container exists before considering it "installed"
                                container_name = f"mcp-{mcp_name.replace('_', '-')}"
                                container_exists = False
                                try:
                                    docker_client = docker.from_env()
                                    docker_client.containers.get(container_name)
                                    container_exists = True
                                except docker.errors.NotFound:
                                    pass  # Container doesn't exist

                                if installed_version == package_version and container_exists:
                                    print(f"  ⏭️  Skipping {mcp_name} - already installed and running (v{installed_version})")
                                    break

                            # Install or upgrade from file:// registry
                            if installed_mcp:
                                print(f"  🔄 Upgrading {mcp_name} from v{installed_mcp.get('version')} to v{mcp_package.get('version')}...")
                            else:
                                print(f"  📥 Installing {mcp_name} from {reg['name']}...")

                            result = get_mcp_manager().install(mcp_package)

                            if result["status"] in ["installed", "already_installed"]:
                                print(f"  ✅ Installed {mcp_name} successfully from file:// registry")
                                installed_mcps.append(result)
                                break
                            else:
                                print(f"  ❌ Failed to install {mcp_name}: {result.get('error', 'Unknown error')}")

                            continue

                        async with httpx.AsyncClient(
                            timeout=config.get_http_timeout_default()
                        ) as client:
                            # Try to find MCP by name
                            response = await client.get(f"{reg['url']}/catalog")
                            response.raise_for_status()
                            catalog = response.json()

                            # Find MCP in catalog
                            mcp_id = None
                            for mcp in catalog.get("mcps", []):
                                if mcp.get("name") == mcp_name:
                                    mcp_id = mcp.get("id")
                                    break

                            if mcp_id:
                                # Fetch full package
                                response = await client.get(
                                    f"{reg['url']}/mcps/{mcp_id}"
                                )
                                response.raise_for_status()
                                mcp_package = response.json()

                                # Check if version matches installed version AND container actually exists
                                if installed_mcp:
                                    installed_version = installed_mcp.get("version")
                                    package_version = mcp_package.get("version")
                                    # Verify container exists before considering it "installed"
                                    container_name = f"mcp-{mcp_name.replace('_', '-')}"
                                    container_exists = False
                                    try:
                                        docker_client = docker.from_env()
                                        docker_client.containers.get(container_name)
                                        container_exists = True
                                    except docker.errors.NotFound:
                                        pass  # Container doesn't exist

                                    if installed_version == package_version and container_exists:
                                        print(f"  ⏭️  Skipping {mcp_name} - already installed and running (v{installed_version})")
                                        break

                                # Install or upgrade
                                if installed_mcp:
                                    print(
                                        f"  🔄 Upgrading {mcp_name} from v{installed_mcp.get('version')} to v{mcp_package.get('version')}..."
                                    )
                                else:
                                    print(
                                        f"  📥 Installing {mcp_name} from {reg['name']}..."
                                    )
                                result = get_mcp_manager().install(mcp_package)

                                if result["status"] in [
                                    "installed",
                                    "already_installed",
                                ]:
                                    print(f"  ✅ Installed {mcp_name} successfully")
                                    installed_mcps.append(result)
                                    break
                                else:
                                    print(
                                        f"  ❌ Failed to install {mcp_name}: {result.get('error', 'Unknown error')}"
                                    )
                    except Exception as e:
                        print(
                            f"  ⚠️  Error fetching {mcp_name} from {reg.get('name', 'registry')}: {e}"
                        )
                        continue

                # If not found in any registry, try installing from local mcp_servers/ as final fallback
                base_dir = os.getenv('APP_BASE_DIR', '/app')
                local_mcp_path = _PathForEnv(base_dir) / "mcp_servers" / mcp_name / "mcp.json"
                if local_mcp_path.exists():
                    print(f"  📦 Loading {mcp_name} from local mcp_servers/...")
                    try:
                        with open(local_mcp_path, 'r') as f:
                            mcp_package = json.load(f)

                        # Check if version matches installed version
                        if installed_mcp:
                            installed_version = installed_mcp.get("version")
                            package_version = mcp_package.get("version")
                            if installed_version == package_version:
                                print(f"  ⏭️  Skipping {mcp_name} - already installed (v{installed_version})")
                                continue

                        # Install or upgrade from local
                        if installed_mcp:
                            print(
                                f"  🔄 Upgrading {mcp_name} from v{installed_mcp.get('version')} to v{mcp_package.get('version')}..."
                            )
                        else:
                            print(f"  📥 Installing {mcp_name} from local mcp_servers/...")

                        result = get_mcp_manager().install(mcp_package)

                        if result["status"] in ["installed", "already_installed"]:
                            print(f"  ✅ Installed {mcp_name} successfully")
                            installed_mcps.append(result)
                        else:
                            print(
                                f"  ❌ Failed to install {mcp_name}: {result.get('error', 'Unknown error')}"
                            )
                    except Exception as e:
                        print(f"  ⚠️  Failed to install {mcp_name} from local: {e}")

            except Exception as e:
                print(f"  ⚠️  Failed to auto-install {mcp_name}: {e}")

    # 5. Register all installed MCPs with orchestrator
    print("🔧 Registering installed MCPs...")
    installed_mcps = get_mcp_manager().list_installed()

    for mcp in installed_mcps:
        # Only register if running
        if mcp.get("running"):
            try:
                # Get full package info to register
                # Use backwards-compatible property access (works for both MCPManager and DockerManager)
                mcp_manager = get_mcp_manager()
                installed_registry = getattr(
                    mcp_manager, "installed", mcp_manager.installed_mcps
                )
                mcp_info = installed_registry.get(mcp["name"])
                if mcp_info and "package" in mcp_info:
                    mcp_package = mcp_info["package"]
                    deployment = mcp_package.get("deployment", {})

                    # Determine endpoint based on network mode
                    if deployment.get("network_mode") == "host":
                        # Host mode: use host.docker.internal
                        port_env_var = f"{mcp['name'].upper()}_PORT"
                        port = os.getenv(port_env_var, str(config.get_nmap_port()))
                        endpoint = config.get_docker_host_url_pattern().format(
                            port=port
                        )
                    else:
                        # Bridge mode: use container name
                        container_name = deployment.get(
                            "container_name", f"mcp-{mcp['name']}"
                        )
                        port_config = deployment.get("ports", [{}])[0]
                        port = port_config.get(
                            "container", str(config.get_agent_port())
                        )
                        # Resolve environment variables in port
                        port = (
                            port.replace("${", "").split(":-")[1].replace("}", "")
                            if "${" in str(port)
                            else port
                        )
                        endpoint = config.get_docker_container_url_pattern().format(
                            container_name=container_name, port=port
                        )

                    # Register with orchestrator
                    registry.register(
                        MCPServerInfo(
                            name=mcp["name"],
                            endpoint=endpoint,
                            description=mcp_package.get("description", ""),
                            version=mcp_package.get("version", "1.0.0"),
                        )
                    )
                    print(
                        f"  ✅ Registered {mcp['name']} v{mcp['version']} at {endpoint}"
                    )
            except Exception as e:
                print(f"  ⚠️  Failed to register {mcp['name']}: {e}")

    print(f"✅ Orchestrator ready! {len(registry.servers)} MCP servers registered.")

    # 6. Load model configurations from configs/models.yaml
    print("🤖 Loading model configurations from configs/models.yaml...")
    # Import models_db from main to update it
    from app.services.model_config_service import models_db as db, models_lock
    async with models_lock:
        db.clear()
        db.extend(load_models_from_config())
    print(f"✅ Loaded {len(db)} models")
