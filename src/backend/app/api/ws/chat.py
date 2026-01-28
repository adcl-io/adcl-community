# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""WebSocket endpoints for AI chat."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.errors import sanitize_error_for_user

router = APIRouter()


def create_chat_websocket_router(manager, agent_runtime):
    """
    Factory function to create chat WebSocket router with dependencies.

    This deduplicates the three identical WebSocket handlers (scanner, vulnerabilities, attack-console)
    that were previously copy-pasted in main.py (Phase 2.2 refactoring).
    """

    @router.websocket("/ws/chat/{context_type}/{session_id}")
    async def websocket_chat(websocket: WebSocket, context_type: str, session_id: str):
        """
        Unified WebSocket endpoint for AI chat with context.

        Supports context_type: scanner, vulnerabilities, attack-console
        """
        from app.services.chat_service import ChatService

        await manager.connect(session_id, websocket)

        try:
            # Initialize chat service
            chat_service = ChatService(agent_runtime=agent_runtime)

            # Wait for messages
            while True:
                data = await websocket.receive_json()
                message = data.get("message")

                if not message:
                    continue

                # Create callback for streaming
                async def send_update(update: dict):
                    await manager.send_update(session_id, update)

                # Process chat message with specified context
                await chat_service.chat(
                    message=message,
                    context_type=context_type,
                    conversation_history=data.get("history"),
                    progress_callback=send_update,
                )

        except WebSocketDisconnect:
            manager.disconnect(session_id)
        except Exception as e:
            await manager.send_update(session_id, {
                "type": "error",
                "error": sanitize_error_for_user(e, include_type=False)
            })
            manager.disconnect(session_id)

    return router
