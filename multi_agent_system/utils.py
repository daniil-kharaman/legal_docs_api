import logging
from .config import PROMPTS_DIR
from .exceptions import AgentInternalError

logger = logging.getLogger(__name__)


def load_prompt(filename: str) -> str:
    """Load prompt from text file."""
    try:
        prompt_path = PROMPTS_DIR / filename
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError as e:
        logger.error(f"Prompt file not found: {filename}", exc_info=True)
        raise AgentInternalError(f"Missing prompt file: {filename}") from e
    except Exception as e:
        logger.error(f"Error reading prompt file {filename}: {e}", exc_info=True)
        raise AgentInternalError(f"Failed to load prompt: {filename}") from e


def parse_full_name(full_name: str) -> tuple[str, str]:
    """Parse full name into first and last name."""
    name_parts = full_name.strip().split()
    if len(name_parts) < 2:
        raise ValueError("Invalid full name format. Please provide first and last name.")
    return name_parts[0], name_parts[1]


async def safe_create_agent(agent_manager, system_manager, built_agents: list, built_handoff_tools: list):
    """Safely create an agent and handle errors."""
    try:
        agent = await agent_manager.create_agent()
        built_agents.append(agent)
        built_handoff_tools.append(agent_manager.handoff_tool)
        system_manager.build_info[agent_manager.agent_name] = True
    except AgentInternalError:
        system_manager.build_info[agent_manager.agent_name] = False
        logger.warning(f"{agent_manager.agent_name} was not built")
