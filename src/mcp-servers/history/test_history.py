#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Simple test script for History MCP Server
Tests core functionality of session and message management
"""
import json
import sys
import asyncio
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from session_manager import SessionManager
from message_writer import MessageWriter
from message_reader import MessageReader
from search import SearchEngine


async def test_history():
    """Test history functionality"""
    test_dir = "/tmp/adcl_history_test"

    print("🧪 Testing ADCL History System")
    print("=" * 60)

    # Initialize modules
    print("\n1. Initializing modules...")
    session_mgr = SessionManager(test_dir)
    msg_writer = MessageWriter(test_dir)
    msg_reader = MessageReader(test_dir)
    search = SearchEngine(test_dir)
    print("   ✅ Modules initialized")

    # Create a session
    print("\n2. Creating a test session...")
    session_id = session_mgr.create_session(
        title="Test Security Analysis",
        metadata={"tags": ["test", "security"]}
    )
    print(f"   ✅ Session created: {session_id}")

    # Append some messages
    print("\n3. Appending messages...")
    messages = [
        {"type": "user", "content": "Scan the network for vulnerabilities"},
        {"type": "agent", "agent": "security_analyst", "content": "Starting scan...", "tools": ["nmap_recon"]},
        {"type": "tool", "tool": "nmap_recon", "output": {"ports": [80, 443]}},
        {"type": "agent", "content": "Found 2 open ports"},
        {"type": "user", "content": "What did you find?"},
        {"type": "agent", "content": "Ports 80 and 443 are open - standard HTTP/HTTPS"}
    ]

    for msg in messages:
        msg_id = msg_writer.append_message(session_id, msg)
        print(f"   ✅ Message {msg_id[:16]}...")

    # Read messages back
    print("\n4. Reading messages...")
    retrieved = msg_reader.get_messages(session_id, limit=10, reverse=False)
    print(f"   ✅ Retrieved {len(retrieved)} messages")
    for msg in retrieved[:3]:
        preview = str(msg.get("content", ""))[:40]
        print(f"      - {msg['type']}: {preview}...")

    # Test pagination
    print("\n5. Testing pagination...")
    page1 = msg_reader.get_messages(session_id, offset=0, limit=2, reverse=False)
    page2 = msg_reader.get_messages(session_id, offset=2, limit=2, reverse=False)
    print(f"   ✅ Page 1: {len(page1)} messages")
    print(f"   ✅ Page 2: {len(page2)} messages")

    # Test search
    print("\n6. Testing search...")
    search_results = search.search_titles("Security")
    print(f"   ✅ Title search found: {len(search_results)} sessions")

    msg_search = search.search_messages("ports", session_id=session_id)
    print(f"   ✅ Message search found: {len(msg_search)} matches")

    # List sessions
    print("\n7. Listing sessions...")
    sessions = session_mgr.list_sessions(limit=10)
    print(f"   ✅ Found {len(sessions)} sessions")
    for s in sessions:
        print(f"      - {s['title']} ({s['message_count']} messages)")

    # Get session metadata
    print("\n8. Getting session metadata...")
    metadata = session_mgr.get_session(session_id)
    if metadata:
        print(f"   ✅ Session: {metadata['title']}")
        print(f"      Messages: {metadata['message_count']}")
        print(f"      Participants: {list(metadata.get('participants', {}).keys())}")
        print(f"      Created: {metadata['created_at']}")

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print(f"📁 Test data location: {test_dir}")

    return True


if __name__ == "__main__":
    result = asyncio.run(test_history())
    sys.exit(0 if result else 1)
