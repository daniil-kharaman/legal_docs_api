import pytest
from unittest.mock import Mock, patch
from fastapi import status, FastAPI
from fastapi.testclient import TestClient

from app.routers.auth import router
from storage.database import get_db
from auth import user_login


class TestLoginForAccessToken:
    """Tests for JWT token login endpoint"""

    @patch('app.routers.auth.user_login.authenticate_user')
    @patch('app.routers.auth.user_login.create_access_token')
    def test_login_success(self, mock_create_token, mock_authenticate, mock_user, mock_db):
        """Test successful login with valid credentials"""
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)

        mock_authenticate.return_value = mock_user
        mock_create_token.return_value = "test_token_12345"

        response = client.post(
            "/auth/jwt/token",
            data={"username": "testuser", "password": "testpassword123"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
        mock_authenticate.assert_called_once()

    @patch('app.routers.auth.user_login.authenticate_user')
    def test_login_invalid_credentials(self, mock_authenticate, mock_db):
        """Test login with invalid credentials"""
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)

        mock_authenticate.return_value = False

        response = client.post(
            "/auth/jwt/token",
            data={"username": "wronguser", "password": "wrongpassword"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect login or password"

    def test_login_missing_credentials(self, mock_db):
        """Test login with missing credentials"""
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)

        response = client.post("/auth/jwt/token", data={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGoogleOAuthInitiate:
    """Tests for Google OAuth initiation endpoint"""

    @patch('app.routers.auth.initiate_google_auth')
    def test_initiate_google_oauth_success(self, mock_initiate_auth, mock_user, mock_db):
        """Test successful Google OAuth initiation"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_initiate_auth.return_value = {
            "authorization_url": "https://accounts.google.com/o/oauth2/auth?test=123",
            "state": "test_state"
        }

        response = client.get("/auth/google/initiate")

        assert response.status_code == status.HTTP_200_OK
        assert "authorization_url" in response.json()
        assert "message" in response.json()

    @patch('app.routers.auth.initiate_google_auth')
    def test_initiate_google_oauth_failure(self, mock_initiate_auth, mock_user, mock_db):
        """Test Google OAuth initiation failure"""
        app = FastAPI()
        app.include_router(router)

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[user_login.get_current_active_user] = override_get_current_user

        client = TestClient(app)

        mock_initiate_auth.side_effect = Exception("OAuth initialization failed")

        response = client.get("/auth/google/initiate")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Google auth failed" in response.json()["detail"]


class TestGoogleOAuthCallback:
    """Tests for Google OAuth callback endpoint"""

    @patch('app.routers.auth.complete_google_auth')
    def test_google_callback_success(self, mock_complete_auth):
        """Test successful Google OAuth callback"""
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        mock_complete_auth.return_value = None

        response = client.get("/auth/google/callback?code=test_code&state=test_state")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "success"
        assert "message" in response.json()

    def test_google_callback_missing_parameters(self):
        """Test Google OAuth callback with missing parameters"""
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        # Missing code parameter
        response = client.get("/auth/google/callback?state=test_state")
        # FastAPI will provide an empty string for missing query parameters
        # The endpoint checks for falsy values, so this will still trigger the error
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    @patch('app.routers.auth.complete_google_auth')
    def test_google_callback_failure(self, mock_complete_auth):
        """Test Google OAuth callback failure"""
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        mock_complete_auth.side_effect = Exception("Token exchange failed")

        response = client.get("/auth/google/callback?code=test_code&state=test_state")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Google auth failed" in response.json()["detail"]
