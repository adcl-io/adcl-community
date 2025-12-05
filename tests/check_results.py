# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

import asyncio
import websockets
import json

async def test_workflow():
    workflow = {
        "name": "Network Reconnaissance Workflow",
        "nodes": [
            {
                "id": "port-scan",
                "type": "mcp_call",
                "mcp_server": "nmap_recon",
                "tool": "port_scan",
                "params": {
                    "target": "scanme.nmap.org",
                    "scan_type": "quick"
                }
            },
            {
                "id": "service-detection",
                "type": "mcp_call",
                "mcp_server": "nmap_recon",
                "tool": "service_detection",
                "params": {
                    "target": "scanme.nmap.org"
                }
            },
            {
                "id": "analyze-results",
                "type": "mcp_call",
                "mcp_server": "agent",
                "tool": "think",
                "params": {
                    "prompt": "Analyze these network scan results and provide a security assessment:\n\nPort Scan: ${port-scan}\n\nService Detection: ${service-detection}\n\nProvide: 1) Summary of discovered services, 2) Potential security concerns, 3) Recommended next steps"
                }
            },
            {
                "id": "save-report",
                "type": "mcp_call",
                "mcp_server": "file_tools",
                "tool": "write_file",
                "params": {
                    "path": "recon_report.txt",
                    "content": "=== NETWORK RECONNAISSANCE REPORT ===\n\n## Port Scan Results\n${port-scan}\n\n## Service Detection Results\n${service-detection}\n\n## AI Analysis\n${analyze-results.reasoning}"
                }
            }
        ],
        "edges": [
            {"source": "port-scan", "target": "service-detection"},
            {"source": "service-detection", "target": "analyze-results"},
            {"source": "analyze-results", "target": "save-report"}
        ]
    }
    
    uri = "ws://localhost:8000/ws/execute/test-session-456"
    
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({"workflow": workflow}))
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if data["type"] == "complete":
                        result = data["result"]
                        
                        # Print each result
                        print("=== PORT SCAN RESULT ===")
                        print(json.dumps(result["results"]["port-scan"], indent=2))
                        print("\n=== SERVICE DETECTION RESULT ===")
                        print(json.dumps(result["results"]["service-detection"], indent=2))
                        print("\n=== ANALYZE RESULTS ===")
                        print(json.dumps(result["results"]["analyze-results"], indent=2))
                        print("\n=== SAVE REPORT RESULT ===")
                        print(json.dumps(result["results"]["save-report"], indent=2))
                        break
                    
                    elif data["type"] == "error":
                        print(f"Error: {data['error']}")
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    break
                    
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_workflow())
