import json
import os
from typing import List, Dict, Union
from  google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from auth.token_encryption import TokenEncryption, EncryptionError
from storage.data_manager import TokenManager
from storage.database import get_db_session
from validation.schemas import UserAuthToken


class OAuthError(Exception):
    pass


def initiate_google_auth(user_id: str, scopes: List[str]) -> Dict[str, str]:
    """Initiate Google OAuth flow for web users."""
    try:
        credentials = os.getenv('GOOGLE_AUTH_CREDS')
        flow = Flow.from_client_config(
            json.loads(credentials),
            scopes=scopes
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
    except EncryptionError:
        raise
    except Exception as e:
        raise OAuthError(str(e))


def complete_google_auth(code: str, state: str, scopes: List[str]) -> Union[Credentials, str]:
    """Complete Google OAuth flow with authorization code."""
    try:
        credentials = os.getenv('GOOGLE_AUTH_CREDS')
        flow = Flow.from_client_config(json.loads(credentials), scopes)
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
            token_manager.add_object(token_object)

        return flow.credentials
    except EncryptionError:
        raise
    except Exception as e:
        raise OAuthError(str(e))
