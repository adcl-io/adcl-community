# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Scan Service - Network scan orchestration
Following ADCL principle: Backend service (Tier 2) - uses AgentRuntime for AI, not MCP directly
"""
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)
from app.models.red_team import (
    Scan,
    ScanType,
    ScanStatus,
    ScanResults,
    ScanCreateRequest,
)
from app.core.config import get_config


class ScanService:
    """
    Service for network scan orchestration.

    This is a Tier 2 backend service - coordinates scan execution,
    stores results on disk, integrates with AI agents when needed.
    """

    def __init__(self, base_dir: str = "volumes/recon"):
        """
        Initialize scan service.

        Args:
            base_dir: Base directory for scan data storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def create_scan(
        self, target: str, scan_type: ScanType, options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new scan.

        Args:
            target: Target network or host
            scan_type: Type of scan (discovery, deep, vuln)
            options: Additional scan options

        Returns:
            Scan ID
        """
        scan_id = f"scan_{uuid.uuid4().hex[:12]}"
        scan_dir = self.base_dir / scan_id
        scan_dir.mkdir(parents=True, exist_ok=True)

        # Create scan record
        scan = Scan(
            scan_id=scan_id,
            target=target,
            type=scan_type,
            status=ScanStatus.PENDING,
            created_at=datetime.now(),
        )

        # Save scan metadata
        metadata_file = scan_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(scan.model_dump(mode="json"), f, indent=2)

        # Save options if provided
        if options:
            options_file = scan_dir / "options.json"
            with open(options_file, "w") as f:
                json.dump(options, f, indent=2)

        return scan_id

    async def get_scan(self, scan_id: str) -> Optional[Scan]:
        """
        Get scan by ID.

        Args:
            scan_id: Scan identifier

        Returns:
            Scan object or None if not found
        """
        scan_dir = self.base_dir / scan_id
        metadata_file = scan_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r") as f:
                scan_data = json.load(f)

            # result.json contains detailed data for dashboard aggregation
            # The summary counts are already in metadata.json results field
            # No need to overwrite them here

            # Load raw output if available
            raw_output_file = scan_dir / "raw_output.txt"
            if raw_output_file.exists():
                with open(raw_output_file, "r") as f:
                    scan_data["raw_output"] = f.read()

            return Scan(**scan_data)

        except (json.JSONDecodeError, ValueError):
            return None

    async def list_scans(
        self, limit: int = 50, offset: int = 0, status: Optional[ScanStatus] = None
    ) -> List[Scan]:
        """
        List scans with optional filtering.

        Args:
            limit: Maximum scans to return
            offset: Offset for pagination
            status: Filter by status

        Returns:
            List of scans
        """
        scans = []

        # Find all scan directories
        scan_dirs = sorted(
            [d for d in self.base_dir.glob("scan_*") if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,  # Newest first
        )

        for scan_dir in scan_dirs:
            metadata_file = scan_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, "r") as f:
                    scan_data = json.load(f)

                scan = Scan(**scan_data)

                # Apply status filter
                if status and scan.status != status:
                    continue

                scans.append(scan)

            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Skipping malformed scan metadata: {metadata_file} - {e}")
                continue

        # Apply pagination
        return scans[offset : offset + limit]

    async def update_scan_status(
        self,
        scan_id: str,
        status: ScanStatus,
        results: Optional[ScanResults] = None,
        error: Optional[str] = None,
        raw_output: Optional[str] = None,
    ) -> bool:
        """
        Update scan status and results.

        Args:
            scan_id: Scan identifier
            status: New status
            results: Scan results if available
            error: Error message if failed
            raw_output: Raw scan output

        Returns:
            True if updated successfully
        """
        scan_dir = self.base_dir / scan_id
        metadata_file = scan_dir / "metadata.json"

        if not metadata_file.exists():
            return False

        try:
            # Load existing metadata
            with open(metadata_file, "r") as f:
                scan_data = json.load(f)

            # Update status
            scan_data["status"] = status.value

            # Update timestamps
            if status == ScanStatus.RUNNING and not scan_data.get("started_at"):
                scan_data["started_at"] = datetime.now().isoformat()
            elif status in [ScanStatus.COMPLETE, ScanStatus.FAILED, ScanStatus.CANCELLED]:
                scan_data["completed_at"] = datetime.now().isoformat()

            # Update results
            if results:
                scan_data["results"] = results.model_dump(mode="json")

            # Update error
            if error:
                scan_data["error"] = error

            # Save updated metadata
            with open(metadata_file, "w") as f:
                json.dump(scan_data, f, indent=2)

            # Save raw output if provided
            if raw_output:
                output_file = scan_dir / "raw_output.txt"
                with open(output_file, "w") as f:
                    f.write(raw_output)

            return True

        except (json.JSONDecodeError, IOError):
            return False

    async def delete_scan(self, scan_id: str) -> bool:
        """
        Delete a scan and its data.

        Args:
            scan_id: Scan identifier

        Returns:
            True if deleted successfully
        """
        import shutil

        scan_dir = self.base_dir / scan_id

        if not scan_dir.exists():
            return False

        try:
            shutil.rmtree(scan_dir)
            return True
        except OSError:
            return False

    async def get_scan_results(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed scan results.

        Args:
            scan_id: Scan identifier

        Returns:
            Scan results or None if not available
        """
        scan_dir = self.base_dir / scan_id
        result_file = scan_dir / "result.json"

        if not result_file.exists():
            return None

        try:
            with open(result_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None

    async def save_scan_results(
        self, scan_id: str, results: Dict[str, Any]
    ) -> bool:
        """
        Save detailed scan results.

        Args:
            scan_id: Scan identifier
            results: Full scan results

        Returns:
            True if saved successfully
        """
        scan_dir = self.base_dir / scan_id

        if not scan_dir.exists():
            return False

        try:
            result_file = scan_dir / "result.json"
            with open(result_file, "w") as f:
                json.dump(results, f, indent=2)

            return True

        except (IOError, TypeError):
            return False

    async def get_scan_count_by_status(self) -> Dict[str, int]:
        """
        Get count of scans by status.

        Returns:
            Dictionary mapping status to count
        """
        counts = {
            "pending": 0,
            "running": 0,
            "complete": 0,
            "failed": 0,
            "cancelled": 0,
        }

        # Count scans by status
        scan_dirs = list(self.base_dir.glob("scan_*"))

        for scan_dir in scan_dirs:
            metadata_file = scan_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, "r") as f:
                    scan_data = json.load(f)

                status = scan_data.get("status", "pending")
                if status in counts:
                    counts[status] += 1

            except (json.JSONDecodeError, KeyError):
                continue

        return counts

    async def execute_scan(self, scan_id: str, mcp_session_manager) -> bool:
        """
        Execute a scan using the nmap_recon MCP server.

        Args:
            scan_id: Scan identifier
            mcp_session_manager: MCPSessionManager instance for calling MCP tools

        Returns:
            True if scan started successfully
        """
        import asyncio
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Starting scan execution for {scan_id}")

        # Get scan metadata
        scan = await self.get_scan(scan_id)
        if not scan:
            logger.error(f"❌ Scan {scan_id} not found")
            return False

        # Update status to running
        await self.update_scan_status(scan_id, ScanStatus.RUNNING)
        logger.info(f"⏳ Scan {scan_id} status updated to RUNNING")

        try:
            # Determine which nmap tool to use based on scan type
            # Note: network_discovery uses 'network' parameter, others use 'target'
            if scan.type == ScanType.DISCOVERY:
                tool_name = "network_discovery"
                arguments = {"network": scan.target}  # network_discovery uses 'network' not 'target'
            elif scan.type == ScanType.DEEP:
                tool_name = "port_scan"
                arguments = {
                    "target": scan.target,
                    "scan_type": "full"
                }
            elif scan.type == ScanType.VULN:
                tool_name = "vulnerability_scan"
                arguments = {"target": scan.target}
            else:
                # Default to network discovery
                tool_name = "network_discovery"
                arguments = {"network": scan.target}  # network_discovery uses 'network' not 'target'

            # Call nmap MCP server via config (no hardcoded endpoints)
            # Note: nmap runs on host network, accessed via docker host gateway
            config = get_config()
            nmap_endpoint = config.nmap_mcp_url
            logger.info(f"🌐 Calling nmap MCP at {nmap_endpoint}: tool={tool_name}, target={arguments.get('target') or arguments.get('network')}")

            result = await mcp_session_manager.call_tool(
                endpoint=nmap_endpoint,
                tool_name=tool_name,
                arguments=arguments
            )

            logger.info(f"✅ Received result from nmap MCP: {len(str(result))} chars")

            # Parse results and update scan
            if result and "content" in result:
                # Extract scan results from MCP response
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    # Get text content
                    text_content = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])

                    # Try to parse as JSON
                    try:
                        parsed_result = json.loads(text_content)

                        # Extract hosts - handle different formats
                        hosts = []
                        if "hosts_discovered" in parsed_result:
                            hosts = parsed_result["hosts_discovered"]
                        elif "results" in parsed_result and "hosts" in parsed_result["results"]:
                            hosts = parsed_result["results"]["hosts"]
                        elif "hosts" in parsed_result:
                            hosts = parsed_result["hosts"]

                        # Extract ports - handle different formats
                        ports = []
                        if "results" in parsed_result and "ports" in parsed_result["results"]:
                            # Port scan format: results.ports is a flat array
                            ports = parsed_result["results"]["ports"]
                        else:
                            # Host-centric format: ports are nested in each host
                            for host in hosts:
                                if "ports" in host:
                                    ports.extend(host["ports"])

                        # Extract vulnerabilities from multiple sources
                        vulnerabilities = []

                        # Source 1: From host-level vulnerabilities array
                        for host in hosts:
                            if "vulnerabilities" in host:
                                vulnerabilities.extend(host["vulnerabilities"])

                        # Source 2: From port script outputs that indicate VULNERABLE
                        for port in ports:
                            if "scripts" in port:
                                for script in port["scripts"]:
                                    output = script.get("output", "")
                                    # Check if script output indicates a vulnerability
                                    # Exclude "NOT VULNERABLE" findings
                                    if ("VULNERABLE" in output or "State: VULNERABLE" in output) and "NOT VULNERABLE" not in output:
                                        # Extract vulnerability info from script
                                        vuln_entry = {
                                            "port": port.get("port"),
                                            "protocol": port.get("protocol", "tcp"),
                                            "script": script.get("id"),
                                            "finding": output.strip(),
                                            "service": port.get("service", {}).get("name", "unknown")
                                        }
                                        vulnerabilities.append(vuln_entry)

                        # Create ScanResults object
                        scan_results = ScanResults(
                            hosts_found=len(hosts),
                            ports_found=len(ports),
                            vulnerabilities_found=len(vulnerabilities)
                        )

                        # Save detailed results to result.json for dashboard
                        await self.save_scan_results(scan_id, {
                            "hosts": hosts,
                            "ports": ports,
                            "vulnerabilities": vulnerabilities,
                            "raw": parsed_result
                        })

                        # Update scan status to complete with results
                        await self.update_scan_status(
                            scan_id,
                            ScanStatus.COMPLETE,
                            results=scan_results,
                            raw_output=text_content
                        )

                        return True
                    except json.JSONDecodeError:
                        # If not JSON, save as raw output
                        await self.update_scan_status(
                            scan_id,
                            ScanStatus.COMPLETE,
                            raw_output=text_content
                        )
                        return True

            # No valid results received
            await self.update_scan_status(
                scan_id,
                ScanStatus.FAILED,
                error="No valid results received from nmap"
            )
            return False

        except Exception as e:
            # Mark scan as failed
            logger.error(f"❌ Scan execution failed for {scan_id}: {str(e)}")
            logger.exception(e)
            await self.update_scan_status(
                scan_id,
                ScanStatus.FAILED,
                error=str(e)
            )
            return False
