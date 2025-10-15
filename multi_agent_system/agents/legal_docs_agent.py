import os
import logging
from typing import Any
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from ..config import LLM_MODEL
from ..exceptions import AgentInternalError
from ..utils import load_prompt
from ..tools import create_custom_handoff_tool

logger = logging.getLogger(__name__)


class LegalDocsAgentManager:
    def __init__(self, legal_docs_token: str | None, llm_model: str = LLM_MODEL) -> None:
        self.agent_name = 'legal_docs_app_agent'
        self.legal_docs_token = legal_docs_token
        self.handoff_tool = create_custom_handoff_tool(
            agent_name=self.agent_name,
            description="Ask legal_docs_app_agent for help when user's requests are related to interaction with app, like: maintaining users, clients, legal documents templates etc."
        )
        self.llm_model = llm_model


    async def _get_legal_docs_mcp_tools(self) -> list[BaseTool]:
        """Get MCP tools from Legal Docs API."""
        if not self.legal_docs_token:
            raise ValueError("Legal Docs API token is required")

        mcp_client = MultiServerMCPClient({
            "fastapi_app": {
                "url": os.getenv('LEGAL_DOCS_MCP'),
                "transport": "streamable_http",
                "headers": {
                    "Authorization": f"Bearer {self.legal_docs_token}"
                }
            }
        })
        mcp_tools = await mcp_client.get_tools()
        return mcp_tools


    async def create_agent(self) -> Any:
        """Create and configure the legal docs agent with MCP tools."""
        try:
            mcp_tools = await self._get_legal_docs_mcp_tools()
            legal_docs_agent = create_react_agent(
                self.llm_model,
                name=self.agent_name,
                tools=mcp_tools,
                prompt=load_prompt('legal_docs_agent/v1.txt')
            )
            return legal_docs_agent
        except ValueError as e:
            logger.error(f"Legal Docs Agent token error: {e}", exc_info=True)
            raise AgentInternalError('Legal Docs authorization is required') from e
        except Exception as e:
            logger.error(f"Unexpected Legal Docs Agent error: {e}", exc_info=True)
            raise AgentInternalError("Failed to create legal docs agent") from e
