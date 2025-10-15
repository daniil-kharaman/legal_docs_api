import functools
from typing import Callable
import json
import os
from  google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from auth.token_encryption import TokenEncryption, EncryptionError
from storage.data_manager import TokenManager
from storage.database import get_db_session, DatabaseError
from validation.schemas import UserAuthToken
from google.auth.transport.requests import Request
import logging

logger = logging.getLogger(__name__)

SCOPES = ["https://mail.google.com/", "https://www.googleapis.com/auth/calendar"]


class OAuthError(Exception):
    pass


def google_auth_validation(func: Callable) -> Callable:
    """Decorator for handling Google auth errors."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DatabaseError:
            raise
        except OAuthError:
            raise
        except EncryptionError as e:
            logger.error(f"Encryption error: {e}", exc_info=True)
            raise OAuthError("Authorization problem. Try again later.") from e
        except Exception as e:
            logger.error(f"Unexpected auth error: {e}", exc_info=True)
            raise OAuthError("Authentication failed. Please try again.") from e
    return wrapper


def validate_token_in_db(token_name: str, token_in_db_func: Callable):
    """Check if token exists in database; raise OAuthError if already authorized."""
    token = token_in_db_func(token_name)
    if token:
        logger.error('Google auth error: User is already authorized.')
        raise OAuthError('User is already authorized.')


def initiate_google_auth(user_id: str) -> dict[str, str]:
    """Initiate Google OAuth flow for web users."""
    try:
        credentials = os.getenv('GOOGLE_AUTH_CREDS')
        flow = Flow.from_client_config(
            json.loads(credentials),
            scopes=SCOPES
        )
        base_url = os.getenv('BASE_URL')
        flow.redirect_uri = f"{base_url}/auth/google/callback"
        id_encryption = TokenEncryption()
        secure_state = id_encryption.encrypt(user_id)
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=secure_state,
            prompt='consent'
        )
        return {
            "authorization_url": authorization_url,
            "state": secure_state
        }
    except EncryptionError as e:
        logger.error(f"Encryption error: {e}", exc_info=True)
        raise OAuthError('Google auth failed.') from e
    except Exception as e:
        logger.error(f"Unexpected initiate google auth error: {e}", exc_info=True)
        raise OAuthError('Google auth failed.') from e


def complete_google_auth(code: str, state: str) -> Credentials | str:
    """Complete Google OAuth flow with authorization code."""
    try:
        credentials = os.getenv('GOOGLE_AUTH_CREDS')
        flow = Flow.from_client_config(json.loads(credentials), SCOPES)
        base_url = os.getenv('BASE_URL')
        flow.redirect_uri = f"{base_url}/auth/google/callback"
        flow.fetch_token(code=code)
        with get_db_session() as db:
            token_encryption = TokenEncryption()
            user_id = token_encryption.decrypt(state)
            token_manager = TokenManager(db=db, object_id=None, user_id=user_id)
            token_object = UserAuthToken(
                token_name='google_auth',
                token_data=token_encryption.encrypt(flow.credentials.to_json()),
                user_id=int(user_id)
            )
            validate_token_in_db('google_auth', token_manager.get_object_by_name)
            token_manager.add_object(token_object)

        return flow.credentials
    except OAuthError:
        raise
    except EncryptionError as e:
        logger.error(f"Encryption error: {e}", exc_info=True)
        raise OAuthError('Google auth failed.') from e
    except Exception as e:
        logger.error(f"Unexpected complete google auth error: {e}", exc_info=True)
        raise OAuthError('Google auth failed.') from e


def check_scopes(token_data_json: dict, user_id: str, token_manager: TokenManager):
    """Validate stored scopes match required scopes; delete token if mismatch."""
    stored_scopes = token_data_json.get('scopes', [])
    if set(stored_scopes) != set(SCOPES):
        logger.error(f"Scope mismatch for user {user_id}: stored={stored_scopes}, requested={SCOPES}")
        token_manager.delete_object()
        raise OAuthError('User must re-authenticate with updated permissions')


def get_creds(
        encrypt_manager: TokenEncryption,
        token_manager: TokenManager,
        token: UserAuthToken,
        user_id: str
) -> Credentials:
    """Decrypt and validate stored token; return Google credentials."""
    try:
        decrypted_token_data = encrypt_manager.decrypt(token.token_data)
        token_data_json = json.loads(decrypted_token_data)
        check_scopes(token_data_json, user_id, token_manager)
        creds = Credentials.from_authorized_user_info(token_data_json, SCOPES)
        return creds
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Invalid credentials for {user_id}: {e}", exc_info=True)
        # Delete corrupted token
        token_manager.delete_object()
        raise OAuthError('Invalid google credentials. Please re-authenticate.') from e


@google_auth_validation
def auth_google(user_id: str) -> Credentials:
    """Authenticate user with Google OAuth and manage tokens."""
    with get_db_session() as db:
        token_encryption = TokenEncryption()
        creds = None
        token_manager = TokenManager(db=db, object_id=None, user_id=user_id)
        token = token_manager.get_object_by_name('google_auth')
        if token:
            creds = get_creds(token_encryption, token_manager, token, user_id)
        if creds and creds.valid:
            return creds
        elif creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            updated_token_data = token_encryption.encrypt(creds.to_json())
            token.token_data = updated_token_data
            db.commit()
            return creds
        logger.error(f"No valid google auth token for user: {user_id}")
        raise OAuthError('User must authenticate with google')
