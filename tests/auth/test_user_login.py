import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
import jwt

from auth.user_login import (
    verify_password,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_active_user
)
from auth.authentication import pwd_context, SECRET_KEY, ALGORITHM


class TestVerifyPassword:
    """Tests for the verify_password function"""

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password_123"
        hashed = pwd_context.hash(password)

        result = verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        hashed = pwd_context.hash(correct_password)

        result = verify_password(wrong_password, hashed)
        assert result is False

    def test_verify_password_empty_password(self):
        """Test password verification with empty password"""
        password = "test_password"
        hashed = pwd_context.hash(password)

        result = verify_password("", hashed)
        assert result is False


class TestAuthenticateUser:
    """Tests for the authenticate_user function"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock()

    @pytest.fixture
    def mock_user(self):
        """Create a mock user object"""
        user = Mock()
        user.username = "testuser"
        user.password = pwd_context.hash("correct_password")
        user.disabled = False
        return user

    @patch('auth.user_login.UserManager')
    def test_authenticate_user_success(self, mock_user_manager, mock_db, mock_user):
        """Test successful user authentication"""
        mock_manager_instance = Mock()
        mock_manager_instance.user_in_database.return_value = mock_user
        mock_user_manager.return_value = mock_manager_instance

        result = authenticate_user("testuser", "correct_password", mock_db)

        assert result == mock_user
        mock_manager_instance.user_in_database.assert_called_once_with(username_or_email="testuser")

    @patch('auth.user_login.UserManager')
    def test_authenticate_user_not_found(self, mock_user_manager, mock_db):
        """Test authentication with non-existent user"""
        mock_manager_instance = Mock()
        mock_manager_instance.user_in_database.return_value = None
        mock_user_manager.return_value = mock_manager_instance

        result = authenticate_user("nonexistent", "password", mock_db)

        assert result is False

    @patch('auth.user_login.UserManager')
    def test_authenticate_user_wrong_password(self, mock_user_manager, mock_db, mock_user):
        """Test authentication with wrong password"""
        mock_manager_instance = Mock()
        mock_manager_instance.user_in_database.return_value = mock_user
        mock_user_manager.return_value = mock_manager_instance

        result = authenticate_user("testuser", "wrong_password", mock_db)

        assert result is False


class TestCreateAccessToken:
    """Tests for the create_access_token function"""

    def test_create_access_token_with_default_expiry(self):
        """Test token creation with default expiration"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Decode and verify token
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "testuser"
        assert "exp" in decoded

    def test_create_access_token_with_custom_expiry(self):
        """Test token creation with custom expiration"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)

        token = create_access_token(data, expires_delta)

        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "testuser"

        # Check expiration is approximately 30 minutes from now
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + expires_delta

        # Allow 5 seconds tolerance
        time_diff = abs((exp_datetime - expected_exp).total_seconds())
        assert time_diff < 5

    def test_create_access_token_preserves_data(self):
        """Test that token includes all provided data"""
        data = {
            "sub": "testuser",
            "email": "test@example.com",
            "role": "admin"
        }
        token = create_access_token(data)

        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "testuser"
        assert decoded["email"] == "test@example.com"
        assert decoded["role"] == "admin"

    def test_create_access_token_does_not_modify_input(self):
        """Test that creating token doesn't modify the input dict"""
        original_data = {"sub": "testuser"}
        data_copy = original_data.copy()

        create_access_token(original_data)

        assert original_data == data_copy


class TestGetCurrentUser:
    """Tests for the get_current_user function"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock()

    @pytest.fixture
    def mock_user(self):
        """Create a mock user object"""
        user = Mock()
        user.username = "testuser"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def valid_token(self):
        """Create a valid JWT token"""
        data = {"sub": "testuser"}
        return create_access_token(data, timedelta(minutes=30))

    @patch('auth.user_login.UserManager')
    def test_get_current_user_success(self, mock_user_manager, valid_token, mock_db, mock_user):
        """Test successful user retrieval from valid token"""
        mock_manager_instance = Mock()
        mock_manager_instance.user_in_database.return_value = mock_user
        mock_user_manager.return_value = mock_manager_instance

        result = get_current_user(valid_token, mock_db)

        assert result == mock_user
        mock_manager_instance.user_in_database.assert_called_once_with(username_or_email="testuser")

    @patch('auth.user_login.UserManager')
    def test_get_current_user_invalid_token(self, mock_user_manager, mock_db):
        """Test with invalid token format"""
        invalid_token = "invalid.token.format"

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(invalid_token, mock_db)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Could not validate credentials"

    @patch('auth.user_login.UserManager')
    def test_get_current_user_expired_token(self, mock_user_manager, mock_db):
        """Test with expired token"""
        data = {"sub": "testuser"}
        expired_token = create_access_token(data, timedelta(seconds=-1))

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(expired_token, mock_db)

        assert exc_info.value.status_code == 401

    @patch('auth.user_login.UserManager')
    def test_get_current_user_missing_subject(self, mock_user_manager, mock_db):
        """Test with token missing 'sub' claim"""
        # Create token without 'sub'
        data = {"email": "test@example.com"}
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token, mock_db)

        assert exc_info.value.status_code == 401

    @patch('auth.user_login.UserManager')
    def test_get_current_user_not_in_database(self, mock_user_manager, valid_token, mock_db):
        """Test when user from token is not in database"""
        mock_manager_instance = Mock()
        mock_manager_instance.user_in_database.return_value = None
        mock_user_manager.return_value = mock_manager_instance

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(valid_token, mock_db)

        assert exc_info.value.status_code == 401


class TestGetCurrentActiveUser:
    """Tests for the get_current_active_user async function"""

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self):
        """Test with active user"""
        mock_user = Mock()
        mock_user.disabled = False

        result = await get_current_active_user(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_current_active_user_disabled(self):
        """Test with disabled user"""
        mock_user = Mock()
        mock_user.disabled = True

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(mock_user)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Inactive user"
