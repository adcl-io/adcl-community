# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP & Team Registry Server v2
Enhanced registry with GPG signature support and nested package structure

Registry Structure:
  registry/
    publishers/{publisher_id}/
      pubkey.asc
      metadata.json
    agents/{name}/{version}/
      agent.json
      agent.json.asc
      metadata.json
    mcps/{name}/{version}/
      mcp.json
      mcp.json.asc
      metadata.json
    teams/{name}/{version}/
      team.json
      team.json.asc
      metadata.json
    triggers/{name}/{version}/
      trigger.json
      trigger.json.asc
      metadata.json
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

app = FastAPI(
    title="ADCL Package Registry Server v2",
    description="Package registry with GPG signing support for agents, MCPs, teams, and triggers",
    version="2.0.0"
)

# CORS for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registry directory (new nested structure)
REGISTRY_DIR = Path("/app/registry")


class PackageInfo(BaseModel):
    """Package information for catalog"""
    name: str
    version: str
    description: str = ""
    publisher: Optional[str] = None
    signed: bool = False
    package_type: str


def scan_packages(package_dir: Path, package_type: str) -> List[Dict[str, Any]]:
    """
    Scan packages in new nested structure.

    Args:
        package_dir: Directory containing packages (e.g. registry/mcps/)
        package_type: Type of package ("agent", "mcp", "team")

    Returns:
        List of package metadata
    """
    packages = []

    if not package_dir.exists():
        return packages

    # Iterate through package names
    for name_dir in package_dir.iterdir():
        if not name_dir.is_dir():
            continue

        # Iterate through versions
        for version_dir in name_dir.iterdir():
            if not version_dir.is_dir():
                continue

            # Look for package config file
            config_file = version_dir / f"{package_type}.json"
            metadata_file = version_dir / "metadata.json"
            signature_file = version_dir / f"{package_type}.json.asc"

            if not config_file.exists():
                continue

            try:
                # Read config
                config = json.loads(config_file.read_text())

                # Read metadata if available
                metadata = {}
                if metadata_file.exists():
                    metadata = json.loads(metadata_file.read_text())

                # Check signature
                has_signature = signature_file.exists()

                packages.append({
                    "name": name_dir.name,
                    "version": version_dir.name,
                    "description": config.get("description", metadata.get("description", "")),
                    "publisher": metadata.get("publisher", "unknown"),
                    "signed": has_signature and metadata.get("signature", {}).get("signed", False),
                    "package_type": package_type,
                    "created_at": metadata.get("created_at"),
                    "checksum": metadata.get("checksum", {}),
                    # Include package-specific fields
                    **({"agents": len(config.get("agents", []))} if package_type == "team" else {})
                })
            except Exception as e:
                print(f"Error reading package {name_dir.name}/{version_dir.name}: {e}")

    return packages


def get_catalog() -> Dict[str, Any]:
    """Generate catalog of available packages"""
    catalog = {
        "registry": {
            "name": "Default MCP Registry",
            "url": "http://localhost:9000",
            "version": "2.0.0",
            "features": ["gpg_signing", "nested_versions", "publisher_keys"]
        },
        "publishers": [],
        "agents": [],
        "mcps": [],
        "teams": []
    }

    # Scan publishers
    publishers_dir = REGISTRY_DIR / "publishers"
    if publishers_dir.exists():
        for publisher_dir in publishers_dir.iterdir():
            if not publisher_dir.is_dir():
                continue

            metadata_file = publisher_dir / "metadata.json"
            pubkey_file = publisher_dir / "pubkey.asc"

            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())
                    catalog["publishers"].append({
                        "id": publisher_dir.name,
                        "name": metadata.get("name", "Unknown"),
                        "email": metadata.get("email"),
                        "created_at": metadata.get("created_at"),
                        "has_pubkey": pubkey_file.exists()
                    })
                except Exception as e:
                    print(f"Error reading publisher {publisher_dir.name}: {e}")

    # Scan packages
    catalog["agents"] = scan_packages(REGISTRY_DIR / "agents", "agent")
    catalog["mcps"] = scan_packages(REGISTRY_DIR / "mcps", "mcp")
    catalog["teams"] = scan_packages(REGISTRY_DIR / "teams", "team")

    return catalog


@app.get("/")
async def root():
    """Registry information"""
    return {
        "name": "MCP Registry Server v2",
        "version": "2.0.0",
        "description": "Package registry with GPG signing support for MCP servers and agent teams",
        "features": [
            "GPG package signing",
            "Nested version directories",
            "Publisher key management",
            "Package metadata",
            "Checksum verification"
        ],
        "endpoints": {
            "catalog": "/catalog",
            "publishers": "/publishers",
            "agents": "/agents",
            "mcps": "/mcps",
            "teams": "/teams"
        }
    }


@app.get("/catalog")
async def get_full_catalog():
    """Get full catalog of available packages"""
    return get_catalog()


# Publishers API
@app.get("/publishers")
async def list_publishers():
    """List all registered publishers"""
    catalog = get_catalog()
    return catalog["publishers"]


@app.get("/publishers/{publisher_id}")
async def get_publisher(publisher_id: str):
    """Get publisher details"""
    publisher_dir = REGISTRY_DIR / "publishers" / publisher_id
    if not publisher_dir.exists():
        raise HTTPException(status_code=404, detail="Publisher not found")

    metadata_file = publisher_dir / "metadata.json"
    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail="Publisher metadata not found")

    metadata = json.loads(metadata_file.read_text())
    metadata["id"] = publisher_id
    metadata["has_pubkey"] = (publisher_dir / "pubkey.asc").exists()

    return metadata


@app.get("/publishers/{publisher_id}/pubkey")
async def get_publisher_key(publisher_id: str):
    """Get publisher's public GPG key"""
    pubkey_file = REGISTRY_DIR / "publishers" / publisher_id / "pubkey.asc"
    if not pubkey_file.exists():
        raise HTTPException(status_code=404, detail="Publisher public key not found")

    return {"public_key": pubkey_file.read_text()}


# Agents API
@app.get("/agents")
async def list_agents():
    """List available agent packages"""
    return scan_packages(REGISTRY_DIR / "agents", "agent")


@app.get("/agents/{agent_name}")
async def list_agent_versions(agent_name: str):
    """List all versions of a specific agent"""
    agent_dir = REGISTRY_DIR / "agents" / agent_name
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="Agent not found")

    versions = []
    for version_dir in agent_dir.iterdir():
        if version_dir.is_dir() and (version_dir / "agent.json").exists():
            metadata_file = version_dir / "metadata.json"
            metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}

            versions.append({
                "version": version_dir.name,
                "signed": metadata.get("signature", {}).get("signed", False),
                "publisher": metadata.get("publisher"),
                "created_at": metadata.get("created_at")
            })

    return sorted(versions, key=lambda v: v["version"], reverse=True)


@app.get("/agents/{agent_name}/{version}")
async def get_agent(agent_name: str, version: str):
    """Get specific agent package details"""
    agent_dir = REGISTRY_DIR / "agents" / agent_name / version
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="Agent version not found")

    config_file = agent_dir / "agent.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="Agent configuration not found")

    # Read config, metadata, and signature status
    config = json.loads(config_file.read_text())

    metadata_file = agent_dir / "metadata.json"
    metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}

    signature_file = agent_dir / "agent.json.asc"

    return {
        "config": config,
        "metadata": metadata,
        "has_signature": signature_file.exists(),
        "signature_path": str(signature_file) if signature_file.exists() else None
    }


# MCPs API
@app.get("/mcps")
async def list_mcps():
    """List available MCP packages"""
    return scan_packages(REGISTRY_DIR / "mcps", "mcp")


@app.get("/mcps/{mcp_name}")
async def list_mcp_versions(mcp_name: str):
    """List all versions of a specific MCP"""
    mcp_dir = REGISTRY_DIR / "mcps" / mcp_name
    if not mcp_dir.exists():
        raise HTTPException(status_code=404, detail="MCP not found")

    versions = []
    for version_dir in mcp_dir.iterdir():
        if version_dir.is_dir() and (version_dir / "mcp.json").exists():
            metadata_file = version_dir / "metadata.json"
            metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}

            versions.append({
                "version": version_dir.name,
                "signed": metadata.get("signature", {}).get("signed", False),
                "publisher": metadata.get("publisher"),
                "created_at": metadata.get("created_at")
            })

    return sorted(versions, key=lambda v: v["version"], reverse=True)


@app.get("/mcps/{mcp_name}/{version}")
async def get_mcp(mcp_name: str, version: str):
    """Get specific MCP package details"""
    mcp_dir = REGISTRY_DIR / "mcps" / mcp_name / version
    if not mcp_dir.exists():
        raise HTTPException(status_code=404, detail="MCP version not found")

    config_file = mcp_dir / "mcp.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="MCP configuration not found")

    # Read config, metadata, and signature status
    config = json.loads(config_file.read_text())

    metadata_file = mcp_dir / "metadata.json"
    metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}

    signature_file = mcp_dir / "mcp.json.asc"

    return {
        "config": config,
        "metadata": metadata,
        "has_signature": signature_file.exists(),
        "signature_path": str(signature_file) if signature_file.exists() else None
    }


# Teams API
@app.get("/teams")
async def list_teams():
    """List available team packages"""
    return scan_packages(REGISTRY_DIR / "teams", "team")


@app.get("/teams/{team_name}")
async def list_team_versions(team_name: str):
    """List all versions of a specific team"""
    team_dir = REGISTRY_DIR / "teams" / team_name
    if not team_dir.exists():
        raise HTTPException(status_code=404, detail="Team not found")

    versions = []
    for version_dir in team_dir.iterdir():
        if version_dir.is_dir() and (version_dir / "team.json").exists():
            metadata_file = version_dir / "metadata.json"
            metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}

            versions.append({
                "version": version_dir.name,
                "signed": metadata.get("signature", {}).get("signed", False),
                "publisher": metadata.get("publisher"),
                "created_at": metadata.get("created_at")
            })

    return sorted(versions, key=lambda v: v["version"], reverse=True)


@app.get("/teams/{team_name}/{version}")
async def get_team(team_name: str, version: str):
    """Get specific team package details"""
    team_dir = REGISTRY_DIR / "teams" / team_name / version
    if not team_dir.exists():
        raise HTTPException(status_code=404, detail="Team version not found")

    config_file = team_dir / "team.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="Team configuration not found")

    # Read config, metadata, and signature status
    config = json.loads(config_file.read_text())

    metadata_file = team_dir / "metadata.json"
    metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}

    signature_file = team_dir / "team.json.asc"

    return {
        "config": config,
        "metadata": metadata,
        "has_signature": signature_file.exists(),
        "signature_path": str(signature_file) if signature_file.exists() else None
    }


# ============================================================================
# Trigger Package Endpoints
# ============================================================================

@app.get("/triggers")
async def list_triggers():
    """List all trigger packages in registry"""
    triggers_dir = REGISTRY_DIR / "triggers"
    return scan_packages(triggers_dir, "trigger")


@app.get("/triggers/{trigger_name}")
async def list_trigger_versions(trigger_name: str):
    """List all versions of a trigger"""
    trigger_dir = REGISTRY_DIR / "triggers" / trigger_name

    if not trigger_dir.exists():
        raise HTTPException(status_code=404, detail=f"Trigger '{trigger_name}' not found")

    versions = []
    for version_dir in trigger_dir.iterdir():
        if not version_dir.is_dir():
            continue

        config_file = version_dir / "trigger.json"
        if config_file.exists():
            versions.append({
                "version": version_dir.name,
                "url": f"/triggers/{trigger_name}/{version_dir.name}"
            })

    if not versions:
        raise HTTPException(status_code=404, detail=f"No versions found for trigger '{trigger_name}'")

    return versions


@app.get("/triggers/{trigger_name}/{version}")
async def get_trigger(trigger_name: str, version: str):
    """Get specific trigger package with metadata"""
    trigger_dir = REGISTRY_DIR / "triggers" / trigger_name / version

    if not trigger_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Trigger '{trigger_name}' version '{version}' not found"
        )

    config_file = trigger_dir / "trigger.json"
    metadata_file = trigger_dir / "metadata.json"
    signature_file = trigger_dir / "trigger.json.asc"

    if not config_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Trigger config file not found"
        )

    # Read config
    config = json.loads(config_file.read_text())

    # Read metadata if exists
    metadata = None
    if metadata_file.exists():
        metadata = json.loads(metadata_file.read_text())

    # Check for signature
    has_signature = signature_file.exists()

    return {
        "config": config,
        "metadata": metadata,
        "signed": has_signature,
        "package_path": str(trigger_dir),
        "files": {
            "config": str(config_file),
            "metadata": str(metadata_file) if metadata_file.exists() else None,
            "signature": str(signature_file) if has_signature else None
        }
    }


# Legacy compatibility endpoints (for old {package}-{version}.json format)
@app.get("/legacy/mcps/{mcp_id}")
async def get_mcp_legacy(mcp_id: str):
    """
    Get MCP package (legacy format compatibility)
    Maps old {name}-{version} format to new {name}/{version} structure
    """
    # Try to parse {name}-{version} format
    if "-" in mcp_id:
        parts = mcp_id.rsplit("-", 1)
        if len(parts) == 2:
            name, version = parts
            try:
                result = await get_mcp(name, version)
                # Return just config for legacy compatibility
                return result["config"]
            except:
                pass

    raise HTTPException(status_code=404, detail="MCP package not found")


@app.get("/legacy/teams/{team_id}")
async def get_team_legacy(team_id: str):
    """
    Get team package (legacy format compatibility)
    Maps old {name}-{version} format to new {name}/{version} structure
    """
    # Try to parse {name}-{version} format
    if "-" in team_id:
        parts = team_id.rsplit("-", 1)
        if len(parts) == 2:
            name, version = parts
            try:
                result = await get_team(name, version)
                # Return just config for legacy compatibility
                return result["config"]
            except:
                pass

    raise HTTPException(status_code=404, detail="Team package not found")


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "registry-v2"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
