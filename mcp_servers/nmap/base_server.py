# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Base MCP Server implementation
Provides common functionality for all MCP servers in the platform
Supports both official MCP protocol (JSON-RPC 2.0) and legacy endpoints
"""
import asyncio
import json
import logging
import os
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logger = logging.getLogger(__name__)


@dataclass
class MCPServerSession:
    """Server-side session state"""
    session_id: str
    client_info: Dict[str, Any]
    protocol_version: str
    initialized: bool
    created_at: datetime


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

        # MCP protocol support
        self.protocol_version = "2025-11-25"
        self.server_info = {
            "name": name,
            "version": "1.0.0",
            "description": description
        }
        self.capabilities = {
            "tools": {"listChanged": False},
            "logging": {}
        }
        self.sessions: Dict[str, MCPServerSession] = {}
        self.session_timeout_seconds = int(os.getenv("MCP_SESSION_TIMEOUT", "3600"))

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
        
        # Cleanup task will be started when server runs
        self._cleanup_task = None

    def _setup_routes(self):
        """Setup both official MCP and legacy protocol routes"""

        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "server": self.name}

        # ===== OFFICIAL MCP PROTOCOL (JSON-RPC 2.0) =====
        
        @self.app.post("/")
        async def mcp_endpoint(request: Request):
            """Main MCP endpoint - handles all JSON-RPC messages"""
            # Validate Origin header
            origin = request.headers.get("Origin")
            if origin and not self._is_valid_origin(origin):
                raise HTTPException(status_code=403, detail="Invalid Origin header")
            
            body = await request.json()
            
            # Validate JSON-RPC
            if body.get("jsonrpc") != "2.0":
                return JSONResponse(
                    status_code=400,
                    content=self._build_error_response(None, -32600, "Invalid JSON-RPC version")
                )
            
            method = body.get("method")
            
            # Validate MCP-Protocol-Version header (except for initialize)
            if method != "initialize":
                protocol_version = request.headers.get("MCP-Protocol-Version")
                if protocol_version and protocol_version != self.protocol_version:
                    return JSONResponse(
                        status_code=400,
                        content=self._build_error_response(
                            body.get("id"), -32600,
                            f"Unsupported protocol version: {protocol_version}. Supported: {self.protocol_version}"
                        )
                    )
            
            if method == "initialize":
                return await self._handle_initialize(body, request)
            elif method == "notifications/initialized":
                return await self._handle_initialized(body, request)
            elif method == "notifications/cancelled":
                return await self._handle_cancelled(body, request)
            elif method == "tools/list":
                return await self._handle_tools_list(body, request)
            elif method == "tools/call":
                return await self._handle_tools_call(body, request)
            else:
                return JSONResponse(
                    status_code=400,
                    content=self._build_error_response(
                        body.get("id"), -32601, f"Method not found: {method}"
                    )
                )

        # ===== LEGACY PROTOCOL (DEPRECATED) =====

        @self.app.post("/mcp/list_tools", response_model=ListToolsResponse)
        async def list_tools_legacy():
            """Legacy endpoint - deprecated"""
            logger.warning(f"[{self.name}] Using deprecated /mcp/list_tools endpoint")
            return ListToolsResponse(tools=self.tool_definitions)

        @self.app.post("/mcp/call_tool", response_model=ToolCallResponse)
        async def call_tool_legacy(request: ToolCallRequest):
            """Legacy endpoint - deprecated"""
            logger.warning(f"[{self.name}] Using deprecated /mcp/call_tool endpoint")
            if request.tool not in self.tools:
                raise HTTPException(status_code=404, detail=f"Tool '{request.tool}' not found")

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

    async def _handle_initialize(self, body: Dict, request: Request) -> JSONResponse:
        """Handle initialize request"""
        request_id = body.get("id")
        params = body.get("params", {})
        
        client_protocol = params.get("protocolVersion")
        client_info = params.get("clientInfo", {})
        
        if client_protocol != self.protocol_version:
            return JSONResponse(
                status_code=400,
                content=self._build_error_response(
                    request_id, -32602,
                    f"Unsupported protocol version: {client_protocol}",
                    {"supported": [self.protocol_version]}
                )
            )
        
        session_id = str(uuid.uuid4())
        session = MCPServerSession(
            session_id=session_id,
            client_info=client_info,
            protocol_version=client_protocol,
            initialized=False,
            created_at=datetime.now()
        )
        self.sessions[session_id] = session
        
        response_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": self.protocol_version,
                "capabilities": self.capabilities,
                "serverInfo": self.server_info
            }
        }
        
        return JSONResponse(content=response_data, headers={"MCP-Session-Id": session_id})

    async def _handle_initialized(self, body: Dict, request: Request) -> Response:
        """Handle initialized notification"""
        session_id = request.headers.get("MCP-Session-Id")
        
        if not session_id or session_id not in self.sessions:
            return JSONResponse(
                status_code=400,
                content=self._build_error_response(None, -32600, "Invalid or missing session ID")
            )
        
        self.sessions[session_id].initialized = True
        return Response(status_code=202)

    async def _handle_cancelled(self, body: Dict, request: Request) -> Response:
        """Handle cancellation notification from client"""
        params = body.get("params", {})
        request_id = params.get("requestId")
        reason = params.get("reason", "No reason provided")
        
        logger.info(f"[{self.name}] Client cancelled request {request_id}: {reason}")
        return Response(status_code=202)

    async def _handle_tools_list(self, body: Dict, request: Request) -> JSONResponse:
        """Handle tools/list request"""
        request_id = body.get("id")
        session_id = request.headers.get("MCP-Session-Id")
        
        if session_id and session_id not in self.sessions:
            return JSONResponse(
                status_code=404,
                content=self._build_error_response(request_id, -32600, "Session not found or expired")
            )
        
        # Protocol boundary translation: Python snake_case → MCP camelCase
        # Internal: tool.input_schema (Python convention via Pydantic)
        # Wire: "inputSchema" (MCP protocol specification)
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema  # Intentional camelCase for MCP spec compliance
            }
            for tool in self.tool_definitions
        ]
        
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        })

    async def _handle_tools_call(self, body: Dict, request: Request) -> JSONResponse:
        """Handle tools/call request"""
        request_id = body.get("id")
        session_id = request.headers.get("MCP-Session-Id")
        
        if session_id and session_id not in self.sessions:
            return JSONResponse(
                status_code=404,
                content=self._build_error_response(request_id, -32600, "Session not found or expired")
            )
        
        params = body.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return JSONResponse(
                content=self._build_error_response(request_id, -32602, f"Tool not found: {tool_name}")
            )
        
        try:
            result = await self._execute_tool(tool_name, arguments)
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result)}]}
            })
        except Exception as e:
            return JSONResponse(
                content=self._build_error_response(request_id, -32603, f"Tool execution failed: {str(e)}")
            )

    def _build_error_response(self, request_id: Optional[int], code: int, message: str, data: Optional[Dict] = None) -> Dict:
        """Build JSON-RPC error response"""
        error = {"code": code, "message": message}
        if data:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": request_id, "error": error}

    def _is_valid_origin(self, origin: str) -> bool:
        """Validate Origin header to prevent DNS rebinding attacks"""
        try:
            parsed = urlparse(origin)
            hostname = parsed.hostname
            
            allowed_hosts = ["localhost", "127.0.0.1", "::1"]
            
            env_origins = os.getenv("MCP_ALLOWED_ORIGINS", "")
            if env_origins:
                for env_origin in env_origins.split(","):
                    env_parsed = urlparse(env_origin.strip())
                    if env_parsed.hostname:
                        allowed_hosts.append(env_parsed.hostname)
            
            return hostname in allowed_hosts
        except Exception:
            return False

    async def _cleanup_expired_sessions(self):
        """Periodically clean up expired sessions"""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            
            now = datetime.now()
            expired = [
                session_id
                for session_id, session in self.sessions.items()
                if (now - session.created_at).total_seconds() > self.session_timeout_seconds
            ]
            
            for session_id in expired:
                del self.sessions[session_id]
                logger.info(f"[{self.name}] Cleaned up expired session: {session_id}")

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
        
        # Start cleanup task when event loop is running
        async def startup():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
        
        @self.app.on_event("startup")
        async def on_startup():
            await startup()
        
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
