import logging
from typing import Any
from google.oauth2.credentials import Credentials
from langchain_core.messages import AIMessage
from langgraph.types import Command
from .exceptions import AgentInternalError
from .utils import safe_create_agent
from .agents import EmailAgentManager, CalendarAgentManager, LegalDocsAgentManager, SupervisorAgentManager

logger = logging.getLogger(__name__)


class SupervisorSystemManager:
    def __init__(self, user_id: str, legal_docs_token: str | None, google_credentials: Credentials | None) -> None:
        self.user_id = user_id
        self.legal_docs_token = legal_docs_token
        self.google_credentials = google_credentials
        self._supervisor_agent = None
        self.build_info = {}


    async def build(self) -> None:
        """Build the supervisor system."""
        built_agents = []
        built_handoff_tools = []
        managers = [
            EmailAgentManager(self.google_credentials),
            CalendarAgentManager(self.google_credentials),
            LegalDocsAgentManager(self.legal_docs_token)
        ]

        for manager in managers:
            await safe_create_agent(manager, self, built_agents, built_handoff_tools)

        if not built_agents:
            logger.error('Failed to build any agents. Cannot create supervisor.')
            raise AgentInternalError("Failed to build any agents - cannot create supervisor system")


        supervisor_agent_manager = SupervisorAgentManager(agents=built_agents, handoff_tools=built_handoff_tools)
        self._supervisor_agent = await supervisor_agent_manager.create_agent()

        logger.info(f"Supervisor built successfully with agents: {[agent.name for agent in built_agents]}")


    def _process_node_messages(self, node_name: str, node_state: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process messages from a single node and return the event to yield.
        """
        if node_name.startswith('__'):
            return None

        if not (node_state and isinstance(node_state, dict)):
            return None

        messages = node_state.get('messages', [])
        if not messages:
            return None

        last_message = messages[-1]

        if not (hasattr(last_message, 'content') and
                last_message.content and
                isinstance(last_message, AIMessage)):
            return None

        message_name = getattr(last_message, 'name', node_name)

        # Check if conversation is complete (supervisor finished)
        if node_name == 'supervisor':
            finish_reason = getattr(last_message, 'response_metadata', {}).get('finish_reason')
            if finish_reason == 'STOP':
                return {
                    'type': 'complete',
                    'content': last_message.content,
                    'agent': message_name
                }

        # Sub-Agent final message
        return {
            'type': 'message',
            'content': last_message.content,
            'agent': message_name
        }


    async def stream_agent_events(self, user_message: str, user_config: dict[str, Any], user_context: dict[str, Any]):
        """
        Stream supervisor messages and handle interrupts for WebSocket communication.

        This async generator yields supervisor messages as they arrive and handles
        interrupt events that require user input.
        """
        try:
            events = self._supervisor_agent.astream(
                {"messages": [{"role": "user", "content": user_message}]},
                config=user_config,
                context=user_context
            )

            async for event in events:
                # Check if this is an interrupt event (supervisor needs user input)
                if '__interrupt__' in event:
                    yield {
                        'type': 'interrupt',
                        'content': event['__interrupt__'][0].value
                    }
                    return

                for node_name, node_state in event.items():
                    result = self._process_node_messages(node_name, node_state)
                    if result:
                        yield result
                        if result['type'] == 'complete':
                            return

        except Exception as e:
            logger.error(f"Stream error during agent execution: {e}", exc_info=True)
            raise AgentInternalError("Failed to stream agent events") from e


    async def resume_agent_after_interrupt(
            self, user_response: str,
            user_config: dict[str, Any],
            user_context: dict[str, Any]
    ):
        """
        Resume agent execution after an interrupt with the user's response.

        After the agent sends an interrupt, use this function to continue execution
        by providing the user's response to the interrupt prompt.
        """

        try:
            # Resume the agent with the user's response
            events = self._supervisor_agent.astream(
                Command(resume=user_response),
                config=user_config,
                context=user_context
            )

            async for event in events:
                # Handle nested interrupts (agent might interrupt again)
                if '__interrupt__' in event:
                    yield {
                        'type': 'interrupt',
                        'content': event['__interrupt__'][0].value
                    }
                    return

                for node_name, node_state in event.items():
                    result = self._process_node_messages(node_name, node_state)
                    if result:
                        yield result
                        if result['type'] == 'complete':
                            return

        except Exception as e:
            logger.error(f"Resume error during agent execution: {e}", exc_info=True)
            raise AgentInternalError("Failed to resume agent after interrupt") from e
