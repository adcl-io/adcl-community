# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Linear API Client

Provides GraphQL operations for Linear API integration.
Handles issue management, agent activities, comments, and workflow states.
"""
import os
import logging
import requests
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel
from dotenv import load_dotenv

from oauth_manager import LinearOAuthManager
from exceptions import LinearConfigError, LinearAPIError, LinearValidationError

load_dotenv()

# Configure logger
logger = logging.getLogger("linear.client")
logger.setLevel(logging.INFO)

class AgentSessionState(str, Enum):
    """Linear agent session states."""
    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"
    AWAITING_INPUT = "awaitingInput"
    COMPLETE = "complete"


class ActivityType(str, Enum):
    """Types of agent activities in Linear."""
    THOUGHT = "thought"
    ELICITATION = "elicitation"
    ACTION = "action"
    RESPONSE = "response"
    ERROR = "error"

class LinearIssue(BaseModel):
    """
    Linear issue data model.
    
    Attributes:
        id: Issue unique identifier
        title: Issue title
        description: Issue description (optional)
        state: Current workflow state
        assignee: Assigned user (optional)
        team: Team information
        priority: Priority level (optional)
        labels: List of labels
        url: Issue URL
    """
    id: str
    title: str
    description: Optional[str]
    state: str
    assignee: Optional[Dict]
    team: Dict
    priority: Optional[int]
    labels: List[Dict]
    url: str


class AgentActivity(BaseModel):
    """
    Agent activity data model.
    
    Attributes:
        type: Activity type (thought, action, response, etc.)
        content: Activity content/description
        action: Action name (required for ACTION type)
        parameter: Action parameter (required for ACTION type)
        result: Action result (optional)
        metadata: Additional metadata (optional)
    """
    type: ActivityType
    content: str
    action: Optional[str] = None
    parameter: Optional[str] = None
    result: Optional[str] = None
    metadata: Optional[Dict] = None

    def model_post_init(self, __context) -> None:
        """
        Validate that ACTION activities have required fields.
        
        Raises:
            LinearValidationError: If ACTION activity missing action or parameter
        """
        if self.type == ActivityType.ACTION:
            if not self.action:
                raise LinearValidationError(
                    "ACTION activities must have a non-empty 'action' field"
                )
            if not self.parameter:
                raise LinearValidationError(
                    "ACTION activities must have a non-empty 'parameter' field"
                )

class LinearClient:
    """
    Linear API GraphQL client.
    
    Provides methods for issue management, agent activities, comments,
    and workflow state operations via Linear's GraphQL API.
    """
    
    def __init__(self, access_token: Optional[str] = None) -> None:
        """
        Initialize Linear client with OAuth access token.
        
        Linear agents MUST use OAuth 2.0 application credentials.
        
        Args:
            access_token: Direct access token (optional, uses OAuth if not provided)
            
        Raises:
            LinearConfigError: If neither access_token nor OAuth credentials provided
        """
        self.base_url = "https://api.linear.app/graphql"

        if access_token:
            self.oauth_manager = None
            self.headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            logger.info("LinearClient initialized with direct access token")
        elif os.getenv("LINEAR_CLIENT_ID") and os.getenv("LINEAR_CLIENT_SECRET"):
            self.oauth_manager = LinearOAuthManager()
            self.headers = self.oauth_manager.get_authorization_headers()
            logger.info("LinearClient initialized with OAuth")
        else:
            raise LinearConfigError(
                "LINEAR_CLIENT_ID and LINEAR_CLIENT_SECRET required"
            )

    def _get_headers(self) -> Dict[str, str]:
        """
        Get current authorization headers, refreshing OAuth token if needed.
        
        Returns:
            Dictionary with Authorization and Content-Type headers
        """
        if self.oauth_manager:
            return self.oauth_manager.get_authorization_headers()
        return self.headers

    def get_issue(self, issue_id: str) -> LinearIssue:
        """
        Get a specific Linear issue by ID.
        
        Args:
            issue_id: Linear issue identifier
            
        Returns:
            LinearIssue object with issue data
            
        Raises:
            LinearAPIError: If API request fails
        """
        query = """
        query GetIssue($id: String!) {
            issue(id: $id) {
                id
                title
                description
                state {
                    name
                    type
                }
                assignee {
                    id
                    name
                    email
                }
                team {
                    id
                    name
                    key
                }
                priority
                labels {
                    nodes {
                        id
                        name
                        color
                    }
                }
                url
            }
        }
        """

        response = self._execute_query(query, {"id": issue_id})
        issue_data = response["data"]["issue"]

        return LinearIssue(
            id=issue_data["id"],
            title=issue_data["title"],
            description=issue_data.get("description"),
            state=issue_data["state"]["name"],
            assignee=issue_data.get("assignee"),
            team=issue_data["team"],
            priority=issue_data.get("priority"),
            labels=[label for label in issue_data["labels"]["nodes"]],
            url=issue_data["url"]
        )

    def create_agent_activity(self, session_id: str, activity: AgentActivity) -> Dict:
        """
        Create an agent activity for a session.
        
        Args:
            session_id: Agent session identifier
            activity: AgentActivity object with type, content, and optional fields
            
        Returns:
            Dictionary with success status and activity data
            
        Raises:
            LinearAPIError: If API request fails
            LinearValidationError: If activity validation fails
        """
        logger.debug(f"Creating agent activity: session={session_id}, type={activity.type.value}")
        mutation = """
        mutation CreateAgentActivity($agentSessionId: String!, $content: JSONObject!) {
            agentActivityCreate(input: {
                agentSessionId: $agentSessionId
                content: $content
            }) {
                success
                agentActivity {
                    id
                    createdAt
                }
            }
        }
        """

        # Build content object based on activity type
        if activity.type == ActivityType.ACTION:
            action_value = activity.action if activity.action else "analyze"
            parameter_value = activity.parameter if activity.parameter else (activity.content if activity.content else "default")

            content_obj = {
                "type": activity.type.value,
                "action": action_value,
                "parameter": parameter_value
            }
            logger.debug(f"ACTION activity - action: {action_value}, parameter: {parameter_value}")

            if activity.result:
                content_obj["result"] = activity.result
        else:
            content_obj = {
                "type": activity.type.value,
                "body": activity.content if activity.content else ""
            }
            logger.debug(f"{activity.type.value.upper()} activity - body length: {len(activity.content) if activity.content else 0}")

        variables = {
            "agentSessionId": session_id,
            "content": content_obj
        }

        logger.debug(f"Sending to Linear API - content_obj keys: {list(content_obj.keys())}")
        result = self._execute_query(mutation, variables)
        logger.debug(f"Agent activity created successfully")
        return result

    def set_issue_delegate(self, issue_id: str, agent_id: str) -> Dict:
        """
        Set the agent as delegate for an issue.
        
        Args:
            issue_id: Linear issue identifier
            agent_id: Agent/user identifier to set as delegate
            
        Returns:
            Dictionary with success status and updated issue data
            
        Raises:
            LinearAPIError: If API request fails
        """
        logger.debug(f"Setting delegate for issue {issue_id} to agent {agent_id}")
        mutation = """
        mutation SetIssueDelegate($issueId: String!, $delegateId: String!) {
            issueUpdate(
                id: $issueId
                input: {
                    delegateId: $delegateId
                }
            ) {
                success
                issue {
                    id
                    delegate {
                        id
                        name
                    }
                }
            }
        }
        """

        variables = {
            "issueId": issue_id,
            "delegateId": agent_id
        }

        result = self._execute_query(mutation, variables)
        logger.debug(f"Set delegate result: {result.get('data', {}).get('issueUpdate', {}).get('success')}")
        return result

    def update_issue_state(self, issue_id: str, state_id: str) -> Dict:
        """
        Update issue workflow state.
        
        Args:
            issue_id: Linear issue identifier
            state_id: Workflow state identifier
            
        Returns:
            Dictionary with success status and updated issue data
            
        Raises:
            LinearAPIError: If API request fails
        """
        mutation = """
        mutation UpdateIssueState($issueId: String!, $stateId: String!) {
            issueUpdate(
                id: $issueId
                input: {
                    stateId: $stateId
                }
            ) {
                success
                issue {
                    id
                    state {
                        id
                        name
                    }
                }
            }
        }
        """

        variables = {
            "issueId": issue_id,
            "stateId": state_id
        }

        return self._execute_query(mutation, variables)

    def get_team_workflow_states(self, team_id: str) -> List[Dict]:
        """
        Get workflow states for a team.
        
        Args:
            team_id: Linear team identifier
            
        Returns:
            List of workflow state dictionaries with id, name, type, color
            
        Raises:
            LinearAPIError: If API request fails
        """
        query = """
        query GetTeamStates($teamId: String!) {
            team(id: $teamId) {
                states {
                    nodes {
                        id
                        name
                        type
                        position
                    }
                }
            }
        }
        """

        response = self._execute_query(query, {"teamId": team_id})
        return response["data"]["team"]["states"]["nodes"]

    def create_comment(self, issue_id: str, body: str) -> Dict:
        """
        Create a comment on an issue.
        
        Args:
            issue_id: Linear issue identifier
            body: Comment text (supports Markdown)
            
        Returns:
            Dictionary with success status and comment data
            
        Raises:
            LinearAPIError: If API request fails
        """
        mutation = """
        mutation CreateComment($issueId: String!, $body: String!) {
            commentCreate(input: {
                issueId: $issueId
                body: $body
            }) {
                success
                comment {
                    id
                    body
                    createdAt
                }
            }
        }
        """

        variables = {
            "issueId": issue_id,
            "body": body
        }

        return self._execute_query(mutation, variables)

    def get_current_user(self) -> Dict:
        """
        Get current user/agent information.
        
        Returns:
            Dictionary with user id, name, and email
            
        Raises:
            LinearAPIError: If API request fails
        """
        query = """
        query GetCurrentUser {
            viewer {
                id
                name
                email
            }
        }
        """

        response = self._execute_query(query, {})
        return response["data"]["viewer"]

    def _execute_query(self, query: str, variables: Dict) -> Dict:
        """
        Execute a GraphQL query against Linear API.
        
        Args:
            query: GraphQL query string
            variables: Query variables dictionary
            
        Returns:
            GraphQL response data
            
        Raises:
            LinearAPIError: If HTTP request fails or GraphQL returns errors
        """
        logger.debug("Executing GraphQL query to Linear API")
        
        try:
            response = requests.post(
                self.base_url,
                json={"query": query, "variables": variables},
                headers=self._get_headers(),
                timeout=30
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Linear API request failed: {e}")
            raise LinearAPIError(f"Linear API request failed: {e}")

        if response.status_code != 200:
            logger.error(f"Linear API error: {response.status_code} - {response.text}")
            raise LinearAPIError(
                f"Linear API error: {response.status_code} - {response.text}"
            )

        data = response.json()
        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            raise LinearAPIError(f"GraphQL errors: {data['errors']}")

        logger.debug("GraphQL query successful")
        return data
