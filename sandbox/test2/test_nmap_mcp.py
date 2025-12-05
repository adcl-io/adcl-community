#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Test harness for nmap MCP server

Tests:
1. Server health check
2. Port scan (quick)
3. Service detection
4. MCP protocol compliance
"""

import asyncio
import httpx
import json
import sys

MCP_SERVER_URL = "http://localhost:6000"


async def test_health():
    """Test server health endpoint"""
    print("\n" + "=" * 70)
    print("TEST 1: Health Check")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{MCP_SERVER_URL}/health")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Health check passed")
                print(f"  Status: {data.get('status')}")
                print(f"  Service: {data.get('service')}")
                print(f"  Version: {data.get('version')}")
                return True
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ Health check error: {e}")
            return False


async def test_tools_list():
    """Test MCP tools/list method"""
    print("\n" + "=" * 70)
    print("TEST 2: List Available Tools")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            payload = {
                "method": "tools/list",
                "params": {}
            }

            response = await client.post(f"{MCP_SERVER_URL}/mcp", json=payload)

            if response.status_code == 200:
                data = response.json()

                if data.get("error"):
                    print(f"✗ MCP error: {data['error']}")
                    return False

                tools = data.get("result", {}).get("tools", [])
                print(f"✓ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
                return True
            else:
                print(f"✗ Tools list failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ Tools list error: {e}")
            return False


async def test_port_scan(target: str = "127.0.0.1"):
    """Test port scan tool"""
    print("\n" + "=" * 70)
    print(f"TEST 3: Port Scan ({target})")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            payload = {
                "method": "tools/call",
                "params": {
                    "name": "port_scan",
                    "parameters": {
                        "target": target,
                        "scan_type": "quick"
                    }
                }
            }

            print(f"Running quick port scan on {target}...")
            response = await client.post(f"{MCP_SERVER_URL}/mcp", json=payload)

            if response.status_code == 200:
                data = response.json()

                if data.get("error"):
                    print(f"✗ MCP error: {data['error']}")
                    return False

                result = data.get("result", {})
                print(f"✓ Scan completed")
                print(f"  Target: {result.get('target')}")
                print(f"  Hosts up: {result.get('hosts_up')}")
                print(f"  Ports found: {len(result.get('ports', []))}")

                # Show open ports
                open_ports = [p for p in result.get('ports', []) if p['state'] == 'open']
                if open_ports:
                    print(f"\n  Open ports:")
                    for port in open_ports[:10]:  # Show first 10
                        print(f"    {port['port']}/{port['protocol']}: {port['service']}")

                # Show findings
                findings = result.get('findings', [])
                if findings:
                    print(f"\n  Findings: {len(findings)}")
                    for finding in findings[:5]:  # Show first 5
                        print(f"    [{finding['severity']}] {finding['title']}")

                return True
            else:
                print(f"✗ Port scan failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ Port scan error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_service_detection(target: str = "127.0.0.1", ports: str = "22,80,443"):
    """Test service detection tool"""
    print("\n" + "=" * 70)
    print(f"TEST 4: Service Detection ({target}:{ports})")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            payload = {
                "method": "tools/call",
                "params": {
                    "name": "service_detection",
                    "parameters": {
                        "target": target,
                        "ports": ports
                    }
                }
            }

            print(f"Running service detection on {target} ports {ports}...")
            response = await client.post(f"{MCP_SERVER_URL}/mcp", json=payload)

            if response.status_code == 200:
                data = response.json()

                if data.get("error"):
                    print(f"✗ MCP error: {data['error']}")
                    return False

                result = data.get("result", {})
                print(f"✓ Service detection completed")
                print(f"  Target: {result.get('target')}")

                services = result.get('services', [])
                print(f"  Services found: {len(services)}")

                if services:
                    print(f"\n  Detected services:")
                    for svc in services:
                        product = svc.get('product', 'Unknown')
                        version = svc.get('version', '')
                        port = svc['port']
                        print(f"    {port}/{svc['protocol']}: {product} {version}")

                return True
            else:
                print(f"✗ Service detection failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ Service detection error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("NMAP MCP SERVER TEST HARNESS")
    print("=" * 70)
    print(f"Testing server at: {MCP_SERVER_URL}")

    # Allow custom target from command line
    target = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"

    results = []

    # Run tests
    results.append(("Health Check", await test_health()))
    results.append(("Tools List", await test_tools_list()))
    results.append(("Port Scan", await test_port_scan(target)))
    results.append(("Service Detection", await test_service_detection(target)))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
