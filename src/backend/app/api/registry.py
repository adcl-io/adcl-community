# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Registry API Endpoints

YUM-style package management REST API for installing, updating,
and managing MCP packages through the registry system.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.services.registry import RegistryService
from app.models.registry_models import (
    InstallOptions,
    PackageSearchResult,
    TransactionOperation
)
from app.core.logging import get_service_logger

logger = get_service_logger("registry_api")

router = APIRouter(prefix="/api/v1/registry", tags=["registry"])

# Dependency injection: Get registry service from app state
def get_registry_service(request: Request) -> RegistryService:
    """
    Get registry service instance from FastAPI app state.

    Uses dependency injection pattern to avoid global mutable state.
    Service is initialized in main.py on startup and stored in app.state.

    Args:
        request: FastAPI request object

    Returns:
        RegistryService instance

    Raises:
        HTTPException: If service not initialized
    """
    service = getattr(request.app.state, "registry_service", None)
    if service is None:
        raise HTTPException(
            status_code=500,
            detail="Registry service not initialized. Check server startup logs."
        )
    return service


# Request/Response Models
class RefreshIndexRequest(BaseModel):
    registry_name: Optional[str] = None


class InstallRequest(BaseModel):
    name: str
    version: Optional[str] = None
    skip_dependencies: bool = False
    verify_signature: bool = False
    force: bool = False
    registry: Optional[str] = None
    local_path: Optional[str] = None  # For air-gapped installation


class UpdateRequest(BaseModel):
    to_version: Optional[str] = None


class RemoveRequest(BaseModel):
    force: bool = False


class LocalDiscoveryRequest(BaseModel):
    directory: str


# Package Discovery Endpoints
@router.get("/packages", response_model=List[PackageSearchResult])
async def list_packages(
    query: Optional[str] = Query(None, description="Search query for name/description"),
    type: Optional[str] = Query(None, description="Filter by package type"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    service: RegistryService = Depends(get_registry_service)
):
    """
    List all packages across all enabled registries.

    Supports filtering by query, type, and tags.
    """
    filters = {}
    if type:
        filters["type"] = type
    if tags:
        filters["tags"] = tags

    try:
        packages = await service.search_packages(query=query, filters=filters)
        return packages
    except Exception as e:
        logger.error(f"Failed to list packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/packages/search", response_model=List[PackageSearchResult])
async def search_packages(
    q: str = Query(..., description="Search query"),
    type: Optional[str] = Query(None, description="Filter by package type"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    service: RegistryService = Depends(get_registry_service)
):
    """
    Search packages across all enabled registries.

    Supports filtering by query, type, and tags.
    """

    filters = {}
    if type:
        filters["type"] = type
    if tags:
        filters["tags"] = tags

    try:
        packages = await service.search_packages(query=q, filters=filters)
        return packages
    except Exception as e:
        logger.error(f"Failed to search packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/packages/{name}")
async def get_package_info(
    name: str,
    version: Optional[str] = Query(None, description="Specific version"),
    service: RegistryService = Depends(get_registry_service)
):
    """Get detailed information about a package."""

    try:
        package_info = await service.get_package_info(name, version)

        if not package_info:
            raise HTTPException(
                status_code=404,
                detail=f"Package not found: {name}@{version or 'latest'}"
            )

        return package_info.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get package info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/packages/{name}/versions")
async def list_package_versions(name: str,
    service: RegistryService = Depends(get_registry_service)
):
    """List all available versions of a package."""

    try:
        # Search for all versions of this package
        all_packages = await service.search_packages(query=name, filters={})

        # Filter exact name matches
        versions = []
        for pkg in all_packages:
            if pkg.name == name:
                versions.append({
                    "version": pkg.version,
                    "registry": pkg.registry,
                    "installed": pkg.installed
                })

        if not versions:
            raise HTTPException(status_code=404, detail=f"Package not found: {name}")

        return {"name": name, "versions": versions}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/packages/{name}/deps")
async def get_package_dependencies(name: str, version: Optional[str] = None,
    service: RegistryService = Depends(get_registry_service)
):
    """Get dependency tree for a package."""

    try:
        package_info = await service.get_package_info(name, version)

        if not package_info:
            raise HTTPException(
                status_code=404,
                detail=f"Package not found: {name}@{version or 'latest'}"
            )

        # Get dependencies using the resolver module
        deps = service.resolver.resolve(package_info.metadata, service.installed_packages)

        return {
            "package": name,
            "version": package_info.metadata.version,
            "dependencies": [
                {"name": dep.name, "version": dep.version}
                for dep in deps
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Package Operations Endpoints
@router.post("/install")
async def install_package(
    request: InstallRequest,
    service: RegistryService = Depends(get_registry_service)
):
    """
    Install a package with dependencies.

    Automatically resolves and installs dependencies unless skip_dependencies is True.
    """
    options = InstallOptions(
        skip_dependencies=request.skip_dependencies,
        verify_signature=request.verify_signature,
        force=request.force,
        registry=request.registry
    )

    try:
        transaction = await service.install_package(
            name=request.name,
            version=request.version,
            options=options,
            local_path=request.local_path  # Support for air-gapped installation
        )

        install_source = "local path" if request.local_path else "registry"
        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "message": f"Package {request.name} installed successfully from {install_source}",
            "failover_used": len(service.get_ordered_registries("install")) > 1
        }
    except Exception as e:
        logger.error(f"Installation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update/{name}")
async def update_package(
    name: str,
    request: UpdateRequest,
    service: RegistryService = Depends(get_registry_service)
):
    """Update a package to a new version."""
    try:
        transaction = await service.update_package(
            name=name,
            to_version=request.to_version
        )

        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "message": f"Package {name} updated successfully"
        }
    except Exception as e:
        logger.error(f"Update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-all")
async def update_all_packages(
    service: RegistryService = Depends(get_registry_service)
):
    """Update all installed packages to latest versions."""

    results = []
    for name in service.installed_packages.keys():
        try:
            transaction = await service.update_package(name, to_version=None)
            results.append({
                "name": name,
                "status": "updated",
                "transaction_id": transaction.id
            })
        except Exception as e:
            logger.error(f"Failed to update {name}: {e}")
            results.append({
                "name": name,
                "status": "failed",
                "error": str(e)
            })

    return {
        "success": True,
        "results": results,
        "total": len(results),
        "updated": len([r for r in results if r["status"] == "updated"]),
        "failed": len([r for r in results if r["status"] == "failed"])
    }


@router.delete("/remove/{name}")
async def remove_package(
    name: str,
    force: bool = Query(False),
    service: RegistryService = Depends(get_registry_service)
):
    """Remove a package."""
    try:
        transaction = await service.remove_package(name=name, force=force)

        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "message": f"Package {name} removed successfully"
        }
    except Exception as e:
        logger.error(f"Removal failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Transaction Management Endpoints
@router.get("/transactions")
async def list_transactions(
    limit: int = Query(50, le=500),
    service: RegistryService = Depends(get_registry_service)
):
    """List recent transactions."""

    try:
        transactions = service.list_transactions(limit=limit)
        return {"transactions": transactions, "total": len(transactions)}
    except Exception as e:
        logger.error(f"Failed to list transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Air-Gapped Environment Endpoints
@router.post("/discover-local")
async def discover_local_packages(
    request: LocalDiscoveryRequest,
    service: RegistryService = Depends(get_registry_service)
):
    """
    Discover packages in a local directory (air-gapped mode).
    
    Scans the specified directory for packages with mcp.json files
    and returns their metadata for installation.
    """
    try:
        packages = await service.discover_local_packages(request.directory)
        
        return {
            "success": True,
            "directory": request.directory,
            "packages": [pkg.model_dump() for pkg in packages],
            "total": len(packages)
        }
    except Exception as e:
        logger.error(f"Failed to discover local packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install-local")
async def install_from_local_path(
    local_path: str = Query(..., description="Path to local package directory"),
    skip_dependencies: bool = Query(False, description="Skip dependency installation"),
    force: bool = Query(False, description="Force installation even if already installed"),
    service: RegistryService = Depends(get_registry_service)
):
    """
    Install a package directly from a local directory (air-gapped mode).
    
    This endpoint allows installation without needing to know the package name
    in advance - it reads the metadata from the local directory.
    """
    options = InstallOptions(
        skip_dependencies=skip_dependencies,
        force=force
    )
    
    try:
        transaction = await service.install_from_local_path(local_path, options)
        
        return {
            "success": True,
            "transaction": transaction.to_dict(),
            "message": f"Package installed successfully from {local_path}"
        }
    except Exception as e:
        logger.error(f"Local installation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local-registries")
async def list_local_registries(
    service: RegistryService = Depends(get_registry_service)
):
    """
    List all configured local (file://) registries.
    
    Useful for air-gapped environments to see what local package
    sources are available.
    """
    try:
        local_registries = {
            name: config for name, config in service.registries.items()
            if config.url.startswith("file://")
        }
        
        return {
            "success": True,
            "local_registries": {
                name: {
                    "name": config.display_name,
                    "url": config.url,
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "type": config.type
                }
                for name, config in local_registries.items()
            },
            "total": len(local_registries)
        }
    except Exception as e:
        logger.error(f"Failed to list local registries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-local-package")
async def validate_local_package(
    local_path: str = Query(..., description="Path to local package directory")
):
    """
    Validate a local package directory structure and metadata.
    
    Checks that the directory contains required files (mcp.json, Dockerfile)
    and that the metadata is valid.
    """
    try:
        from pathlib import Path
        import json
        from app.models.registry_models import PackageMetadata
        
        package_dir = Path(local_path).resolve()
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "package_info": None
        }
        
        # Check directory exists
        if not package_dir.exists():
            validation_results["valid"] = False
            validation_results["errors"].append(f"Directory does not exist: {local_path}")
            return validation_results
        
        if not package_dir.is_dir():
            validation_results["valid"] = False
            validation_results["errors"].append(f"Path is not a directory: {local_path}")
            return validation_results
        
        # Check for mcp.json
        mcp_json_path = package_dir / "mcp.json"
        if not mcp_json_path.exists():
            validation_results["valid"] = False
            validation_results["errors"].append("Missing required file: mcp.json")
        else:
            try:
                with open(mcp_json_path) as f:
                    metadata_dict = json.load(f)
                
                # Validate metadata structure
                if "name" not in metadata_dict:
                    validation_results["errors"].append("Missing required field: name")
                if "version" not in metadata_dict:
                    validation_results["errors"].append("Missing required field: version")
                if "deployment" not in metadata_dict:
                    validation_results["warnings"].append("Missing deployment configuration")
                
                # Add type field if missing
                if "type" not in metadata_dict:
                    metadata_dict["type"] = "mcp"
                    validation_results["warnings"].append("Missing type field, defaulting to 'mcp'")
                
                # Try to create PackageMetadata object
                try:
                    package_metadata = PackageMetadata(**metadata_dict)
                    validation_results["package_info"] = package_metadata.model_dump()
                except Exception as e:
                    validation_results["errors"].append(f"Invalid metadata structure: {e}")
                
            except json.JSONDecodeError as e:
                validation_results["errors"].append(f"Invalid JSON in mcp.json: {e}")
            except Exception as e:
                validation_results["errors"].append(f"Failed to read mcp.json: {e}")
        
        # Check for Dockerfile
        dockerfile_path = package_dir / "Dockerfile"
        if not dockerfile_path.exists():
            validation_results["warnings"].append("Missing Dockerfile (may be required for installation)")
        
        # Update valid status based on errors
        if validation_results["errors"]:
            validation_results["valid"] = False
        
        return {
            "success": True,
            "validation": validation_results
        }
        
    except Exception as e:
        logger.error(f"Package validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str,
    service: RegistryService = Depends(get_registry_service)
):
    """Get details of a specific transaction."""

    try:
        transactions = service.list_transactions(limit=1000)

        for txn in transactions:
            if txn.get("id") == transaction_id:
                return txn

        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions/{transaction_id}/rollback")
async def rollback_transaction(transaction_id: str,
    service: RegistryService = Depends(get_registry_service)
):
    """Rollback a transaction."""

    try:
        success = await service.rollback_transaction(transaction_id)

        return {
            "success": success,
            "message": f"Transaction {transaction_id} rolled back successfully"
        }
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Registry Management Endpoints
@router.get("/registries")
async def list_registries(
    service: RegistryService = Depends(get_registry_service)
):
    """List all configured registries."""

    registries = []
    for name, config in service.registries.items():
        registries.append({
            "name": name,
            "display_name": config.display_name,
            "url": config.url,
            "enabled": config.enabled,
            "priority": config.priority,
            "trust_level": config.trust_level.value,
            "type": config.type
        })

    return {"registries": registries}


@router.post("/registries/{name}/enable")
async def enable_registry(name: str,
    service: RegistryService = Depends(get_registry_service)
):
    """Enable a registry."""

    if name not in service.registries:
        raise HTTPException(status_code=404, detail=f"Registry not found: {name}")

    service.registries[name].enabled = True

    return {
        "success": True,
        "message": f"Registry {name} enabled"
    }


@router.post("/registries/{name}/disable")
async def disable_registry(name: str,
    service: RegistryService = Depends(get_registry_service)
):
    """Disable a registry."""

    if name not in service.registries:
        raise HTTPException(status_code=404, detail=f"Registry not found: {name}")

    service.registries[name].enabled = False

    return {
        "success": True,
        "message": f"Registry {name} disabled"
    }


@router.post("/registries/refresh")
async def refresh_index(request: RefreshIndexRequest,
    service: RegistryService = Depends(get_registry_service)
):
    """Refresh package index from registries."""

    try:
        await service.refresh_index(registry_name=request.registry_name)

        return {
            "success": True,
            "message": "Package index refreshed successfully"
        }
    except Exception as e:
        logger.error(f"Index refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cache Management Endpoints
@router.get("/cache")
async def list_cache(
    service: RegistryService = Depends(get_registry_service)
):
    """List cached packages."""

    cache_dir = service.packages_dir

    cached_packages = []
    if cache_dir.exists():
        for pkg_dir in cache_dir.iterdir():
            if pkg_dir.is_dir() and not pkg_dir.name.startswith("."):
                cached_packages.append({
                    "name": pkg_dir.name,
                    "path": str(pkg_dir),
                    "size_bytes": sum(f.stat().st_size for f in pkg_dir.rglob("*") if f.is_file())
                })

    return {"cached_packages": cached_packages, "total": len(cached_packages)}


@router.post("/cache/clean")
async def clean_cache(
    service: RegistryService = Depends(get_registry_service)
):
    """Clean package cache."""

    cache_dir = service.packages_dir

    removed = []
    if cache_dir.exists():
        for pkg_dir in cache_dir.iterdir():
            if pkg_dir.is_dir() and not pkg_dir.name.startswith("."):
                # Only remove if not currently installed
                pkg_name = pkg_dir.name.split("-")[0]  # Remove version suffix
                if pkg_name not in service.installed_packages:
                    import shutil
                    shutil.rmtree(pkg_dir)
                    removed.append(pkg_dir.name)

    return {
        "success": True,
        "removed": removed,
        "total": len(removed),
        "message": f"Removed {len(removed)} cached packages"
    }


# Installed Packages Endpoint
@router.get("/installed")
async def list_installed_packages(
    service: RegistryService = Depends(get_registry_service)
):
    """List all installed packages."""

    packages = []
    for name, record in service.installed_packages.items():
        packages.append({
            "name": name,
            "version": record.version,
            "installed_at": record.installed_at.isoformat(),
            "installed_from": record.installed_from,
            "container_id": record.container_id,
            "container_name": record.container_name,
            "transaction_id": record.transaction_id
        })

    return {"packages": packages, "total": len(packages)}


# Registry Health and Failover Endpoints
@router.get("/registries/health")
async def get_registry_health(
    service: RegistryService = Depends(get_registry_service)
):
    """Get health status for all registries."""
    try:
        health_summary = service.get_registry_health()
        ordered_registries = service.get_ordered_registries("health_check")
        
        return {
            "success": True,
            "registry_health": health_summary,
            "ordered_registries": ordered_registries,
            "total_registries": len(service.registries),
            "available_registries": len([
                name for name, health in health_summary.items() 
                if health.get("is_available", False)
            ])
        }
    except Exception as e:
        logger.error(f"Failed to get registry health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/registries/health/check")
async def run_health_checks(
    service: RegistryService = Depends(get_registry_service)
):
    """Run health checks on all enabled registries."""
    try:
        await service.run_health_checks()
        health_summary = service.get_registry_health()
        
        return {
            "success": True,
            "message": "Health checks completed",
            "registry_health": health_summary
        }
    except Exception as e:
        logger.error(f"Health checks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failover/config")
async def get_failover_config(
    service: RegistryService = Depends(get_registry_service)
):
    """Get current failover configuration."""
    try:
        config = service.get_failover_config()
        return {
            "success": True,
            "failover_config": {
                "max_retries": config.max_retries,
                "retry_delay": config.retry_delay,
                "max_retry_delay": config.max_retry_delay,
                "backoff_multiplier": config.backoff_multiplier,
                "health_check_interval": config.health_check_interval,
                "timeout": config.timeout,
                "circuit_breaker_threshold": config.circuit_breaker_threshold,
                "circuit_breaker_reset_time": config.circuit_breaker_reset_time
            }
        }
    except Exception as e:
        logger.error(f"Failed to get failover config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class FailoverConfigRequest(BaseModel):
    max_retries: Optional[int] = None
    retry_delay: Optional[float] = None
    max_retry_delay: Optional[float] = None
    backoff_multiplier: Optional[float] = None
    health_check_interval: Optional[int] = None
    timeout: Optional[float] = None
    circuit_breaker_threshold: Optional[int] = None
    circuit_breaker_reset_time: Optional[int] = None


@router.post("/failover/config")
async def update_failover_config(
    request: FailoverConfigRequest,
    service: RegistryService = Depends(get_registry_service)
):
    """Update failover configuration."""
    try:
        from app.services.registry.failover import FailoverConfig
        
        current_config = service.get_failover_config()
        
        # Update only provided fields
        config_data = current_config.__dict__.copy()
        for field, value in request.dict(exclude_unset=True).items():
            if value is not None:
                config_data[field] = value
        
        new_config = FailoverConfig(**config_data)
        service.update_failover_config(new_config)
        
        return {
            "success": True,
            "message": "Failover configuration updated",
            "failover_config": config_data
        }
    except Exception as e:
        logger.error(f"Failed to update failover config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/registries/{name}/circuit-breaker/reset")
async def reset_circuit_breaker(
    name: str,
    service: RegistryService = Depends(get_registry_service)
):
    """Reset circuit breaker for a specific registry."""
    try:
        success = service.reset_circuit_breaker(name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Registry not found: {name}")
        
        return {
            "success": True,
            "message": f"Circuit breaker reset for registry: {name}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registries/ordered")
async def get_ordered_registries(
    operation: str = Query("general", description="Operation context for ordering"),
    service: RegistryService = Depends(get_registry_service)
):
    """Get registries ordered by priority and health for optimal selection."""
    try:
        ordered_registries = service.get_ordered_registries(operation)
        
        return {
            "success": True,
            "operation": operation,
            "ordered_registries": ordered_registries,
            "total": len(ordered_registries)
        }
    except Exception as e:
        logger.error(f"Failed to get ordered registries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
