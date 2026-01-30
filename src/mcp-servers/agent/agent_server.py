# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Agent MCP Server
Exposes AI agent capabilities as MCP tools (think, code, review)
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any

import yaml

from base_server import BaseMCPServer
from anthropic import Anthropic


class AgentMCPServer(BaseMCPServer):
    """
    Agent MCP Server that exposes Claude as tools
    Tools: think, code, review
    """

    def __init__(self, port: int = 7000):
        super().__init__(
            name="agent",
            port=port,
            description="AI Agent MCP Server - Provides thinking, coding, and review capabilities"
        )

        # Load configuration (ADCL: Configuration is Code)
        config_path = Path(__file__).parent / "config.yaml"

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                "Agent MCP server requires config.yaml with llm settings."
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file {config_path}: {e}")

        llm_config = config.get("llm")
        if not llm_config:
            raise ValueError("Missing 'llm' configuration in config.yaml")

        self.model_name = llm_config.get("default_model")
        self.max_tokens = llm_config.get("max_tokens")
        self.temperature = llm_config.get("temperature")

        if not self.model_name:
            raise ValueError("Missing 'llm.default_model' in config.yaml")
        if not self.max_tokens:
            raise ValueError("Missing 'llm.max_tokens' in config.yaml")
        if self.temperature is None:
            raise ValueError("Missing 'llm.temperature' in config.yaml")

        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic = Anthropic(api_key=api_key) if api_key else None

        # Register agent tools
        self._register_agent_tools()

    def _register_agent_tools(self):
        """Register all agent capabilities as tools"""

        self.register_tool(
            name="think",
            handler=self.think,
            description="Use AI to analyze and reason about a problem",
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The problem or question to think about"
                    }
                },
                "required": ["prompt"]
            }
        )

        self.register_tool(
            name="code",
            handler=self.code,
            description="Generate code based on a specification",
            input_schema={
                "type": "object",
                "properties": {
                    "spec": {
                        "type": "string",
                        "description": "Specification for the code to generate"
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (default: python)"
                    }
                },
                "required": ["spec"]
            }
        )

        self.register_tool(
            name="review",
            handler=self.review,
            description="Review code and provide feedback",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code to review"
                    }
                },
                "required": ["code"]
            }
        )

    async def think(self, prompt: str) -> Dict[str, Any]:
        """Think about a problem using AI"""
        if not self.anthropic:
            return {
                "reasoning": f"[MOCK] Analysis of: {prompt[:100]}...",
                "conclusion": "Mock thinking response - set ANTHROPIC_API_KEY to use real AI"
            }

        try:
            message = self.anthropic.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": f"Think deeply about this:\n\n{prompt}\n\nProvide structured reasoning and conclusions."
                    }
                ]
            )
            return {
                "reasoning": message.content[0].text,
                "model": self.model_name
            }
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    async def code(self, spec: str, language: str = "python") -> Dict[str, Any]:
        """Generate code from specification"""
        if not self.anthropic:
            return {
                "code": f"# Mock code for: {spec[:50]}...\ndef example():\n    pass",
                "language": language,
                "note": "Mock response - set ANTHROPIC_API_KEY to use real AI"
            }

        try:
            message = self.anthropic.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": f"Generate {language} code for:\n\n{spec}\n\nIMPORTANT: Return ONLY the executable code with inline comments. Do NOT include:\n- Markdown code fences (```)\n- Explanatory text before or after the code\n- Multiple alternative versions\n- Usage examples outside the code\n\nJust return clean, executable {language} code that can be directly saved to a file and run."
                    }
                ]
            )

            # Extract code from markdown blocks if present
            code_text = message.content[0].text.strip()

            # Remove markdown code fences if they exist
            if code_text.startswith("```"):
                lines = code_text.split("\n")
                # Remove first line (opening fence)
                lines = lines[1:]
                # Remove last line if it's a closing fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                code_text = "\n".join(lines)

            return {
                "code": code_text,
                "language": language,
                "model": self.model_name
            }
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    async def review(self, code: str) -> Dict[str, Any]:
        """Review code and provide feedback"""
        if not self.anthropic:
            return {
                "feedback": f"[MOCK] Review of code ({len(code)} chars)",
                "issues": ["Mock issue 1", "Mock issue 2"],
                "suggestions": ["Mock suggestion 1"],
                "note": "Mock response - set ANTHROPIC_API_KEY to use real AI"
            }

        try:
            message = self.anthropic.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": f"Review this code:\n\n```\n{code}\n```\n\nProvide:\n1. Issues found\n2. Suggestions for improvement\n3. Overall assessment"
                    }
                ]
            )
            return {
                "feedback": message.content[0].text,
                "model": self.model_name
            }
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", "7000"))
    server = AgentMCPServer(port=port)
    server.run()
