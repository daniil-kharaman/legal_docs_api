import pytest
from unittest.mock import Mock, patch
from fastapi import status, FastAPI
from fastapi.testclient import TestClient

from app.routers.user import router
from storage.database import get_db
from auth import user_login


class TestCreateUser:
    """Tests for user creation endpoint"""

    @patch('app.routers.user.UserManager')
    @patch('app.routers.user.validation.validate_username_in_db')
    @patch('app.routers.user.validation.validate_email_in_db')
    def test_create_user_success(self, mock_validate_email, mock_validate_username, mock_user_manager, mock_user, mock_db):
        """Test successful user creation"""
        app = FastAPI()
        app.include_router(router)

        # Override dependencies
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.user_in_database.return_value = None
        mock_manager_instance.add_object.return_value = mock_user
        mock_user_manager.return_value = mock_manager_instance

        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "securepassword123"
        }

        response = client.post("/user/add", json=user_data)

        assert response.status_code == status.HTTP_200_OK
        assert "username" in response.json()
        mock_validate_username.assert_called_once()
        mock_validate_email.assert_called_once()

    @patch('app.routers.user.UserManager')
    @patch('app.routers.user.validation.validate_username_in_db')
    def test_create_user_duplicate_username(self, mock_validate_username, mock_user_manager, mock_user, mock_db):
        """Test user creation with duplicate username"""
        from fastapi import HTTPException

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.user_in_database.return_value = mock_user
        mock_user_manager.return_value = mock_manager_instance
        mock_validate_username.side_effect = HTTPException(status_code=400, detail="Username already exists")

        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }

        response = client.post("/user/add", json=user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_user_invalid_data(self, mock_db):
        """Test user creation with invalid data"""
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)

        user_data = {
            "username": "test",
            "email": "invalid-email",
            "password": "pass"
        }

        response = client.post("/user/add", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestReadUsersMe:
    """Tests for current user endpoint"""

    def test_read_users_me_success(self, mock_user):
        """Test getting current user information"""
        app = FastAPI()
        app.include_router(router)

        # Override authentication dependency
        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)
        response = client.get("/user/me")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == "testuser"
        assert response.json()["email"] == "test@example.com"


class TestDeleteUser:
    """Tests for user deletion endpoint"""

    @patch('app.routers.user.UserManager')
    def test_delete_user_success(self, mock_user_manager, mock_db, mock_user):
        """Test successful user deletion"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.delete_object.return_value = None
        mock_user_manager.return_value = mock_manager_instance

        response = client.delete("/user/delete")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        assert response.json()["user"] == "testuser"
        mock_manager_instance.delete_object.assert_called_once()


class TestUpdateUser:
    """Tests for user update endpoint"""

    @patch('app.routers.user.UserManager')
    @patch('app.routers.user.validation.validate_username_in_db')
    @patch('app.routers.user.validation.validate_email_in_db')
    def test_update_user_success(self, mock_validate_email, mock_validate_username, mock_user_manager, mock_db, mock_user):
        """Test successful user update"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.user_in_database.return_value = None
        mock_manager_instance.update_object.return_value = None
        mock_user_manager.return_value = mock_manager_instance

        update_data = {
            "full_name": "Updated Name"
        }

        response = client.patch("/user/update", json=update_data)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_manager_instance.update_object.assert_called_once()


class TestGetAllClients:
    """Tests for getting all user's clients"""

    @patch('app.routers.user.ClientManager')
    def test_get_all_clients_success(self, mock_client_manager, mock_db, mock_user, mock_client):
        """Test getting all user's clients"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_query = Mock()
        mock_query.all.return_value = [mock_client]
        mock_manager_instance.get_objects_by_user.return_value = mock_query
        mock_client_manager.return_value = mock_manager_instance

        response = client.get("/user/clients")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)


class TestGetAllTemplates:
    """Tests for getting all user's templates"""

    @patch('app.routers.user.TemplateManager')
    def test_get_all_templates_success(self, mock_template_manager, mock_db, mock_user, mock_template):
        """Test getting all user's templates"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_query = Mock()
        mock_query.all.return_value = [mock_template]
        mock_manager_instance.get_objects_by_user.return_value = mock_query
        mock_template_manager.return_value = mock_manager_instance

        response = client.get("/user/templates")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
