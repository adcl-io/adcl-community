# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit Tests for Workflow Parameter Substitution

Tests the critical ${params.X} syntax that was fixed in PRD-103.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.workflow_engine import ExecutionContext


def test_params_in_execution_context():
    """Test ${params.X} variables are available in ExecutionContext"""
    ctx = ExecutionContext(
        execution_id="test-123",
        workflow_name="test-workflow",
        params={"user_id": "123", "action": "test"}
    )
    
    # Critical: params must be in variables for ${params.X} syntax
    assert "params" in ctx.variables
    assert ctx.variables["params"]["user_id"] == "123"
    assert ctx.variables["params"]["action"] == "test"


def test_params_not_input():
    """Test that params are NOT stored as 'input' (the bug we fixed)"""
    ctx = ExecutionContext(
        execution_id="test-456",
        workflow_name="test-workflow",
        params={"test_value": "hello"}
    )
    
    # The bug: engine was using variables['input']
    # The fix: engine now uses variables['params']
    assert "params" in ctx.variables
    assert "input" not in ctx.variables  # Should NOT exist


def test_multiple_params():
    """Test multiple parameter values"""
    ctx = ExecutionContext(
        execution_id="test-789",
        workflow_name="test-workflow",
        params={
            "session_id": "sess-123",
            "issue_id": "TES-3",
            "user": "test-user"
        }
    )
    
    assert ctx.variables["params"]["session_id"] == "sess-123"
    assert ctx.variables["params"]["issue_id"] == "TES-3"
    assert ctx.variables["params"]["user"] == "test-user"
