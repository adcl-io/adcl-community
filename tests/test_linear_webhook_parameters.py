# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Tests for Linear webhook parameter extraction"""
import pytest
import sys
import os

# Add triggers directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'triggers', 'webhook'))

from linear_webhook_trigger import extract_parameters


class TestAgentSessionParameterExtraction:
    """Test parameter extraction for agentSession events"""
    
    def test_created_event_basic(self):
        """Test extraction of basic created event parameters"""
        payload = {
            "type": "agentSession",
            "action": "created",
            "agentSession": {
                "id": "session-123",
                "issueId": "issue-456",
                "state": "pending",
                "createdAt": "2025-11-20T23:00:00Z",
                "updatedAt": "2025-11-20T23:00:00Z"
            }
        }
        
        params = extract_parameters(payload, "agentSession")
        
        assert params["linear_event"] == "agentSession"
        assert params["action"] == "created"
        assert params["session_id"] == "session-123"
        assert params["issue_id"] == "issue-456"
        assert params["state"] == "pending"
        assert params["created_at"] == "2025-11-20T23:00:00Z"
        assert params["updated_at"] == "2025-11-20T23:00:00Z"
        assert "prompt" not in params  # No prompt for created events
    
    def test_created_event_with_guidance(self):
        """Test extraction with guidance field"""
        payload = {
            "type": "agentSession",
            "action": "created",
            "agentSession": {
                "id": "session-123",
                "issueId": "issue-456"
            },
            "guidance": ["Be thorough", "Consider edge cases"]
        }
        
        params = extract_parameters(payload, "agentSession")
        
        assert params["guidance"] == ["Be thorough", "Consider edge cases"]
    
    def test_created_event_with_previous_comments(self):
        """Test extraction with previousComments field"""
        payload = {
            "type": "agentSession",
            "action": "created",
            "agentSession": {
                "id": "session-123",
                "issueId": "issue-456"
            },
            "previousComments": [
                {"text": "Initial analysis", "author": "user1"},
                {"text": "Follow-up", "author": "user2"}
            ]
        }
        
        params = extract_parameters(payload, "agentSession")
        
        assert len(params["previousComments"]) == 2
        assert params["previousComments"][0]["text"] == "Initial analysis"
    
    def test_prompted_event_with_dict_content(self):
        """Test extraction of prompted event with dict content"""
        payload = {
            "type": "agentSession",
            "action": "prompted",
            "agentSession": {
                "id": "session-789",
                "issueId": "issue-101",
                "state": "active"
            },
            "agentActivity": {
                "content": {
                    "body": "Can you add more details about the implementation?"
                }
            }
        }
        
        params = extract_parameters(payload, "agentSession")
        
        assert params["action"] == "prompted"
        assert params["session_id"] == "session-789"
        assert params["prompt"] == "Can you add more details about the implementation?"
    
    def test_prompted_event_with_string_content(self):
        """Test extraction of prompted event with string content"""
        payload = {
            "type": "agentSession",
            "action": "prompted",
            "agentSession": {
                "id": "session-999",
                "issueId": "issue-202"
            },
            "agentActivity": {
                "content": "Simple string prompt"
            }
        }
        
        params = extract_parameters(payload, "agentSession")
        
        assert params["prompt"] == "Simple string prompt"
    
    def test_prompted_event_with_empty_content(self):
        """Test extraction with empty content"""
        payload = {
            "type": "agentSession",
            "action": "prompted",
            "agentSession": {
                "id": "session-empty",
                "issueId": "issue-303"
            },
            "agentActivity": {
                "content": {}
            }
        }
        
        params = extract_parameters(payload, "agentSession")
        
        assert params["prompt"] == ""
    
    def test_prompted_event_missing_activity(self):
        """Test extraction when agentActivity is missing"""
        payload = {
            "type": "agentSession",
            "action": "prompted",
            "agentSession": {
                "id": "session-missing",
                "issueId": "issue-404"
            }
        }
        
        params = extract_parameters(payload, "agentSession")
        
        # Should not crash, prompt should be empty
        assert params["prompt"] == ""
    
    def test_prompted_event_with_all_context(self):
        """Test extraction with all optional context fields"""
        payload = {
            "type": "agentSession",
            "action": "prompted",
            "agentSession": {
                "id": "session-full",
                "issueId": "issue-505",
                "state": "active"
            },
            "agentActivity": {
                "content": {
                    "body": "What about security?"
                }
            },
            "guidance": ["Focus on security"],
            "previousComments": [{"text": "Initial plan"}]
        }
        
        params = extract_parameters(payload, "agentSession")
        
        assert params["prompt"] == "What about security?"
        assert params["guidance"] == ["Focus on security"]
        assert params["previousComments"] == [{"text": "Initial plan"}]


class TestIssueParameterExtraction:
    """Test parameter extraction for issue events"""
    
    def test_issue_event(self):
        """Test extraction of issue event parameters"""
        payload = {
            "type": "issue",
            "action": "updated",
            "data": {
                "id": "issue-123",
                "title": "Fix bug in login",
                "state": {"name": "In Progress"},
                "assignee": {"name": "John Doe"}
            }
        }
        
        params = extract_parameters(payload, "issue")
        
        assert params["linear_event"] == "issue"
        assert params["action"] == "updated"
        assert params["issue_id"] == "issue-123"
        assert params["issue_title"] == "Fix bug in login"
        assert params["issue_state"] == "In Progress"
        assert params["assignee"] == "John Doe"


class TestGenericParameterExtraction:
    """Test parameter extraction for other event types"""
    
    def test_generic_event(self):
        """Test extraction of generic event parameters"""
        payload = {
            "type": "comment",
            "action": "created",
            "data": {
                "id": "comment-789"
            }
        }
        
        params = extract_parameters(payload, "comment")
        
        assert params["linear_event"] == "comment"
        assert params["action"] == "created"
        assert params["data_id"] == "comment-789"
