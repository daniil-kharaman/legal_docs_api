import logging
from typing import Any
from google.oauth2.credentials import Credentials
from langchain_google_community import CalendarToolkit
from langchain_google_community.calendar.utils import build_resource_service as calendar_build
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from ..config import LLM_MODEL
from ..exceptions import AgentInternalError
from ..utils import load_prompt
from ..tools import get_email_from_database, create_custom_handoff_tool

logger = logging.getLogger(__name__)


class CalendarAgentManager:
    def __init__(self, google_credentials: Credentials | None, llm_model: str = LLM_MODEL) -> None:
        self.agent_name = 'calendar_agent'
        self.google_credentials = google_credentials
        self.handoff_tool = create_custom_handoff_tool(
            agent_name=self.agent_name,
            description="Ask calendar_agent for help with scheduling, calendar events, appointments, and meeting management."
        )
        self.llm_model = llm_model


    def _get_calendar_tools(self) -> list[BaseTool]:
        """Get Google Calendar tools from Google API toolkit."""
        if not self.google_credentials:
            raise ValueError("Google credentials are required")
        calendar_api_resource = calendar_build(credentials=self.google_credentials)
        calendar_toolkit = CalendarToolkit(api_resource=calendar_api_resource)
        calendar_tools = calendar_toolkit.get_tools()
        return calendar_tools



    async def create_agent(self) -> Any:
        """Create and configure the calendar agent with Google Calendar tools."""
        try:
            calendar_tools = self._get_calendar_tools()
            calendar_agent = create_react_agent(
                self.llm_model,
                name=self.agent_name,
                tools=calendar_tools + [get_email_from_database],
                prompt=load_prompt('calendar_agent/v1.txt')
            )
            return calendar_agent
        except ValueError as e:
            logger.error(f"Calendar Agent credentials error: {e}", exc_info=True)
            raise AgentInternalError('Google authorization is required') from e
        except Exception as e:
            logger.error(f"Unexpected Calendar Agent error: {e}", exc_info=True)
            raise AgentInternalError("Failed to create calendar agent") from e
