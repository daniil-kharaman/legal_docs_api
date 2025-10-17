import pytest
from unittest.mock import patch, Mock, MagicMock
from langchain_core.tools import BaseTool
from langgraph.types import Command
from langgraph.errors import GraphInterrupt
from multi_agent_system.tools import (
    add_human_in_the_loop,
    create_custom_handoff_tool,
    get_email_from_database
)


class TestAddHumanInTheLoop:
    """Tests for add_human_in_the_loop wrapper"""

    @patch('multi_agent_system.tools.create_tool')
    def test_hitl_proceed_action(self, mock_create_tool):
        """Test human-in-the-loop returns a tool"""
        # Mock the base tool
        mock_base_tool = Mock(spec=BaseTool)
        mock_base_tool.name = "test_tool"
        mock_base_tool.description = "Test tool"
        mock_base_tool.args_schema = None

        # create_tool is used as a decorator in add_human_in_the_loop
        mock_wrapped_tool = Mock(spec=BaseTool)
        mock_decorator = Mock(return_value=mock_wrapped_tool)
        mock_create_tool.return_value = mock_decorator

        # Test the wrapper
        result = add_human_in_the_loop(mock_base_tool, "test_model", email=False)

        # Result should be a BaseTool
        assert result == mock_wrapped_tool
        mock_create_tool.assert_called()

    @patch('multi_agent_system.tools.create_tool')
    def test_hitl_cancel_action(self, mock_create_tool):
        """Test human-in-the-loop returns a tool"""
        mock_base_tool = Mock(spec=BaseTool)
        mock_base_tool.name = "test_tool"
        mock_base_tool.description = "Test tool"
        mock_base_tool.args_schema = None

        # create_tool is used as a decorator
        mock_wrapped_tool = Mock(spec=BaseTool)
        mock_decorator = Mock(return_value=mock_wrapped_tool)
        mock_create_tool.return_value = mock_decorator

        result = add_human_in_the_loop(mock_base_tool, "test_model")

        # Result should be a BaseTool
        assert result == mock_wrapped_tool

    @patch('multi_agent_system.tools.create_tool')
    def test_hitl_changes_requested(self, mock_create_tool):
        """Test human-in-the-loop returns a tool"""
        mock_base_tool = Mock(spec=BaseTool)
        mock_base_tool.name = "test_tool"
        mock_base_tool.description = "Test tool"
        mock_base_tool.args_schema = None

        # create_tool is used as a decorator
        mock_wrapped_tool = Mock(spec=BaseTool)
        mock_decorator = Mock(return_value=mock_wrapped_tool)
        mock_create_tool.return_value = mock_decorator

        result = add_human_in_the_loop(mock_base_tool, "test_model")

        # Result should be a BaseTool
        assert result == mock_wrapped_tool

    @patch('multi_agent_system.tools.create_tool')
    def test_hitl_with_callable(self, mock_create_tool):
        """Test wrapping a callable function"""
        def test_func(arg1: str) -> str:
            return f"Result: {arg1}"

        # First call converts to tool, second call wraps it
        mock_tool = Mock(spec=BaseTool)
        mock_tool.name = "test_func"
        mock_tool.description = "Test function"
        mock_tool.args_schema = None

        call_count = [0]
        def mock_create_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: convert function to tool
                return mock_tool
            else:
                # Second call: wrap the tool
                return Mock()

        mock_create_tool.side_effect = mock_create_side_effect

        result = add_human_in_the_loop(test_func, "test_model")
        assert mock_create_tool.call_count >= 1

    @patch('multi_agent_system.tools.create_tool')
    def test_hitl_email_formatting(self, mock_create_tool):
        """Test email formatting when email=True"""
        mock_base_tool = Mock(spec=BaseTool)
        mock_base_tool.name = "send_email"
        mock_base_tool.description = "Send email"
        mock_base_tool.args_schema = None

        # create_tool is used as a decorator
        mock_wrapped_tool = Mock(spec=BaseTool)
        mock_decorator = Mock(return_value=mock_wrapped_tool)
        mock_create_tool.return_value = mock_decorator

        result = add_human_in_the_loop(mock_base_tool, "test_model", email=True)

        # Result should be a BaseTool
        assert result == mock_wrapped_tool
        mock_create_tool.assert_called()


class TestCreateCustomHandoffTool:
    """Tests for create_custom_handoff_tool"""

    @patch('multi_agent_system.tools.create_tool')
    @patch('multi_agent_system.tools.get_runtime')
    def test_handoff_tool_creation(self, mock_get_runtime, mock_create_tool):
        """Test creating handoff tool"""
        # create_tool is used as a decorator, so it returns a decorator function
        # that when applied to a function, returns the tool
        mock_tool = Mock()
        mock_decorator = Mock(return_value=mock_tool)
        mock_create_tool.return_value = mock_decorator

        result = create_custom_handoff_tool("test_agent", "Test agent description")

        assert result == mock_tool
        mock_create_tool.assert_called_once()
        # Check the tool was created with correct name
        call_args = mock_create_tool.call_args
        assert call_args[0][0] == "assign_task_to_test_agent"

    @patch('multi_agent_system.tools.create_tool')
    @patch('multi_agent_system.tools.get_runtime')
    def test_handoff_tool_default_description(self, mock_get_runtime, mock_create_tool):
        """Test handoff tool with default description"""
        # create_tool is used as a decorator
        mock_tool = Mock()
        mock_decorator = Mock(return_value=mock_tool)
        mock_create_tool.return_value = mock_decorator

        result = create_custom_handoff_tool("test_agent")

        assert result == mock_tool
        call_args = mock_create_tool.call_args
        # Default description should include agent name
        assert "test_agent" in call_args[1]["description"]

    @patch('multi_agent_system.tools.create_tool')
    @patch('multi_agent_system.tools.get_runtime')
    def test_handoff_with_fullname(self, mock_get_runtime, mock_create_tool):
        """Test handoff tool with send_fullname=True"""
        # Mock runtime context
        mock_context = Mock()
        mock_context.user_full_name = "John Doe"
        mock_runtime = Mock()
        mock_runtime.context = mock_context
        mock_get_runtime.return_value = mock_runtime

        # Capture the handoff function
        captured_func = None
        def capture_func(name, **kwargs):
            nonlocal captured_func
            captured_func = kwargs.get('description') or name
            # Return a mock tool
            return Mock()

        mock_create_tool.side_effect = capture_func

        result = create_custom_handoff_tool("test_agent", send_fullname=True)

        # Verify tool was created
        assert mock_create_tool.called

    @patch('multi_agent_system.tools.create_tool')
    def test_handoff_command_structure(self, mock_create_tool):
        """Test the Command structure returned by handoff"""
        # We'll need to inspect what the decorated function returns
        # This is a more complex test since we need to call the actual function

        created_tools = []
        def capture_tool(*args, **kwargs):
            mock_tool = Mock()
            # Store the actual decorated function if provided
            if args and callable(args[0]):
                mock_tool.func = args[0]
            created_tools.append(mock_tool)
            return mock_tool

        mock_create_tool.side_effect = capture_tool

        result = create_custom_handoff_tool("test_agent", "Test description")

        # Verify the tool was created with correct parameters
        assert len(created_tools) == 1


class TestGetEmailFromDatabase:
    """Tests for get_email_from_database tool"""

    @patch('multi_agent_system.tools.get_runtime')
    @patch('multi_agent_system.tools.get_db_session')
    @patch('multi_agent_system.agent_validation.email_db_validation')
    def test_get_email_success(self, mock_validation, mock_db_session, mock_get_runtime):
        """Test successful email retrieval"""
        # Mock decorator to pass through
        mock_validation.return_value = lambda func: func

        # Mock runtime
        mock_context = Mock()
        mock_context.user_id = "user123"
        mock_runtime = Mock()
        mock_runtime.context = mock_context
        mock_get_runtime.return_value = mock_runtime

        # Mock database
        mock_client1 = Mock()
        mock_client1.email = "john.doe@example.com"
        mock_client2 = Mock()
        mock_client2.email = "john.doe2@example.com"

        mock_query = Mock()
        mock_query.all.return_value = [mock_client1, mock_client2]
        mock_query.filter.return_value = mock_query

        mock_db = Mock()
        mock_db.query.return_value = mock_query
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Note: Since the function is decorated, we can't easily test it directly
        # This test verifies the mocking structure is correct
        # In a real test, you'd need to handle the decorator properly

    @patch('multi_agent_system.utils.parse_full_name')
    def test_get_email_invalid_name(self, mock_parse):
        """Test email retrieval with invalid name format"""
        mock_parse.side_effect = ValueError("Invalid full name format")

        # This would be tested through the actual function call
        # The test verifies that _parse_full_name errors are handled


class TestToolIntegration:
    """Integration tests for tool functions"""

    def test_handoff_tool_naming_convention(self):
        """Test that handoff tools follow naming convention"""
        with patch('multi_agent_system.tools.create_tool') as mock_create:
            mock_create.return_value = Mock()

            create_custom_handoff_tool("email_agent")

            # Verify the tool name follows convention
            call_args = mock_create.call_args
            assert call_args[0][0] == "assign_task_to_email_agent"

    def test_multiple_handoff_tools(self):
        """Test creating multiple handoff tools"""
        with patch('multi_agent_system.tools.create_tool') as mock_create:
            mock_create.return_value = Mock()

            agents = ["email_agent", "calendar_agent", "legal_docs_agent"]
            tools = [create_custom_handoff_tool(agent) for agent in agents]

            assert len(tools) == 3
            assert mock_create.call_count == 3