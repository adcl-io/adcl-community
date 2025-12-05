# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

import asyncio
import websockets
import json

async def test_agent_workflow():
    workflow = {
        "name": "Test Agent Workflow",
        "nodes": [
            {
                "id": "test-think",
                "type": "mcp_call",
                "mcp_server": "agent",
                "tool": "think",
                "params": {
                    "prompt": "Analyze the following network scan data:\n\nPort 22: SSH OpenSSH 6.6.1\nPort 80: HTTP Apache 2.4.7\n\nProvide a brief security assessment."
                }
            }
        ],
        "edges": []
    }
    
    uri = "ws://localhost:8000/ws/execute/test-agent-789"
    
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({"workflow": workflow}))
            print("Workflow sent, monitoring messages...\n")
            
            message_count = 0
            while True:
                try:
                    message = await websocket.recv()
                    message_count += 1
                    
                    print(f"\n=== MESSAGE {message_count} ===")
                    print(f"Size: {len(message)} bytes")
                    
                    data = json.loads(message)
                    print(f"Type: {data['type']}")
                    
                    if data["type"] == "complete":
                        result = data["result"]
                        
                        # Check the agent result specifically
                        if "test-think" in result["results"]:
                            agent_result = result["results"]["test-think"]
                            print("\n=== AGENT RESULT ===")
                            print(json.dumps(agent_result, indent=2))
                            
                            # Check if reasoning field exists and its length
                            if "reasoning" in agent_result:
                                print(f"\nReasoning length: {len(agent_result['reasoning'])} chars")
                                print(f"First 200 chars: {agent_result['reasoning'][:200]}")
                        break
                    
                    elif data["type"] == "error":
                        print(f"Error: {data['error']}")
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    print(f"Raw message: {message[:500]}")
                    break
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_agent_workflow())
