#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Run a real campaign against target network
"""

import asyncio
import sys
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

# Campaign configuration
CAMPAIGN_CONFIG = {
    "name": "Live Network Scan - 192.168.50.0/24",
    "target": "192.168.50.0/24",
    "mode": "sequential",
    "team": [
        {
            "persona": "methodical_recon",
            "count": 1,
            "config": {
                "system_prompt": "You are a thorough reconnaissance specialist. Scan the target network and identify all active hosts, open ports, and running services. Document everything you find.",
                "mcp_servers": ["nmap"],
                "llm_model": "claude-sonnet-4",
                "temperature": 0.3,
                "max_tasks": 20,
                "timeout_minutes": 30
            }
        }
    ],
    "safety": {
        "require_approval_for": [],
        "max_concurrent_agents": 3,
        "global_timeout_hours": 2
    }
}


async def create_campaign():
    """Create a new campaign"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Creating campaign: {CAMPAIGN_CONFIG['name']}")
        print(f"Target: {CAMPAIGN_CONFIG['target']}")
        print()

        response = await client.post(
            f"{API_BASE}/campaigns",
            json=CAMPAIGN_CONFIG
        )

        if response.status_code != 201:
            print(f"Error creating campaign: {response.status_code}")
            print(response.text)
            return None

        campaign = response.json()
        campaign_id = campaign['id']

        print(f"✓ Campaign created: {campaign_id}")
        print(f"  Status: {campaign['status']}")
        print(f"  Created: {campaign['created_at']}")
        print()

        return campaign_id


async def start_campaign_orchestrator(campaign_id: str):
    """Start the orchestrator to launch agents"""
    print(f"Starting orchestrator for campaign {campaign_id}...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(f"{API_BASE}/campaigns/{campaign_id}/start")

            if response.status_code != 200:
                print(f"Error starting campaign: {response.status_code}")
                print(response.text)
                return False

            print(f"✓ Orchestrator started")
            print()
        except Exception as e:
            print(f"Error starting orchestrator: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True


async def monitor_campaign(campaign_id: str):
    """Monitor campaign progress"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("=" * 70)
        print("MONITORING CAMPAIGN")
        print("=" * 70)
        print("Press Ctrl+C to stop monitoring (campaign will continue)\n")

        last_agent_count = 0
        last_finding_count = 0

        try:
            while True:
                # Get campaign status
                response = await client.get(f"{API_BASE}/campaigns/{campaign_id}")
                if response.status_code == 200:
                    campaign = response.json()
                    status = campaign['status']

                    print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Campaign Status: {status}", end="", flush=True)

                    # Get agents
                    agents_resp = await client.get(f"{API_BASE}/campaigns/{campaign_id}/agents")
                    if agents_resp.status_code == 200:
                        agents = agents_resp.json()
                        if len(agents) != last_agent_count:
                            print()  # New line for agent update
                            for agent in agents:
                                print(f"  Agent {agent['persona']}: {agent['status']} (tasks: {agent['tasks_completed']})")
                            last_agent_count = len(agents)

                    # Get findings
                    findings_resp = await client.get(f"{API_BASE}/campaigns/{campaign_id}/findings")
                    if findings_resp.status_code == 200:
                        findings = findings_resp.json()
                        if len(findings) != last_finding_count:
                            print()  # New line for finding update
                            for finding in findings[last_finding_count:]:
                                print(f"  🎯 FINDING: [{finding['severity']}] {finding['title']}")
                                print(f"     Target: {finding['target_host']}:{finding.get('target_port', 'N/A')}")
                                print(f"     {finding['description'][:100]}...")
                            last_finding_count = len(findings)

                    # Check if campaign completed
                    if status in ['completed', 'failed', 'cancelled']:
                        print("\n")
                        print("=" * 70)
                        print(f"Campaign {status.upper()}")
                        print("=" * 70)

                        # Show final summary
                        if last_finding_count > 0:
                            print(f"\nTotal Findings: {last_finding_count}")
                            print("\nFindings Summary:")
                            for finding in findings:
                                print(f"  • [{finding['severity'].upper()}] {finding['title']}")
                                print(f"    {finding['target_host']}:{finding.get('target_port', 'N/A')}")
                        else:
                            print("\nNo vulnerabilities found.")

                        break

                await asyncio.sleep(2)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped (campaign continues in background)")
            print(f"To check status: curl {API_BASE}/campaigns/{campaign_id}")
            print(f"To view findings: curl {API_BASE}/campaigns/{campaign_id}/findings")


async def main():
    """Main execution"""
    print()
    print("=" * 70)
    print("AI RED TEAM - LIVE CAMPAIGN")
    print("=" * 70)
    print()

    # Create campaign
    campaign_id = await create_campaign()
    if not campaign_id:
        print("Failed to create campaign")
        return 1

    # Start orchestrator
    success = await start_campaign_orchestrator(campaign_id)
    if not success:
        print("Failed to start orchestrator")
        return 1

    # Monitor progress
    await monitor_campaign(campaign_id)

    print()
    print("Campaign URL:", f"{API_BASE}/campaigns/{campaign_id}")
    print("Findings URL:", f"{API_BASE}/campaigns/{campaign_id}/findings")
    print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
