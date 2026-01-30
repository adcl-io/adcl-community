# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Attack Session Service - Automatic State Management
Listens to workflow completion events and automatically updates session state.
Backend reads execution results and enriches host data.
"""
from pathlib import Path
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

SESSIONS_DIR = Path("/app/volumes/data/attack_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class AttackSessionService:
    """Manages attack playground session state (backend is source of truth)"""

    @staticmethod
    def parse_services_from_answer(answer: str) -> List[Dict[str, Any]]:
        """Extract services from fast-recon agent answer"""
        try:
            # Try to extract from code block first (```json ... ```)
            code_block_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', answer)
            if code_block_match:
                data = json.loads(code_block_match.group(1))
                if "services" in data:
                    print(f"Parsed {len(data['services'])} services from code block")
                    return data["services"]

            # Fallback: Look for JSON object with services (more robust pattern)
            # Match from { to matching } with proper nesting
            json_pattern = r'\{[^{}]*"services"\s*:\s*\[[^\]]*\][^{}]*\}'
            json_match = re.search(json_pattern, answer, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                print(f"Parsed {len(data.get('services', []))} services from inline JSON")
                return data.get("services", [])
        except Exception as e:
            print(f"Failed to parse services: {e}")
        return []

    @staticmethod
    def parse_vulnerabilities_from_answer(answer: str) -> List[Dict[str, Any]]:
        """Extract vulnerabilities from cve-analysis agent answer"""
        try:
            # Try to extract from code block first (```json ... ```)
            # Use greedy matching to get full JSON with nested objects
            code_block_match = re.search(r'```json\s*(\{[\s\S]*\})\s*```', answer)
            if code_block_match:
                json_str = code_block_match.group(1)
                # Parse and validate
                data = json.loads(json_str)
                if "vulnerabilities" in data and isinstance(data["vulnerabilities"], list):
                    print(f"✓ Parsed {len(data['vulnerabilities'])} vulnerabilities from code block")
                    return data["vulnerabilities"]

            # Fallback: Try to find any JSON with vulnerabilities key
            # Look for the pattern more flexibly
            lines = answer.split('\n')
            json_start = -1
            for i, line in enumerate(lines):
                if '{' in line and '"vulnerabilities"' in answer[answer.find(line):]:
                    json_start = i
                    break

            if json_start >= 0:
                # Try to extract JSON from this point
                partial = '\n'.join(lines[json_start:])
                # Find the first { and match to closing }
                brace_count = 0
                start_idx = partial.find('{')
                if start_idx >= 0:
                    for i in range(start_idx, len(partial)):
                        if partial[i] == '{':
                            brace_count += 1
                        elif partial[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = partial[start_idx:i+1]
                                data = json.loads(json_str)
                                if "vulnerabilities" in data:
                                    print(f"✓ Parsed {len(data.get('vulnerabilities', []))} vulnerabilities from balanced JSON")
                                    return data.get("vulnerabilities", [])
                                break

        except Exception as e:
            print(f"✗ Failed to parse vulnerabilities: {e}")
            import traceback
            print(traceback.format_exc())
        return []

    @staticmethod
    def parse_exploit_results_from_answer(answer: str) -> Dict[str, Any]:
        """Extract exploitation results from smart-exploit agent answer"""
        try:
            # Try 1: Look for JSON in markdown code block
            code_block_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', answer)
            if code_block_match:
                json_str = code_block_match.group(1)
                data = json.loads(json_str)
                print(f"✓ Parsed exploitation results from markdown code block")
            else:
                # Try 2: Look for raw JSON in answer (search for {...} with "target_ip")
                json_match = re.search(r'\{[\s\S]*?"target_ip"[\s\S]*?\}', answer)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    print(f"✓ Parsed exploitation results from raw JSON")
                else:
                    print(f"✗ No JSON found in answer (length: {len(answer)} chars)")
                    print(f"   Answer preview: {answer[:200]}")
                    return {}

            # Validate it's exploitation data
            if "target_ip" in data or "successful_exploits" in data or "proof_of_compromise" in data or "access_level" in data:
                # Extract confirmed CVEs from successful exploits
                confirmed_cves = []
                if data.get("successful_exploits"):
                    for exploit in data["successful_exploits"]:
                        if exploit.get("cve"):
                            confirmed_cves.append(exploit["cve"])

                # Extract key fields
                result = {
                    "target_ip": data.get("target_ip"),
                    "exploited_at": datetime.utcnow().isoformat(),
                    "successful_exploits": data.get("successful_exploits", []),
                    "exploits_attempted": data.get("exploits_attempted", []),
                    "proof_of_compromise": data.get("proof_of_compromise", data.get("proof", "")),
                    "access_level": data.get("access_level", "unknown"),
                    "raw_output": answer[:2000],  # Keep first 2000 chars of full output
                    "confirmed_cves": confirmed_cves
                }
                print(f"✅ Exploitation results parsed: {len(confirmed_cves)} CVEs, access_level={result['access_level']}")
                return result
            else:
                print(f"✗ JSON found but missing required fields (target_ip, successful_exploits, access_level)")
                print(f"   Keys found: {list(data.keys())}")
                return {}

        except Exception as e:
            print(f"✗ Failed to parse exploit results: {e}")
            import traceback
            print(traceback.format_exc())

        return {}

    @staticmethod
    def extract_target_ip(target_description: str) -> Optional[str]:
        """Extract IP address from target description"""
        # Match IP addresses in common formats
        import re
        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', target_description)
        if ip_match:
            return ip_match.group(1)
        return None

    @staticmethod
    def get_or_create_session(session_id: str) -> Dict[str, Any]:
        """Load session or create new one"""
        session_file = SESSIONS_DIR / f"{session_id}.json"

        if session_file.exists():
            with open(session_file) as f:
                return json.load(f)

        # Create new session
        session = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "hosts": []
        }
        session_file.write_text(json.dumps(session, indent=2))
        return session

    @staticmethod
    def save_session(session: Dict[str, Any]):
        """Save session to disk"""
        session_file = SESSIONS_DIR / f"{session['session_id']}.json"
        session_file.write_text(json.dumps(session, indent=2))

    @staticmethod
    def get_host_from_session(session_id: str, target_ip: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve host data from attack session for a specific target IP.

        Args:
            session_id: Attack playground session ID
            target_ip: Target IP address to find

        Returns:
            Host dict with services/vulnerabilities/ports, or None if not found
        """
        try:
            session_file = SESSIONS_DIR / f"{session_id}.json"
            if not session_file.exists():
                print(f"Session file not found: {session_id}")
                return None

            with open(session_file) as f:
                session = json.load(f)

            # Find host matching target IP
            for host in session.get("hosts", []):
                if host.get("ip") == target_ip:
                    print(f"Found host data for {target_ip} in session {session_id}")
                    return host

            print(f"No host found for {target_ip} in session {session_id}")
            return None

        except Exception as e:
            print(f"Error loading session host data: {e}")
            return None

    @staticmethod
    def update_host_in_session(session_id: str, host_ip: str, update_data: Dict[str, Any]):
        """Update host data in session (merge strategy)"""
        session = AttackSessionService.get_or_create_session(session_id)

        # Find existing host
        host_idx = None
        for idx, host in enumerate(session["hosts"]):
            if host["ip"] == host_ip:
                host_idx = idx
                break

        if host_idx is not None:
            # Merge with existing host
            session["hosts"][host_idx] = {
                **session["hosts"][host_idx],
                **update_data,
                "updated_at": datetime.utcnow().isoformat()
            }
        else:
            # Add new host
            session["hosts"].append({
                "ip": host_ip,
                **update_data,
                "added_at": datetime.utcnow().isoformat()
            })

        AttackSessionService.save_session(session)
        return session

    @staticmethod
    def on_workflow_complete(session_id: str, workflow_id: str, target: str, execution_result: Dict[str, Any]):
        """
        Workflow completion hook - automatically parse results and update session state
        Called by workflow engine when workflow completes
        """
        print(f"\n{'='*80}")
        print(f"🎯 HOOK CALLED: on_workflow_complete")
        print(f"   Session ID: {session_id}")
        print(f"   Workflow ID: {workflow_id}")
        print(f"   Target: {target}")
        print(f"{'='*80}\n")

        # Extract target IP
        target_ip = AttackSessionService.extract_target_ip(target)
        if not target_ip:
            print(f"❌ Could not extract IP from target: {target}")
            return

        print(f"✓ Extracted target IP: {target_ip}")

        # Extract node results (dict mapping node_id → agent result)
        node_results = execution_result.get("result", {})
        if not isinstance(node_results, dict):
            print(f"❌ Unexpected result structure: {type(node_results)}")
            return

        print(f"✓ Node results keys: {list(node_results.keys())}")

        # For single-node workflows, get the first (and only) node's result
        # For multi-node workflows, process all relevant nodes
        answers = {}
        for node_id, node_result in node_results.items():
            if isinstance(node_result, dict):
                answer = node_result.get("answer", "")
                answers[node_id] = answer
                print(f"✓ Node {node_id}: answer length = {len(answer)} chars")
            else:
                print(f"⚠ Node {node_id}: result is {type(node_result)}, not dict")

        # Parse based on workflow type
        update_data = {}

        if workflow_id == "fast-recon":
            # Single-node workflow: just the recon node
            recon_answer = answers.get("recon", "")
            if recon_answer:
                services = AttackSessionService.parse_services_from_answer(recon_answer)
                if services:
                    update_data["services"] = services
                    update_data["ports"] = [s.get("port") for s in services if "port" in s]
                    print(f"Parsed {len(services)} services for {target_ip}")

        elif workflow_id == "cve-analysis":
            # Single-node workflow: just the analyze node
            print(f"\n📊 Processing CVE-ANALYSIS workflow")
            analyze_answer = answers.get("analyze", "")
            if analyze_answer:
                print(f"   Analyze answer length: {len(analyze_answer)} chars")
                print(f"   First 200 chars: {analyze_answer[:200]}...")
                vulnerabilities = AttackSessionService.parse_vulnerabilities_from_answer(analyze_answer)
                if vulnerabilities:
                    update_data["vulnerabilities"] = vulnerabilities
                    print(f"✅ Parsed {len(vulnerabilities)} vulnerabilities for {target_ip}")
                    for vuln in vulnerabilities:
                        print(f"   - {vuln.get('cve')}: {vuln.get('severity')}")
                else:
                    print(f"❌ No vulnerabilities parsed from answer")
            else:
                print(f"❌ No 'analyze' node answer found")

        elif workflow_id == "smart-exploit":
            # Single-node workflow: just the exploit node
            print(f"\n💥 Processing SMART-EXPLOIT workflow")
            exploit_answer = answers.get("exploit", "")
            if exploit_answer:
                print(f"   Exploit answer length: {len(exploit_answer)} chars")
                exploit_result = AttackSessionService.parse_exploit_results_from_answer(exploit_answer)
                if exploit_result:
                    # Add to exploits list (append mode, don't overwrite)
                    update_data["exploitation_results"] = exploit_result
                    print(f"✅ Parsed exploitation results for {target_ip}")
                    print(f"   Successful exploits: {exploit_result.get('successful_exploits', [])}")
                    print(f"   Access level: {exploit_result.get('access_level')}")

                    # Also update vulnerabilities with exploitation status
                    # Mark CVEs that were successfully exploited
                    successful_cves = exploit_result.get("confirmed_cves", [])
                    if successful_cves:
                        # We'll update the vulnerability list to mark exploited CVEs
                        update_data["exploitation_confirmed_cves"] = successful_cves
                        print(f"✅ Confirmed CVEs: {successful_cves}")
                        print(f"   Type check: confirmed_cves is {type(successful_cves)}, first item type: {type(successful_cves[0]) if successful_cves else 'N/A'}")

                        # CRITICAL FIX: Add exploited CVEs to vulnerabilities list if missing
                        # The exploit agent may find CVEs not in the initial vuln scan
                        # Load current host to check existing vulnerabilities
                        current_host = AttackSessionService.get_host_from_session(session_id, target_ip) or {}
                        current_vulns = current_host.get("vulnerabilities", [])
                        current_cve_ids = {v.get("cve") for v in current_vulns if v.get("cve")}

                        # Extract exploits_attempted from exploitation results for CVE details
                        exploits_attempted = exploit_result.get("exploits_attempted", [])

                        # For each successful CVE, ensure it's in the vulnerabilities list
                        for successful_cve_str in successful_cves:
                            # Handle both string CVEs and dict objects from successful_exploits
                            if isinstance(successful_cve_str, dict):
                                # Extract CVE from dict (agent returned full exploit object)
                                cve_id = successful_cve_str.get("cve", "")
                                if not cve_id:
                                    continue
                                # Clean CVE ID if it has extra text
                                cve_match = re.search(r'(CVE-\d{4}-\d+)', cve_id) if isinstance(cve_id, str) else None
                                if cve_match:
                                    cve_id = cve_match.group(1)
                                else:
                                    # If no CVE pattern match, skip this entry
                                    continue
                            else:
                                # Extract just the CVE ID (e.g., "CVE-2017-5638" from "CVE-2017-5638 (Struts2 S2-045)")
                                cve_match = re.search(r'(CVE-\d{4}-\d+)', successful_cve_str)
                                if not cve_match:
                                    continue
                                cve_id = cve_match.group(1)

                            # Check if this CVE already exists in vulnerabilities
                            if cve_id not in current_cve_ids:
                                # Find details from exploits_attempted
                                exploit_details = None
                                for attempt in exploits_attempted:
                                    if attempt.get("success") and attempt.get("cve") == cve_id:
                                        exploit_details = attempt
                                        break

                                # Create vulnerability entry for the exploited CVE
                                new_vuln = {
                                    "cve": cve_id,
                                    "service": exploit_details.get("vulnerability", "").split("-")[0].strip() if exploit_details else "Unknown",
                                    "severity": exploit_details.get("severity", "critical").lower(),
                                    "exploit_type": "RCE",
                                    "exploit_method": exploit_details.get("method", "Successfully exploited"),
                                    "confidence": "verified",  # Mark as verified since it was exploited
                                    "source": "exploitation"   # Mark source as exploitation discovery
                                }

                                current_vulns.append(new_vuln)
                                print(f"✅ Added exploited CVE {cve_id} to vulnerabilities list (discovered during exploitation)")

                        # Update vulnerabilities list with newly discovered exploited CVEs
                        if current_vulns:
                            update_data["vulnerabilities"] = current_vulns
                else:
                    print(f"❌ No exploitation results parsed from answer")

        elif workflow_id == "autonomous-attack":
            # Multi-node workflow: recon + analyze + exploit
            # Parse all stages
            recon_answer = answers.get("recon", "")
            if recon_answer:
                services = AttackSessionService.parse_services_from_answer(recon_answer)
                if services:
                    update_data["services"] = services
                    update_data["ports"] = [s.get("port") for s in services if "port" in s]

            analyze_answer = answers.get("analyze", "")
            if analyze_answer:
                vulnerabilities = AttackSessionService.parse_vulnerabilities_from_answer(analyze_answer)
                if vulnerabilities:
                    update_data["vulnerabilities"] = vulnerabilities

            # Exploit results
            # TODO: Add proof parsing when needed

        # Update session if we parsed anything
        if update_data:
            AttackSessionService.update_host_in_session(session_id, target_ip, update_data)
            print(f"Updated session {session_id} host {target_ip}: {list(update_data.keys())}")


# Singleton instance
attack_session_service = AttackSessionService()
