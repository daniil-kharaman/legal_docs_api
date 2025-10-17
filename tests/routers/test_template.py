import pytest
from unittest.mock import Mock, patch
from fastapi import status, FastAPI
from fastapi.testclient import TestClient
from io import BytesIO

from app.routers.template import router
from storage.database import get_db
from auth import user_login


class TestGetTemplate:
    """Tests for getting a template"""

    @patch('app.routers.template.validation.get_template_from_db')
    @patch('app.routers.template.TemplateManager')
    def test_get_template_success(self, mock_template_manager, mock_get_template, mock_db, mock_user, mock_template):
        """Test successful template retrieval"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_template_manager.return_value = mock_manager_instance
        mock_get_template.return_value = mock_template

        response = client.get("/template/template/1")

        assert response.status_code == status.HTTP_200_OK
        assert "template_name" in response.json()


class TestDeleteTemplate:
    """Tests for deleting a template"""

    @patch('app.routers.template.delete_file_s3')
    @patch('app.routers.template.validation.get_template_from_db')
    @patch('app.routers.template.TemplateManager')
    def test_delete_template_success(self, mock_template_manager, mock_get_template, mock_delete_s3, mock_db, mock_user, mock_template):
        """Test successful template deletion"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.delete_object.return_value = None
        mock_template_manager.return_value = mock_manager_instance
        mock_get_template.return_value = mock_template

        response = client.delete("/template/template/1")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        mock_delete_s3.assert_called_once_with(mock_template.template_path)
        mock_manager_instance.delete_object.assert_called_once()


class TestUpdateTemplate:
    """Tests for updating a template"""

    @patch('app.routers.template.validation.get_template_from_db')
    @patch('app.routers.template.TemplateManager')
    def test_update_template_success(self, mock_template_manager, mock_get_template, mock_db, mock_user, mock_template):
        """Test successful template name update"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.update_object.return_value = None
        mock_template_manager.return_value = mock_manager_instance
        mock_get_template.return_value = mock_template

        update_data = {
            "template_name": "Updated Template Name"
        }

        response = client.patch("/template/template/1", json=update_data)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_manager_instance.update_object.assert_called_once()


class TestGenerateFile:
    """Tests for document generation from template"""

    @patch('app.routers.template.docx_processor.render_template')
    @patch('app.routers.template.get_file_s3')
    @patch('app.routers.template.docx_processor.parse_context')
    @patch('app.routers.template.validation.get_template_from_db')
    @patch('app.routers.template.TemplateManager')
    def test_generate_file_success(self, mock_template_manager, mock_get_template, mock_parse_context, mock_get_s3, mock_render, mock_db, mock_user, mock_template):
        """Test successful document generation"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_template_manager.return_value = mock_manager_instance
        mock_get_template.return_value = mock_template

        # Mock context parsing
        mock_parse_context.return_value = {"key": "value"}

        # Mock template stream
        mock_template_stream = BytesIO(b"template content")
        mock_get_s3.return_value = mock_template_stream

        # Mock render template
        mock_rendered = BytesIO(b"rendered document")
        mock_render.return_value = mock_rendered

        context_data = {
            "party_one_id": [1],
            "party_two_id": [2],
            "date": "2024-01-01"
        }

        response = client.post("/template/template/1/generate", json=context_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        mock_parse_context.assert_called_once()
        mock_get_s3.assert_called_once_with(mock_template.template_path)
        mock_render.assert_called_once()

    def test_generate_file_invalid_context(self, mock_db, mock_user):
        """Test document generation with invalid context"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        context_data = {
            "party_one_id": [],  # Invalid: empty list
            "party_two_id": [2]
        }

        response = client.post("/template/template/1/generate", json=context_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
