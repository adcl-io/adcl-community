#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Test parameter substitution fix
Verifies that embedded template variables like ${node-id} are properly resolved
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.main import WorkflowEngine, MCPRegistry

def test_parameter_substitution():
    """Test the _resolve_params method with various scenarios"""

    registry = MCPRegistry()
    engine = WorkflowEngine(registry)

    # Mock previous results
    previous_results = {
        "port-scan": {
            "target": "scanme.nmap.org",
            "summary": {
                "open_ports": 2,
                "ports": ["22/tcp", "80/tcp"]
            }
        },
        "service-detection": {
            "services": [
                {"port": "22", "service": {"name": "ssh", "product": "OpenSSH", "version": "6.6.1p1"}},
                {"port": "80", "service": {"name": "http", "product": "Apache", "version": "2.4.7"}}
            ]
        }
    }

    print("=" * 60)
    print("Testing Parameter Substitution")
    print("=" * 60)

    # Test 1: Full value reference
    print("\n✅ Test 1: Full value reference")
    params1 = {"content": "${port-scan}"}
    resolved1 = engine._resolve_params(params1, previous_results)
    print(f"Input:  {params1}")
    print(f"Output: {resolved1}")
    assert resolved1["content"] == previous_results["port-scan"], "Full value reference failed!"
    print("✅ PASSED: Full value reference works")

    # Test 2: Nested path reference
    print("\n✅ Test 2: Nested path reference")
    params2 = {"content": "${port-scan.summary.open_ports}"}
    resolved2 = engine._resolve_params(params2, previous_results)
    print(f"Input:  {params2}")
    print(f"Output: {resolved2}")
    assert resolved2["content"] == 2, "Nested path reference failed!"
    print("✅ PASSED: Nested path reference works")

    # Test 3: Embedded reference (THE BUG FIX)
    print("\n✅ Test 3: Embedded reference in string")
    params3 = {"prompt": "Analyze these scan results: ${port-scan}"}
    resolved3 = engine._resolve_params(params3, previous_results)
    print(f"Input:  {params3}")
    print(f"Output: {resolved3['prompt'][:100]}...")
    assert "${port-scan}" not in resolved3["prompt"], "Embedded reference not resolved!"
    assert "scanme.nmap.org" in resolved3["prompt"], "Scan data not embedded!"
    print("✅ PASSED: Embedded reference works - template was replaced with actual data")

    # Test 4: Multiple embedded references
    print("\n✅ Test 4: Multiple embedded references")
    params4 = {
        "prompt": "Port scan: ${port-scan}\n\nServices: ${service-detection}"
    }
    resolved4 = engine._resolve_params(params4, previous_results)
    print(f"Input:  Port scan: ${{port-scan}}\\n\\nServices: ${{service-detection}}")
    print(f"Output: {resolved4['prompt'][:150]}...")
    assert "${port-scan}" not in resolved4["prompt"], "First template not resolved!"
    assert "${service-detection}" not in resolved4["prompt"], "Second template not resolved!"
    assert "scanme.nmap.org" in resolved4["prompt"], "Port scan data not embedded!"
    assert "ssh" in resolved4["prompt"], "Service data not embedded!"
    print("✅ PASSED: Multiple embedded references work")

    # Test 5: Nested path in embedded reference
    print("\n✅ Test 5: Nested path in embedded reference")
    params5 = {"prompt": "Found ${port-scan.summary.open_ports} open ports"}
    resolved5 = engine._resolve_params(params5, previous_results)
    print(f"Input:  {params5}")
    print(f"Output: {resolved5}")
    assert "Found 2 open ports" in resolved5["prompt"], "Nested path in embedded reference failed!"
    print("✅ PASSED: Nested path in embedded reference works")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("\n✅ Parameter substitution is working correctly!")
    print("✅ Agents will now receive actual scan data instead of template strings")
    print("\n📋 What this means:")
    print("   • Before: Agent received '${port-scan}'")
    print("   • After:  Agent receives actual scan data as JSON")
    print("\n🔍 Next Step: Test via WebUI")
    print("   1. Open http://localhost:3000")
    print("   2. Click '🔍 Nmap Recon' workflow")
    print("   3. Click 'Execute Workflow'")
    print("   4. Agent should now provide real security analysis!")
    print()

if __name__ == "__main__":
    try:
        test_parameter_substitution()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
