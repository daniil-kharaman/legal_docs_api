import pytest
import json
from unittest.mock import Mock, patch, MagicMock, call
from google.oauth2.credentials import Credentials

# Import directly without mocking the module
# We'll patch validate_token_in_db where it's used instead
from auth.oauth import (
    OAuthError,
    initiate_google_auth,
    complete_google_auth,
    check_scopes,
    get_creds,
    auth_google,
    SCOPES
)
from auth.token_encryption import EncryptionError


class TestInitiateGoogleAuth:
    """Tests for the initiate_google_auth function"""

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables"""
        return {
            'GOOGLE_AUTH_CREDS': json.dumps({
                "web": {
                    "client_id": "test_client_id",
                    "client_secret": "test_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }),
            'BASE_URL': 'https://example.com',
            'TOKEN_ENCRYPTION_KEY': 'test_key_32_bytes_long_for_fernet!!'
        }

    @patch('auth.oauth.Flow')
    @patch('auth.oauth.TokenEncryption')
    def test_initiate_google_auth_success(self, mock_encryption, mock_flow, mock_env_vars):
        """Test successful OAuth initiation"""
        with patch.dict('os.environ', mock_env_vars):
            # Mock Flow
            mock_flow_instance = Mock()
            mock_flow_instance.authorization_url.return_value = (
                "https://accounts.google.com/o/oauth2/auth?state=encrypted_state",
                None
            )
            mock_flow.from_client_config.return_value = mock_flow_instance

            # Mock encryption
            mock_encryption_instance = Mock()
            mock_encryption_instance.encrypt.return_value = "encrypted_user_id"
            mock_encryption.return_value = mock_encryption_instance

            result = initiate_google_auth("123")

            assert "authorization_url" in result
            assert "state" in result
            assert result["state"] == "encrypted_user_id"
            mock_encryption_instance.encrypt.assert_called_once_with("123")
            mock_flow_instance.authorization_url.assert_called_once()

    @patch('auth.oauth.TokenEncryption')
    def test_initiate_google_auth_encryption_error(self, mock_encryption, mock_env_vars):
        """Test OAuth initiation with encryption error"""
        with patch.dict('os.environ', mock_env_vars):
            mock_encryption.side_effect = EncryptionError("Encryption failed")

            with pytest.raises(OAuthError, match="Google auth failed"):
                initiate_google_auth("123")

    @patch('auth.oauth.Flow')
    @patch('auth.oauth.TokenEncryption')
    def test_initiate_google_auth_flow_error(self, mock_encryption, mock_flow, mock_env_vars):
        """Test OAuth initiation with Flow error"""
        with patch.dict('os.environ', mock_env_vars):
            mock_encryption_instance = Mock()
            mock_encryption_instance.encrypt.return_value = "encrypted_user_id"
            mock_encryption.return_value = mock_encryption_instance

            mock_flow.from_client_config.side_effect = Exception("Flow error")

            with pytest.raises(OAuthError, match="Google auth failed"):
                initiate_google_auth("123")


class TestCompleteGoogleAuth:
    """Tests for the complete_google_auth function"""

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables"""
        return {
            'GOOGLE_AUTH_CREDS': json.dumps({
                "web": {
                    "client_id": "test_client_id",
                    "client_secret": "test_secret"
                }
            }),
            'BASE_URL': 'https://example.com',
            'TOKEN_ENCRYPTION_KEY': 'test_key_32_bytes_long_for_fernet!!'
        }

    @patch('auth.oauth.get_db_session')
    @patch('auth.oauth.TokenManager')
    @patch('auth.oauth.TokenEncryption')
    @patch('auth.oauth.Flow')
    @patch('auth.oauth.validate_token_in_db')
    def test_complete_google_auth_success(
        self,
        mock_validate,
        mock_flow,
        mock_encryption,
        mock_token_manager,
        mock_db_session,
        mock_env_vars
    ):
        """Test successful OAuth completion"""
        with patch.dict('os.environ', mock_env_vars):
            # Mock database session
            mock_db = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_db

            # Mock encryption
            mock_encryption_instance = Mock()
            mock_encryption_instance.decrypt.return_value = "123"
            mock_encryption_instance.encrypt.return_value = "encrypted_token"
            mock_encryption.return_value = mock_encryption_instance

            # Mock Flow
            mock_flow_instance = Mock()
            mock_credentials = Mock()
            mock_credentials.to_json.return_value = '{"token": "test_token"}'
            mock_flow_instance.credentials = mock_credentials
            mock_flow.from_client_config.return_value = mock_flow_instance

            # Mock TokenManager
            mock_manager_instance = Mock()
            mock_token_manager.return_value = mock_manager_instance

            result = complete_google_auth("auth_code", "encrypted_state")

            assert result == mock_credentials
            mock_flow_instance.fetch_token.assert_called_once_with(code="auth_code")
            mock_manager_instance.add_object.assert_called_once()

    @patch('auth.oauth.get_db_session')
    @patch('auth.oauth.Flow')
    @patch('auth.oauth.TokenEncryption')
    def test_complete_google_auth_encryption_error(self, mock_encryption, mock_flow, mock_db_session, mock_env_vars):
        """Test OAuth completion with encryption error"""
        with patch.dict('os.environ', mock_env_vars):
            # Mock database session
            mock_db = Mock()
            mock_db_session.return_value.__enter__.return_value = mock_db

            # Mock Flow first to avoid client config error
            mock_flow_instance = Mock()
            mock_flow.from_client_config.return_value = mock_flow_instance
            mock_flow_instance.fetch_token.return_value = None

            # Mock encryption to raise error
            mock_encryption_instance = Mock()
            mock_encryption_instance.decrypt.side_effect = EncryptionError("Decryption failed")
            mock_encryption.return_value = mock_encryption_instance

            with pytest.raises(OAuthError, match="Google auth failed"):
                complete_google_auth("code", "state")


class TestCheckScopes:
    """Tests for the check_scopes function"""

    def test_check_scopes_match(self):
        """Test with matching scopes"""
        token_data = {"scopes": SCOPES.copy()}
        mock_manager = Mock()

        # Should not raise any exception
        check_scopes(token_data, "123", mock_manager)

        # Should not delete token
        mock_manager.delete_object.assert_not_called()

    def test_check_scopes_mismatch(self):
        """Test with mismatched scopes"""
        token_data = {"scopes": ["https://www.googleapis.com/auth/calendar"]}
        mock_manager = Mock()

        with pytest.raises(OAuthError, match="must re-authenticate"):
            check_scopes(token_data, "123", mock_manager)

        # Should delete token
        mock_manager.delete_object.assert_called_once()

    def test_check_scopes_missing(self):
        """Test with missing scopes key"""
        token_data = {}
        mock_manager = Mock()

        with pytest.raises(OAuthError):
            check_scopes(token_data, "123", mock_manager)

        mock_manager.delete_object.assert_called_once()


class TestGetCreds:
    """Tests for the get_creds function"""

    @pytest.fixture
    def valid_token_json(self):
        """Valid token JSON with correct scopes"""
        return json.dumps({
            "token": "test_token",
            "refresh_token": "refresh_token",
            "scopes": SCOPES
        })

    @patch('auth.oauth.check_scopes')
    @patch('auth.oauth.Credentials')
    def test_get_creds_success(self, mock_credentials, mock_check_scopes, valid_token_json):
        """Test successful credential retrieval"""
        mock_encrypt_manager = Mock()
        mock_encrypt_manager.decrypt.return_value = valid_token_json

        mock_token_manager = Mock()
        mock_token = Mock()
        mock_token.token_data = "encrypted_data"

        mock_creds = Mock()
        mock_credentials.from_authorized_user_info.return_value = mock_creds

        result = get_creds(mock_encrypt_manager, mock_token_manager, mock_token, "123")

        assert result == mock_creds
        mock_encrypt_manager.decrypt.assert_called_once_with("encrypted_data")
        mock_check_scopes.assert_called_once()

    def test_get_creds_invalid_json(self):
        """Test with invalid JSON"""
        mock_encrypt_manager = Mock()
        mock_encrypt_manager.decrypt.return_value = "invalid json"

        mock_token_manager = Mock()
        mock_token = Mock()
        mock_token.token_data = "encrypted_data"

        with pytest.raises(OAuthError, match="Invalid google credentials"):
            get_creds(mock_encrypt_manager, mock_token_manager, mock_token, "123")

        mock_token_manager.delete_object.assert_called_once()

    @patch('auth.oauth.check_scopes')
    def test_get_creds_scope_mismatch_deletes_token(self, mock_check_scopes):
        """Test that scope mismatch properly deletes token"""
        mock_check_scopes.side_effect = OAuthError("Scope mismatch")

        mock_encrypt_manager = Mock()
        mock_encrypt_manager.decrypt.return_value = json.dumps({"scopes": []})

        mock_token_manager = Mock()
        mock_token = Mock()

        with pytest.raises(OAuthError):
            get_creds(mock_encrypt_manager, mock_token_manager, mock_token, "123")


class TestAuthGoogle:
    """Tests for the auth_google function"""

    @patch('auth.oauth.get_db_session')
    @patch('auth.oauth.TokenManager')
    @patch('auth.oauth.TokenEncryption')
    @patch('auth.oauth.get_creds')
    def test_auth_google_with_valid_creds(
        self,
        mock_get_creds,
        mock_encryption,
        mock_token_manager,
        mock_db_session
    ):
        """Test with valid, non-expired credentials"""
        # Mock database session
        mock_db = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock TokenManager
        mock_manager_instance = Mock()
        mock_token = Mock()
        mock_manager_instance.get_object_by_name.return_value = mock_token
        mock_token_manager.return_value = mock_manager_instance

        # Mock credentials - valid and not expired
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_creds.expired = False
        mock_get_creds.return_value = mock_creds

        result = auth_google("123")

        assert result == mock_creds
        mock_manager_instance.get_object_by_name.assert_called_once_with('google_auth')

    @patch('auth.oauth.get_db_session')
    @patch('auth.oauth.TokenManager')
    @patch('auth.oauth.TokenEncryption')
    @patch('auth.oauth.get_creds')
    @patch('auth.oauth.Request')
    def test_auth_google_with_expired_creds(
        self,
        mock_request,
        mock_get_creds,
        mock_encryption,
        mock_token_manager,
        mock_db_session
    ):
        """Test with expired but refreshable credentials"""
        # Mock database session
        mock_db = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock TokenManager
        mock_manager_instance = Mock()
        mock_token = Mock()
        mock_manager_instance.get_object_by_name.return_value = mock_token
        mock_token_manager.return_value = mock_manager_instance

        # Mock encryption
        mock_encryption_instance = Mock()
        mock_encryption_instance.encrypt.return_value = "encrypted_refreshed_token"
        mock_encryption.return_value = mock_encryption_instance

        # Mock credentials - expired but has refresh token
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_creds.to_json.return_value = '{"token": "refreshed"}'
        mock_get_creds.return_value = mock_creds

        result = auth_google("123")

        assert result == mock_creds
        mock_creds.refresh.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('auth.oauth.get_db_session')
    @patch('auth.oauth.TokenManager')
    @patch('auth.oauth.TokenEncryption')
    def test_auth_google_no_token(
        self,
        mock_encryption,
        mock_token_manager,
        mock_db_session
    ):
        """Test when no token exists in database"""
        # Mock database session
        mock_db = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock TokenManager - no token found
        mock_manager_instance = Mock()
        mock_manager_instance.get_object_by_name.return_value = None
        mock_token_manager.return_value = mock_manager_instance

        with pytest.raises(OAuthError, match="must authenticate with google"):
            auth_google("123")

    @patch('auth.oauth.get_db_session')
    @patch('auth.oauth.TokenManager')
    @patch('auth.oauth.TokenEncryption')
    @patch('auth.oauth.get_creds')
    def test_auth_google_invalid_no_refresh_token(
        self,
        mock_get_creds,
        mock_encryption,
        mock_token_manager,
        mock_db_session
    ):
        """Test with invalid credentials and no refresh token"""
        # Mock database session
        mock_db = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db

        # Mock TokenManager
        mock_manager_instance = Mock()
        mock_token = Mock()
        mock_manager_instance.get_object_by_name.return_value = mock_token
        mock_token_manager.return_value = mock_manager_instance

        # Mock credentials - invalid and no refresh token
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = None
        mock_get_creds.return_value = mock_creds

        with pytest.raises(OAuthError, match="must authenticate with google"):
            auth_google("123")
