from typing import Callable
import functools
from storage.database import DatabaseError
import logging

logger = logging.getLogger(__name__)


def email_db_validation(func: Callable) -> Callable:
    """Decorator for handling email database operation errors."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> str:
        try:
            return func(*args, **kwargs)
        except DatabaseError as e:
            logger.error(f"Database error: {e}", exc_info=True)
            return str(e)
        except ValueError as e:
            logger.error(f"Name parsing error: {e}", exc_info=True)
            return str(e)
        except AttributeError as e:
            logger.error(f"Data access error: {e}", exc_info=True)
            return "Error: Invalid client data format."
        except Exception as e:
            logger.error(f"Unexpected error in get_email_from_database: {e}", exc_info=True)
            return "Error: Failed to retrieve email from database. Please try again."
    return wrapper
