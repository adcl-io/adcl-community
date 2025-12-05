# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP & Team Registry Server
Similar to yum repository - serves MCPs and Teams for installation
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import os
from typing import List, Dict, Any

app = FastAPI(
    title="MCP Registry Server",
    description="Package registry for MCP servers and agent teams",
    version="1.0.0"
)

# CORS for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REGISTRY_DIR = Path(os.getenv("CONTAINER_REGISTRY_DATA_PATH", "/app/registries"))


def get_catalog() -> Dict[str, Any]:
    """Generate catalog of available packages"""
    registry_port = os.getenv("REGISTRY_PORT", "9000")
    registry_host = os.getenv("API_HOST", "localhost")
    registry_protocol = os.getenv("API_PROTOCOL", "http")

    catalog = {
        "registry": {
            "name": "Default MCP Registry",
            "url": f"{registry_protocol}://{registry_host}:{registry_port}",
            "version": "1.0.0"
        },
        "mcps": [],
        "teams": [],
        "triggers": []
    }

    # Scan MCP packages
    mcps_dir = REGISTRY_DIR / "mcps"
    if mcps_dir.exists():
        for file in mcps_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                catalog["mcps"].append({
                    "id": file.stem,
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "description": data.get("description"),
                    "file": file.name
                })
            except Exception as e:
                print(f"Error reading MCP {file}: {e}")

    # Scan team packages
    teams_dir = REGISTRY_DIR / "teams"
    if teams_dir.exists():
        for file in teams_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                catalog["teams"].append({
                    "id": file.stem,
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "description": data.get("description"),
                    "agents": len(data.get("agents", [])),
                    "file": file.name
                })
            except Exception as e:
                print(f"Error reading team {file}: {e}")

    # Scan trigger packages
    triggers_dir = REGISTRY_DIR / "triggers"
    if triggers_dir.exists():
        for file in triggers_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                catalog["triggers"].append({
                    "id": file.stem,
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "description": data.get("description"),
                    "trigger_type": data.get("trigger", {}).get("type", "unknown"),
                    "file": file.name
                })
            except Exception as e:
                print(f"Error reading trigger {file}: {e}")

    return catalog


@app.get("/")
async def root():
    """Registry information"""
    return {
        "name": "MCP Registry Server",
        "version": "1.0.0",
        "description": "Package registry for MCP servers and agent teams",
        "endpoints": {
            "catalog": "/catalog",
            "mcps": "/mcps",
            "teams": "/teams",
            "triggers": "/triggers"
        }
    }


@app.get("/catalog")
async def get_full_catalog():
    """Get full catalog of available packages"""
    return get_catalog()


@app.get("/mcps")
async def list_mcps():
    """List available MCP packages"""
    catalog = get_catalog()
    return catalog["mcps"]


@app.get("/mcps/{mcp_id}")
async def get_mcp(mcp_id: str):
    """Get specific MCP package details"""
    file_path = REGISTRY_DIR / "mcps" / f"{mcp_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="MCP package not found")

    return json.loads(file_path.read_text())


@app.get("/teams")
async def list_teams():
    """List available team packages"""
    catalog = get_catalog()
    return catalog["teams"]


@app.get("/teams/{team_id}")
async def get_team(team_id: str):
    """Get specific team package details"""
    file_path = REGISTRY_DIR / "teams" / f"{team_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Team package not found")

    return json.loads(file_path.read_text())


@app.get("/triggers")
async def list_triggers():
    """List available trigger packages"""
    catalog = get_catalog()
    return catalog["triggers"]


@app.get("/triggers/{trigger_id}")
async def get_trigger(trigger_id: str):
    """Get specific trigger package details"""
    file_path = REGISTRY_DIR / "triggers" / f"{trigger_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Trigger package not found")

    return json.loads(file_path.read_text())


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "registry"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("REGISTRY_PORT", "9000"))
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
