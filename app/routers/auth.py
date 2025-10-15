from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from auth import user_login
from auth.authentication import ACCESS_TOKEN_EXPIRE_MINUTES
from auth.oauth import initiate_google_auth, complete_google_auth
from storage.database import get_db
from validation import schemas

router = APIRouter(
    prefix='/auth',
    tags=['Authentication']
)

@router.post(
    '/jwt/token',
    summary="Login and get access token",
)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
) -> schemas.Token:
    """
    Authenticate user and return a JWT access token upon successful login.
    """
    user = user_login.authenticate_user(username=form_data.username, password=form_data.password, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = user_login.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")


@router.get(
    '/google/initiate',
    summary="Initiate Google OAuth auth",
)
def initiate_google_oauth(
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)]
):
    """
    Initiate Google OAuth flow for Gmail API access.
    Returns authorization URL that the frontend should redirect the user to.
    """
    try:
        auth_data = initiate_google_auth(str(current_user.id))
        return {
            "authorization_url": auth_data["authorization_url"],
            "message": "Redirect user to this URL to complete Google auth"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google auth failed: {str(e)}"
        )


@router.get(
    '/google/callback',
    summary="Handle Google OAuth callback"
)
def google_oauth_callback(code: str, state: str):
    """
    Handle Google OAuth callback and store user credentials.
    This endpoint is called by Google after user grants permission.
    """
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required parameters")
    try:
        complete_google_auth(code, state)
        return {"message": "Google auth completed successfully", "status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google auth failed: {str(e)}"
        )

