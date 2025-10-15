from starlette.websockets import WebSocketState, WebSocketDisconnect
from typing import Annotated, Any
from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketException
from fastapi.params import Depends, Query
from auth import user_login
from multi_agent_system import SupervisorSystemManager, AgentInternalError
from storage import database
from auth.oauth import auth_google, OAuthError
import logging
from storage.database import DatabaseError

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 40_000  # ~10,000 tokens

router = APIRouter(
    tags=['AI Chat']
)


async def get_websocket_user(
    websocket: WebSocket,
    token: Annotated[str | None, Query()] = None,
    db: database.Session = Depends(database.get_db)
) -> tuple[Any, str]:
    """Authenticate WebSocket connection and return current user with token."""
    if token is None:
        logger.warning(f"WebSocket authentication failed: No token provided from {websocket.client}")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    try:
        current_user = user_login.get_current_user(token, db)
        if not current_user or current_user.disabled:
            logger.warning(f"WebSocket authentication failed: Invalid or disabled user")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        return current_user, token
    except HTTPException as e:
        logger.warning(f"WebSocket authentication failed: {e}", exc_info=True)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION) from e


async def chat(
    websocket: WebSocket,
    supervisor: SupervisorSystemManager,
    config: dict[str, Any],
    context: dict[str, str]
) -> None:
    """Handle WebSocket chat loop, streaming agent responses and managing interrupts."""
    # Track if we're in interrupt mode (waiting for user response to resume)
    interrupt_mode = False
    user_id = context['user_id']

    while True:
        data = await websocket.receive_text()

        # Validate message length
        if len(data) > MAX_MESSAGE_LENGTH:
            logger.warning(f"User {user_id} sent message exceeding length limit: {len(data)} chars")
            await websocket.send_text(f"Error: Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.\n")
            continue

        await websocket.send_text(f"User: {data}\n")

        # Determine which function to call based on interrupt mode
        if interrupt_mode:
            event_stream = supervisor.resume_agent_after_interrupt(data, config, context)
            interrupt_mode = False
        else:
            event_stream = supervisor.stream_agent_events(data, config, context)

        async for event in event_stream:
            event_type = event.get('type')
            content = event.get('content')

            if event_type == 'interrupt':

                await websocket.send_text(f"Agent [INTERRUPT]: {content}\n")
                interrupt_mode = True
                # Break to wait for user's response
                break

            elif event_type == 'complete':
                # Final response from agent
                await websocket.send_text(f"Agent: {content}\n")
                interrupt_mode = False
                break

            elif event_type == 'message':
                # Sub-agent message (if any)
                await websocket.send_text(f"Agent [UPDATE]: {content}\n")


async def send_error_message(websocket: WebSocket, error: str) -> None:
    """Send error message and close WebSocket connection if still connected."""
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_text(f"Error: {error}\n")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}", exc_info=True)


@router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        user_data: Annotated[tuple, Depends(get_websocket_user)]
):
    """
    WebSocket endpoint for real-time AI agent chat with interrupt handling.

    Flow:
    1. User sends message
    2. Agent streams responses back (message/complete/interrupt)
    3. If interrupt occurs, wait for user response and resume
    4. Repeat until complete
    """
    try:
        await websocket.accept()
        current_user, token = user_data
        credentials = auth_google(current_user.id)
        config = {"configurable": {"thread_id": str(current_user.id)}}
        context = {"user_full_name": current_user.full_name,
                   "user_id": str(current_user.id),
                  }
        supervisor = SupervisorSystemManager(current_user.id, token, credentials)
        await supervisor.build()
        logger.info(f"WebSocket connection established for user {current_user.id} ({current_user.full_name})")
        await chat(websocket, supervisor, config, context)
    except WebSocketDisconnect:
        logger.info('Client disconnected normally')
    except (AgentInternalError, OAuthError, DatabaseError) as e:
        await send_error_message(websocket, str(e))
    except Exception as e:
        await send_error_message(websocket, str(e))
        logger.error(f"Unexpected AI chat error: {e}", exc_info=True)
