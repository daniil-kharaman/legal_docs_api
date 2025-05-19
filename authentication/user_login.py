from datetime import datetime, timedelta, timezone
from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session
from storage.data_manager import UserManager
from storage.database import get_db
from authentication.authentication import pwd_context, oauth2_scheme, SECRET_KEY, ALGORITHM
from validation.validation import db_connection_handler
from validation import schemas


def verify_password(plain_password, hashed_password):
    """
    Verify a plain password against its hashed version using the configured password context.
    """
    return pwd_context.verify(plain_password, hashed_password)


@db_connection_handler
def authenticate_user(username: str, password: str, db: Annotated[Session, Depends(get_db)]):
    """
    Authenticate a user by username and password; return the user object if credentials are valid.
    """
    user_manager = UserManager(db, object_id=None)
    user = user_manager.user_in_database(username_or_email=username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Generate a JWT access token with an optional expiration time.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@db_connection_handler
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]):
    """
    Retrieve the current user based on the provided JWT token; raise HTTP 401 if token is invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user_manager = UserManager(db, object_id=None)
    user = user_manager.user_in_database(username_or_email=username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: Annotated[schemas.UserInDB, Depends(get_current_user)]):
    """
    Ensure the current user is active; raise HTTP 400 if the user is disabled.
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
