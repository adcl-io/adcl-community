#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Integration test: Agent + Real nmap MCP server

Tests that agents can successfully call the real nmap MCP server
"""

import asyncio
import sys
import httpx

# Simple MCP client for testing
class SimpleMCPClient:
    """Simple MCP client that talks to MCP server via HTTP"""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.client = None

    async def connect(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(timeout=120.0)

    async def call_tool(self, tool_name: str, parameters: dict) -> dict:
        """Call a tool via MCP protocol"""
        if not self.client:
            await self.connect()

        payload = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "parameters": parameters
            }
        }

        response = await self.client.post(f"{self.server_url}/mcp", json=payload)

        if response.status_code != 200:
            raise Exception(f"MCP call failed: {response.status_code}")

        data = response.json()

        if data.get("error"):
            raise Exception(f"MCP error: {data['error']}")

        return data.get("result", {})

    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()


async def test_agent_nmap_integration():
    """Test that agent can use real nmap MCP server"""

    print("\n" + "=" * 70)
    print("AGENT + NMAP MCP INTEGRATION TEST")
    print("=" * 70)

    # Create MCP client
    nmap_client = SimpleMCPClient("http://localhost:6000")
    await nmap_client.connect()

    try:
        # Test 1: Quick port scan
        print("\n[Agent] Task: Scan localhost for open ports")
        print("[Agent] Calling nmap MCP server...")

        result = await nmap_client.call_tool("port_scan", {
            "target": "127.0.0.1",
            "scan_type": "quick"
        })

        print(f"[Agent] ✓ Scan completed")
        print(f"[Agent]   Hosts up: {result.get('hosts_up')}")
        print(f"[Agent]   Ports scanned: {len(result.get('ports', []))}")

        open_ports = [p for p in result.get('ports', []) if p['state'] == 'open']
        print(f"[Agent]   Open ports: {len(open_ports)}")

        if open_ports:
            print(f"[Agent]   Discovered services:")
            for port in open_ports[:5]:
                print(f"[Agent]     - {port['port']}/{port['protocol']}: {port['service']}")

        # Test 2: Process findings
        findings = result.get('findings', [])
        print(f"\n[Agent] Processing {len(findings)} findings...")

        for finding in findings[:3]:
            print(f"[Agent]   [{finding['severity']}] {finding['title']}")
            print(f"[Agent]      {finding['description']}")

        # Test 3: Service detection on a specific port
        if open_ports:
            test_port = open_ports[0]['port']
            print(f"\n[Agent] Task: Detect service on port {test_port}")
            print(f"[Agent] Calling service_detection...")

            result2 = await nmap_client.call_tool("service_detection", {
                "target": "127.0.0.1",
                "ports": str(test_port)
            })

            print(f"[Agent] ✓ Service detection completed")
            services = result2.get('services', [])

            if services:
                svc = services[0]
                product = svc.get('product', 'Unknown')
                version = svc.get('version', '')
                print(f"[Agent]   Detected: {product} {version}")

        print("\n" + "=" * 70)
        print("✓ INTEGRATION TEST PASSED")
        print("=" * 70)
        print("\nAgent successfully:")
        print("  1. Connected to nmap MCP server")
        print("  2. Executed port scan")
        print("  3. Processed findings")
        print("  4. Performed service detection")
        print("\n✅ Ready for full campaign integration!")

        return 0

    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await nmap_client.close()


if __name__ == "__main__":
    exit_code = asyncio.run(test_agent_nmap_integration())
    sys.exit(exit_code)
