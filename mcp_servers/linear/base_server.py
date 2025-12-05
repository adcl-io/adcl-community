# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Base MCP Server implementation
Provides common functionality for all MCP servers in the platform
"""
import asyncio
import json
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


class ToolDefinition(BaseModel):
    """MCP Tool Definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolCallRequest(BaseModel):
    """Request to call a tool"""
    tool: str
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    """Response from a tool call"""
    content: List[Dict[str, Any]]
    isError: bool = False


class ListToolsResponse(BaseModel):
    """Response listing available tools"""
    tools: List[ToolDefinition]


class BaseMCPServer:
    """
    Base MCP Server that any agent or tool can extend.
    Provides standard MCP protocol endpoints.
    """

    def __init__(self, name: str, port: int, description: str = ""):
        self.name = name
        self.port = port
        self.description = description
        self.tools: Dict[str, Callable] = {}
        self.tool_definitions: List[ToolDefinition] = []

        # Create FastAPI app
        self.app = FastAPI(title=f"MCP Server: {name}", description=description)

        # Add CORS middleware to allow frontend access
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins for development
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register standard MCP endpoints
        self._setup_routes()

    def _setup_routes(self):
        """Setup standard MCP protocol routes"""

        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "server": self.name}

        @self.app.post("/mcp/list_tools", response_model=ListToolsResponse)
        async def list_tools():
            """List all available tools on this server"""
            return ListToolsResponse(tools=self.tool_definitions)

        @self.app.post("/mcp/call_tool", response_model=ToolCallResponse)
        async def call_tool(request: ToolCallRequest):
            """Execute a tool by name"""
            if request.tool not in self.tools:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool '{request.tool}' not found"
                )

            try:
                result = await self._execute_tool(request.tool, request.arguments)
                return ToolCallResponse(
                    content=[{"type": "text", "text": json.dumps(result)}],
                    isError=False
                )
            except Exception as e:
                return ToolCallResponse(
                    content=[{"type": "text", "text": str(e)}],
                    isError=True
                )

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        input_schema: Dict[str, Any]
    ):
        """Register a tool with this MCP server"""
        self.tools[name] = handler
        self.tool_definitions.append(
            ToolDefinition(
                name=name,
                description=description,
                input_schema=input_schema
            )
        )
        print(f"[{self.name}] Registered tool: {name}")

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool handler"""
        handler = self.tools[tool_name]

        # Handle both sync and async handlers
        if asyncio.iscoroutinefunction(handler):
            return await handler(**arguments)
        else:
            return handler(**arguments)

    def run(self):
        """Start the MCP server"""
        print(f"Starting MCP Server: {self.name} on port {self.port}")
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)


if __name__ == "__main__":
    # Example usage
    server = BaseMCPServer(
        name="example",
        port=8000,
        description="Example MCP Server"
    )

    def hello(name: str) -> str:
        return f"Hello, {name}!"

    server.register_tool(
        name="hello",
        handler=hello,
        description="Say hello to someone",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to greet"}
            },
            "required": ["name"]
        }
    )

    server.run()
