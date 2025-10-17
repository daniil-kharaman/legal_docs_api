import pytest
from unittest.mock import Mock, patch
from fastapi import status, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.routers.client import router
from storage.database import get_db
from auth import user_login


class TestAddClient:
    """Tests for adding a client"""

    @patch('app.routers.client.ClientManager')
    def test_add_client_success(self, mock_client_manager, mock_db, mock_user, mock_client):
        """Test successful client creation"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.client_in_database.return_value = False
        mock_manager_instance.add_object.return_value = mock_client
        mock_client_manager.return_value = mock_manager_instance

        client_data = {
            "firstname": "John",
            "second_name": "Michael",
            "lastname": "Doe",
            "birthdate": "1990-01-01",
            "phone_number": "+4915112534961",
            "email": "john.doe@example.com"
        }

        response = client.post("/client/add", json=client_data)

        assert response.status_code == status.HTTP_200_OK
        mock_manager_instance.add_object.assert_called_once()

    @patch('app.routers.client.ClientManager')
    def test_add_client_duplicate(self, mock_client_manager, mock_db, mock_user):
        """Test adding a duplicate client"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.client_in_database.return_value = True
        mock_client_manager.return_value = mock_manager_instance

        client_data = {
            "firstname": "John",
            "second_name": "Michael",
            "lastname": "Doe",
            "birthdate": "1990-01-01"
        }

        response = client.post("/client/add", json=client_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Client is already in database" in response.json()["detail"]


class TestGetClient:
    """Tests for getting a client"""

    @patch('app.routers.client.validation.get_client_from_db')
    @patch('app.routers.client.ClientManager')
    def test_get_client_success(self, mock_client_manager, mock_get_client, mock_db, mock_user, mock_client):
        """Test successful client retrieval"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        mock_get_client.return_value = mock_client

        response = client.get("/client/1")

        assert response.status_code == status.HTTP_200_OK
        assert "firstname" in response.json()


class TestDeleteClient:
    """Tests for deleting a client"""

    @patch('app.routers.client.validation.get_client_from_db')
    @patch('app.routers.client.ClientManager')
    def test_delete_client_success(self, mock_client_manager, mock_get_client, mock_db, mock_user, mock_client):
        """Test successful client deletion"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.delete_object.return_value = None
        mock_client_manager.return_value = mock_manager_instance
        mock_get_client.return_value = mock_client

        response = client.delete("/client/1")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        mock_manager_instance.delete_object.assert_called_once()


class TestUpdateClient:
    """Tests for updating a client"""

    @patch('app.routers.client.validation.get_client_from_db')
    @patch('app.routers.client.ClientManager')
    def test_update_client_success(self, mock_client_manager, mock_get_client, mock_db, mock_user, mock_client):
        """Test successful client update"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_manager_instance = Mock()
        mock_manager_instance.update_object.return_value = None
        mock_client_manager.return_value = mock_manager_instance
        mock_get_client.return_value = mock_client

        update_data = {
            "phone_number": "+4915112534962"
        }

        response = client.patch("/client/1", json=update_data)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_manager_instance.update_object.assert_called_once()


class TestAddAddress:
    """Tests for adding client address"""

    @patch('app.routers.client.validation.validate_address_by_client')
    @patch('app.routers.client.validation.get_client_from_db')
    @patch('app.routers.client.AddressManager')
    @patch('app.routers.client.ClientManager')
    def test_add_address_success(self, mock_client_manager, mock_address_manager, mock_get_client, mock_validate_address, mock_db, mock_user, mock_client, mock_address):
        """Test successful address creation"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_client_mgr_instance = Mock()
        mock_client_manager.return_value = mock_client_mgr_instance
        mock_get_client.return_value = mock_client
        mock_address_mgr_instance = Mock()
        mock_address_mgr_instance.add_object.return_value = mock_address
        mock_address_manager.return_value = mock_address_mgr_instance

        address_data = {
            "house_number": "123",
            "street": "Main Street",
            "city": "New York",
            "postal_code": "10001",
            "country": "USA",
            "state": "NY"
        }

        response = client.post("/client/1/address", json=address_data)

        assert response.status_code == status.HTTP_200_OK
        assert "house_number" in response.json()
        mock_address_mgr_instance.add_object.assert_called_once()
