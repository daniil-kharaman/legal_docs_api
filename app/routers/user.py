from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from auth import user_login
from storage.data_manager import UserManager, ClientManager, TemplateManager
from storage.database import get_db
from validation import schemas, validation


router = APIRouter(
    prefix='/user',
    tags=['Users']
)

@router.post(
    '/add',
    response_model=schemas.UserResponse,
    summary="Add new user"
)
def create_user(user: schemas.UserCreate, db: Annotated[Session, Depends(get_db)]):
    """
    Create a new user after validating that the username and email are unique.
    """
    user_manager = UserManager(db=db, object_id=None)
    user_in_db_username = user_manager.user_in_database(username_or_email=user.username)
    user_in_db_email = user_manager.user_in_database(username_or_email=user.email)
    validation.validate_username_in_db(user_in_db_username)
    validation.validate_email_in_db(user_in_db_email)
    return user_manager.add_object(user)


@router.get(
    '/me',
    response_model=schemas.UserResponse,
    summary="Get current user information"
)
def read_users_me(
    current_user: Annotated[schemas.UserResponse, Depends(user_login.get_current_active_user)],
):
    """
    Retrieve the current authenticated user's information.
    """
    return current_user


@router.delete(
    '/delete',
    summary="Delete current user account",
)
def delete_user(
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Delete the current authenticated user's account.
    """
    user_manager = UserManager(db=db, object_id=current_user.id)
    user_manager.delete_object()
    return JSONResponse(
        content={"user": current_user.username, "message": "User was successfully deleted"},
        status_code=200
    )


@router.patch(
    '/update',
    response_model=schemas.UserResponse,
    summary="Update user information",
)
def update_user(
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        new_data: schemas.UserUpdate,
        db: Annotated[Session, Depends(get_db)]
):
    """
    Update the current authenticated user's information.
    """
    user_manager = UserManager(db=db, object_id=current_user.id)
    if new_data.username or new_data.email:
        user_in_db_username = user_manager.user_in_database(username_or_email=new_data.username)
        user_in_db_email = user_manager.user_in_database(username_or_email=new_data.email)
        validation.validate_username_in_db(user_in_db_username)
        validation.validate_email_in_db(user_in_db_email)
    user_manager.update_object(new_data)
    return JSONResponse(
        content={"message": "User was successfully updated"},
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.get(
    '/clients',
    summary="Get all user's clients",
    response_model=List[schemas.ClientInDb]
)
def get_all_clients(
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Retrieve all clients associated with the current user.
    """
    client_manager = ClientManager(db=db, object_id=None, user_id=current_user.id)
    clients = client_manager.get_objects_by_user().all()
    return clients


@router.get(
    '/templates',
    summary="Get all user's templates",
    response_model=List[schemas.DocumentTemplateInDb]
)
def get_all_templates(
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Retrieve all document templates associated with the current user.
    """
    template_manager = TemplateManager(db=db, object_id=None, user_id=current_user.id)
    templates = template_manager.get_objects_by_user().all()
    return templates
