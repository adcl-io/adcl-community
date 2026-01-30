# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Trigger management API endpoints."""

import httpx
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from app.core.config import get_config

router = APIRouter()
config = get_config()


def parse_registries_conf():
    """Parse registries.conf file - TODO: Move to service layer"""
    import configparser
    from pathlib import Path

    conf_path = Path("/configs/registries.conf")
    if not conf_path.exists():
        return []

    parser = configparser.ConfigParser()
    parser.read(conf_path)

    registries = []
    for section in parser.sections():
        registry = {
            "id": section,
            "name": parser.get(section, "name"),
            "url": parser.get(section, "baseurl"),
            "enabled": parser.getboolean(section, "enabled", fallback=True),
            "priority": parser.getint(section, "priority", fallback=99),
        }
        registries.append(registry)

    return registries


def get_trigger_manager():
    """Get trigger manager instance - TODO: Use dependency injection"""
    # Import here to avoid circular dependency
    # Access via app.state if available, otherwise use lazy initialization
    try:
        from fastapi import Request
        from app.main import app
        if hasattr(app.state, 'trigger_manager') and app.state.trigger_manager:
            return app.state.trigger_manager
    except:
        pass

    # Fallback to main.py global (for backward compatibility)
    from app.main import get_trigger_manager as main_get_trigger_manager
    return main_get_trigger_manager()


@router.post("/registries/install/trigger/{trigger_id}")
async def install_trigger_from_registry(trigger_id: str, user_config: Dict[str, Any]):
    """
    Install trigger from registry with user-specified target

    Args:
        trigger_id: Trigger package ID (format: {name}-{version})
        user_config: User configuration {"workflow_id": "..." OR "team_id": "..."}

    Returns:
        Installation result
    """
    registries = parse_registries_conf()

    # Try each enabled registry by priority
    enabled_registries = [r for r in registries if r.get("enabled", True)]
    enabled_registries.sort(key=lambda r: r.get("priority", 99))

    if not enabled_registries:
        raise HTTPException(status_code=404, detail="No enabled registries found")

    for registry in enabled_registries:
        try:
            async with httpx.AsyncClient(
                timeout=config.get_http_timeout_default()
            ) as client:
                # Try to get trigger package
                # Support both versioned paths (registry/triggers/{name}/{version}/)
                # and flat paths (triggers/{id})
                response = await client.get(f"{registry['url']}/triggers/{trigger_id}")
                response.raise_for_status()
                trigger_package = response.json()

                # Install using Trigger Manager
                result = get_trigger_manager().install(trigger_package, user_config)

                if result["status"] in ["installed", "already_installed"]:
                    result["registry"] = registry.get("name", "Unknown")
                    return result
                elif result["status"] == "error":
                    raise HTTPException(
                        status_code=500,
                        detail=result.get("error", "Installation failed"),
                    )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                continue
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            print(f"Failed to install from {registry.get('name', 'unknown')}: {e}")
            continue

    raise HTTPException(
        status_code=404,
        detail=f"Trigger '{trigger_id}' not found in any enabled registry",
    )


@router.delete("/triggers/{trigger_name}")
async def uninstall_trigger(trigger_name: str):
    """Uninstall a trigger"""
    result = get_trigger_manager().uninstall(trigger_name)

    if result["status"] == "not_installed":
        raise HTTPException(
            status_code=404, detail=f"Trigger '{trigger_name}' is not installed"
        )

    return result


@router.post("/triggers/{trigger_name}/start")
async def start_trigger(trigger_name: str):
    """Start a stopped trigger"""
    return get_trigger_manager().start(trigger_name)


@router.post("/triggers/{trigger_name}/stop")
async def stop_trigger(trigger_name: str):
    """Stop a running trigger"""
    return get_trigger_manager().stop(trigger_name)


@router.post("/triggers/{trigger_name}/restart")
async def restart_trigger(trigger_name: str):
    """Restart a trigger"""
    return get_trigger_manager().restart(trigger_name)


@router.get("/triggers")
async def list_triggers():
    """List all installed triggers (alias for /triggers/installed)"""
    return get_trigger_manager().list_installed()


@router.get("/triggers/installed")
async def list_installed_triggers():
    """List all installed triggers with their status"""
    return get_trigger_manager().list_installed()


@router.get("/triggers/{trigger_name}/status")
async def get_trigger_status(trigger_name: str):
    """Get detailed status of an installed trigger"""
    return get_trigger_manager().get_status(trigger_name)


@router.post("/triggers/{trigger_name}/update")
async def update_trigger(trigger_name: str, registry_id: Optional[str] = None):
    """
    Update a trigger to the latest version from registry
    """
    registries = parse_registries_conf()

    # If no registry specified, try all enabled registries by priority
    if not registry_id:
        registries = [r for r in registries if r.get("enabled", True)]
        registries.sort(key=lambda r: r.get("priority", 99))
    else:
        registries = [
            r for r in registries if r["id"] == registry_id and r.get("enabled", True)
        ]

    if not registries:
        raise HTTPException(status_code=404, detail="No enabled registries found")

    # Get current version
    status = get_trigger_manager().get_status(trigger_name)
    if status.get("status") == "not_installed":
        raise HTTPException(
            status_code=404, detail=f"Trigger '{trigger_name}' is not installed"
        )

    # Try to fetch latest version from registries
    for registry in registries:
        try:
            async with httpx.AsyncClient(
                timeout=config.get_http_timeout_default()
            ) as client:
                # List all triggers and find latest version
                response = await client.get(f"{registry['url']}/triggers")
                response.raise_for_status()
                triggers = response.json()

                # Find trigger by name
                trigger_id = None
                for trigger in triggers:
                    if trigger.get("name") == trigger_name or trigger.get(
                        "id", ""
                    ).startswith(f"{trigger_name}-"):
                        trigger_id = trigger.get("id")
                        break

                if not trigger_id:
                    continue

                # Get full package
                response = await client.get(f"{registry['url']}/triggers/{trigger_id}")
                response.raise_for_status()
                trigger_package = response.json()

                # Update using Trigger manager
                result = get_trigger_manager().update(trigger_name, trigger_package)

                if result["status"] == "updated":
                    result["registry"] = registry.get("name", "Unknown")

                return result

        except Exception as e:
            print(f"Failed to update from {registry.get('name', 'unknown')}: {e}")
            continue

    raise HTTPException(
        status_code=404, detail=f"No updates found for trigger '{trigger_name}'"
    )
