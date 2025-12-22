# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP Session Manager
Manages MCP initialization, sessions, and JSON-RPC communication
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List

import aiohttp

from app.mcp_session import MCPSession
from app.mcp_exceptions import MCPInitializationError, MCPSessionExpiredError, MCPProtocolError
from app.mcp_jsonrpc import (
    build_initialize_request,
    build_initialized_notification,
    build_list_tools_request,
    build_call_tool_request,
    build_cancel_notification
)

logger = logging.getLogger(__name__)


class MCPSessionManager:
    """Manages MCP initialization and sessions"""
    
    def __init__(self, notification_handler: Optional[Callable[[Dict], None]] = None):
        self.sessions: Dict[str, MCPSession] = {}
        self.init_locks: Dict[str, asyncio.Lock] = {}
        self.request_locks: Dict[str, asyncio.Lock] = {}
        self.request_id_counter = 0
        self.protocol_version = "2025-11-25"
        self.client_info = {
            "name": "ADCL-Orchestrator",
            "version": "1.0.0",
            "description": "ADCL Agent Platform Orchestrator"
        }
        
        # Configurable timeouts (seconds)
        self.timeout_init = int(os.getenv("MCP_TIMEOUT_INIT", "30"))
        self.timeout_list = int(os.getenv("MCP_TIMEOUT_LIST", "10"))
        self.timeout_call = int(os.getenv("MCP_TIMEOUT_CALL", "300"))
        
        # SSE resumability tracking
        self.last_event_id: Optional[str] = None
        self.retry_ms: Optional[int] = None
        
        # HTTP session pooling
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        # Notification handler
        self.notification_handler = notification_handler or self._default_notification_handler
    
    def _default_notification_handler(self, notification: Dict) -> None:
        """Default handler for server notifications"""
        method = notification.get("method", "unknown")
        params = notification.get("params", {})
        logger.info(f"Server notification: {method} - {params}")
    
    def _next_request_id(self) -> int:
        """Generate next request ID"""
        self.request_id_counter += 1
        return self.request_id_counter
    
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create persistent HTTP session"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session
    
    async def close(self):
        """Clean up resources"""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        self.sessions.clear()
    
    def _build_headers(self, session: Optional[MCPSession] = None) -> Dict[str, str]:
        """Build HTTP headers for MCP requests"""
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if session:
            headers["MCP-Protocol-Version"] = session.protocol_version
            if session.session_id:
                headers["MCP-Session-Id"] = session.session_id
        return headers
    
    async def initialize(self, endpoint: str) -> MCPSession:
        """Perform 3-step MCP initialization handshake"""
        logger.info(f"Initializing MCP session for {endpoint}")
        
        request_id = self._next_request_id()
        init_request = build_initialize_request(request_id, self.protocol_version, self.client_info)
        
        http_session = await self._get_http_session()
        
        try:
            async with http_session.post(
                endpoint,
                json=init_request,
                headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.timeout_init)
            ) as response:
                if response.status != 200:
                    raise MCPInitializationError(f"Initialize failed with status {response.status}")
                
                result = await self._handle_response(response)
                
                if "error" in result:
                    error = result["error"]
                    raise MCPInitializationError(f"Initialize error: {error.get('message', 'Unknown error')}")
                
                init_result = result.get("result", {})
                server_capabilities = init_result.get("capabilities", {})
                server_protocol = init_result.get("protocolVersion")
                session_id = response.headers.get("MCP-Session-Id")
                
                # Create session
                session = MCPSession(
                    endpoint=endpoint,
                    protocol_version=server_protocol or self.protocol_version,
                    session_id=session_id,
                    server_capabilities=server_capabilities,
                    client_capabilities=init_request["params"]["capabilities"],
                    initialized_at=datetime.now()
                )
                
                # Send initialized notification
                init_notification = build_initialized_notification()
                async with http_session.post(
                    endpoint,
                    json=init_notification,
                    headers=self._build_headers(session),
                    timeout=aiohttp.ClientTimeout(total=self.timeout_init)
                ) as notif_response:
                    if notif_response.status != 202:
                        logger.warning(f"Initialized notification returned {notif_response.status}")
                
                # Cache session
                self.sessions[endpoint] = session
                logger.info(f"MCP session initialized for {endpoint}")
                return session
                
        except asyncio.TimeoutError:
            raise MCPInitializationError(f"Initialize timeout for {endpoint}")
        except aiohttp.ClientError as e:
            raise MCPInitializationError(f"Initialize failed: {e}")
    
    async def get_or_initialize(self, endpoint: str) -> MCPSession:
        """Get cached session or initialize new one"""
        # Fast path
        if endpoint in self.sessions:
            return self.sessions[endpoint]
        
        # Slow path with lock
        if endpoint not in self.init_locks:
            self.init_locks[endpoint] = asyncio.Lock()
        
        async with self.init_locks[endpoint]:
            # Double-check
            if endpoint in self.sessions:
                return self.sessions[endpoint]
            
            return await self.initialize(endpoint)
    
    async def list_tools(self, endpoint: str) -> List[Dict]:
        """List tools using JSON-RPC tools/list"""
        session = await self.get_or_initialize(endpoint)
        request_id = self._next_request_id()
        request = build_list_tools_request(request_id)
        
        http_session = await self._get_http_session()
        
        try:
            async with http_session.post(
                endpoint,
                json=request,
                headers=self._build_headers(session),
                timeout=aiohttp.ClientTimeout(total=self.timeout_list)
            ) as response:
                if response.status == 404:
                    # Session expired - re-initialize
                    logger.warning(f"Session expired for {endpoint}, re-initializing")
                    del self.sessions[endpoint]
                    return await self.list_tools(endpoint)
                
                result = await self._handle_response(response)
                
                if "error" in result:
                    raise MCPProtocolError(f"List tools error: {result['error']}")
                
                return result.get("result", {}).get("tools", [])
                
        except asyncio.TimeoutError:
            raise MCPProtocolError(f"List tools timeout for {endpoint}")
    
    async def call_tool(self, endpoint: str, tool_name: str, arguments: Dict) -> Dict:
        """Call tool using JSON-RPC tools/call"""
        # Serialize requests per endpoint
        if endpoint not in self.request_locks:
            self.request_locks[endpoint] = asyncio.Lock()
        
        async with self.request_locks[endpoint]:
            return await self._call_tool_with_retry(endpoint, tool_name, arguments)
    
    async def _call_tool_with_retry(self, endpoint: str, tool_name: str, arguments: Dict, max_retries: int = 3) -> Dict:
        """Call tool with retry logic"""
        last_event_id = self.last_event_id
        request_id = None
        
        for attempt in range(max_retries):
            try:
                session = await self.get_or_initialize(endpoint)
                request_id = self._next_request_id()
                request = build_call_tool_request(request_id, tool_name, arguments)
                
                headers = self._build_headers(session)
                if last_event_id and attempt > 0:
                    headers["Last-Event-ID"] = last_event_id
                    logger.info(f"Resuming SSE stream from event ID: {last_event_id}")
                
                http_session = await self._get_http_session()
                async with http_session.post(
                    endpoint,
                    json=request,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_call)
                ) as response:
                    if response.status == 404:
                        # Session expired
                        logger.warning(f"Session expired for {endpoint}, re-initializing")
                        del self.sessions[endpoint]
                        continue
                    
                    result = await self._handle_response(response)
                    
                    if "error" in result:
                        raise MCPProtocolError(f"Tool call error: {result['error']}")
                    
                    return result.get("result", {})
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    retry_delay = (self.retry_ms / 1000) if self.retry_ms else (2 ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s: {e}")
                    await asyncio.sleep(retry_delay)
                    continue
                
                # Final attempt - send cancellation
                if request_id and isinstance(e, asyncio.TimeoutError):
                    try:
                        cancel_notification = build_cancel_notification(request_id)
                        http_session = await self._get_http_session()
                        await http_session.post(
                            endpoint,
                            json=cancel_notification,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=5)
                        )
                        logger.info(f"Sent cancellation notification for request {request_id}")
                    except Exception as cancel_error:
                        logger.warning(f"Failed to send cancellation: {cancel_error}")
                
                raise MCPProtocolError(f"Tool call failed after {max_retries} attempts: {e}")
        
        raise MCPProtocolError(f"Tool call failed after {max_retries} attempts")
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict:
        """Handle both JSON and SSE responses"""
        content_type = response.headers.get("Content-Type", "")
        
        if "text/event-stream" in content_type:
            return await self._read_sse_stream(response)
        else:
            return await response.json()
    
    async def _read_sse_stream(self, response: aiohttp.ClientResponse) -> Dict:
        """Read SSE stream per HTML5 spec"""
        event_id = None
        data_buffer = []
        
        # Read entire response text and split into lines
        text = await response.text()
        lines = text.split('\n')
        
        for line in lines:
            line = line.rstrip('\r')
            
            if not line:
                # Empty line = dispatch event
                if data_buffer:
                    data = '\n'.join(data_buffer)
                    try:
                        parsed = json.loads(data)
                        
                        if "result" in parsed or "error" in parsed:
                            if event_id:
                                self.last_event_id = event_id
                            return parsed
                        
                        if "method" in parsed:
                            self.notification_handler(parsed)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse SSE data: {e}")
                    
                    data_buffer = []
                continue
            
            if line.startswith('id:'):
                event_id = line[3:].strip()
            elif line.startswith('data:'):
                data_buffer.append(line[5:].strip())
            elif line.startswith('retry:'):
                try:
                    self.retry_ms = int(line[6:].strip())
                except ValueError:
                    logger.warning(f"Invalid retry value: {line}")
            elif line.startswith(':'):
                pass  # Comment
        
        raise MCPProtocolError("SSE stream ended without JSON-RPC response")
