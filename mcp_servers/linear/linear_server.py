# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Linear MCP Server

Exposes Linear API operations as MCP tools.
Provides 8 tools for issue management, agent activities, and workflow operations.
"""
import os
import logging
from typing import Dict, Any
from pathlib import Path
import yaml

from base_server import BaseMCPServer
from linear_client import LinearClient, AgentActivity, ActivityType
from exceptions import LinearConfigError

# Configure logging
logger = logging.getLogger("linear.server")
logger.setLevel(logging.INFO)


class LinearMCPServer(BaseMCPServer):
    """
    Linear MCP Server - GraphQL operations for Linear integration.
    
    Provides 8 tools:
    - get_issue: Get issue by ID
    - create_agent_activity: Create agent session activity
    - set_issue_delegate: Assign agent as delegate
    - update_issue_state: Update issue workflow state
    - get_team_workflow_states: Get team workflow states
    - create_comment: Add comment to issue
    - get_current_user: Get current user/agent info
    - execute_query: Execute raw GraphQL query
    """

    def __init__(self, port: int = 7005) -> None:
        """
        Initialize Linear MCP Server.
        
        Args:
            port: Server port (default: 7005)
            
        Raises:
            LinearConfigError: If configuration file invalid or missing
        """
        super().__init__(
            name="linear",
            port=port,
            description="Linear API MCP Server - GraphQL operations for Linear integration"
        )

        logger.info(f"Initializing Linear MCP Server on port {port}")

        # Load configuration
        config_path = Path(__file__).parent / "config.yaml"
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.debug(f"Configuration loaded from {config_path}")
        except FileNotFoundError:
            error_msg = f"Configuration file not found: {config_path}"
            logger.error(error_msg)
            raise LinearConfigError(error_msg)
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in config file {config_path}: {e}"
            logger.error(error_msg)
            raise LinearConfigError(error_msg)

        # Initialize Linear client
        self.client = LinearClient()
        logger.info("Linear client initialized")

        # Register Linear tools
        self._register_linear_tools()
        logger.info("Linear MCP Server initialized successfully")

    def _register_linear_tools(self) -> None:
        """Register all 8 Linear API tools with input schemas."""
        logger.debug("Registering Linear tools")

        self.register_tool(
            name="get_issue",
            handler=self.get_issue,
            description="Get a Linear issue by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "string",
                        "description": "Linear issue ID"
                    }
                },
                "required": ["issue_id"]
            }
        )

        self.register_tool(
            name="create_agent_activity",
            handler=self.create_agent_activity,
            description="Create an agent activity for a session",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Agent session ID"
                    },
                    "activity_type": {
                        "type": "string",
                        "enum": ["thought", "elicitation", "action", "response", "error"],
                        "description": "Type of activity"
                    },
                    "content": {
                        "type": "string",
                        "description": "Activity content"
                    },
                    "action": {
                        "type": "string",
                        "description": "Action name (required for ACTION type)"
                    },
                    "parameter": {
                        "type": "string",
                        "description": "Action parameter (required for ACTION type)"
                    },
                    "result": {
                        "type": "string",
                        "description": "Action result (optional for ACTION type)"
                    }
                },
                "required": ["session_id", "activity_type", "content"]
            }
        )

        self.register_tool(
            name="set_issue_delegate",
            handler=self.set_issue_delegate,
            description="Set an agent as delegate for an issue",
            input_schema={
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "string",
                        "description": "Linear issue ID"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Agent/user ID to set as delegate"
                    }
                },
                "required": ["issue_id", "agent_id"]
            }
        )

        self.register_tool(
            name="update_issue_state",
            handler=self.update_issue_state,
            description="Update an issue's workflow state",
            input_schema={
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "string",
                        "description": "Linear issue ID"
                    },
                    "state_id": {
                        "type": "string",
                        "description": "Workflow state ID"
                    }
                },
                "required": ["issue_id", "state_id"]
            }
        )

        self.register_tool(
            name="get_team_workflow_states",
            handler=self.get_team_workflow_states,
            description="Get workflow states for a team",
            input_schema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Linear team ID"
                    }
                },
                "required": ["team_id"]
            }
        )

        self.register_tool(
            name="create_comment",
            handler=self.create_comment,
            description="Create a comment on an issue",
            input_schema={
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "string",
                        "description": "Linear issue ID"
                    },
                    "body": {
                        "type": "string",
                        "description": "Comment body (Markdown supported)"
                    }
                },
                "required": ["issue_id", "body"]
            }
        )

        self.register_tool(
            name="get_current_user",
            handler=self.get_current_user,
            description="Get current user/agent information",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )

        self.register_tool(
            name="execute_query",
            handler=self.execute_query,
            description="Execute a raw GraphQL query (advanced)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GraphQL query string"
                    },
                    "variables": {
                        "type": "object",
                        "description": "Query variables"
                    }
                },
                "required": ["query"]
            }
        )

    async def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """
        Get a Linear issue by ID.
        
        Args:
            issue_id: Linear issue identifier
            
        Returns:
            Dictionary with issue data or error
        """
        try:
            logger.debug(f"Getting issue: {issue_id}")
            issue = self.client.get_issue(issue_id)
            return issue.dict()
        except Exception as e:
            logger.error(f"Failed to get issue {issue_id}: {e}")
            return {"error": str(e)}

    async def create_agent_activity(
        self,
        session_id: str,
        activity_type: str,
        content: str,
        action: str = None,
        parameter: str = None,
        result: str = None
    ) -> Dict[str, Any]:
        """
        Create an agent activity for a session.
        
        Args:
            session_id: Agent session identifier
            activity_type: Activity type (thought, action, response, etc.)
            content: Activity content/description
            action: Action name (required for ACTION type)
            parameter: Action parameter (required for ACTION type)
            result: Action result (optional)
            
        Returns:
            Dictionary with activity data or error
        """
        try:
            logger.debug(f"Creating activity: session={session_id}, type={activity_type}")
            activity = AgentActivity(
                type=ActivityType(activity_type),
                content=content,
                action=action,
                parameter=parameter,
                result=result
            )
            response = self.client.create_agent_activity(session_id, activity)
            return response
        except Exception as e:
            logger.error(f"Failed to create activity: {e}")
            return {"error": str(e)}

    async def set_issue_delegate(self, issue_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Set an agent as delegate for an issue.
        
        Args:
            issue_id: Linear issue identifier
            agent_id: Agent/user identifier
            
        Returns:
            Dictionary with updated issue data or error
        """
        try:
            logger.debug(f"Setting delegate: issue={issue_id}, agent={agent_id}")
            response = self.client.set_issue_delegate(issue_id, agent_id)
            return response
        except Exception as e:
            logger.error(f"Failed to set delegate: {e}")
            return {"error": str(e)}

    async def update_issue_state(self, issue_id: str, state_id: str) -> Dict[str, Any]:
        """
        Update an issue's workflow state.
        
        Args:
            issue_id: Linear issue identifier
            state_id: Workflow state identifier
            
        Returns:
            Dictionary with updated issue data or error
        """
        try:
            logger.debug(f"Updating state: issue={issue_id}, state={state_id}")
            response = self.client.update_issue_state(issue_id, state_id)
            return response
        except Exception as e:
            logger.error(f"Failed to update state: {e}")
            return {"error": str(e)}

    async def get_team_workflow_states(self, team_id: str) -> Dict[str, Any]:
        """
        Get workflow states for a team.
        
        Args:
            team_id: Linear team identifier
            
        Returns:
            Dictionary with states list or error
        """
        try:
            logger.debug(f"Getting workflow states for team: {team_id}")
            states = self.client.get_team_workflow_states(team_id)
            return {"states": states}
        except Exception as e:
            logger.error(f"Failed to get workflow states: {e}")
            return {"error": str(e)}

    async def create_comment(self, issue_id: str, body: str) -> Dict[str, Any]:
        """
        Create a comment on an issue.
        
        Args:
            issue_id: Linear issue identifier
            body: Comment text (supports Markdown)
            
        Returns:
            Dictionary with comment data or error
        """
        try:
            logger.debug(f"Creating comment on issue: {issue_id}")
            response = self.client.create_comment(issue_id, body)
            return response
        except Exception as e:
            logger.error(f"Failed to create comment: {e}")
            return {"error": str(e)}

    async def get_current_user(self) -> Dict[str, Any]:
        """
        Get current user/agent information.
        
        Returns:
            Dictionary with user data or error
        """
        try:
            logger.debug("Getting current user")
            user = self.client.get_current_user()
            return user
        except Exception as e:
            logger.error(f"Failed to get current user: {e}")
            return {"error": str(e)}

    async def execute_query(self, query: str, variables: Dict = None) -> Dict[str, Any]:
        """
        Execute a raw GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Query variables (optional)
            
        Returns:
            Dictionary with query response or error
        """
        try:
            if variables is None:
                variables = {}
            logger.debug("Executing raw GraphQL query")
            response = self.client._execute_query(query, variables)
            return response
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    port = int(os.getenv("LINEAR_PORT", "7005"))
    server = LinearMCPServer(port=port)
    server.run()
