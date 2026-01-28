# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Chat Service - AI chat orchestration for Red Team Dashboard
Following ADCL principle: Backend service (Tier 2) - uses AgentRuntime, not direct MCP
"""
from typing import Dict, Any, Optional, Callable, List
from app.agent_runtime import AgentRuntime
from app.models.red_team import ChatMessage, ChatMessageRole, ChatStreamEvent
from datetime import datetime
from pathlib import Path
import json


class ChatService:
    """
    Service for AI chat orchestration in Red Team Dashboard.

    This is a Tier 2 backend service - orchestrates AI conversations,
    manages context, streams responses via callbacks.
    """

    def __init__(self, agent_runtime: AgentRuntime, agents_dir: Optional[Path] = None):
        """
        Initialize chat service.

        Args:
            agent_runtime: Agent runtime for AI execution
            agents_dir: Directory containing agent definitions (defaults to agent-definitions/)
        """
        self.agent_runtime = agent_runtime
        self.agents_dir = agents_dir or Path("agent-definitions")

        # Context templates for different dashboard sections
        self.context_templates = {
            "scanner": """You are a cybersecurity expert assistant helping with network scanning and reconnaissance.

Your capabilities:
- Analyze scan results and identify important findings
- Recommend scan types and options for different scenarios
- Explain vulnerabilities and their implications
- Suggest next steps based on scan results

When the user asks to perform a scan, provide guidance on:
1. What type of scan to use (discovery, deep, vulnerability)
2. Recommended scan options
3. Expected results and how to interpret them

Be concise, technical, and security-focused.""",
            "vulnerabilities": """You are a cybersecurity expert assistant specializing in vulnerability analysis.

Your capabilities:
- Analyze vulnerability data and assess risk
- Explain CVEs and their impact
- Recommend remediation strategies
- Prioritize vulnerabilities based on severity and exploitability
- Suggest exploitation techniques (for authorized testing only)

When analyzing vulnerabilities:
1. Consider severity, CVSS score, and exploitability
2. Assess business impact and risk
3. Recommend remediation in order of priority
4. Suggest verification methods

Be concise, technical, and risk-focused.""",
            "attack-console": """You are a cybersecurity expert assistant for attack orchestration and penetration testing.

Your capabilities:
- Design multi-stage attack workflows
- Recommend exploitation techniques
- Analyze attack results and suggest pivoting strategies
- Explain security implications of findings

When planning attacks:
1. Ensure proper authorization and legal compliance
2. Recommend appropriate attack vectors based on vulnerabilities
3. Design workflows that gather evidence systematically
4. Suggest defensive mitigations based on successful attacks

IMPORTANT: Only assist with authorized penetration testing. Always verify authorization before proceeding.

Be concise, technical, and ethical.""",
        }

    def _load_agent_definition(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Load agent definition from file.

        Args:
            agent_id: Agent identifier (filename without .json)

        Returns:
            Agent definition dict or None if not found
        """
        agent_file = self.agents_dir / f"{agent_id}.json"
        if not agent_file.exists():
            return None

        try:
            with open(agent_file, "r") as f:
                agent_def = json.load(f)
                # Ensure agent has an id field
                if "id" not in agent_def:
                    agent_def["id"] = agent_id
                return agent_def
        except Exception as e:
            print(f"Error loading agent definition {agent_id}: {e}")
            return None

    async def chat(
        self,
        message: str,
        context_type: Optional[str] = None,
        conversation_history: Optional[List[ChatMessage]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message with AI.

        Args:
            message: User message
            context_type: Context identifier (scanner, vulnerabilities, attack-console)
            conversation_history: Previous conversation messages
            progress_callback: Callback for streaming updates

        Returns:
            AI response with metadata
        """
        # Get context template
        system_context = self.context_templates.get(
            context_type, "You are a helpful cybersecurity assistant."
        )

        # Build conversation history
        messages = []

        # Add system context
        messages.append(
            {
                "role": "user",
                "content": f"System context:\n{system_context}\n\nRemember this context for our conversation.",
            }
        )

        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append({"role": msg.role.value, "content": msg.content})

        # Add current message
        messages.append({"role": "user", "content": message})

        # Send thinking status
        if progress_callback:
            await progress_callback(
                ChatStreamEvent(
                    type="thinking",
                    content="Processing your request...",
                    timestamp=datetime.now(),
                ).model_dump(mode="json")
            )

        # Execute AI request
        # Note: Using agent_runtime's think capability
        # This is Tier 2 (backend service) calling Tier 3 (AI agent via MCP)
        try:
            # Load security analyst agent definition
            agent_def = self._load_agent_definition("security-analyst")
            if not agent_def:
                raise Exception("Security analyst agent not found in agent-definitions/")

            # Build prompt from conversation
            conversation_text = "\n\n".join(
                [f"{m['role']}: {m['content']}" for m in messages]
            )

            # Use agent runtime to execute thinking
            # The agent runtime handles MCP communication (Tier 3)
            result = await self.agent_runtime.run_agent(
                agent_definition=agent_def,
                task=conversation_text,
                context={},
                progress_callback=progress_callback,
            )

            # Extract response
            response_text = result.get("answer", "I apologize, but I couldn't process that request.")

            # Send response event
            if progress_callback:
                await progress_callback(
                    ChatStreamEvent(
                        type="response",
                        content=response_text,
                        timestamp=datetime.now(),
                    ).model_dump(mode="json")
                )

            # Send completion
            if progress_callback:
                await progress_callback(
                    ChatStreamEvent(
                        type="complete",
                        content="Response complete",
                        timestamp=datetime.now(),
                    ).model_dump(mode="json")
                )

            return {
                "response": response_text,
                "metadata": {
                    "context_type": context_type,
                    "timestamp": datetime.now().isoformat(),
                    "token_usage": result.get("token_usage"),
                },
            }

        except Exception as e:
            error_message = f"Error processing chat: {str(e)}"

            if progress_callback:
                await progress_callback(
                    ChatStreamEvent(
                        type="error",
                        content=error_message,
                        timestamp=datetime.now(),
                    ).model_dump(mode="json")
                )

            return {
                "response": "I apologize, but I encountered an error processing your request.",
                "error": error_message,
                "metadata": {
                    "context_type": context_type,
                    "timestamp": datetime.now().isoformat(),
                },
            }

    async def analyze_scan_results(
        self,
        scan_results: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """
        Use AI to analyze scan results.

        Args:
            scan_results: Scan results data
            progress_callback: Callback for streaming updates

        Returns:
            Analysis text
        """
        prompt = f"""Analyze the following network scan results and provide a concise summary:

{scan_results}

Provide:
1. Number of hosts discovered
2. Most critical findings
3. Recommended next steps
4. Security risks identified

Keep the analysis concise and actionable."""

        result = await self.chat(
            message=prompt,
            context_type="scanner",
            progress_callback=progress_callback,
        )

        return result.get("response", "Analysis unavailable")

    async def analyze_vulnerability(
        self,
        vulnerability: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """
        Use AI to analyze a vulnerability.

        Args:
            vulnerability: Vulnerability data
            progress_callback: Callback for streaming updates

        Returns:
            Analysis text
        """
        prompt = f"""Analyze this vulnerability and provide remediation guidance:

{vulnerability}

Provide:
1. Risk assessment and business impact
2. Exploitation difficulty and likelihood
3. Recommended remediation steps
4. Verification methods after remediation

Be concise and prioritize critical information."""

        result = await self.chat(
            message=prompt,
            context_type="vulnerabilities",
            progress_callback=progress_callback,
        )

        return result.get("response", "Analysis unavailable")

    async def suggest_attack_workflow(
        self,
        target_info: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """
        Use AI to suggest an attack workflow.

        Args:
            target_info: Target information including vulnerabilities
            progress_callback: Callback for streaming updates

        Returns:
            Attack workflow suggestion
        """
        prompt = f"""Based on the following target information, suggest a penetration testing workflow:

{target_info}

Provide:
1. Recommended attack sequence
2. Tools and techniques to use
3. Expected outcomes at each stage
4. Data to collect for reporting

IMPORTANT: This is for authorized penetration testing only.

Be concise and provide actionable steps."""

        result = await self.chat(
            message=prompt,
            context_type="attack-console",
            progress_callback=progress_callback,
        )

        return result.get("response", "Workflow suggestion unavailable")
