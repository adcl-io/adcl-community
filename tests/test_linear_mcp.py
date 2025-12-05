# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for Linear MCP Server
Tests OAuth manager and Linear client functionality
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add mcp_servers to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp_servers', 'linear'))

from oauth_manager import LinearOAuthManager, OAuthToken
from linear_client import LinearClient, AgentActivity, ActivityType
from exceptions import LinearConfigError, LinearAuthError, LinearValidationError


class TestOAuthManager:
    """Test OAuth token management"""

    @patch.dict(os.environ, {'LINEAR_CLIENT_ID': 'test_id', 'LINEAR_CLIENT_SECRET': 'test_secret'})
    def test_oauth_manager_initialization(self):
        """Test OAuth manager initializes with credentials"""
        manager = LinearOAuthManager()
        assert manager.client_id == 'test_id'
        assert manager.client_secret == 'test_secret'
        assert manager.token_url == 'https://api.linear.app/oauth/token'

    @patch.dict(os.environ, {}, clear=True)
    def test_oauth_manager_missing_credentials(self):
        """Test OAuth manager raises error without credentials"""
        with pytest.raises(LinearConfigError, match="LINEAR_CLIENT_ID and LINEAR_CLIENT_SECRET"):
            LinearOAuthManager()

    def test_oauth_token_expiry(self):
        """Test OAuth token expiry calculation"""
        token = OAuthToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            scope="read write",
            created_at=datetime.now()
        )
        
        assert not token.is_expired
        assert not token.needs_refresh
        
        # Token near expiry
        token.created_at = datetime.now() - timedelta(seconds=3300)  # 55 minutes ago
        assert not token.is_expired
        assert token.needs_refresh  # Less than 5 minutes remaining

    @patch('oauth_manager.requests.post')
    @patch.dict(os.environ, {'LINEAR_CLIENT_ID': 'test_id', 'LINEAR_CLIENT_SECRET': 'test_secret'})
    def test_get_client_credentials_token_success(self, mock_post):
        """Test successful token acquisition"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'token_type': 'Bearer',
            'expires_in': 86400,
            'scope': 'read write'
        }
        mock_post.return_value = mock_response

        manager = LinearOAuthManager()
        token = manager.get_client_credentials_token()

        assert token.access_token == 'test_access_token'
        assert token.token_type == 'Bearer'
        assert token.expires_in == 86400
        mock_post.assert_called_once()

    @patch('oauth_manager.requests.post')
    @patch.dict(os.environ, {'LINEAR_CLIENT_ID': 'test_id', 'LINEAR_CLIENT_SECRET': 'test_secret'})
    def test_get_client_credentials_token_cached(self, mock_post):
        """Test token is cached and not re-requested"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'token_type': 'Bearer',
            'expires_in': 86400,
            'scope': 'read write'
        }
        mock_post.return_value = mock_response

        manager = LinearOAuthManager()
        token1 = manager.get_client_credentials_token()
        token2 = manager.get_client_credentials_token()

        assert token1 == token2
        mock_post.assert_called_once()  # Only called once

    @patch('oauth_manager.requests.post')
    @patch.dict(os.environ, {'LINEAR_CLIENT_ID': 'test_id', 'LINEAR_CLIENT_SECRET': 'test_secret'})
    def test_get_client_credentials_token_retry(self, mock_post):
        """Test retry logic on server errors"""
        # First call fails with 502, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 502
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'access_token': 'test_access_token',
            'token_type': 'Bearer',
            'expires_in': 86400,
            'scope': 'read write'
        }
        
        mock_post.side_effect = [mock_response_fail, mock_response_success]

        manager = LinearOAuthManager()
        token = manager.get_client_credentials_token()

        assert token.access_token == 'test_access_token'
        assert mock_post.call_count == 2

    @patch('oauth_manager.requests.post')
    @patch.dict(os.environ, {'LINEAR_CLIENT_ID': 'test_id', 'LINEAR_CLIENT_SECRET': 'test_secret'})
    def test_get_authorization_headers(self, mock_post):
        """Test authorization headers generation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'token_type': 'Bearer',
            'expires_in': 86400,
            'scope': 'read write'
        }
        mock_post.return_value = mock_response

        manager = LinearOAuthManager()
        headers = manager.get_authorization_headers()

        assert headers['Authorization'] == 'Bearer test_access_token'
        assert headers['Content-Type'] == 'application/json'


class TestLinearClient:
    """Test Linear API client"""

    @patch.dict(os.environ, {'LINEAR_CLIENT_ID': 'test_id', 'LINEAR_CLIENT_SECRET': 'test_secret'})
    @patch('linear_client.LinearOAuthManager')
    def test_linear_client_initialization_oauth(self, mock_oauth_manager):
        """Test Linear client initializes with OAuth"""
        mock_manager = Mock()
        mock_manager.get_authorization_headers.return_value = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }
        mock_oauth_manager.return_value = mock_manager

        client = LinearClient()
        assert client.oauth_manager is not None
        assert client.base_url == 'https://api.linear.app/graphql'

    def test_linear_client_initialization_token(self):
        """Test Linear client initializes with direct token"""
        client = LinearClient(access_token='direct_token')
        assert client.oauth_manager is None
        assert client.headers['Authorization'] == 'Bearer direct_token'

    @patch.dict(os.environ, {}, clear=True)
    def test_linear_client_missing_credentials(self):
        """Test Linear client raises error without credentials"""
        with pytest.raises(LinearConfigError, match="LINEAR_CLIENT_ID and LINEAR_CLIENT_SECRET required"):
            LinearClient()

    def test_agent_activity_validation_action_type(self):
        """Test ACTION activity requires action and parameter"""
        with pytest.raises(LinearValidationError, match="ACTION activities must have a non-empty 'action' field"):
            AgentActivity(
                type=ActivityType.ACTION,
                content="test content"
                # Missing action and parameter
            )

    def test_agent_activity_validation_thought_type(self):
        """Test THOUGHT activity doesn't require action/parameter"""
        activity = AgentActivity(
            type=ActivityType.THOUGHT,
            content="thinking about the problem"
        )
        assert activity.type == ActivityType.THOUGHT
        assert activity.content == "thinking about the problem"

    @patch('linear_client.requests.post')
    @patch.dict(os.environ, {'LINEAR_CLIENT_ID': 'test_id', 'LINEAR_CLIENT_SECRET': 'test_secret'})
    @patch('linear_client.LinearOAuthManager')
    def test_get_issue_success(self, mock_oauth_manager, mock_post):
        """Test successful issue retrieval"""
        mock_manager = Mock()
        mock_manager.get_authorization_headers.return_value = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }
        mock_oauth_manager.return_value = mock_manager

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'issue': {
                    'id': 'issue-123',
                    'title': 'Test Issue',
                    'description': 'Test description',
                    'state': {'name': 'In Progress', 'type': 'started'},
                    'assignee': None,
                    'team': {'id': 'team-1', 'name': 'Engineering', 'key': 'ENG'},
                    'priority': 2,
                    'labels': {'nodes': []},
                    'url': 'https://linear.app/test/issue/TEST-123'
                }
            }
        }
        mock_post.return_value = mock_response

        client = LinearClient()
        issue = client.get_issue('issue-123')

        assert issue.id == 'issue-123'
        assert issue.title == 'Test Issue'
        assert issue.state == 'In Progress'
        mock_post.assert_called_once()

    @patch('linear_client.requests.post')
    @patch.dict(os.environ, {'LINEAR_CLIENT_ID': 'test_id', 'LINEAR_CLIENT_SECRET': 'test_secret'})
    @patch('linear_client.LinearOAuthManager')
    def test_execute_query_error_handling(self, mock_oauth_manager, mock_post):
        """Test GraphQL error handling"""
        mock_manager = Mock()
        mock_manager.get_authorization_headers.return_value = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }
        mock_oauth_manager.return_value = mock_manager

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'errors': [{'message': 'Invalid query'}]
        }
        mock_post.return_value = mock_response

        client = LinearClient()
        
        with pytest.raises(Exception, match="GraphQL errors"):
            client._execute_query("query { invalid }", {})


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
