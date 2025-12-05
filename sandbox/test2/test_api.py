#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Simple test script for API endpoints
Run this after starting the API server
"""

import requests
import json
from uuid import UUID

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200
    print("  ✓ Health check passed\n")


def test_create_campaign():
    """Test creating a campaign"""
    print("Testing POST /campaigns endpoint...")

    campaign_data = {
        "name": "Test Recon Campaign",
        "target": "192.168.1.0/24",
        "mode": "sequential",
        "team": [
            {
                "persona": "methodical_recon",
                "count": 1,
                "config": {
                    "system_prompt": "You are a thorough reconnaissance specialist. Map the network methodically.",
                    "mcp_servers": ["nmap"],
                    "llm_model": "claude-sonnet-4",
                    "temperature": 0.3,
                    "max_tasks": 10,
                    "timeout_minutes": 30
                }
            }
        ],
        "safety": {
            "require_approval_for": [],
            "max_concurrent_agents": 5,
            "global_timeout_hours": 8
        }
    }

    response = requests.post(
        f"{BASE_URL}/campaigns",
        json=campaign_data,
        headers={"Content-Type": "application/json"}
    )

    print(f"  Status: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 201

    campaign = response.json()
    campaign_id = campaign["id"]
    print(f"  ✓ Campaign created with ID: {campaign_id}\n")

    return campaign_id


def test_get_campaign(campaign_id):
    """Test getting campaign details"""
    print(f"Testing GET /campaigns/{campaign_id} endpoint...")

    response = requests.get(f"{BASE_URL}/campaigns/{campaign_id}")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("  ✓ Campaign retrieved successfully\n")


def test_list_campaigns():
    """Test listing campaigns"""
    print("Testing GET /campaigns endpoint...")

    response = requests.get(f"{BASE_URL}/campaigns")
    print(f"  Status: {response.status_code}")
    campaigns = response.json()
    print(f"  Found {len(campaigns)} campaign(s)")
    assert response.status_code == 200
    print("  ✓ Campaigns listed successfully\n")


def test_list_agents():
    """Test listing agents"""
    print("Testing GET /agents endpoint...")

    response = requests.get(f"{BASE_URL}/agents")
    print(f"  Status: {response.status_code}")
    agents = response.json()
    print(f"  Found {len(agents)} agent(s)")
    assert response.status_code == 200
    print("  ✓ Agents listed successfully\n")


def test_list_findings():
    """Test listing findings"""
    print("Testing GET /findings endpoint...")

    response = requests.get(f"{BASE_URL}/findings")
    print(f"  Status: {response.status_code}")
    findings = response.json()
    print(f"  Found {len(findings)} finding(s)")
    assert response.status_code == 200
    print("  ✓ Findings listed successfully\n")


def main():
    """Run all tests"""
    print("=" * 60)
    print("API Endpoint Tests")
    print("=" * 60 + "\n")

    try:
        # Test health
        test_health()

        # Test campaign creation
        campaign_id = test_create_campaign()

        # Test campaign retrieval
        test_get_campaign(campaign_id)

        # Test listing
        test_list_campaigns()
        test_list_agents()
        test_list_findings()

        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        print("   Make sure the server is running on http://localhost:8000")
        print("   Run: uvicorn api.main:app --reload")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
