import logging
from typing import Any
from google.oauth2.credentials import Credentials
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import build_resource_service as gmail_build
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from ..config import LLM_MODEL
from ..exceptions import AgentInternalError
from ..utils import load_prompt
from ..tools import get_email_from_database, add_human_in_the_loop, create_custom_handoff_tool

logger = logging.getLogger(__name__)


class EmailAgentManager:
    def __init__(self, google_credentials: Credentials | None, llm_model: str = LLM_MODEL) -> None:
        self.agent_name = 'email_agent'
        self.google_credentials = google_credentials
        self.handoff_tool = create_custom_handoff_tool(
            agent_name=self.agent_name,
            description=f"Ask email_agent for help. Do not suggest email texts to email_agent. Just give him a task.",
            send_fullname=True
        )
        self.llm_model = llm_model


    def _get_gmail_send_tool(self) -> BaseTool:
        """Get Gmail send tool from Google API toolkit."""
        if not self.google_credentials:
            raise ValueError("Google credentials are required")
        gmail_api_resource = gmail_build(credentials=self.google_credentials)
        gmail_toolkit = GmailToolkit(api_resource=gmail_api_resource)
        gmail_tools = gmail_toolkit.get_tools()
        send_email_gmail = next(tool for tool in gmail_tools if tool.name == 'send_gmail_message')
        return send_email_gmail


    async def create_agent(self) -> Any:
        """Create and configure the email agent with Gmail tools."""
        try:
            send_gmail_tool = self._get_gmail_send_tool()
            send_gmail_tool_hitl = add_human_in_the_loop(send_gmail_tool, email=True, llm=self.llm_model)
            email_agent = create_react_agent(
                self.llm_model,
                name=self.agent_name,
                tools=[get_email_from_database, send_gmail_tool_hitl],
                prompt=load_prompt('email_agent/v1.txt')
            )
            return email_agent
        except ValueError as e:
            logger.error(f"Email Agent credentials error: {e}", exc_info=True)
            raise AgentInternalError('Google authorization is required') from e
        except Exception as e:
            logger.error(f"Unexpected Email Agent error: {e}", exc_info=True)
            raise AgentInternalError("Failed to create email agent") from e
