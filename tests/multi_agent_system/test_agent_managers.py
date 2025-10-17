import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from multi_agent_system.agents import (
    EmailAgentManager,
    CalendarAgentManager,
    LegalDocsAgentManager,
    SupervisorAgentManager
)
from multi_agent_system import AgentInternalError
from multi_agent_system.config import LLM_MODEL


class TestEmailAgentManager:
    """Tests for EmailAgentManager"""

    def test_init(self, mock_google_credentials):
        """Test EmailAgentManager initialization"""
        manager = EmailAgentManager(mock_google_credentials)

        assert manager.agent_name == 'email_agent'
        assert manager.google_credentials == mock_google_credentials
        assert manager.llm_model == LLM_MODEL
        assert manager.handoff_tool is not None

    def test_init_custom_llm(self, mock_google_credentials):
        """Test EmailAgentManager with custom LLM model"""
        custom_model = "openai:gpt-4"
        manager = EmailAgentManager(mock_google_credentials, llm_model=custom_model)

        assert manager.llm_model == custom_model

    def test_get_gmail_send_tool_success(self, mock_google_credentials):
        """Test getting Gmail send tool successfully"""
        with patch('multi_agent_system.agents.email_agent.gmail_build') as mock_build, \
             patch('multi_agent_system.agents.email_agent.GmailToolkit') as mock_toolkit_class:

            # Mock the toolkit
            mock_send_tool = Mock()
            mock_send_tool.name = 'send_gmail_message'
            mock_toolkit = Mock()
            mock_toolkit.get_tools.return_value = [mock_send_tool]
            mock_toolkit_class.return_value = mock_toolkit

            manager = EmailAgentManager(mock_google_credentials)
            result = manager._get_gmail_send_tool()

            assert result == mock_send_tool
            mock_build.assert_called_once_with(credentials=mock_google_credentials)

    def test_get_gmail_send_tool_no_credentials(self):
        """Test getting Gmail tool without credentials"""
        manager = EmailAgentManager(None)

        with pytest.raises(ValueError, match="Google credentials are required"):
            manager._get_gmail_send_tool()

    @pytest.mark.asyncio
    @patch('multi_agent_system.agents.email_agent.create_react_agent')
    @patch('multi_agent_system.agents.email_agent.add_human_in_the_loop')
    @patch('multi_agent_system.agents.email_agent.load_prompt')
    async def test_create_agent_success(self, mock_load_prompt, mock_hitl, mock_create_agent,
                                       mock_google_credentials):
        """Test successful agent creation"""
        from langchain_core.tools import BaseTool

        with patch('multi_agent_system.agents.email_agent.gmail_build'), \
             patch('multi_agent_system.agents.email_agent.GmailToolkit') as mock_toolkit_class:

            # Setup mocks
            mock_send_tool = Mock(spec=BaseTool)
            mock_send_tool.name = 'send_gmail_message'
            mock_toolkit = Mock()
            mock_toolkit.get_tools.return_value = [mock_send_tool]
            mock_toolkit_class.return_value = mock_toolkit

            mock_hitl.return_value = Mock(spec=BaseTool)
            mock_load_prompt.return_value = "Test prompt"
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent

            manager = EmailAgentManager(mock_google_credentials)
            result = await manager.create_agent()

            assert result == mock_agent
            mock_load_prompt.assert_called_once_with('email_agent/v1.txt')
            mock_create_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_no_credentials(self):
        """Test agent creation without credentials raises error"""
        manager = EmailAgentManager(None)

        with pytest.raises(AgentInternalError, match="Google authorization is required"):
            await manager.create_agent()

    @pytest.mark.asyncio
    @patch('multi_agent_system.agents.email_agent.gmail_build')
    async def test_create_agent_unexpected_error(self, mock_build, mock_google_credentials):
        """Test agent creation with unexpected error"""
        mock_build.side_effect = Exception("Unexpected error")

        manager = EmailAgentManager(mock_google_credentials)

        with pytest.raises(AgentInternalError, match="Failed to create email agent"):
            await manager.create_agent()


class TestCalendarAgentManager:
    """Tests for CalendarAgentManager"""

    def test_init(self, mock_google_credentials):
        """Test CalendarAgentManager initialization"""
        manager = CalendarAgentManager(mock_google_credentials)

        assert manager.agent_name == 'calendar_agent'
        assert manager.google_credentials == mock_google_credentials
        assert manager.llm_model == LLM_MODEL
        assert manager.handoff_tool is not None

    def test_get_calendar_tools_success(self, mock_google_credentials):
        """Test getting calendar tools successfully"""
        with patch('multi_agent_system.agents.calendar_agent.calendar_build') as mock_build, \
             patch('multi_agent_system.agents.calendar_agent.CalendarToolkit') as mock_toolkit_class:

            # Mock the toolkit
            mock_tools = [Mock(), Mock()]
            mock_toolkit = Mock()
            mock_toolkit.get_tools.return_value = mock_tools
            mock_toolkit_class.return_value = mock_toolkit

            manager = CalendarAgentManager(mock_google_credentials)
            result = manager._get_calendar_tools()

            assert result == mock_tools
            mock_build.assert_called_once_with(credentials=mock_google_credentials)

    def test_get_calendar_tools_no_credentials(self):
        """Test getting calendar tools without credentials"""
        manager = CalendarAgentManager(None)

        with pytest.raises(ValueError, match="Google credentials are required"):
            manager._get_calendar_tools()

    @pytest.mark.asyncio
    @patch('multi_agent_system.agents.calendar_agent.create_react_agent')
    @patch('multi_agent_system.agents.calendar_agent.load_prompt')
    async def test_create_agent_success(self, mock_load_prompt, mock_create_agent,
                                       mock_google_credentials):
        """Test successful calendar agent creation"""
        from langchain_core.tools import BaseTool

        with patch('multi_agent_system.agents.calendar_agent.calendar_build'), \
             patch('multi_agent_system.agents.calendar_agent.CalendarToolkit') as mock_toolkit_class:

            # Setup mocks
            mock_tools = [Mock(spec=BaseTool), Mock(spec=BaseTool)]
            mock_toolkit = Mock()
            mock_toolkit.get_tools.return_value = mock_tools
            mock_toolkit_class.return_value = mock_toolkit

            mock_load_prompt.return_value = "Calendar prompt"
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent

            manager = CalendarAgentManager(mock_google_credentials)
            result = await manager.create_agent()

            assert result == mock_agent
            mock_load_prompt.assert_called_once_with('calendar_agent/v1.txt')
            mock_create_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_no_credentials(self):
        """Test calendar agent creation without credentials"""
        manager = CalendarAgentManager(None)

        with pytest.raises(AgentInternalError, match="Google authorization is required"):
            await manager.create_agent()


class TestLegalDocsAgentManager:
    """Tests for LegalDocsAgentManager"""

    def test_init(self):
        """Test LegalDocsAgentManager initialization"""
        token = "test_token"
        manager = LegalDocsAgentManager(token)

        assert manager.agent_name == 'legal_docs_app_agent'
        assert manager.legal_docs_token == token
        assert manager.llm_model == LLM_MODEL
        assert manager.handoff_tool is not None

    @pytest.mark.asyncio
    @patch('multi_agent_system.agents.legal_docs_agent.MultiServerMCPClient')
    async def test_get_legal_docs_mcp_tools_success(self, mock_mcp_class, mock_env_vars):
        """Test getting MCP tools successfully"""
        with patch.dict('os.environ', mock_env_vars):
            # Mock MCP client
            mock_tools = [Mock(), Mock()]
            mock_client = AsyncMock()
            mock_client.get_tools = AsyncMock(return_value=mock_tools)
            mock_mcp_class.return_value = mock_client

            manager = LegalDocsAgentManager("test_token")
            result = await manager._get_legal_docs_mcp_tools()

            assert result == mock_tools
            mock_client.get_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_legal_docs_mcp_tools_no_token(self):
        """Test getting MCP tools without token"""
        manager = LegalDocsAgentManager(None)

        with pytest.raises(ValueError, match="Legal Docs API token is required"):
            await manager._get_legal_docs_mcp_tools()

    @pytest.mark.asyncio
    @patch('multi_agent_system.agents.legal_docs_agent.create_react_agent')
    @patch('multi_agent_system.agents.legal_docs_agent.load_prompt')
    @patch('multi_agent_system.agents.legal_docs_agent.MultiServerMCPClient')
    async def test_create_agent_success(self, mock_mcp_class, mock_load_prompt,
                                       mock_create_agent, mock_env_vars):
        """Test successful legal docs agent creation"""
        from langchain_core.tools import BaseTool

        with patch.dict('os.environ', mock_env_vars):
            # Mock MCP client
            mock_tools = [Mock(spec=BaseTool), Mock(spec=BaseTool)]
            mock_client = AsyncMock()
            mock_client.get_tools = AsyncMock(return_value=mock_tools)
            mock_mcp_class.return_value = mock_client

            mock_load_prompt.return_value = "Legal docs prompt"
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent

            manager = LegalDocsAgentManager("test_token")
            result = await manager.create_agent()

            assert result == mock_agent
            mock_load_prompt.assert_called_once_with('legal_docs_agent/v1.txt')
            mock_create_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_no_token(self):
        """Test legal docs agent creation without token"""
        manager = LegalDocsAgentManager(None)

        with pytest.raises(AgentInternalError, match="Legal Docs authorization is required"):
            await manager.create_agent()


class TestSupervisorAgentManager:
    """Tests for SupervisorAgentManager"""

    def test_init(self):
        """Test SupervisorAgentManager initialization"""
        mock_agents = [Mock(), Mock()]
        mock_tools = [Mock(), Mock()]

        manager = SupervisorAgentManager(mock_agents, mock_tools)

        assert manager.agent_name == 'supervisor'
        assert manager.agents == mock_agents
        assert manager.handoff_tools == mock_tools
        assert manager.llm_model == LLM_MODEL
        assert manager.summarization_node is not None
        assert manager.forwarding_tool is not None

    @pytest.mark.asyncio
    @patch('multi_agent_system.agents.supervisor_agent.create_supervisor')
    @patch('multi_agent_system.agents.supervisor_agent.load_prompt')
    @patch('multi_agent_system.agents.supervisor_agent.init_chat_model')
    async def test_create_agent_success(self, mock_init_model, mock_load_prompt,
                                       mock_create_supervisor):
        """Test successful supervisor agent creation"""
        from langchain_core.tools import BaseTool

        # Set up global checkpointer
        import multi_agent_system.database as ss
        ss._checkpointer = AsyncMock()

        mock_agents = [Mock(name="agent1"), Mock(name="agent2")]
        mock_tools = [Mock(spec=BaseTool), Mock(spec=BaseTool)]

        mock_model = Mock()
        mock_init_model.return_value = mock_model
        mock_load_prompt.return_value = "Supervisor prompt"

        # Mock supervisor creation
        mock_compiled = Mock()
        mock_supervisor = Mock()
        mock_supervisor.compile.return_value = mock_compiled
        mock_create_supervisor.return_value = mock_supervisor

        manager = SupervisorAgentManager(mock_agents, mock_tools)
        result = await manager.create_agent()

        assert result == mock_compiled
        mock_load_prompt.assert_called_once_with('supervisor_agent/v1.txt')
        mock_create_supervisor.assert_called_once()
        mock_supervisor.compile.assert_called_once()

    @pytest.mark.asyncio
    @patch('multi_agent_system.agents.supervisor_agent.create_supervisor')
    async def test_create_agent_error(self, mock_create_supervisor):
        """Test supervisor agent creation with error"""
        mock_agents = [Mock(), Mock()]
        mock_tools = [Mock(), Mock()]

        mock_create_supervisor.side_effect = Exception("Creation failed")

        manager = SupervisorAgentManager(mock_agents, mock_tools)

        with pytest.raises(AgentInternalError, match="Failed to create supervisor agent"):
            await manager.create_agent()

    def test_summarization_node_config(self):
        """Test summarization node configuration"""
        mock_agents = [Mock(), Mock()]
        mock_tools = [Mock(), Mock()]

        manager = SupervisorAgentManager(mock_agents, mock_tools)

        assert manager.summarization_node is not None
        # Verify summarization parameters are set correctly
        # Note: These are internal to SummarizationNode, so we just verify it exists