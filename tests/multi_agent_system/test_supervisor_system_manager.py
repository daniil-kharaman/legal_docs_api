import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from multi_agent_system import SupervisorSystemManager, AgentInternalError
from multi_agent_system.utils import safe_create_agent


class TestSupervisorSystemManager:
    """Tests for SupervisorSystemManager"""

    def test_init(self, mock_google_credentials):
        """Test SupervisorSystemManager initialization"""
        manager = SupervisorSystemManager(
            user_id="user123",
            legal_docs_token="token",
            google_credentials=mock_google_credentials
        )

        assert manager.user_id == "user123"
        assert manager.legal_docs_token == "token"
        assert manager.google_credentials == mock_google_credentials
        assert manager._supervisor_agent is None
        assert manager.build_info == {}

    @pytest.mark.asyncio
    @patch('multi_agent_system.system_manager.SupervisorAgentManager')
    @patch('multi_agent_system.system_manager.LegalDocsAgentManager')
    @patch('multi_agent_system.system_manager.CalendarAgentManager')
    @patch('multi_agent_system.system_manager.EmailAgentManager')
    async def test_build_success_all_agents(self, mock_email_class, mock_calendar_class,
                                            mock_legal_class, mock_supervisor_class,
                                            mock_google_credentials):
        """Test successful build with all agents"""
        # Mock agent managers
        mock_email_agent = Mock()
        mock_email_agent.name = "email_agent"
        mock_email_manager = AsyncMock()
        mock_email_manager.agent_name = "email_agent"
        mock_email_manager.create_agent = AsyncMock(return_value=mock_email_agent)
        mock_email_manager.handoff_tool = Mock()
        mock_email_class.return_value = mock_email_manager

        mock_calendar_agent = Mock()
        mock_calendar_agent.name = "calendar_agent"
        mock_calendar_manager = AsyncMock()
        mock_calendar_manager.agent_name = "calendar_agent"
        mock_calendar_manager.create_agent = AsyncMock(return_value=mock_calendar_agent)
        mock_calendar_manager.handoff_tool = Mock()
        mock_calendar_class.return_value = mock_calendar_manager

        mock_legal_agent = Mock()
        mock_legal_agent.name = "legal_docs_app_agent"
        mock_legal_manager = AsyncMock()
        mock_legal_manager.agent_name = "legal_docs_app_agent"
        mock_legal_manager.create_agent = AsyncMock(return_value=mock_legal_agent)
        mock_legal_manager.handoff_tool = Mock()
        mock_legal_class.return_value = mock_legal_manager

        mock_supervisor_agent = Mock()
        mock_supervisor_manager = AsyncMock()
        mock_supervisor_manager.create_agent = AsyncMock(return_value=mock_supervisor_agent)
        mock_supervisor_class.return_value = mock_supervisor_manager

        manager = SupervisorSystemManager(
            user_id="user123",
            legal_docs_token="token",
            google_credentials=mock_google_credentials
        )

        await manager.build()

        assert manager._supervisor_agent == mock_supervisor_agent
        assert manager.build_info["email_agent"] is True
        assert manager.build_info["calendar_agent"] is True
        assert manager.build_info["legal_docs_app_agent"] is True

    @pytest.mark.asyncio
    @patch('multi_agent_system.system_manager.SupervisorAgentManager')
    @patch('multi_agent_system.system_manager.LegalDocsAgentManager')
    @patch('multi_agent_system.system_manager.CalendarAgentManager')
    @patch('multi_agent_system.system_manager.EmailAgentManager')
    async def test_build_partial_success(self, mock_email_class, mock_calendar_class,
                                         mock_legal_class, mock_supervisor_class,
                                         mock_google_credentials):
        """Test build with some agents failing"""
        # Mock email agent - success
        mock_email_agent = Mock()
        mock_email_agent.name = "email_agent"
        mock_email_manager = AsyncMock()
        mock_email_manager.agent_name = "email_agent"
        mock_email_manager.create_agent = AsyncMock(return_value=mock_email_agent)
        mock_email_manager.handoff_tool = Mock()
        mock_email_class.return_value = mock_email_manager

        # Mock calendar agent - failure
        mock_calendar_manager = AsyncMock()
        mock_calendar_manager.agent_name = "calendar_agent"
        mock_calendar_manager.create_agent = AsyncMock(
            side_effect=AgentInternalError("Calendar failed")
        )
        mock_calendar_class.return_value = mock_calendar_manager

        # Mock legal agent - success
        mock_legal_agent = Mock()
        mock_legal_agent.name = "legal_docs_app_agent"
        mock_legal_manager = AsyncMock()
        mock_legal_manager.agent_name = "legal_docs_app_agent"
        mock_legal_manager.create_agent = AsyncMock(return_value=mock_legal_agent)
        mock_legal_manager.handoff_tool = Mock()
        mock_legal_class.return_value = mock_legal_manager

        mock_supervisor_agent = Mock()
        mock_supervisor_manager = AsyncMock()
        mock_supervisor_manager.create_agent = AsyncMock(return_value=mock_supervisor_agent)
        mock_supervisor_class.return_value = mock_supervisor_manager

        manager = SupervisorSystemManager(
            user_id="user123",
            legal_docs_token="token",
            google_credentials=mock_google_credentials
        )

        await manager.build()

        assert manager._supervisor_agent == mock_supervisor_agent
        assert manager.build_info["email_agent"] is True
        assert manager.build_info["calendar_agent"] is False
        assert manager.build_info["legal_docs_app_agent"] is True

    @pytest.mark.asyncio
    @patch('multi_agent_system.system_manager.LegalDocsAgentManager')
    @patch('multi_agent_system.system_manager.CalendarAgentManager')
    @patch('multi_agent_system.system_manager.EmailAgentManager')
    async def test_build_all_agents_fail(self, mock_email_class, mock_calendar_class,
                                        mock_legal_class, mock_google_credentials):
        """Test build when all agents fail"""
        # All managers fail
        mock_email_manager = AsyncMock()
        mock_email_manager.agent_name = "email_agent"
        mock_email_manager.create_agent = AsyncMock(
            side_effect=AgentInternalError("Email failed")
        )
        mock_email_class.return_value = mock_email_manager

        mock_calendar_manager = AsyncMock()
        mock_calendar_manager.agent_name = "calendar_agent"
        mock_calendar_manager.create_agent = AsyncMock(
            side_effect=AgentInternalError("Calendar failed")
        )
        mock_calendar_class.return_value = mock_calendar_manager

        mock_legal_manager = AsyncMock()
        mock_legal_manager.agent_name = "legal_docs_app_agent"
        mock_legal_manager.create_agent = AsyncMock(
            side_effect=AgentInternalError("Legal failed")
        )
        mock_legal_class.return_value = mock_legal_manager

        manager = SupervisorSystemManager(
            user_id="user123",
            legal_docs_token="token",
            google_credentials=mock_google_credentials
        )

        with pytest.raises(AgentInternalError, match="Failed to build any agents"):
            await manager.build()

    def test_process_node_messages_ai_message(self):
        """Test processing AI message from node"""
        manager = SupervisorSystemManager("user123", "token", None)

        ai_message = AIMessage(content="Hello from agent", name="test_agent")
        node_state = {"messages": [ai_message]}

        result = manager._process_node_messages("test_agent", node_state)

        assert result is not None
        assert result["type"] == "message"
        assert result["content"] == "Hello from agent"
        assert result["agent"] == "test_agent"

    def test_process_node_messages_supervisor_complete(self):
        """Test processing supervisor completion message"""
        manager = SupervisorSystemManager("user123", "token", None)

        ai_message = AIMessage(
            content="Task completed",
            name="supervisor",
            response_metadata={"finish_reason": "STOP"}
        )
        node_state = {"messages": [ai_message]}

        result = manager._process_node_messages("supervisor", node_state)

        assert result is not None
        assert result["type"] == "complete"
        assert result["content"] == "Task completed"
        assert result["agent"] == "supervisor"

    def test_process_node_messages_skip_internal(self):
        """Test skipping internal keys"""
        manager = SupervisorSystemManager("user123", "token", None)

        result = manager._process_node_messages("__internal__", {"messages": []})

        assert result is None

    def test_process_node_messages_no_messages(self):
        """Test processing node with no messages"""
        manager = SupervisorSystemManager("user123", "token", None)

        result = manager._process_node_messages("test_agent", {"messages": []})

        assert result is None

    def test_process_node_messages_non_ai_message(self):
        """Test processing non-AI message"""
        manager = SupervisorSystemManager("user123", "token", None)

        human_message = HumanMessage(content="User input")
        node_state = {"messages": [human_message]}

        result = manager._process_node_messages("test_agent", node_state)

        assert result is None

    def test_process_node_messages_empty_content(self):
        """Test processing AI message with empty content"""
        manager = SupervisorSystemManager("user123", "token", None)

        ai_message = AIMessage(content="", name="test_agent")
        node_state = {"messages": [ai_message]}

        result = manager._process_node_messages("test_agent", node_state)

        assert result is None

    @pytest.mark.asyncio
    async def test_stream_agent_events_success(self):
        """Test successful agent event streaming"""
        manager = SupervisorSystemManager("user123", "token", None)

        # Mock supervisor agent
        ai_message1 = AIMessage(content="Processing...", name="supervisor")
        ai_message2 = AIMessage(
            content="Done",
            name="supervisor",
            response_metadata={"finish_reason": "STOP"}
        )

        async def mock_astream(*args, **kwargs):
            yield {"supervisor": {"messages": [ai_message1]}}
            yield {"supervisor": {"messages": [ai_message2]}}

        mock_supervisor = Mock()
        mock_supervisor.astream = mock_astream
        manager._supervisor_agent = mock_supervisor

        results = []
        async for event in manager.stream_agent_events(
            "test message",
            {"configurable": {"thread_id": "123"}},
            {"user_id": "user123"}
        ):
            results.append(event)

        assert len(results) == 2
        assert results[0]["type"] == "message"
        assert results[1]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_stream_agent_events_interrupt(self):
        """Test agent event streaming with interrupt"""
        manager = SupervisorSystemManager("user123", "token", None)

        # Mock supervisor agent with interrupt
        async def mock_astream(*args, **kwargs):
            interrupt_obj = Mock()
            interrupt_obj.value = "Please confirm action"
            yield {"__interrupt__": [interrupt_obj]}

        mock_supervisor = Mock()
        mock_supervisor.astream = mock_astream
        manager._supervisor_agent = mock_supervisor

        results = []
        async for event in manager.stream_agent_events(
            "test message",
            {"configurable": {"thread_id": "123"}},
            {"user_id": "user123"}
        ):
            results.append(event)

        assert len(results) == 1
        assert results[0]["type"] == "interrupt"
        assert results[0]["content"] == "Please confirm action"

    @pytest.mark.asyncio
    async def test_stream_agent_events_error(self):
        """Test agent event streaming with error"""
        manager = SupervisorSystemManager("user123", "token", None)

        # Mock supervisor agent that raises error
        async def mock_astream(*args, **kwargs):
            raise Exception("Stream error")
            yield  # Make it a generator

        mock_supervisor = Mock()
        mock_supervisor.astream = mock_astream
        manager._supervisor_agent = mock_supervisor

        with pytest.raises(AgentInternalError, match="Failed to stream agent events"):
            async for event in manager.stream_agent_events(
                "test message",
                {"configurable": {"thread_id": "123"}},
                {"user_id": "user123"}
            ):
                pass

    @pytest.mark.asyncio
    async def test_resume_agent_after_interrupt_success(self):
        """Test successful resume after interrupt"""
        manager = SupervisorSystemManager("user123", "token", None)

        # Mock supervisor agent
        ai_message = AIMessage(
            content="Action completed",
            name="supervisor",
            response_metadata={"finish_reason": "STOP"}
        )

        async def mock_astream(*args, **kwargs):
            yield {"supervisor": {"messages": [ai_message]}}

        mock_supervisor = Mock()
        mock_supervisor.astream = mock_astream
        manager._supervisor_agent = mock_supervisor

        results = []
        async for event in manager.resume_agent_after_interrupt(
            "proceed",
            {"configurable": {"thread_id": "123"}},
            {"user_id": "user123"}
        ):
            results.append(event)

        assert len(results) == 1
        assert results[0]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_resume_agent_nested_interrupt(self):
        """Test resume with nested interrupt"""
        manager = SupervisorSystemManager("user123", "token", None)

        # Mock supervisor agent with another interrupt
        async def mock_astream(*args, **kwargs):
            interrupt_obj = Mock()
            interrupt_obj.value = "Another confirmation needed"
            yield {"__interrupt__": [interrupt_obj]}

        mock_supervisor = Mock()
        mock_supervisor.astream = mock_astream
        manager._supervisor_agent = mock_supervisor

        results = []
        async for event in manager.resume_agent_after_interrupt(
            "proceed",
            {"configurable": {"thread_id": "123"}},
            {"user_id": "user123"}
        ):
            results.append(event)

        assert len(results) == 1
        assert results[0]["type"] == "interrupt"


class TestSafeCreateAgent:
    """Tests for safe_create_agent helper function"""

    @pytest.mark.asyncio
    async def testsafe_create_agent_success(self):
        """Test successful agent creation"""
        # Mock agent manager
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_manager = AsyncMock()
        mock_manager.agent_name = "test_agent"
        mock_manager.create_agent = AsyncMock(return_value=mock_agent)
        mock_manager.handoff_tool = Mock()

        # Mock system manager
        mock_system = Mock()
        mock_system.build_info = {}

        built_agents = []
        built_tools = []

        await safe_create_agent(mock_manager, mock_system, built_agents, built_tools)

        assert len(built_agents) == 1
        assert built_agents[0] == mock_agent
        assert len(built_tools) == 1
        assert mock_system.build_info["test_agent"] is True

    @pytest.mark.asyncio
    async def testsafe_create_agent_failure(self):
        """Test agent creation failure"""
        # Mock agent manager that fails
        mock_manager = AsyncMock()
        mock_manager.agent_name = "test_agent"
        mock_manager.create_agent = AsyncMock(
            side_effect=AgentInternalError("Creation failed")
        )

        # Mock system manager
        mock_system = Mock()
        mock_system.build_info = {}

        built_agents = []
        built_tools = []

        # Should not raise exception, just log
        await safe_create_agent(mock_manager, mock_system, built_agents, built_tools)

        assert len(built_agents) == 0
        assert len(built_tools) == 0
        assert mock_system.build_info["test_agent"] is False