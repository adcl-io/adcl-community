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
    
    uri = "ws://localhost:8000/ws/execute/test-session-123"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Send workflow
            await websocket.send(json.dumps({"workflow": workflow}))
            print("Workflow sent, waiting for updates...\n")
            
            # Receive updates
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if data["type"] == "log":
                        log = data["log"]
                        print(f"[{log['level'].upper()}] {log['message']}")
                    
                    elif data["type"] == "node_state":
                        print(f"Node {data['node_id']}: {data['status']}")
                    
                    elif data["type"] == "complete":
                        print("\n=== WORKFLOW COMPLETE ===")
                        result = data["result"]
                        print(f"Status: {result['status']}")
                        print(f"Nodes completed: {len(result['node_states'])}")
                        
                        # Check each result size
                        for node_id, node_result in result["results"].items():
                            result_str = json.dumps(node_result)
                            print(f"  {node_id}: {len(result_str)} bytes")
                        
                        if result['errors']:
                            print(f"Errors: {result['errors']}")
                        break
                    
                    elif data["type"] == "error":
                        print(f"\n=== ERROR ===\n{data['error']}")
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
                    
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_workflow())
