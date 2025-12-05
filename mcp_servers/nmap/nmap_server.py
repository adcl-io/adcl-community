# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Nmap Recon MCP Server
Provides network reconnaissance capabilities for defensive security analysis
DEFENSIVE USE ONLY - For authorized security testing and network analysis
"""
import os
import sys
import subprocess
import json
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
from datetime import datetime

from base_server import BaseMCPServer


class NmapMCPServer(BaseMCPServer):
    """
    Nmap MCP Server for network reconnaissance
    DEFENSIVE SECURITY TOOL - Use only on authorized networks

    Tools:
    - port_scan: Scan for open ports
    - service_detection: Detect running services
    - os_detection: Identify operating system
    - vulnerability_scan: Check for known vulnerabilities
    - network_discovery: Discover hosts on network
    - full_recon: Comprehensive reconnaissance
    """

    def __init__(self, port: int = 7001):
        super().__init__(
            name="nmap_recon",
            port=port,
            description="Network reconnaissance MCP server using Nmap (Defensive Security Tool)"
        )

        # Check if nmap is available
        self._check_nmap_available()

        # Register recon tools
        self._register_recon_tools()

    def _check_nmap_available(self):
        """Check if nmap is installed"""
        try:
            result = subprocess.run(
                ["nmap", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"[{self.name}] Nmap is available")
            else:
                print(f"[{self.name}] WARNING: Nmap not found, using simulation mode")
        except Exception as e:
            print(f"[{self.name}] WARNING: Nmap check failed: {e}")

    def _register_recon_tools(self):
        """Register all recon capabilities as tools"""

        self.register_tool(
            name="port_scan",
            handler=self.port_scan,
            description="Scan target for open ports (defensive security analysis)",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target IP or hostname to scan"
                    },
                    "ports": {
                        "type": "string",
                        "description": "Port range to scan (e.g., '1-1000', '80,443', default: common ports)"
                    },
                    "scan_type": {
                        "type": "string",
                        "description": "Scan type: 'quick', 'full', 'stealth' (default: quick)"
                    }
                },
                "required": ["target"]
            }
        )

        self.register_tool(
            name="service_detection",
            handler=self.service_detection,
            description="Detect services and versions running on open ports",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target IP or hostname"
                    },
                    "ports": {
                        "type": "string",
                        "description": "Specific ports to check (optional)"
                    }
                },
                "required": ["target"]
            }
        )

        self.register_tool(
            name="os_detection",
            handler=self.os_detection,
            description="Detect operating system of target",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target IP or hostname"
                    }
                },
                "required": ["target"]
            }
        )

        self.register_tool(
            name="vulnerability_scan",
            handler=self.vulnerability_scan,
            description="Scan for known vulnerabilities using NSE scripts",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target IP or hostname"
                    },
                    "scripts": {
                        "type": "string",
                        "description": "NSE scripts to run (default: vuln)"
                    }
                },
                "required": ["target"]
            }
        )

        self.register_tool(
            name="network_discovery",
            handler=self.network_discovery,
            description="Discover active hosts on network segment",
            input_schema={
                "type": "object",
                "properties": {
                    "network": {
                        "type": "string",
                        "description": "Network range (e.g., '192.168.1.0/24')"
                    }
                },
                "required": ["network"]
            }
        )

        self.register_tool(
            name="full_recon",
            handler=self.full_recon,
            description="Comprehensive reconnaissance: ports, services, OS, and vulnerabilities",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target IP or hostname"
                    }
                },
                "required": ["target"]
            }
        )

    async def port_scan(self, target: str, ports: str = "", scan_type: str = "quick") -> Dict[str, Any]:
        """Scan for open ports on target"""
        print(f"[{self.name}] Port scanning {target} (type: {scan_type})")

        # Build nmap command
        cmd = ["nmap"]

        # Scan type options
        if scan_type == "stealth":
            cmd.append("-sS")  # SYN scan
        elif scan_type == "full":
            cmd.extend(["-p-", "-T4"])  # All ports, faster timing
        else:  # quick
            cmd.append("-F")  # Fast scan (100 most common ports)

        if ports:
            cmd.extend(["-p", ports])

        cmd.extend(["-oX", "-", target])  # XML output to stdout

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                return {
                    "error": "Scan failed",
                    "stderr": result.stderr,
                    "target": target
                }

            # Parse XML output
            scan_results = self._parse_nmap_xml(result.stdout)

            return {
                "target": target,
                "scan_type": scan_type,
                "timestamp": datetime.now().isoformat(),
                "results": scan_results,
                "summary": self._summarize_ports(scan_results)
            }

        except subprocess.TimeoutExpired:
            return {"error": "Scan timeout", "target": target}
        except Exception as e:
            return {"error": str(e), "target": target}

    async def service_detection(self, target: str, ports: str = "") -> Dict[str, Any]:
        """Detect services and versions"""
        print(f"[{self.name}] Service detection on {target}")

        cmd = ["nmap", "-sV"]  # Version detection

        if ports:
            cmd.extend(["-p", ports])
        else:
            cmd.append("-F")  # Fast scan common ports

        cmd.extend(["-oX", "-", target])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                return {"error": "Service detection failed", "stderr": result.stderr}

            scan_results = self._parse_nmap_xml(result.stdout)

            return {
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "services": scan_results.get("ports", []),
                "summary": self._summarize_services(scan_results)
            }

        except Exception as e:
            return {"error": str(e), "target": target}

    async def os_detection(self, target: str) -> Dict[str, Any]:
        """Detect operating system"""
        print(f"[{self.name}] OS detection on {target}")

        cmd = ["nmap", "-O", "-oX", "-", target]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            scan_results = self._parse_nmap_xml(result.stdout)

            return {
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "os_matches": scan_results.get("os_matches", []),
                "note": "OS detection requires root/admin privileges"
            }

        except Exception as e:
            return {"error": str(e), "target": target}

    async def vulnerability_scan(self, target: str, scripts: str = "vuln") -> Dict[str, Any]:
        """Scan for vulnerabilities using NSE scripts"""
        print(f"[{self.name}] Vulnerability scanning {target}")

        cmd = ["nmap", "--script", scripts, "-oX", "-", target]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for vuln scans
            )

            scan_results = self._parse_nmap_xml(result.stdout)

            return {
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "scripts_used": scripts,
                "results": scan_results,
                "vulnerabilities": self._extract_vulnerabilities(scan_results)
            }

        except Exception as e:
            return {"error": str(e), "target": target}

    async def network_discovery(self, network: str) -> Dict[str, Any]:
        """Discover active hosts on network"""
        print(f"[{self.name}] Network discovery on {network}")

        cmd = ["nmap", "-sn", "-oX", "-", network]  # Ping scan only

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            scan_results = self._parse_nmap_xml(result.stdout)

            return {
                "network": network,
                "timestamp": datetime.now().isoformat(),
                "hosts_discovered": scan_results.get("hosts", []),
                "total_hosts": len(scan_results.get("hosts", []))
            }

        except Exception as e:
            return {"error": str(e), "network": network}

    async def full_recon(self, target: str) -> Dict[str, Any]:
        """Comprehensive reconnaissance"""
        print(f"[{self.name}] Full reconnaissance on {target}")

        # Run comprehensive scan
        cmd = [
            "nmap",
            "-A",  # Aggressive: OS, version, script, traceroute
            "-T4", # Faster timing
            "-oX", "-",
            target
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            scan_results = self._parse_nmap_xml(result.stdout)

            return {
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "scan_type": "comprehensive",
                "results": scan_results,
                "summary": {
                    "ports": self._summarize_ports(scan_results),
                    "services": self._summarize_services(scan_results),
                    "os": scan_results.get("os_matches", [])[:3]  # Top 3 OS matches
                }
            }

        except Exception as e:
            return {"error": str(e), "target": target}

    def _parse_nmap_xml(self, xml_output: str) -> Dict[str, Any]:
        """Parse nmap XML output"""
        try:
            root = ET.fromstring(xml_output)
            results = {
                "hosts": [],
                "ports": [],
                "os_matches": []
            }

            # Parse each host
            for host in root.findall(".//host"):
                host_data = {"status": host.find("status").get("state")}

                # Get address
                addr = host.find(".//address[@addrtype='ipv4']")
                if addr is not None:
                    host_data["ip"] = addr.get("addr")

                # Get hostname
                hostname = host.find(".//hostname")
                if hostname is not None:
                    host_data["hostname"] = hostname.get("name")

                # Get ports
                for port in host.findall(".//port"):
                    port_data = {
                        "port": port.get("portid"),
                        "protocol": port.get("protocol"),
                        "state": port.find("state").get("state")
                    }

                    # Service info
                    service = port.find("service")
                    if service is not None:
                        port_data["service"] = {
                            "name": service.get("name", "unknown"),
                            "product": service.get("product", ""),
                            "version": service.get("version", "")
                        }

                    # Script results
                    scripts = []
                    for script in port.findall(".//script"):
                        scripts.append({
                            "id": script.get("id"),
                            "output": script.get("output")
                        })
                    if scripts:
                        port_data["scripts"] = scripts

                    results["ports"].append(port_data)

                # OS detection
                for osmatch in host.findall(".//osmatch"):
                    results["os_matches"].append({
                        "name": osmatch.get("name"),
                        "accuracy": osmatch.get("accuracy")
                    })

                results["hosts"].append(host_data)

            return results

        except Exception as e:
            return {"parse_error": str(e), "raw_output": xml_output[:500]}

    def _summarize_ports(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize port scan results"""
        ports = results.get("ports", [])
        open_ports = [p for p in ports if p.get("state") == "open"]

        return {
            "total_scanned": len(ports),
            "open_ports": len(open_ports),
            "open_port_list": [f"{p['port']}/{p['protocol']}" for p in open_ports]
        }

    def _summarize_services(self, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Summarize detected services"""
        services = []
        for port in results.get("ports", []):
            if port.get("state") == "open" and "service" in port:
                svc = port["service"]
                services.append({
                    "port": port["port"],
                    "service": svc.get("name", "unknown"),
                    "version": f"{svc.get('product', '')} {svc.get('version', '')}".strip()
                })
        return services

    def _extract_vulnerabilities(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract vulnerability information from script results"""
        vulnerabilities = []
        for port in results.get("ports", []):
            for script in port.get("scripts", []):
                if "vuln" in script.get("id", "").lower():
                    vulnerabilities.append({
                        "port": port["port"],
                        "script": script["id"],
                        "finding": script.get("output", "")[:200]  # Truncate long output
                    })
        return vulnerabilities


if __name__ == "__main__":
    port = int(os.getenv("NMAP_PORT", "7001"))
    server = NmapMCPServer(port=port)
    server.run()
