import logging
from typing import Any
from langchain.chat_models import init_chat_model
from langgraph_supervisor import create_supervisor
from langgraph_supervisor.handoff import create_forward_message_tool
from langmem.short_term import SummarizationNode
from ..config import LLM_MODEL
from ..schemas import ContextSchema, CustomState
from ..exceptions import AgentInternalError
from ..utils import load_prompt
from ..tools import search_tool
from ..database import get_checkpointer

logger = logging.getLogger(__name__)


class SupervisorAgentManager:
    def __init__(self, agents: list, handoff_tools: list, llm_model: str = LLM_MODEL) -> None:
        self.agent_name = 'supervisor'
        self.agents = agents
        self.handoff_tools = handoff_tools
        self.llm_model = llm_model
        self.summarization_node = SummarizationNode(
            model=init_chat_model(self.llm_model),
            max_tokens=50000,  # Increased for longer conversations before summarization
            max_summary_tokens=2000  # More detailed summaries to retain important context
        )
        self.forwarding_tool = create_forward_message_tool(self.agent_name)


    async def create_agent(self) -> Any:
        """Create and configure the main supervisor agent with sub-agents and tools."""
        try:

            main_supervisor = create_supervisor(
                model=init_chat_model(self.llm_model),
                agents=self.agents,
                prompt=load_prompt('supervisor_agent/v1.txt'),
                tools=[self.forwarding_tool, search_tool] + self.handoff_tools,
                supervisor_name=self.agent_name,
                context_schema=ContextSchema,
                add_handoff_messages=False,
                add_handoff_back_messages=False,
                state_schema=CustomState,
                pre_model_hook=self.summarization_node
            ).compile(checkpointer=await get_checkpointer(), name=self.agent_name)
            return main_supervisor
        except Exception as e:
            logger.error(f"Unexpected Supervisor Agent error: {e}", exc_info=True)
            raise AgentInternalError("Failed to create supervisor agent") from e
