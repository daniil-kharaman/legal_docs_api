import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from multi_agent_system.utils import parse_full_name, load_prompt
from multi_agent_system import AgentInternalError


class TestParseFullName:
    """Tests for parse_full_name function"""

    def testparse_full_name_success(self):
        """Test parsing valid full name"""
        first, last = parse_full_name("John Doe")
        assert first == "John"
        assert last == "Doe"

    def testparse_full_name_with_middle_name(self):
        """Test parsing name with middle name (takes first two parts)"""
        first, last = parse_full_name("John Michael Doe")
        assert first == "John"
        assert last == "Michael"

    def testparse_full_name_with_extra_spaces(self):
        """Test parsing name with extra spaces"""
        first, last = parse_full_name("  John   Doe  ")
        assert first == "John"
        assert last == "Doe"

    def testparse_full_name_single_name(self):
        """Test parsing single name raises ValueError"""
        with pytest.raises(ValueError, match="Invalid full name format"):
            parse_full_name("John")

    def testparse_full_name_empty_string(self):
        """Test parsing empty string raises ValueError"""
        with pytest.raises(ValueError, match="Invalid full name format"):
            parse_full_name("")

    def testparse_full_name_whitespace_only(self):
        """Test parsing whitespace-only string raises ValueError"""
        with pytest.raises(ValueError, match="Invalid full name format"):
            parse_full_name("   ")


class TestLoadPrompt:
    """Tests for load_prompt function"""

    def testload_prompt_success(self, temp_prompts_dir):
        """Test loading existing prompt file"""
        with patch('multi_agent_system.utils.PROMPTS_DIR', temp_prompts_dir):
            content = load_prompt("email_agent/v1.txt")
            assert content == "You are an email agent."

    def testload_prompt_file_not_found(self, temp_prompts_dir):
        """Test loading non-existent prompt file raises AgentInternalError"""
        with patch('multi_agent_system.utils.PROMPTS_DIR', temp_prompts_dir):
            with pytest.raises(AgentInternalError, match="Missing prompt file"):
                load_prompt("nonexistent.txt")

    def testload_prompt_invalid_directory(self):
        """Test loading from invalid directory raises AgentInternalError"""
        with patch('multi_agent_system.utils.PROMPTS_DIR', Path("/invalid/path")):
            with pytest.raises(AgentInternalError, match="Missing prompt file"):
                load_prompt("test.txt")

    @patch('builtins.open')
    def testload_prompt_read_error(self, mock_open, temp_prompts_dir):
        """Test handling read error raises AgentInternalError"""
        mock_open.side_effect = Exception("Read error")
        with patch('multi_agent_system.utils.PROMPTS_DIR', temp_prompts_dir):
            with pytest.raises(AgentInternalError, match="Failed to load prompt"):
                load_prompt("email_agent/v1.txt")

    def testload_prompt_empty_file(self, temp_prompts_dir):
        """Test loading empty prompt file"""
        empty_file = temp_prompts_dir / "empty.txt"
        empty_file.write_text("")

        with patch('multi_agent_system.utils.PROMPTS_DIR', temp_prompts_dir):
            content = load_prompt("empty.txt")
            assert content == ""

    def testload_prompt_with_unicode(self, temp_prompts_dir):
        """Test loading prompt with unicode characters"""
        unicode_file = temp_prompts_dir / "unicode.txt"
        unicode_content = "Hello 你好 мир 🌍"
        unicode_file.write_text(unicode_content, encoding='utf-8')

        with patch('multi_agent_system.utils.PROMPTS_DIR', temp_prompts_dir):
            content = load_prompt("unicode.txt")
            assert content == unicode_content