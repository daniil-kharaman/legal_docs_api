import logging
from typing import Callable, Annotated
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_tavily import TavilySearch
from langchain_core.tools import BaseTool, tool as create_tool, InjectedToolCallId
from langgraph.runtime import get_runtime
from langgraph.types import Command, interrupt
from langgraph.errors import GraphInterrupt
from langgraph.types import Send
from storage import db_models
from storage.database import get_db_session
from .agent_validation import email_db_validation
from .schemas import ContextSchema
from .utils import parse_full_name

logger = logging.getLogger(__name__)


search_tool = TavilySearch(max_results=2)


@create_tool
@email_db_validation
def get_email_from_database(client_full_name: str) -> list | str:
    """Retrieve client email from database by name and optional birthdate."""
    runtime = get_runtime(ContextSchema)
    first_name, last_name = parse_full_name(client_full_name)
    with get_db_session() as db:
        query = db.query(db_models.Client).filter(
            db_models.Client.firstname == first_name,
            db_models.Client.lastname == last_name,
            db_models.Client.user_id == runtime.context.user_id
        )
        clients = query.all()
        return [client.email for client in clients]


def add_human_in_the_loop(
    tool: Callable | BaseTool,
    llm: str,
    email: bool | None = None
) -> BaseTool:
    """Wrap a tool to support human-in-the-loop review."""
    if not isinstance(tool, BaseTool):
        tool = create_tool(tool)

    @create_tool(
        tool.name,
        description=tool.description,
        args_schema=tool.args_schema
    )

    def call_tool_with_interrupt(config: RunnableConfig, **tool_input) -> str:
        try:
            user_response = interrupt(f"Check the data before the execution please: \n\n{tool_input}")

            llm_chat = init_chat_model(llm).invoke(
                f"""Analyze the user's response and determine their intent. Return ONLY one of these exact words:
                - 'proceed' if user wants to continue with the action (examples: "send it", "ok", "yes", "proceed", "continue")
                - 'changes' if user wants to modify something (examples: "change subject", "modify message", "edit")
                - 'cancel' if user wants to stop/cancel the action (examples: "cancel", "stop", "don't send", "abort", "no")

                User input: {user_response}""")

            intent = llm_chat.content.lower().strip()

            if 'proceed' in intent:
                if email:
                    tool_input['message'] = tool_input['message'].replace('\n', '<br>')
                tool_response = tool.invoke(tool_input, config)
                return tool_response
            elif 'changes' in intent:
                return f"ACTION CANCELLED - User requested modifications: {user_response}. Implement desired modifications and retry."
            else:  # cancel or any other response
                return f"ACTION CANCELLED - User cancelled the operation. Abort the execution of operation."
        except GraphInterrupt:
            # Re-raise GraphInterrupt so LangGraph can handle the interrupt flow
            raise
        except Exception as e:
            logger.error(f"Error while calling the tool with interrupt: {e}", exc_info=True)
            return 'ERROR - Action was not completed due to the internal error.'

    return call_tool_with_interrupt


def create_custom_handoff_tool(
    agent_name: str, description: str | None = None, send_fullname: bool | None = None
) -> BaseTool:
    """
    Create a custom tool for handing off tasks between agents.

    Unlike the default handoff tool which passes all messages to sub-agents,
    this custom implementation only passes task descriptions and user preferences (if they exist).
    """
    name = f"assign_task_to_{agent_name}"
    description = description or f"Ask {agent_name} for help."

    @create_tool(name, description=description)
    def handoff_tool(
        task_description: Annotated[
            str,
            "Description of what the next agent should do, including all of the relevant context.",
        ],
        tool_call_id: Annotated[str, InjectedToolCallId],
        learned_user_preferences: Annotated[
            str | None,
            "Additional instructions for the next agent ONLY IF you learned something from the user's typical actions concerning the tasks related to next agent's expertise"
        ] = None,
    ) -> Command:
        from .exceptions import AgentInternalError

        try:
            tool_message = ToolMessage(
                content=f"Successfully transferred to {agent_name}",
                name=name,
                tool_call_id=tool_call_id,
            )

            content = f"""Task: {task_description}"""

            if send_fullname:
                content += f"\nUser fullname: {get_runtime(ContextSchema).context.user_full_name}"

            if learned_user_preferences:
                preferences_task = (f"\nUser Preferences & Learned Patterns: {learned_user_preferences}"
                                    f"Please incorporate these preferences into your response.")

                content += preferences_task
            task_description_message = HumanMessage(content)
            agent_input = {"messages": [task_description_message]}
            return Command(
                goto=[Send(agent_name, agent_input)],
                graph=Command.PARENT,
                update={'messages': [tool_message]}
            )
        except Exception as e:
            logger.error(f"Agent handoff error: {e}", exc_info=True)
            raise AgentInternalError(f"Failed to execute handoff to {agent_name}") from e
    return handoff_tool
