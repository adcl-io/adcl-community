# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Kali Linux MCP Server
Provides penetration testing tools for authorized security assessments
DEFENSIVE USE ONLY - For authorized penetration testing and security analysis
"""
import os
import sys
import subprocess
import json
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
from datetime import datetime

from base_server import BaseMCPServer


class KaliMCPServer(BaseMCPServer):
    """
    Kali Linux MCP Server for penetration testing
    DEFENSIVE SECURITY TOOL - Use only on authorized targets

    Tools:
    - nikto_scan: Web vulnerability scanner
    - dirb_scan: Directory/file brute forcing
    - sqlmap_scan: SQL injection detection
    - metasploit_search: Search for exploits
    - hydra_bruteforce: Password brute forcing
    - wpscan: WordPress vulnerability scanner
    - dns_enum: DNS enumeration with dnsenum
    - subdomain_enum: Subdomain discovery with sublist3r
    """

    def __init__(self, port: int = 7005):
        super().__init__(
            name="kali",
            port=port,
            description="Kali Linux penetration testing tools (Defensive Security)"
        )

        # Check available tools
        self._check_tools_available()

        # Register penetration testing tools
        self._register_pentest_tools()

    def _check_tools_available(self):
        """Check which Kali tools are installed"""
        tools_to_check = [
            "nikto",
            "dirb",
            "sqlmap",
            "msfconsole",
            "hydra",
            "wpscan",
            "dnsenum",
            "sublist3r"
        ]

        self.available_tools = {}
        for tool in tools_to_check:
            try:
                result = subprocess.run(
                    ["which", tool],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                self.available_tools[tool] = result.returncode == 0
            except Exception:
                self.available_tools[tool] = False

        print(f"[{self.name}] Available tools: {[k for k, v in self.available_tools.items() if v]}")

    def _register_pentest_tools(self):
        """Register all penetration testing capabilities as tools"""

        self.register_tool(
            name="nikto_scan",
            handler=self.nikto_scan,
            description="Scan web server for vulnerabilities using Nikto",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target URL (e.g., http://example.com)"
                    },
                    "port": {
                        "type": "string",
                        "description": "Target port (default: 80)"
                    },
                    "ssl": {
                        "type": "boolean",
                        "description": "Use SSL (HTTPS)"
                    }
                },
                "required": ["target"]
            }
        )

        self.register_tool(
            name="dirb_scan",
            handler=self.dirb_scan,
            description="Brute force directories and files on web server",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target URL (e.g., http://example.com)"
                    },
                    "wordlist": {
                        "type": "string",
                        "description": "Wordlist to use (default: common)"
                    }
                },
                "required": ["target"]
            }
        )

        self.register_tool(
            name="sqlmap_scan",
            handler=self.sqlmap_scan,
            description="Test for SQL injection vulnerabilities",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target URL with parameter (e.g., http://example.com/page?id=1)"
                    },
                    "level": {
                        "type": "string",
                        "description": "Test level: 1-5 (default: 1)"
                    },
                    "risk": {
                        "type": "string",
                        "description": "Risk level: 1-3 (default: 1)"
                    }
                },
                "required": ["target"]
            }
        )

        self.register_tool(
            name="metasploit_search",
            handler=self.metasploit_search,
            description="Search Metasploit for exploits and modules",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term (software/CVE/service)"
                    },
                    "type": {
                        "type": "string",
                        "description": "Module type: exploit, auxiliary, payload (default: exploit)"
                    }
                },
                "required": ["query"]
            }
        )

        self.register_tool(
            name="hydra_bruteforce",
            handler=self.hydra_bruteforce,
            description="Brute force authentication (SSH, FTP, HTTP, etc.)",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target IP or hostname"
                    },
                    "service": {
                        "type": "string",
                        "description": "Service to attack (ssh, ftp, http-get, etc.)"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username to test (or path to username list)"
                    },
                    "password_list": {
                        "type": "string",
                        "description": "Path to password wordlist"
                    }
                },
                "required": ["target", "service", "username", "password_list"]
            }
        )

        self.register_tool(
            name="wpscan",
            handler=self.wpscan,
            description="Scan WordPress sites for vulnerabilities",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target WordPress URL"
                    },
                    "enumerate": {
                        "type": "string",
                        "description": "What to enumerate: vp (plugins), vt (themes), u (users)"
                    }
                },
                "required": ["target"]
            }
        )

        self.register_tool(
            name="dns_enum",
            handler=self.dns_enum,
            description="Enumerate DNS records and subdomains",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Target domain (e.g., example.com)"
                    }
                },
                "required": ["domain"]
            }
        )

        self.register_tool(
            name="subdomain_enum",
            handler=self.subdomain_enum,
            description="Discover subdomains using sublist3r",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Target domain (e.g., example.com)"
                    },
                    "bruteforce": {
                        "type": "boolean",
                        "description": "Enable brute force (slower but more thorough)"
                    }
                },
                "required": ["domain"]
            }
        )

    async def nikto_scan(self, target: str, port: str = "80", ssl: bool = False) -> Dict[str, Any]:
        """Scan web server with Nikto"""
        print(f"[{self.name}] Nikto scan on {target}")

        if not self.available_tools.get("nikto"):
            return {"error": "Nikto not installed", "note": "Install with: apt-get install nikto"}

        cmd = ["nikto", "-h", target, "-port", port]
        if ssl:
            cmd.append("-ssl")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            return {
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "scan_output": result.stdout,
                "vulnerabilities_found": self._parse_nikto_output(result.stdout)
            }

        except subprocess.TimeoutExpired:
            return {"error": "Scan timeout", "target": target}
        except Exception as e:
            return {"error": str(e), "target": target}

    async def dirb_scan(self, target: str, wordlist: str = "common") -> Dict[str, Any]:
        """Directory brute forcing with DIRB"""
        print(f"[{self.name}] DIRB scan on {target}")

        if not self.available_tools.get("dirb"):
            return {"error": "DIRB not installed", "note": "Install with: apt-get install dirb"}

        # Map wordlist names to paths
        wordlist_map = {
            "common": "/usr/share/dirb/wordlists/common.txt",
            "big": "/usr/share/dirb/wordlists/big.txt",
            "small": "/usr/share/dirb/wordlists/small.txt"
        }

        wordlist_path = wordlist_map.get(wordlist, wordlist)

        cmd = ["dirb", target, wordlist_path, "-r", "-S"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            return {
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "directories_found": self._parse_dirb_output(result.stdout),
                "scan_output": result.stdout
            }

        except Exception as e:
            return {"error": str(e), "target": target}

    async def sqlmap_scan(self, target: str, level: str = "1", risk: str = "1") -> Dict[str, Any]:
        """SQL injection testing with sqlmap"""
        print(f"[{self.name}] SQLMap scan on {target}")

        if not self.available_tools.get("sqlmap"):
            return {"error": "SQLMap not installed", "note": "Install with: apt-get install sqlmap"}

        cmd = [
            "sqlmap",
            "-u", target,
            "--level", level,
            "--risk", risk,
            "--batch",  # Non-interactive
            "--random-agent"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            return {
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "vulnerable": "vulnerable" in result.stdout.lower(),
                "scan_output": result.stdout[:2000],  # Truncate long output
                "summary": self._parse_sqlmap_output(result.stdout)
            }

        except Exception as e:
            return {"error": str(e), "target": target}

    async def metasploit_search(self, query: str, type: str = "exploit") -> Dict[str, Any]:
        """Search Metasploit database"""
        print(f"[{self.name}] Metasploit search: {query}")

        if not self.available_tools.get("msfconsole"):
            return {"error": "Metasploit not installed"}

        cmd = ["msfconsole", "-q", "-x", f"search {type}:{query}; exit"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "query": query,
                "type": type,
                "timestamp": datetime.now().isoformat(),
                "results": self._parse_msf_search(result.stdout)
            }

        except Exception as e:
            return {"error": str(e), "query": query}

    async def hydra_bruteforce(
        self,
        target: str,
        service: str,
        username: str,
        password_list: str
    ) -> Dict[str, Any]:
        """Brute force authentication with Hydra"""
        print(f"[{self.name}] Hydra brute force: {service} on {target}")

        if not self.available_tools.get("hydra"):
            return {"error": "Hydra not installed", "note": "Install with: apt-get install hydra"}

        # Security check
        if not os.path.exists(password_list):
            return {"error": f"Password list not found: {password_list}"}

        cmd = [
            "hydra",
            "-l", username,
            "-P", password_list,
            "-t", "4",  # 4 parallel connections
            f"{target}",
            service
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            return {
                "target": target,
                "service": service,
                "timestamp": datetime.now().isoformat(),
                "credentials_found": self._parse_hydra_output(result.stdout),
                "scan_output": result.stdout
            }

        except Exception as e:
            return {"error": str(e), "target": target}

    async def wpscan(self, target: str, enumerate: str = "vp,vt,u") -> Dict[str, Any]:
        """WordPress vulnerability scan"""
        print(f"[{self.name}] WPScan on {target}")

        if not self.available_tools.get("wpscan"):
            return {"error": "WPScan not installed", "note": "Install with: gem install wpscan"}

        cmd = ["wpscan", "--url", target, "--enumerate", enumerate, "--random-user-agent"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            return {
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "vulnerabilities": self._parse_wpscan_output(result.stdout),
                "scan_output": result.stdout[:2000]
            }

        except Exception as e:
            return {"error": str(e), "target": target}

    async def dns_enum(self, domain: str) -> Dict[str, Any]:
        """DNS enumeration with dnsenum"""
        print(f"[{self.name}] DNS enumeration on {domain}")

        if not self.available_tools.get("dnsenum"):
            return {"error": "dnsenum not installed", "note": "Install with: apt-get install dnsenum"}

        cmd = ["dnsenum", "--noreverse", domain]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "domain": domain,
                "timestamp": datetime.now().isoformat(),
                "records": self._parse_dnsenum_output(result.stdout),
                "scan_output": result.stdout
            }

        except Exception as e:
            return {"error": str(e), "domain": domain}

    async def subdomain_enum(self, domain: str, bruteforce: bool = False) -> Dict[str, Any]:
        """Subdomain discovery with sublist3r"""
        print(f"[{self.name}] Subdomain enumeration on {domain}")

        if not self.available_tools.get("sublist3r"):
            return {"error": "Sublist3r not installed", "note": "Install with: pip install sublist3r"}

        cmd = ["sublist3r", "-d", domain]
        if bruteforce:
            cmd.append("-b")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            return {
                "domain": domain,
                "timestamp": datetime.now().isoformat(),
                "subdomains": self._parse_sublist3r_output(result.stdout),
                "scan_output": result.stdout
            }

        except Exception as e:
            return {"error": str(e), "domain": domain}

    # Helper methods to parse tool outputs
    def _parse_nikto_output(self, output: str) -> List[Dict[str, str]]:
        """Extract vulnerabilities from Nikto output"""
        vulnerabilities = []
        for line in output.split('\n'):
            if line.startswith('+'):
                vulnerabilities.append({"finding": line.strip()})
        return vulnerabilities[:20]  # Limit to 20

    def _parse_dirb_output(self, output: str) -> List[str]:
        """Extract found directories from DIRB output"""
        directories = []
        for line in output.split('\n'):
            if '==> DIRECTORY:' in line or 'CODE:200' in line:
                directories.append(line.strip())
        return directories

    def _parse_sqlmap_output(self, output: str) -> Dict[str, Any]:
        """Parse sqlmap results"""
        return {
            "injectable": "injectable" in output.lower(),
            "database_type": self._extract_between(output, "back-end DBMS:", "\n"),
            "payload_found": "Payload:" in output
        }

    def _parse_msf_search(self, output: str) -> List[str]:
        """Parse Metasploit search results"""
        results = []
        for line in output.split('\n'):
            if '/' in line and 'exploit' in line.lower():
                results.append(line.strip())
        return results[:15]  # Limit results

    def _parse_hydra_output(self, output: str) -> List[Dict[str, str]]:
        """Extract found credentials from Hydra output"""
        credentials = []
        for line in output.split('\n'):
            if 'login:' in line and 'password:' in line:
                credentials.append({"credential": line.strip()})
        return credentials

    def _parse_wpscan_output(self, output: str) -> List[str]:
        """Extract vulnerabilities from WPScan output"""
        vulns = []
        for line in output.split('\n'):
            if '[!]' in line:
                vulns.append(line.strip())
        return vulns[:20]

    def _parse_dnsenum_output(self, output: str) -> Dict[str, List[str]]:
        """Parse DNS records from dnsenum"""
        return {
            "nameservers": self._extract_lines_containing(output, "NS"),
            "mail_servers": self._extract_lines_containing(output, "MX"),
            "hosts": self._extract_lines_containing(output, "Host's addresses:")
        }

    def _parse_sublist3r_output(self, output: str) -> List[str]:
        """Extract subdomains from Sublist3r output"""
        subdomains = []
        for line in output.split('\n'):
            if '.' in line and not line.startswith('['):
                subdomains.append(line.strip())
        return subdomains

    def _extract_between(self, text: str, start: str, end: str) -> str:
        """Extract text between two markers"""
        try:
            return text.split(start)[1].split(end)[0].strip()
        except:
            return ""

    def _extract_lines_containing(self, text: str, marker: str) -> List[str]:
        """Extract lines containing a specific marker"""
        return [line.strip() for line in text.split('\n') if marker in line]


if __name__ == "__main__":
    port = int(os.getenv("KALI_PORT", "7005"))
    server = KaliMCPServer(port=port)
    server.run()
