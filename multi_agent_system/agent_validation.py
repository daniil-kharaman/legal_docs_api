import json
from typing import Optional, List, Callable, Union
from pydantic import ValidationError
from storage import db_models
import functools
from google.oauth2.credentials import Credentials
from storage.database import DatabaseError
from authentication.token_encryption import EncryptionError
from authentication.oauth import OAuthError


def clients_validation(clients: List[db_models.Client], birthdate: Optional[str],
                       client_full_name: str, second_check: bool) -> Optional[str]:
    """Validate client search results and return email if unique match found."""

    if not clients:
        return f"Error: There is no client with name {client_full_name}"
    elif len(clients) > 1 and not birthdate:
        return f"Error: There are several persons with name {client_full_name}. Specify the birthdate."
    elif len(clients) > 1 and birthdate and second_check:
        return f"Error: There are several persons with name {client_full_name} and birthdate {birthdate}"
    elif len(clients) == 1:
        return clients[0].email
    return None


def email_db_validation(func: Callable) -> Callable:
    """Decorator for handling email database operation errors."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> str:
        try:
            return func(*args, **kwargs)
        except DatabaseError as e:
            return str(e)
        except ValueError as e:
            print(f"Name parsing error: {e}")
            return str(e)
        except AttributeError as e:
            print(f"Data access error: {e}")
            return "Error: Invalid client data format."
        except Exception as e:
            print(f"Unexpected error in get_email_from_database: {e}")
            return "Error: Failed to retrieve email from database. Please try again."
    return wrapper


def google_auth_validation(func: Callable) -> Callable:
    """Decorator for handling Google authentication errors."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[Credentials, str]:
        try:
            return func(*args, **kwargs)
        except DatabaseError as e:
            return str(e)
        except OAuthError as e:
            print(f"OAuth error: {e}")
            return "Error: Google authorization failed."
        except EncryptionError as e:
            print(f"Encryption error: {e}")
            return "Error: Authorization problem. Try again later."
        except ValidationError as e:
            print(f"Token validation error: {e}")
            return "Error: Invalid token format. Please re-authenticate."
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return "Error: Invalid credential format. Please re-authenticate."
        except Exception as e:
            print(f"Unexpected authentication error: {e}")
            return "Error: Authentication failed. Please try again."
    return wrapper
