import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import UploadFile
from google.cloud import documentai

from ai.photo_to_text_ai import (
    parse_birthdate,
    format_processed_data,
    process_id_photo
)


class TestParseBirthdate:
    """Tests for the parse_birthdate function"""

    def test_valid_birthdate(self):
        """Test parsing a valid birthdate string"""
        result = parse_birthdate("15 01/Jan 90")
        assert result == date(1990, 1, 15)

    def test_valid_birthdate_different_format(self):
        """Test parsing another valid birthdate"""
        result = parse_birthdate("01 12/Dec 00")
        assert result == date(2000, 12, 1)

    def test_empty_string(self):
        """Test that empty string returns None"""
        result = parse_birthdate("")
        assert result is None

    def test_none_input(self):
        """Test that None input returns None"""
        result = parse_birthdate(None)
        assert result is None

    def test_invalid_format_missing_parts(self):
        """Test that incomplete date string returns None"""
        result = parse_birthdate("15 Jan")
        assert result is None

    def test_invalid_format_malformed(self):
        """Test that malformed date string returns None"""
        result = parse_birthdate("invalid date string")
        assert result is None

    def test_invalid_month(self):
        """Test that invalid month returns None"""
        result = parse_birthdate("15 Xxx/99 1990")
        assert result is None


class TestFormatProcessedData:
    """Tests for the format_processed_data function"""

    def test_single_entity_with_text_anchor(self):
        """Test formatting a single entity with text_anchor"""
        entity = Mock()
        entity.type_ = "Name"
        entity.text_anchor = Mock()
        entity.text_anchor.content = "john doe"
        entity.mention_text = ""
        entity.normalized_value = Mock()
        entity.normalized_value.text = ""

        result = format_processed_data([entity])
        assert result == {"Name": "John Doe"}

    def test_single_entity_with_mention_text(self):
        """Test formatting entity with mention_text fallback"""
        entity = Mock()
        entity.type_ = "Name"
        entity.text_anchor = Mock()
        entity.text_anchor.content = ""
        entity.mention_text = "jane smith"
        entity.normalized_value = Mock()
        entity.normalized_value.text = ""

        result = format_processed_data([entity])
        assert result == {"Name": "Jane Smith"}

    def test_birth_entity_with_normalized_value(self):
        """Test Birth entity with normalized value"""
        entity = Mock()
        entity.type_ = "Birth"
        entity.normalized_value = Mock()
        entity.normalized_value.text = "1990-01-15"
        entity.text_anchor = Mock()
        entity.text_anchor.content = ""
        entity.mention_text = ""

        result = format_processed_data([entity])
        assert result == {"Birth": "1990-01-15"}

    @patch('ai.photo_to_text_ai.parse_birthdate')
    def test_birth_entity_without_normalized_value(self, mock_parse):
        """Test Birth entity requiring parsing"""
        mock_parse.return_value = date(1990, 1, 15)

        entity = Mock()
        entity.type_ = "Birth"
        entity.normalized_value = Mock()
        entity.normalized_value.text = ""
        entity.text_anchor = Mock()
        entity.text_anchor.content = "15 01/Jan 90"
        entity.mention_text = ""

        result = format_processed_data([entity])
        assert result == {"Birth": date(1990, 1, 15)}
        mock_parse.assert_called_once_with("15 01/Jan 90")

    def test_duplicate_entity_types_creates_list(self):
        """Test that duplicate entity types are grouped into a list"""
        entity1 = Mock()
        entity1.type_ = "Address"
        entity1.text_anchor = Mock()
        entity1.text_anchor.content = "123 main st"
        entity1.mention_text = ""
        entity1.normalized_value = Mock()
        entity1.normalized_value.text = ""

        entity2 = Mock()
        entity2.type_ = "Address"
        entity2.text_anchor = Mock()
        entity2.text_anchor.content = "456 oak ave"
        entity2.mention_text = ""
        entity2.normalized_value = Mock()
        entity2.normalized_value.text = ""

        result = format_processed_data([entity1, entity2])
        assert result == {"Address": ["123 Main St", "456 Oak Ave"]}

    def test_multiple_different_entities(self):
        """Test formatting multiple different entity types"""
        name_entity = Mock()
        name_entity.type_ = "Name"
        name_entity.text_anchor = Mock()
        name_entity.text_anchor.content = "john doe"
        name_entity.mention_text = ""
        name_entity.normalized_value = Mock()
        name_entity.normalized_value.text = ""

        id_entity = Mock()
        id_entity.type_ = "ID"
        id_entity.text_anchor = Mock()
        id_entity.text_anchor.content = "12345"
        id_entity.mention_text = ""
        id_entity.normalized_value = Mock()
        id_entity.normalized_value.text = ""

        result = format_processed_data([name_entity, id_entity])
        assert result == {"Name": "John Doe", "ID": "12345"}

    def test_empty_entities_list(self):
        """Test that empty list returns empty dict"""
        result = format_processed_data([])
        assert result == {}


class TestProcessIdPhoto:
    """Tests for the process_id_photo async function"""

    @pytest.mark.asyncio
    async def test_successful_processing(self):
        """Test successful ID photo processing"""
        # Mock the UploadFile
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=b"fake_image_content")

        # Mock the Document AI response
        mock_entity = Mock()
        mock_entity.type_ = "Name"
        mock_entity.text_anchor = Mock()
        mock_entity.text_anchor.content = "john doe"
        mock_entity.mention_text = ""
        mock_entity.normalized_value = Mock()
        mock_entity.normalized_value.text = ""

        mock_document = Mock()
        mock_document.entities = [mock_entity]

        mock_result = Mock()
        mock_result.document = mock_document

        # Patch the Document AI client
        with patch('ai.photo_to_text_ai.service_account.Credentials') as mock_creds, \
             patch('ai.photo_to_text_ai.documentai.DocumentProcessorServiceClient') as mock_client_class, \
             patch('ai.photo_to_text_ai.format_processed_data') as mock_format:

            mock_client = Mock()
            mock_client.processor_path.return_value = "projects/test/locations/us/processors/123"
            mock_client.process_document.return_value = mock_result
            mock_client_class.return_value = mock_client

            mock_format.return_value = {"Name": "John Doe"}

            result = await process_id_photo(mock_file)

            assert result == {"Name": "John Doe"}
            mock_file.read.assert_called_once()
            mock_client.process_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_processing_with_exception(self):
        """Test that exceptions are handled and return None"""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(side_effect=Exception("Test error"))

        result = await process_id_photo(mock_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_processing_with_client_error(self):
        """Test handling of Document AI client errors"""
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=b"fake_image_content")

        with patch('ai.photo_to_text_ai.service_account.Credentials'), \
             patch('ai.photo_to_text_ai.documentai.DocumentProcessorServiceClient') as mock_client_class:

            mock_client = Mock()
            mock_client.processor_path.return_value = "projects/test/locations/us/processors/123"
            mock_client.process_document.side_effect = Exception("API Error")
            mock_client_class.return_value = mock_client

            result = await process_id_photo(mock_file)

            assert result is None