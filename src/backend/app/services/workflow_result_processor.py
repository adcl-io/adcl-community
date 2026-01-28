# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow Result Processor

Transforms workflow execution results into ReconService scans and AttackService records.
Single responsibility: Persist workflow outputs to file-based storage.
"""
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.core.logging import get_service_logger

logger = get_service_logger("workflow-result-processor")


class WorkflowResultProcessor:
    """
    Process workflow execution results and persist to appropriate services.

    Architecture: Tier 2 backend service using Python imports (NOT MCP).
    Transforms workflow output → ReconService/AttackService records.
    """

    def __init__(self, recon_service, attack_service):
        """
        Initialize processor with service dependencies.

        Args:
            recon_service: ReconService instance
            attack_service: AttackService instance
        """
        self.recon_service = recon_service
        self.attack_service = attack_service
        self.logger = logger

    async def process_workflow_result(
        self,
        workflow_id: str,
        execution_id: str,
        initial_message: str,
        final_result: Dict[str, Any]
    ) -> Optional[str]:
        """
        Process completed workflow results.

        Args:
            workflow_id: Workflow definition ID (e.g., "red-team-attack-chain")
            execution_id: Execution instance ID
            initial_message: User's initial message (contains target)
            final_result: Dict mapping node_id → agent result

        Returns:
            scan_id if recon data was processed, None otherwise
        """
        try:
            # Extract target from initial_message (e.g., "Scan and assess 192.168.50.1")
            target = self._extract_target(initial_message, final_result)
            if not target:
                self.logger.warning(f"Could not extract target from workflow {execution_id}")
                return None

            # Create scan record
            scan_id = await self.recon_service.create_scan(
                target=target,
                scan_type="workflow_attack_chain",
                options={
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "created_by": "workflow"
                }
            )

            self.logger.info(f"Created scan {scan_id} for workflow {execution_id}")

            # Process each workflow stage's output
            hosts_processed = False

            # Extract and store recon data (from 'recon' or 'discovery' node)
            recon_node = final_result.get("recon") or final_result.get("discovery")
            if recon_node:
                hosts_count = await self._process_recon_node(scan_id, recon_node)
                hosts_processed = hosts_count > 0

            # Extract and store vulnerability data (from 'vuln-analysis' node)
            if "vuln-analysis" in final_result:
                await self._process_vuln_node(scan_id, final_result["vuln-analysis"])

            # Extract and store exploit validation (from 'exploit-validation' node)
            if "exploit-validation" in final_result:
                await self._process_exploit_node(scan_id, final_result["exploit-validation"])

            # Store full workflow result for audit trail (non-critical, don't fail if this breaks)
            try:
                await self._store_workflow_metadata(scan_id, workflow_id, execution_id, final_result)
            except Exception as meta_error:
                self.logger.error(f"Failed to store workflow metadata (non-critical): {meta_error}", exc_info=True)

            # Mark scan as complete (use try/except to handle potential metadata corruption)
            try:
                await self.recon_service.complete_scan(scan_id, {
                    "workflow_completed": True,
                    "hosts_discovered": hosts_processed,
                    "execution_id": execution_id
                })
            except Exception as complete_error:
                self.logger.error(f"Failed to complete scan (attempting recovery): {complete_error}")
                # Try to recover by directly updating status file
                try:
                    scan_dir = self.recon_service.base_dir / scan_id
                    status_file = scan_dir / "status.json"
                    status_file.write_text(json.dumps({
                        "status": "completed",
                        "workflow_completed": True,
                        "hosts_discovered": hosts_processed,
                        "execution_id": execution_id,
                        "completed_at": datetime.now().isoformat()
                    }, indent=2))
                    self.logger.info(f"Recovered scan completion by direct status update")
                except Exception as recovery_error:
                    self.logger.error(f"Failed to recover scan completion: {recovery_error}")

            self.logger.info(f"Completed processing workflow {execution_id} → scan {scan_id}")
            return scan_id

        except Exception as e:
            self.logger.error(f"Failed to process workflow {execution_id}: {e}", exc_info=True)
            raise

    def _extract_target(
        self,
        initial_message: str,
        final_result: Dict[str, Any]
    ) -> Optional[str]:
        """
        Extract target from initial_message or final_result.

        Tries multiple strategies:
        1. Parse IP/CIDR from initial_message (e.g., "Scan 192.168.50.1")
        2. Extract from recon node's output
        3. Look for common target patterns

        Args:
            initial_message: User's initial message
            final_result: Workflow execution results

        Returns:
            Extracted target string or None
        """
        # Strategy 1: Parse IP address or CIDR from initial_message
        if initial_message:
            # Match IPv4 address or CIDR (e.g., 192.168.1.0/24 or 192.168.1.1)
            ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b'
            match = re.search(ip_pattern, initial_message)
            if match:
                return match.group(0)

            # Match domain names (e.g., example.com)
            domain_pattern = r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
            match = re.search(domain_pattern, initial_message)
            if match:
                return match.group(0)

        # Strategy 2: Extract from recon or discovery node result
        recon_result = final_result.get("recon") or final_result.get("discovery")
        if recon_result:
            if isinstance(recon_result, dict):
                # Check answer field (agent runtime output)
                answer = recon_result.get("answer", "")
                if isinstance(answer, str):
                    # Try to parse JSON from answer
                    try:
                        answer_json = json.loads(answer)
                        if "target" in answer_json or "target_network" in answer_json:
                            return answer_json.get("target") or answer_json.get("target_network")
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Check if answer itself has target field
                if "target" in recon_result:
                    return recon_result["target"]

        # Strategy 3: Use a default if nothing found (fallback)
        self.logger.warning(f"Could not extract target from initial_message: {initial_message}")
        return None

    async def _process_recon_node(
        self,
        scan_id: str,
        recon_result: Dict[str, Any]
    ) -> int:
        """
        Extract hosts from recon node and store in ReconService.

        The agent execution result contains:
        - answer: Agent's text response (may or may not be JSON)
        - tools_used: List of tool calls with results [{tool, input, result}, ...]

        We extract host data from nmap tool call results in tools_used.

        Args:
            scan_id: Scan ID to update
            recon_result: Recon node output from agent runtime

        Returns:
            Number of hosts processed
        """
        try:
            # DEBUG: Check what we're receiving
            print(f"🔍 _process_recon_node called for scan {scan_id}")
            print(f"🔍 recon_result keys: {list(recon_result.keys())}")
            print(f"🔍 recon_result has tools_used: {'tools_used' in recon_result}")

            # Extract host data from tool results (more reliable than answer field)
            hosts_data = self._extract_hosts_from_tools(recon_result)

            # Fallback: Try to parse answer if no tool data found
            if not hosts_data:
                print(f"🔍 No hosts from tools, trying answer field...")
                hosts_data = self._extract_hosts_from_answer(recon_result)

            if hosts_data:
                await self.recon_service.update_hosts(scan_id, hosts_data)
                self.logger.info(f"Stored {len(hosts_data)} hosts for scan {scan_id}")
                return len(hosts_data)
            else:
                self.logger.info(f"No hosts discovered in scan {scan_id}")
                return 0

        except Exception as e:
            self.logger.error(f"Failed to process recon node for scan {scan_id}: {e}", exc_info=True)
            return 0

    def _extract_hosts_from_tools(self, recon_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract host data from nmap tool call results.

        Tool results contain the actual scan data from nmap.
        Format: {tool: "nmap_recon__full_recon", result: {...}}

        Returns:
            List of host dicts [{ip, ports, services, ...}]
        """
        tools_used = recon_result.get("tools_used", [])
        if not isinstance(tools_used, list):
            self.logger.warning(f"tools_used is not a list: {type(tools_used)}")
            return []

        # DEBUG: Log what we're actually receiving (use print to bypass log level)
        print(f"🔍 DEBUG: Processing {len(tools_used)} tool calls from recon agent")
        self.logger.info(f"DEBUG: Processing {len(tools_used)} tool calls")
        for i, tool in enumerate(tools_used[:2]):  # Log first 2 tools
            print(f"🔍 DEBUG: Tool {i}: {tool.get('tool', 'unknown')} - result type: {type(tool.get('result'))}")
            self.logger.info(f"DEBUG: Tool {i}: {tool.get('tool', 'unknown')} - result type: {type(tool.get('result'))}")
            if isinstance(tool.get('result'), dict):
                print(f"🔍 DEBUG: Tool {i} result keys: {list(tool.get('result', {}).keys())}")
                self.logger.info(f"DEBUG: Tool {i} result keys: {list(tool.get('result', {}).keys())}")

        # Aggregate host data from all nmap tool calls
        hosts_map = {}  # ip -> host data

        for tool_use in tools_used:
            if not isinstance(tool_use, dict):
                continue

            tool_name = tool_use.get("tool", "")
            result = tool_use.get("result", {})

            # Skip non-nmap tools
            if not tool_name.startswith("nmap_recon__"):
                continue

            # Handle MCP response format: {"content": [{"type": "text", "text": "..."}]}
            if isinstance(result, dict) and "content" in result:
                content = result.get("content", [])
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "")
                    try:
                        result = json.loads(text_content)
                        print(f"🔍 Parsed MCP result for {tool_name}, keys: {list(result.keys())}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse MCP tool result: {text_content[:100]}")
                        print(f"🔍 FAILED to parse JSON from {tool_name}")
                        continue

            # Extract host data based on tool type
            if tool_name == "nmap_recon__network_discovery":
                # network_discovery returns: {"hosts_discovered": [...], "total_hosts": N}
                # This is the primary tool for finding multiple hosts on a network
                hosts_list = result.get("hosts_discovered", [])
                print(f"🔍 network_discovery found {len(hosts_list)} hosts")
                for host in hosts_list:
                    ip = host.get("ip")
                    if ip:
                        if ip not in hosts_map:
                            hosts_map[ip] = {
                                "ip": ip,
                                "hostname": host.get("hostname", ""),
                                "mac": host.get("mac", ""),
                                "ports": [],
                                "services": [],
                                "os": "",
                                "status": host.get("status", "up")
                            }

            elif tool_name == "nmap_recon__full_recon":
                # full_recon returns: {"results": {"hosts": [...], ...}, "summary": {...}}
                # Hosts are nested inside "results" key
                scan_results = result.get("results", {})
                hosts_list = scan_results.get("hosts", [])
                print(f"🔍 full_recon has {len(hosts_list)} hosts")
                if not hosts_list:
                    print(f"🔍 full_recon result keys: {list(result.keys())}")
                    if scan_results:
                        print(f"🔍 results keys: {list(scan_results.keys())}")
                for host in hosts_list:
                    ip = host.get("ip")
                    if ip:
                        if ip not in hosts_map:
                            hosts_map[ip] = {
                                "ip": ip,
                                "hostname": host.get("hostname", ""),
                                "mac": host.get("mac", ""),
                                "ports": [],
                                "services": [],
                                "os": ""
                            }
                        # Merge port data
                        for port in host.get("ports", []):
                            if port not in hosts_map[ip]["ports"]:
                                hosts_map[ip]["ports"].append(port)

            elif tool_name == "nmap_recon__service_detection":
                services_list = result.get("services", [])
                for service in services_list:
                    # Infer IP from service data or use result target
                    ip = service.get("ip") or result.get("target")
                    if ip:
                        if ip not in hosts_map:
                            hosts_map[ip] = {
                                "ip": ip,
                                "hostname": "",
                                "mac": "",
                                "ports": [],
                                "services": [],
                                "os": ""
                            }
                        # Add service info
                        port = service.get("port")
                        protocol = service.get("protocol", "tcp")
                        service_name = service.get("service", "")
                        if port and service_name:
                            hosts_map[ip]["services"].append({
                                "port": port,
                                "protocol": protocol,
                                "service": service_name,
                                "version": service.get("version", "")
                            })
                            # Also add to ports list if not present
                            port_entry = f"{port}/{protocol}"
                            if port_entry not in hosts_map[ip]["ports"]:
                                hosts_map[ip]["ports"].append(port_entry)

            elif tool_name == "nmap_recon__os_detection":
                os_matches = result.get("os_matches", [])
                target_ip = result.get("target")
                if target_ip and os_matches:
                    if target_ip not in hosts_map:
                        hosts_map[target_ip] = {
                            "ip": target_ip,
                            "hostname": "",
                            "mac": "",
                            "ports": [],
                            "services": [],
                            "os": ""
                        }
                    # Use first OS match
                    hosts_map[target_ip]["os"] = os_matches[0].get("name", "")

        return list(hosts_map.values())

    def _extract_hosts_from_answer(self, recon_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fallback: Try to extract hosts from agent's answer field.

        The recon agent may output structured JSON in its answer.

        Returns:
            List of host dicts or empty list
        """
        answer = recon_result.get("answer", "")

        # Parse JSON from answer
        if isinstance(answer, str):
            try:
                recon_data = json.loads(answer)
            except json.JSONDecodeError:
                self.logger.debug(f"Answer is not JSON, no hosts extracted")
                return []
        elif isinstance(answer, dict):
            recon_data = answer
        else:
            return []

        # Extract hosts array
        hosts = recon_data.get("hosts", [])
        if not isinstance(hosts, list):
            return []

        return hosts

    async def _process_vuln_node(
        self,
        scan_id: str,
        vuln_result: Dict[str, Any]
    ):
        """
        Extract vulnerabilities from vuln-analysis node and create attack records.

        Expected format (from vuln-analyzer agent):
        {
          "answer": "{\"vulnerabilities\": [{\"host\": \"...\", \"type\": \"...\"}]}",
          "status": "completed"
        }

        Args:
            scan_id: Parent scan ID
            vuln_result: Vulnerability analysis node output
        """
        try:
            # Extract answer field
            answer = vuln_result.get("answer", "")

            # Parse JSON from answer
            if isinstance(answer, str):
                try:
                    vuln_data = json.loads(answer)
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse vuln answer as JSON: {answer[:100]}")
                    return
            elif isinstance(answer, dict):
                vuln_data = answer
            else:
                self.logger.warning(f"Unexpected vuln answer type: {type(answer)}")
                return

            # Extract vulnerabilities
            vulnerabilities = vuln_data.get("vulnerabilities", [])
            if not isinstance(vulnerabilities, list):
                self.logger.warning(f"Vulnerabilities is not a list: {type(vulnerabilities)}")
                return

            # Create attack record for each vulnerability
            for vuln in vulnerabilities:
                if not isinstance(vuln, dict):
                    continue

                target_host = vuln.get("host", vuln.get("ip", "unknown"))
                attack_type = vuln.get("type", "vulnerability_identified")

                attack_id = await self.attack_service.create_attack(
                    scan_id=scan_id,
                    target_host=target_host,
                    attack_type=attack_type,
                    options={"vulnerability_data": vuln}
                )

                # Mark attack as completed with vulnerability details
                await self.attack_service.complete_attack(
                    scan_id=scan_id,
                    attack_id=attack_id,
                    result={"status": "identified"},
                    vulnerabilities=[vuln]
                )

                self.logger.info(f"Created attack {attack_id} for vulnerability on {target_host}")

        except Exception as e:
            self.logger.error(f"Failed to process vuln node for scan {scan_id}: {e}", exc_info=True)

    async def _process_exploit_node(
        self,
        scan_id: str,
        exploit_result: Dict[str, Any]
    ):
        """
        Extract exploit validation results and link to scan.

        Expected format (from exploit-validator agent):
        {
          "answer": "{\"exploits_validated\": [...], \"pocs\": [...]}",
          "status": "completed"
        }

        Args:
            scan_id: Parent scan ID
            exploit_result: Exploit validation node output
        """
        try:
            # Log exploit validation completion
            await self.recon_service.log_event(scan_id, {
                "type": "exploit_validation_complete",
                "message": "Exploit validation completed",
                "result": exploit_result.get("answer", "")
            })

            self.logger.info(f"Logged exploit validation for scan {scan_id}")

        except Exception as e:
            self.logger.error(f"Failed to process exploit node for scan {scan_id}: {e}", exc_info=True)

    async def _store_workflow_metadata(
        self,
        scan_id: str,
        workflow_id: str,
        execution_id: str,
        final_result: Dict[str, Any]
    ):
        """
        Store full workflow result in scan metadata for audit trail.

        Args:
            scan_id: Scan ID
            workflow_id: Workflow definition ID
            execution_id: Execution instance ID
            final_result: Complete workflow results
        """
        try:
            # Get existing metadata
            metadata = await self.recon_service.get_metadata(scan_id)

            # Serialize workflow result to remove Anthropic TextBlock objects
            # These are not JSON-serializable and will cause errors
            serialized_result = self._serialize_for_json(final_result)

            # Add workflow result
            metadata["workflow_result"] = serialized_result
            metadata["workflow_id"] = workflow_id
            metadata["workflow_execution_id"] = execution_id

            # Save updated metadata
            await self.recon_service._save_metadata(scan_id, metadata)

            self.logger.info(f"Stored workflow metadata for scan {scan_id}")

        except Exception as e:
            self.logger.error(f"Failed to store workflow metadata for scan {scan_id}: {e}", exc_info=True)

    def _serialize_for_json(self, obj: Any) -> Any:
        """
        Recursively serialize objects for JSON storage.
        Handles Anthropic TextBlock objects and other non-JSON types.

        Args:
            obj: Object to serialize

        Returns:
            JSON-serializable version of obj
        """
        # Handle None
        if obj is None:
            return None

        # Handle Anthropic TextBlock objects
        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'TextBlock':
            return {"type": "text", "text": getattr(obj, 'text', str(obj))}

        # Handle Pydantic models
        if hasattr(obj, 'model_dump'):
            try:
                return self._serialize_for_json(obj.model_dump(mode='json'))
            except Exception:
                return str(obj)

        # Handle dicts recursively
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}

        # Handle lists recursively
        if isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]

        # Handle tuples as lists
        if isinstance(obj, tuple):
            return [self._serialize_for_json(item) for item in obj]

        # Return primitives as-is
        return obj
