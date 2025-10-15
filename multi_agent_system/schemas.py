from pydantic.dataclasses import dataclass
from langgraph.prebuilt.chat_agent_executor import AgentState
from langmem.short_term import RunningSummary


@dataclass
class ContextSchema:
    user_full_name: str
    user_id: str


class CustomState(AgentState):
    # this key is to keep track of previous summary information
    # to make sure agent does not summarize on every LLM call
    context: dict[str, RunningSummary]
