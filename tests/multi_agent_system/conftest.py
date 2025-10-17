import pytest
import json
import os
from unittest.mock import Mock, MagicMock, AsyncMock
from google.oauth2.credentials import Credentials
from pathlib import Path


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    return {
        'LLM_MODEL': 'google_genai:gemini-2.5-flash',
        'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db',
        'LEGAL_DOCS_MCP': 'http://localhost:8000/mcp',
        'TAVILY_API_KEY': 'test_tavily_key'
    }


@pytest.fixture
def mock_google_credentials():
    """Mock Google OAuth2 credentials"""
    mock_creds = Mock(spec=Credentials)
    mock_creds.token = "test_token"
    mock_creds.refresh_token = "test_refresh_token"
    mock_creds.valid = True
    mock_creds.expired = False
    mock_creds.to_json.return_value = json.dumps({
        "token": "test_token",
        "refresh_token": "test_refresh_token",
        "scopes": ["email", "calendar"]
    })
    return mock_creds


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    mock_session = MagicMock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=False)
    return mock_session


@pytest.fixture
def mock_connection_pool():
    """Mock AsyncConnectionPool"""
    mock_pool = AsyncMock()
    mock_pool.close = AsyncMock()
    return mock_pool


@pytest.fixture
def mock_checkpointer():
    """Mock AsyncPostgresSaver"""
    mock_cp = AsyncMock()
    mock_cp.setup = AsyncMock()
    return mock_cp


@pytest.fixture
def mock_llm():
    """Mock LLM model"""
    mock_model = Mock()
    mock_response = Mock()
    mock_response.content = "proceed"
    mock_model.invoke.return_value = mock_response
    return mock_model


@pytest.fixture
def mock_gmail_toolkit():
    """Mock Gmail toolkit with tools"""
    mock_tool = Mock()
    mock_tool.name = "send_gmail_message"
    mock_tool.description = "Send email via Gmail"
    mock_tool.invoke.return_value = "Email sent successfully"

    mock_toolkit = Mock()
    mock_toolkit.get_tools.return_value = [mock_tool]
    return mock_toolkit


@pytest.fixture
def mock_calendar_toolkit():
    """Mock Calendar toolkit with tools"""
    mock_tool1 = Mock()
    mock_tool1.name = "create_calendar_event"
    mock_tool1.description = "Create calendar event"

    mock_tool2 = Mock()
    mock_tool2.name = "list_calendar_events"
    mock_tool2.description = "List calendar events"

    mock_toolkit = Mock()
    mock_toolkit.get_tools.return_value = [mock_tool1, mock_tool2]
    return mock_toolkit


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client with tools"""
    mock_tool1 = Mock()
    mock_tool1.name = "get_legal_document"
    mock_tool1.description = "Get legal document"

    mock_tool2 = Mock()
    mock_tool2.name = "create_legal_document"
    mock_tool2.description = "Create legal document"

    mock_client = AsyncMock()
    mock_client.get_tools = AsyncMock(return_value=[mock_tool1, mock_tool2])
    return mock_client


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create temporary prompts directory with test files"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Create test prompt files with new directory structure
    (prompts_dir / "email_agent").mkdir()
    (prompts_dir / "email_agent" / "v1.txt").write_text("You are an email agent.")

    (prompts_dir / "calendar_agent").mkdir()
    (prompts_dir / "calendar_agent" / "v1.txt").write_text("You are a calendar agent.")

    (prompts_dir / "legal_docs_agent").mkdir()
    (prompts_dir / "legal_docs_agent" / "v1.txt").write_text("You are a legal docs agent.")

    (prompts_dir / "supervisor_agent").mkdir()
    (prompts_dir / "supervisor_agent" / "v1.txt").write_text("You are a supervisor agent.")

    return prompts_dir


@pytest.fixture
def mock_runtime_context():
    """Mock runtime context"""
    mock_context = Mock()
    mock_context.user_full_name = "John Doe"
    mock_context.user_id = "user123"
    return mock_context


@pytest.fixture
def mock_agent():
    """Mock a basic agent"""
    mock_agent_obj = Mock()
    mock_agent_obj.name = "test_agent"
    mock_agent_obj.astream = AsyncMock()
    return mock_agent_obj