# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
File Tools MCP Server
Provides file system operations as MCP tools
"""
import os
import sys
from typing import Dict, Any
from pathlib import Path

from base_server import BaseMCPServer


class FileToolsMCPServer(BaseMCPServer):
    """
    File Tools MCP Server
    Tools: read_file, write_file, list_files
    """

    def __init__(self, port: int = 7002, workspace_dir: str = "/workspace"):
        super().__init__(
            name="file_tools",
            port=port,
            description="File operations MCP Server - Read, write, and list files"
        )

        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Register file tools
        self._register_file_tools()

    def _register_file_tools(self):
        """Register all file operation tools"""

        self.register_tool(
            name="read_file",
            handler=self.read_file,
            description="Read contents of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to file (relative to workspace)"
                    }
                },
                "required": ["path"]
            }
        )

        self.register_tool(
            name="write_file",
            handler=self.write_file,
            description="Write content to a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to file (relative to workspace)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["path", "content"]
            }
        )

        self.register_tool(
            name="list_files",
            handler=self.list_files,
            description="List files in a directory",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (relative to workspace, default: .)"
                    }
                }
            }
        )

    def _get_safe_path(self, path: str) -> Path:
        """Get safe path within workspace, prevent directory traversal"""
        full_path = (self.workspace_dir / path).resolve()

        # Ensure path is within workspace
        if not str(full_path).startswith(str(self.workspace_dir.resolve())):
            raise ValueError("Path outside workspace not allowed")

        return full_path

    async def read_file(self, path: str) -> Dict[str, Any]:
        """Read a file from the workspace"""
        try:
            file_path = self._get_safe_path(path)

            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            if not file_path.is_file():
                return {"error": f"Not a file: {path}"}

            content = file_path.read_text()
            return {
                "path": path,
                "content": content,
                "size": len(content)
            }
        except Exception as e:
            return {"error": str(e)}

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file in the workspace"""
        try:
            file_path = self._get_safe_path(path)

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(content)

            return {
                "path": path,
                "size": len(content),
                "success": True
            }
        except Exception as e:
            return {"error": str(e)}

    async def list_files(self, path: str = ".") -> Dict[str, Any]:
        """List files in a directory"""
        try:
            dir_path = self._get_safe_path(path)

            if not dir_path.exists():
                return {"error": f"Directory not found: {path}"}

            if not dir_path.is_dir():
                return {"error": f"Not a directory: {path}"}

            files = []
            directories = []

            for item in dir_path.iterdir():
                if item.is_file():
                    files.append({
                        "name": item.name,
                        "size": item.stat().st_size
                    })
                elif item.is_dir():
                    directories.append(item.name)

            return {
                "path": path,
                "files": files,
                "directories": directories
            }
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    # Get workspace and port from env or use defaults
    workspace = os.getenv("WORKSPACE_DIR", "/workspace")
    port = int(os.getenv("FILE_TOOLS_PORT", "7002"))
    server = FileToolsMCPServer(port=port, workspace_dir=workspace)
    server.run()
