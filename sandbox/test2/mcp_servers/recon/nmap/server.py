# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
nmap MCP Server - Network scanning tools via MCP protocol

Provides network scanning capabilities through the MCP (Model Context Protocol) interface.

Available tools:
- port_scan: Scan ports on target hosts
- service_detection: Detect services and versions
- os_detection: Detect operating system
- version_enum: Enumerate service versions
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import subprocess
import json
import xml.etree.ElementTree as ET
import asyncio
import tempfile
import os

app = FastAPI(
    title="nmap MCP Server",
    description="Network scanning tools via MCP protocol",
    version="0.1.0"
)


# ============================================================================
# MCP Protocol Models
# ============================================================================

class MCPRequest(BaseModel):
    """MCP protocol request"""
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP protocol response"""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# Tool Definitions
# ============================================================================

TOOLS = {
    "port_scan": {
        "name": "port_scan",
        "description": "Scan ports on target hosts",
        "parameters": {
            "target": {"type": "string", "description": "Target host or network (e.g., 192.168.1.1 or 192.168.1.0/24)"},
            "scan_type": {"type": "string", "description": "Scan type: quick, full, or custom", "default": "quick"},
            "ports": {"type": "string", "description": "Port range (e.g., '1-1000' or '80,443,8080')", "optional": True}
        }
    },
    "service_detection": {
        "name": "service_detection",
        "description": "Detect services and versions running on open ports",
        "parameters": {
            "target": {"type": "string", "description": "Target host"},
            "ports": {"type": "string", "description": "Specific ports to check", "optional": True}
        }
    },
    "os_detection": {
        "name": "os_detection",
        "description": "Detect operating system of target host",
        "parameters": {
            "target": {"type": "string", "description": "Target host"}
        }
    },
    "version_enum": {
        "name": "version_enum",
        "description": "Enumerate service versions",
        "parameters": {
            "target": {"type": "string", "description": "Target host"},
            "port": {"type": "integer", "description": "Specific port to enumerate"}
        }
    }
}


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "nmap-mcp-server",
        "version": "0.1.0"
    }


# ============================================================================
# MCP Protocol Endpoints
# ============================================================================

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest) -> MCPResponse:
    """MCP protocol endpoint"""

    method = request.method
    params = request.params or {}

    # Handle different MCP methods
    if method == "tools/list":
        # Return list of available tools
        return MCPResponse(result={"tools": list(TOOLS.values())})

    elif method == "tools/call":
        # Execute a tool
        tool_name = params.get("name")
        tool_params = params.get("parameters", {})

        if tool_name not in TOOLS:
            return MCPResponse(error=f"Unknown tool: {tool_name}")

        # Call the tool
        try:
            result = await execute_tool(tool_name, tool_params)
            return MCPResponse(result=result)
        except Exception as e:
            return MCPResponse(error=str(e))

    else:
        return MCPResponse(error=f"Unknown method: {method}")


# ============================================================================
# Tool Execution
# ============================================================================

async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool based on its name"""

    if tool_name == "port_scan":
        return await port_scan(params)
    elif tool_name == "service_detection":
        return await service_detection(params)
    elif tool_name == "os_detection":
        return await os_detection(params)
    elif tool_name == "version_enum":
        return await version_enum(params)
    else:
        raise Exception(f"Tool not implemented: {tool_name}")


# ============================================================================
# Helper Functions
# ============================================================================

def parse_nmap_xml(xml_file: str) -> Dict[str, Any]:
    """Parse nmap XML output into structured data"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        results = {
            "hosts": [],
            "total_hosts": 0,
            "scan_info": {}
        }

        # Parse scan info
        scaninfo = root.find("scaninfo")
        if scaninfo is not None:
            results["scan_info"] = {
                "type": scaninfo.get("type"),
                "protocol": scaninfo.get("protocol"),
                "services": scaninfo.get("services")
            }

        # Parse hosts
        for host in root.findall("host"):
            # Get host state
            status = host.find("status")
            if status is None or status.get("state") != "up":
                continue

            host_data = {
                "state": "up",
                "addresses": [],
                "hostnames": [],
                "ports": [],
                "os": None
            }

            # Get addresses
            for addr in host.findall("address"):
                host_data["addresses"].append({
                    "addr": addr.get("addr"),
                    "addrtype": addr.get("addrtype")
                })

            # Get hostnames
            hostnames = host.find("hostnames")
            if hostnames is not None:
                for hostname in hostnames.findall("hostname"):
                    host_data["hostnames"].append({
                        "name": hostname.get("name"),
                        "type": hostname.get("type")
                    })

            # Get ports
            ports = host.find("ports")
            if ports is not None:
                for port in ports.findall("port"):
                    port_id = port.get("portid")
                    protocol = port.get("protocol")

                    state = port.find("state")
                    service = port.find("service")

                    port_data = {
                        "port": int(port_id),
                        "protocol": protocol,
                        "state": state.get("state") if state is not None else "unknown"
                    }

                    if service is not None:
                        port_data["service"] = {
                            "name": service.get("name"),
                            "product": service.get("product"),
                            "version": service.get("version"),
                            "extrainfo": service.get("extrainfo"),
                            "ostype": service.get("ostype")
                        }

                    host_data["ports"].append(port_data)

            # Get OS detection
            os_elem = host.find("os")
            if os_elem is not None:
                osmatch = os_elem.find("osmatch")
                if osmatch is not None:
                    host_data["os"] = {
                        "name": osmatch.get("name"),
                        "accuracy": osmatch.get("accuracy")
                    }

            results["hosts"].append(host_data)
            results["total_hosts"] += 1

        return results

    except Exception as e:
        raise Exception(f"Failed to parse nmap XML: {str(e)}")


async def run_nmap_scan(args: List[str]) -> str:
    """
    Run nmap scan and return path to XML output file

    Args:
        args: List of nmap arguments (excluding nmap command itself)

    Returns:
        Path to XML output file
    """
    # Create temp file for XML output
    xml_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False)
    xml_path = xml_file.name
    xml_file.close()

    # Build nmap command
    cmd = ["nmap", "-oX", xml_path] + args

    print(f"[nmap MCP] Running: {' '.join(cmd)}")

    try:
        # Run nmap
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise Exception(f"nmap failed: {error_msg}")

        return xml_path

    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(xml_path):
            os.unlink(xml_path)
        raise e


# ============================================================================
# Tool Implementations
# ============================================================================

async def port_scan(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform port scan on target using real nmap
    """
    target = params.get("target")
    scan_type = params.get("scan_type", "quick")
    ports = params.get("ports")

    if not target:
        raise Exception("target parameter is required")

    print(f"[nmap MCP] Port scanning {target} (type: {scan_type})")

    # Build nmap arguments based on scan type
    nmap_args = []

    if scan_type == "quick":
        # Quick scan: top 100 ports
        nmap_args = ["-F", "--top-ports", "100"]
    elif scan_type == "full":
        # Full scan: all 65535 ports (slow!)
        nmap_args = ["-p-"]
    elif scan_type == "comprehensive":
        # Comprehensive: common ports with service detection
        nmap_args = ["--top-ports", "1000", "-sV"]
    else:
        # Default: top 1000 ports
        nmap_args = ["--top-ports", "1000"]

    # Add custom port range if specified
    if ports:
        nmap_args = ["-p", ports]

    # Add target
    nmap_args.append(target)

    # Run scan
    xml_path = None
    try:
        xml_path = await run_nmap_scan(nmap_args)

        # Parse results
        scan_results = parse_nmap_xml(xml_path)

        # Build response
        ports_list = []
        findings = []

        for host in scan_results["hosts"]:
            target_addr = host["addresses"][0]["addr"] if host["addresses"] else target

            for port in host["ports"]:
                ports_list.append({
                    "port": port["port"],
                    "protocol": port["protocol"],
                    "state": port["state"],
                    "service": port.get("service", {}).get("name", "unknown")
                })

                # Generate findings for open ports
                if port["state"] == "open":
                    service_name = port.get("service", {}).get("name", "unknown")
                    findings.append({
                        "title": f"Open {service_name} port",
                        "severity": "info",
                        "description": f"{service_name} service is accessible on port {port['port']} at {target_addr}",
                        "target_host": target_addr,
                        "target_port": port["port"]
                    })

        return {
            "status": "success",
            "target": target,
            "scan_type": scan_type,
            "hosts_up": scan_results["total_hosts"],
            "ports": ports_list,
            "findings": findings
        }

    finally:
        # Clean up temp file
        if xml_path and os.path.exists(xml_path):
            os.unlink(xml_path)


async def service_detection(params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect services and versions using nmap -sV"""
    target = params.get("target")
    ports = params.get("ports")

    if not target:
        raise Exception("target parameter is required")

    print(f"[nmap MCP] Service detection on {target}")

    # Build nmap arguments for service detection
    nmap_args = ["-sV"]  # Service version detection

    # Add port specification if provided
    if ports:
        nmap_args.extend(["-p", ports])

    nmap_args.append(target)

    # Run scan
    xml_path = None
    try:
        xml_path = await run_nmap_scan(nmap_args)

        # Parse results
        scan_results = parse_nmap_xml(xml_path)

        # Build response
        services = []
        findings = []

        for host in scan_results["hosts"]:
            target_addr = host["addresses"][0]["addr"] if host["addresses"] else target

            for port in host["ports"]:
                if port["state"] == "open":
                    service_info = port.get("service", {})

                    service_data = {
                        "port": port["port"],
                        "protocol": port["protocol"],
                        "service": service_info.get("name", "unknown"),
                        "product": service_info.get("product"),
                        "version": service_info.get("version"),
                        "extrainfo": service_info.get("extrainfo"),
                        "state": port["state"]
                    }
                    services.append(service_data)

                    # Generate findings for detected services
                    product = service_info.get("product", "")
                    version = service_info.get("version", "")
                    if product and version:
                        findings.append({
                            "title": f"{product} {version} detected",
                            "severity": "info",
                            "description": f"{product} version {version} running on port {port['port']} at {target_addr}",
                            "target_host": target_addr,
                            "target_port": port["port"]
                        })

        return {
            "status": "success",
            "target": target,
            "services": services,
            "findings": findings
        }

    finally:
        # Clean up temp file
        if xml_path and os.path.exists(xml_path):
            os.unlink(xml_path)


async def os_detection(params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect operating system"""
    target = params.get("target")

    if not target:
        raise Exception("target parameter is required")

    print(f"[nmap MCP] OS detection on {target}")

    # Mock results
    mock_results = {
        "status": "success",
        "target": target,
        "os": {
            "name": "Linux",
            "version": "Ubuntu 20.04",
            "confidence": 95
        },
        "findings": []
    }

    return mock_results


async def version_enum(params: Dict[str, Any]) -> Dict[str, Any]:
    """Enumerate service version"""
    target = params.get("target")
    port = params.get("port")

    if not target or not port:
        raise Exception("target and port parameters are required")

    print(f"[nmap MCP] Version enumeration on {target}:{port}")

    # Mock results
    mock_results = {
        "status": "success",
        "target": target,
        "port": port,
        "service": "nginx",
        "version": "1.18.0 (Ubuntu)",
        "details": {
            "product": "nginx",
            "version": "1.18.0",
            "os": "Ubuntu"
        },
        "findings": []
    }

    return mock_results


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6000)
