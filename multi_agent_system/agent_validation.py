import json
from typing import Optional, List, Callable, Union
from pydantic import ValidationError
from sqlalchemy.orm.session import Session
from storage import db_models
import functools
from google.oauth2.credentials import Credentials
from storage.data_manager import TokenManager
from validation.schemas import UserAuthToken
from authentication.token_encryption import EncryptionError


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


def clients_validation(clients: List[db_models.Client], birthdate: Optional[str],
                       client_full_name: str, second_check: bool) -> Optional[str]:
    """Validate client search results and return email if unique match found.

    Args:
        clients: List of client objects from database query
        birthdate: Optional birthdate filter
        client_full_name: Full name of the client being searched
        second_check: Whether this is a second validation with birthdate filter

    Returns:
        Client email address if unique match found, error message otherwise, None if no return condition met
    """
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
    """Decorator for handling email database operation errors.

    Args:
        func: Function to wrap with error handling

    Returns:
        Wrapped function with error handling
    """

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
    """Decorator for handling Google authentication errors.

    Args:
        func: Function to wrap with error handling

    Returns:
        Wrapped function with error handling
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Union[Credentials, str]:
        try:
            return func(*args, **kwargs)
        except DatabaseError as e:
            return str(e)
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


def validate_add_object(token_manager: TokenManager, token_object: UserAuthToken, db: Session) -> None:
    """Add token object to database with transaction management.

    Args:
        token_manager: Token manager instance
        token_object: Token object to add
        db: Database session

    Raises:
        Exception: Re-raises any commit errors after rollback
    """
    try:
        token_manager.add_object(token_object)
        db.commit()
    except Exception as commit_error:
        db.rollback()
        print(f"Transaction rollback due to: {commit_error}")
        raise
