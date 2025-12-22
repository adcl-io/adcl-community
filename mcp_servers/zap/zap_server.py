# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
ZAP MCP Server - OWASP ZAP security scanner
Provides security testing tools via MCP protocol
"""
import os
import sys
import subprocess
import time
import requests
import fnmatch
from urllib.parse import urlparse
from zapv2 import ZAPv2

# Import base_server from local directory
from base_server import BaseMCPServer


class ZapMCPServer(BaseMCPServer):
    """OWASP ZAP MCP Server"""

    def __init__(self, port: int = 7008):
        super().__init__(
            name="zap",
            port=port,
            description="OWASP ZAP security scanner MCP"
        )
        
        self.zap_process = None
        self.zap = None
        
        # Start ZAP daemon
        self._start_zap_process()
        
        # Register tools
        self._register_tools()

    def _start_zap_process(self):
        """Start ZAP in foreground mode for better process management"""
        print(f"[{self.name}] Starting ZAP process...")
        
        # Start ZAP in daemon mode with proper host binding
        self.zap_process = subprocess.Popen([
            "zap.sh", "-daemon", "-host", "0.0.0.0",
            "-port", "8080",
            "-config", "api.disablekey=true",
            "-config", "api.addrs.addr.name=.*",
            "-config", "api.addrs.addr.regex=true"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for ZAP to be ready (up to 5 minutes - ZAP takes time to initialize)
        for attempt in range(150):  # 150 attempts * 2 seconds = 5 minutes
            try:
                # Check if process died
                if self.zap_process.poll() is not None:
                    stderr = self.zap_process.stderr.read().decode() if self.zap_process.stderr else "No stderr"
                    raise RuntimeError(f"ZAP process died during startup: {stderr}")
                
                # In daemon mode, API is on port 8080 (same as proxy)
                api_response = requests.get(
                    "http://localhost:8080/JSON/core/view/version/",
                    timeout=2
                )
                
                if api_response.status_code == 200:
                    print(f"[{self.name}] ZAP ready (API responding)")
                    # Initialize ZAP client - API is on port 8080 in daemon mode
                    self.zap = ZAPv2(apikey='', proxies={
                        'http': 'http://localhost:8080',
                        'https': 'http://localhost:8080'
                    })
                    return
            except requests.exceptions.RequestException as e:
                if attempt % 15 == 0:  # Log every 30 seconds
                    print(f"[{self.name}] Waiting for ZAP... ({attempt * 2}s elapsed)")
                time.sleep(2)
        
        raise RuntimeError("ZAP failed to start within 5 minutes")

    def _validate_target(self, target: str) -> bool:
        """Validate target URL against whitelist"""
        allowed = os.environ.get("ALLOWED_SCAN_TARGETS", "").split(",")
        if not allowed or allowed == [""]:
            raise ValueError("ALLOWED_SCAN_TARGETS not configured")
        
        parsed = urlparse(target)
        target_pattern = f"{parsed.scheme}://{parsed.netloc}"
        
        for pattern in allowed:
            if fnmatch.fnmatch(target_pattern, pattern.strip()):
                return True
        
        raise ValueError(f"Target {target} not in whitelist: {allowed}")

    def _register_tools(self):
        """Register ZAP tools"""
        
        self.register_tool(
            name="start_proxy",
            handler=self.start_proxy,
            description="Start ZAP proxy daemon (if not already running)",
            input_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "description": "Proxy port",
                        "default": 8080
                    }
                }
            }
        )
        
        self.register_tool(
            name="get_urls",
            handler=self.get_urls,
            description="Query discovered endpoints from ZAP sitemap",
            input_schema={"type": "object", "properties": {}}
        )
        
        self.register_tool(
            name="active_scan",
            handler=self.active_scan,
            description="Start active vulnerability scan",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target URL to scan"
                    },
                    "scan_policy": {
                        "type": "string",
                        "description": "Scan policy (Light, Medium, Heavy)",
                        "default": "Light"
                    }
                },
                "required": ["target"]
            }
        )
        
        self.register_tool(
            name="get_scan_status",
            handler=self.get_scan_status,
            description="Check scan progress",
            input_schema={
                "type": "object",
                "properties": {
                    "scan_id": {
                        "type": "string",
                        "description": "Scan ID from active_scan"
                    }
                },
                "required": ["scan_id"]
            }
        )
        
        self.register_tool(
            name="get_alerts",
            handler=self.get_alerts,
            description="Query vulnerability findings",
            input_schema={
                "type": "object",
                "properties": {
                    "risk_level": {
                        "type": "string",
                        "description": "Minimum risk level (High, Medium, Low, Informational)",
                        "default": "High"
                    }
                }
            }
        )
        
        self.register_tool(
            name="generate_report",
            handler=self.generate_report,
            description="Generate security report",
            input_schema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Report format (json, html, xml)",
                        "default": "json"
                    }
                }
            }
        )

    async def start_proxy(self, port: int = 8080):
        """Start ZAP proxy daemon"""
        if self.zap_process and self.zap_process.poll() is None:
            return {
                "status": "running",
                "proxy_url": f"http://localhost:{port}"
            }
        else:
            raise RuntimeError("ZAP process not running")

    async def get_urls(self):
        """Query discovered endpoints from ZAP sitemap"""
        urls = self.zap.core.urls()
        return {
            "urls": urls,
            "count": len(urls)
        }

    async def active_scan(self, target: str, scan_policy: str = "Light"):
        """Run active scan with validation"""
        # Validate target
        self._validate_target(target)
        
        # Validate scan_policy
        valid_policies = ["Light", "Medium", "Heavy"]
        if scan_policy not in valid_policies:
            raise ValueError(
                f"Invalid scan_policy: {scan_policy}. "
                f"Must be one of {valid_policies}"
            )
        
        # Start scan
        scan_id = self.zap.ascan.scan(target, scanpolicyname=scan_policy)
        return {
            "scan_id": scan_id,
            "status": "started"
        }

    async def get_scan_status(self, scan_id: str):
        """Check scan progress"""
        progress = int(self.zap.ascan.status(scan_id))
        return {
            "scan_id": scan_id,
            "progress": progress,
            "status": "completed" if progress >= 100 else "running"
        }

    async def get_alerts(self, risk_level: str = "High"):
        """Query vulnerability findings"""
        risk_map = {
            "High": 3,
            "Medium": 2,
            "Low": 1,
            "Informational": 0
        }
        
        min_risk = risk_map.get(risk_level, 3)
        all_alerts = self.zap.core.alerts()
        
        filtered_alerts = [
            alert for alert in all_alerts
            if int(alert.get('risk', 0)) >= min_risk
        ]
        
        return {
            "alerts": filtered_alerts,
            "count": len(filtered_alerts)
        }

    async def generate_report(self, format: str = "json"):
        """Generate security report"""
        if format == "json":
            alerts = self.zap.core.alerts()
            urls = self.zap.core.urls()
            return {
                "format": "json",
                "alerts": alerts,
                "urls": urls,
                "summary": {
                    "total_alerts": len(alerts),
                    "total_urls": len(urls)
                }
            }
        elif format == "html":
            report = self.zap.core.htmlreport()
            return {"format": "html", "report": report}
        elif format == "xml":
            report = self.zap.core.xmlreport()
            return {"format": "xml", "report": report}
        else:
            raise ValueError(f"Unsupported format: {format}")

    def __del__(self):
        """Cleanup: terminate ZAP process on shutdown"""
        if hasattr(self, 'zap_process') and self.zap_process:
            print(f"[{self.name}] Terminating ZAP process...")
            self.zap_process.terminate()
            try:
                self.zap_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.zap_process.kill()


if __name__ == "__main__":
    server = ZapMCPServer(port=7008)
    server.run()
