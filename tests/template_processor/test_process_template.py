import pytest
from io import BytesIO
from datetime import date
from unittest.mock import Mock, patch, MagicMock
from fastapi import UploadFile, HTTPException
from docx import Document

from template_processor.docx_processor import (
    parse_template,
    parse_context,
    render_template
)


class TestParseTemplate:
    """Tests for the parse_template function"""

    @pytest.fixture
    def mock_upload_file(self):
        """Create a mock UploadFile"""
        mock_file = Mock(spec=UploadFile)
        mock_file.file = BytesIO(b"fake docx content")
        mock_file.filename = "test_template.docx"
        return mock_file

    @pytest.fixture
    def mock_document(self):
        """Create a mock Document"""
        with patch('template_processor.docx_processor.Document') as mock_doc:
            yield mock_doc

    @pytest.fixture
    def mock_docx_replace(self):
        """Create a mock docx_replace function"""
        with patch('template_processor.docx_processor.docx_replace') as mock_replace:
            yield mock_replace

    def test_parse_template_success(self, mock_upload_file, mock_document, mock_docx_replace):
        """Test successful template parsing"""
        mock_doc_instance = Mock()
        mock_document.return_value = mock_doc_instance

        result = parse_template(mock_upload_file)

        assert isinstance(result, BytesIO)
        mock_document.assert_called_once_with(mock_upload_file.file)
        mock_docx_replace.assert_called_once()
        mock_doc_instance.save.assert_called_once()
        # Check buffer position is reset to start
        assert result.tell() == 0

    def test_parse_template_with_replacement_context(self, mock_upload_file, mock_document, mock_docx_replace):
        """Test that correct replacement context is used"""
        mock_doc_instance = Mock()
        mock_document.return_value = mock_doc_instance

        parse_template(mock_upload_file)

        # Verify docx_replace was called with correct context
        call_args = mock_docx_replace.call_args
        assert call_args[0][0] == mock_doc_instance

        # Check that replacement context contains expected keys
        replacement_context = call_args[1]
        assert 'DATE' in replacement_context
        assert 'PARTY1_START' in replacement_context
        assert 'PARTY1_END' in replacement_context
        assert 'NAME' in replacement_context
        assert 'ADDRESS' in replacement_context
        assert 'BIRTH' in replacement_context
        assert 'PARTY2_START' in replacement_context
        assert 'PARTY2_END' in replacement_context

    def test_parse_template_jinja2_syntax(self, mock_upload_file, mock_document, mock_docx_replace):
        """Test that Jinja2 syntax is correctly applied"""
        mock_doc_instance = Mock()
        mock_document.return_value = mock_doc_instance

        parse_template(mock_upload_file)

        replacement_context = mock_docx_replace.call_args[1]
        assert replacement_context['DATE'] == '{{date}}'
        assert replacement_context['PARTY1_START'] == '{% for person in party_one %}'
        assert replacement_context['PARTY1_END'] == '{% endfor %}'
        assert '{{person.firstname}}' in replacement_context['NAME']

    def test_parse_template_document_error(self, mock_upload_file, mock_document):
        """Test handling of Document initialization error"""
        mock_document.side_effect = Exception("Invalid document format")

        with pytest.raises(HTTPException) as exc_info:
            parse_template(mock_upload_file)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == 'Something went wrong. Try again.'

    def test_parse_template_docx_replace_error(self, mock_upload_file, mock_document, mock_docx_replace):
        """Test handling of docx_replace error"""
        mock_doc_instance = Mock()
        mock_document.return_value = mock_doc_instance
        mock_docx_replace.side_effect = Exception("Replace failed")

        with pytest.raises(HTTPException) as exc_info:
            parse_template(mock_upload_file)

        assert exc_info.value.status_code == 400

    def test_parse_template_save_error(self, mock_upload_file, mock_document, mock_docx_replace):
        """Test handling of document save error"""
        mock_doc_instance = Mock()
        mock_doc_instance.save.side_effect = Exception("Save failed")
        mock_document.return_value = mock_doc_instance

        with pytest.raises(HTTPException) as exc_info:
            parse_template(mock_upload_file)

        assert exc_info.value.status_code == 400

    def test_parse_template_buffer_is_bytesio(self, mock_upload_file, mock_document, mock_docx_replace):
        """Test that returned buffer is BytesIO instance"""
        mock_doc_instance = Mock()
        mock_document.return_value = mock_doc_instance

        result = parse_template(mock_upload_file)

        assert isinstance(result, BytesIO)
        assert hasattr(result, 'read')
        assert hasattr(result, 'seek')


class TestParseContext:
    """Tests for the parse_context function"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock()

    @pytest.fixture
    def mock_client_manager(self):
        """Mock ClientManager"""
        with patch('template_processor.docx_processor.ClientManager') as mock_manager:
            yield mock_manager

    @pytest.fixture
    def sample_gen_context(self):
        """Create a sample GenContext"""
        from validation.schemas import GenContext
        return GenContext(
            party_one_id=[1, 2],
            party_two_id=[3],
            date=date(2024, 1, 15)
        )

    def create_mock_client(self, client_id=1, birthdate=date(1990, 5, 15)):
        """Create a mock client object"""
        client = Mock()
        client.id = client_id
        client.firstname = "John"
        client.second_name = "Michael"
        client.lastname = "Doe"
        client.birthdate = birthdate
        client.client_address = Mock()
        client.client_address.house_number = "123"
        client.client_address.street = "Main St"
        client.client_address.city = "Boston"
        client.client_address.postal_code = "02101"
        client.client_address.country = "USA"
        return client

    def test_parse_context_success(self, sample_gen_context, mock_db, mock_client_manager):
        """Test successful context parsing"""
        # Setup mock - create fresh client for each call
        mock_manager_instance = Mock()
        mock_manager_instance.get_object.side_effect = [
            self.create_mock_client(1, date(1990, 5, 15)),
            self.create_mock_client(2, date(1991, 6, 16)),
            self.create_mock_client(3, date(1992, 7, 17))
        ]
        mock_client_manager.return_value = mock_manager_instance

        result = parse_context(sample_gen_context, mock_db)

        assert "party_one" in result
        assert "party_two" in result
        assert "date" in result
        assert len(result["party_one"]) == 2
        assert len(result["party_two"]) == 1
        assert result["date"] == "15 January 2024"

    def test_parse_context_date_formatting(self, sample_gen_context, mock_db, mock_client_manager):
        """Test that dates are formatted correctly"""
        # Create fresh clients for each call to avoid mutation issues
        mock_manager_instance = Mock()
        mock_manager_instance.get_object.side_effect = [
            self.create_mock_client(1, date(1990, 5, 15)),
            self.create_mock_client(2, date(1991, 6, 16)),
            self.create_mock_client(3, date(1992, 7, 17))
        ]
        mock_client_manager.return_value = mock_manager_instance

        result = parse_context(sample_gen_context, mock_db)

        # Check date format is "DD Month YYYY"
        assert result["date"] == "15 January 2024"
        # Check client birthdate is formatted
        assert result["party_one"][0].birthdate == "15 May 1990"

    def test_parse_context_party_one_not_found(self, sample_gen_context, mock_db, mock_client_manager):
        """Test when party_one client is not found"""
        mock_manager_instance = Mock()
        mock_manager_instance.get_object.return_value = None
        mock_client_manager.return_value = mock_manager_instance

        with pytest.raises(HTTPException) as exc_info:
            parse_context(sample_gen_context, mock_db)

        assert exc_info.value.status_code == 400
        assert "There is no client with id" in exc_info.value.detail

    def test_parse_context_party_two_not_found(self, mock_db, mock_client_manager):
        """Test when party_two client is not found"""
        from validation.schemas import GenContext

        context = GenContext(
            party_one_id=[1],
            party_two_id=[999],
            date=date(2024, 1, 15)
        )

        mock_client = self.create_mock_client()

        # First call returns client, second call returns None
        mock_manager_instance = Mock()
        mock_manager_instance.get_object.side_effect = [mock_client, None]
        mock_client_manager.return_value = mock_manager_instance

        with pytest.raises(HTTPException) as exc_info:
            parse_context(context, mock_db)

        assert exc_info.value.status_code == 400

    def test_parse_context_multiple_clients_party_one(self, mock_db, mock_client_manager):
        """Test with multiple clients in party_one"""
        from validation.schemas import GenContext

        context = GenContext(
            party_one_id=[1, 2, 3],
            party_two_id=[4],
            date=date(2024, 1, 15)
        )

        mock_client1 = self.create_mock_client(1, date(1990, 1, 1))
        mock_client2 = self.create_mock_client(2, date(1991, 2, 2))
        mock_client3 = self.create_mock_client(3, date(1992, 3, 3))
        mock_client4 = self.create_mock_client(4, date(1993, 4, 4))

        clients = [mock_client1, mock_client2, mock_client3, mock_client4]
        mock_manager_instance = Mock()
        mock_manager_instance.get_object.side_effect = clients
        mock_client_manager.return_value = mock_manager_instance

        result = parse_context(context, mock_db)

        assert len(result["party_one"]) == 3
        assert len(result["party_two"]) == 1

    def test_parse_context_single_client_each_party(self, mock_db, mock_client_manager):
        """Test with single client in each party"""
        from validation.schemas import GenContext

        context = GenContext(
            party_one_id=[1],
            party_two_id=[2],
            date=date(2024, 1, 15)
        )

        mock_client1 = self.create_mock_client(1, date(1990, 1, 1))
        mock_client2 = self.create_mock_client(2, date(1991, 2, 2))

        mock_manager_instance = Mock()
        mock_manager_instance.get_object.side_effect = [mock_client1, mock_client2]
        mock_client_manager.return_value = mock_manager_instance

        result = parse_context(context, mock_db)

        assert len(result["party_one"]) == 1
        assert len(result["party_two"]) == 1
        assert result["date"] == "15 January 2024"

    def test_parse_context_client_manager_calls(self, sample_gen_context, mock_db, mock_client_manager):
        """Test that ClientManager is called correctly for each client"""
        # Create fresh clients for each call to avoid mutation issues
        mock_manager_instance = Mock()
        mock_manager_instance.get_object.side_effect = [
            self.create_mock_client(1, date(1990, 5, 15)),
            self.create_mock_client(2, date(1991, 6, 16)),
            self.create_mock_client(3, date(1992, 7, 17))
        ]
        mock_client_manager.return_value = mock_manager_instance

        parse_context(sample_gen_context, mock_db)

        # Should be called 3 times (2 for party_one, 1 for party_two)
        assert mock_client_manager.call_count == 3


class TestRenderTemplate:
    """Tests for the render_template function"""

    @pytest.fixture
    def mock_docxtpl(self):
        """Mock DocxTemplate"""
        with patch('template_processor.docx_processor.DocxTemplate') as mock_tpl:
            yield mock_tpl

    @pytest.fixture
    def sample_buffer(self):
        """Create a sample BytesIO buffer"""
        return BytesIO(b"template content")

    @pytest.fixture
    def sample_context(self):
        """Create a sample rendering context"""
        return {
            "party_one": [{"name": "John Doe"}],
            "party_two": [{"name": "Jane Smith"}],
            "date": "15 January 2024"
        }

    def test_render_template_success(self, sample_buffer, sample_context, mock_docxtpl):
        """Test successful template rendering"""
        mock_template = Mock()
        mock_docxtpl.return_value = mock_template

        result = render_template(sample_buffer, sample_context)

        assert isinstance(result, BytesIO)
        mock_docxtpl.assert_called_once_with(sample_buffer)
        mock_template.render.assert_called_once_with(sample_context)
        mock_template.save.assert_called_once()
        assert result.tell() == 0

    def test_render_template_with_empty_context(self, sample_buffer, mock_docxtpl):
        """Test rendering with empty context"""
        mock_template = Mock()
        mock_docxtpl.return_value = mock_template
        empty_context = {}

        result = render_template(sample_buffer, empty_context)

        mock_template.render.assert_called_once_with(empty_context)
        assert isinstance(result, BytesIO)

    def test_render_template_complex_context(self, sample_buffer, mock_docxtpl):
        """Test rendering with complex nested context"""
        mock_template = Mock()
        mock_docxtpl.return_value = mock_template

        complex_context = {
            "party_one": [
                {
                    "firstname": "John",
                    "lastname": "Doe",
                    "client_address": {
                        "street": "Main St",
                        "city": "Boston"
                    }
                }
            ],
            "party_two": [],
            "date": "15 January 2024"
        }

        result = render_template(sample_buffer, complex_context)

        mock_template.render.assert_called_once_with(complex_context)
        assert isinstance(result, BytesIO)

    def test_render_template_buffer_position_reset(self, sample_buffer, mock_docxtpl):
        """Test that buffer position is reset to beginning"""
        mock_template = Mock()
        mock_docxtpl.return_value = mock_template

        result = render_template(sample_buffer, {})

        # Buffer should be at position 0
        assert result.tell() == 0

    def test_render_template_creates_new_buffer(self, sample_buffer, mock_docxtpl):
        """Test that a new buffer is created for output"""
        mock_template = Mock()
        mock_docxtpl.return_value = mock_template

        original_buffer = sample_buffer
        result = render_template(sample_buffer, {})

        # Result should be a different buffer instance
        assert result is not original_buffer
        assert isinstance(result, BytesIO)

    def test_render_template_docx_template_error(self, sample_buffer, mock_docxtpl):
        """Test handling of DocxTemplate initialization error"""
        mock_docxtpl.side_effect = Exception("Template error")

        with pytest.raises(Exception):
            render_template(sample_buffer, {})

    def test_render_template_render_error(self, sample_buffer, sample_context, mock_docxtpl):
        """Test handling of render error"""
        mock_template = Mock()
        mock_template.render.side_effect = Exception("Render failed")
        mock_docxtpl.return_value = mock_template

        with pytest.raises(Exception):
            render_template(sample_buffer, sample_context)

    def test_render_template_save_error(self, sample_buffer, sample_context, mock_docxtpl):
        """Test handling of save error"""
        mock_template = Mock()
        mock_template.save.side_effect = Exception("Save failed")
        mock_docxtpl.return_value = mock_template

        with pytest.raises(Exception):
            render_template(sample_buffer, sample_context)


class TestIntegrationScenarios:
    """Integration-style tests for template processing workflow"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('template_processor.docx_processor.Document') as mock_doc, \
             patch('template_processor.docx_processor.docx_replace') as mock_replace, \
             patch('template_processor.docx_processor.DocxTemplate') as mock_tpl, \
             patch('template_processor.docx_processor.ClientManager') as mock_mgr:
            yield {
                'Document': mock_doc,
                'docx_replace': mock_replace,
                'DocxTemplate': mock_tpl,
                'ClientManager': mock_mgr
            }

    def test_full_workflow_parse_and_render(self, mock_dependencies):
        """Test complete workflow: parse template, parse context, render"""
        # Setup mocks
        mock_doc_instance = Mock()
        mock_dependencies['Document'].return_value = mock_doc_instance

        mock_template = Mock()
        mock_dependencies['DocxTemplate'].return_value = mock_template

        # Create properly structured mock client
        def create_test_client():
            client = Mock()
            client.firstname = "John"
            client.birthdate = date(1990, 1, 1)
            client.client_address = Mock()
            client.client_address.house_number = "123"
            client.client_address.street = "Main St"
            client.client_address.city = "Boston"
            client.client_address.postal_code = "02101"
            client.client_address.country = "USA"
            return client

        mock_manager_instance = Mock()
        mock_manager_instance.get_object.side_effect = [create_test_client(), create_test_client()]
        mock_dependencies['ClientManager'].return_value = mock_manager_instance

        # Step 1: Parse template
        mock_upload = Mock(spec=UploadFile)
        mock_upload.file = BytesIO(b"template")
        parsed_buffer = parse_template(mock_upload)

        assert isinstance(parsed_buffer, BytesIO)

        # Step 2: Parse context
        from validation.schemas import GenContext
        gen_context = GenContext(
            party_one_id=[1],
            party_two_id=[2],
            date=date(2024, 1, 15)
        )
        context = parse_context(gen_context, Mock())

        assert "party_one" in context
        assert "party_two" in context
        assert "date" in context

        # Step 3: Render template
        rendered_buffer = render_template(parsed_buffer, context)

        assert isinstance(rendered_buffer, BytesIO)
        mock_template.render.assert_called_once_with(context)