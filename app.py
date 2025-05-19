from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import exc
from storage import db_models, database
import os
from typing import Annotated, List
from storage.data_manager import ClientManager, AddressManager, TemplateManager, UserManager
from datetime import timedelta
from storage.database import get_db
from authentication.authentication import ACCESS_TOKEN_EXPIRE_MINUTES
from authentication import user_login
from validation import validation, schemas
from validation.validation import db_connection_handler


try:
    db_models.Base.metadata.create_all(bind=database.engine)
except (exc.OperationalError, exc.ArgumentError) as e:
    print(f"Database cannot be accessed: {e}")
except Exception as e:
    print(f"Error: {e}")


app = FastAPI(
    title='LegalDocs API',
    description="""
    API for generating legal documents and client management.
    
    This API allows legal professionals to:
    * Manage user accounts
    * Create and manage clients
    * Store client addresses
    * Upload document templates
    * Generate legal documents from templates
    
    ## Authentication
    
    The API uses OAuth2 with JWT tokens. To authenticate:
    1. Create a user account via `/user/create`
    2. Obtain a token via `/token`
    3. Include the token in the Authorization header for protected endpoints
    """,
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication endpoints for obtaining and using access tokens."
        },
        {
            "name": "User",
            "description": "Operations related to user management, including creation, updates, and deletion."
        },
        {
            "name": "Client",
            "description": "Client management endpoints for creating, retrieving, updating, and deleting client records."
        },
        {
            "name": "Address",
            "description": "Operations for managing client addresses including creation, retrieval, and updates."
        },
        {
            "name": "Template",
            "description": "Document template operations including upload, management, and document generation."
        }
    ]
)


@app.post(
    '/user/create',
    response_model=schemas.UserResponse,
    tags=["User"],
    summary="Create new user"
)
@db_connection_handler
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


@app.post(
    '/token',
    tags=["Authentication"],
    summary="Login and get access token",
)
@db_connection_handler
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


@app.get(
    '/user/me',
    response_model=schemas.UserResponse,
    tags=["User"],
    summary="Get current user information"
)
@db_connection_handler
def read_users_me(
    current_user: Annotated[schemas.UserResponse, Depends(user_login.get_current_active_user)],
):
    """
    Retrieve the current authenticated user's information.
    """
    return current_user


@app.delete(
    '/user/delete',
    tags=["User"],
    summary="Delete current user account",
)
@db_connection_handler
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


@app.patch(
    '/user/update',
    response_model=schemas.UserResponse,
    tags=["User"],
    summary="Update user information",
)
@db_connection_handler
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


@app.get(
    '/user/clients',
    tags=["User", "Client"],
    summary="Get all user's clients",
    response_model=List[schemas.ClientInDb]
)
@db_connection_handler
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


@app.get(
    '/user/templates',
    tags=["User", "Template"],
    summary="Get all user's templates",
    response_model=List[schemas.DocumentTemplateInDb]
)
@db_connection_handler
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


@app.post(
    '/client/add',
    response_model=schemas.ClientInDb,
    tags=["Client"],
    summary="Add new client"
)
@db_connection_handler
def add_client(
        client: schemas.Client,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Add a new client for the current user after ensuring the client does not already exist.
    """
    client_manager = ClientManager(db, object_id=None, user_id=current_user.id)
    if client_manager.client_in_database(client):
        raise HTTPException(status_code=400, detail='Client is already in database')
    return client_manager.add_object(client)


@app.get(
    '/client/{client_id}',
    response_model=schemas.ClientResponse,
    tags=["Client"],
    summary="Get client details"
)
@db_connection_handler
def get_client(
        client_id: int,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Retrieve a specific client by ID, including their address ID if available.
    """
    client_manager = ClientManager(db=db, object_id=client_id, user_id=current_user.id)
    client = validation.get_client_from_db(client_id, client_manager.get_object)
    client_address_id_dict = {"client_address_id": (client.client_address.id if client.client_address else None)}
    return client, client_address_id_dict


@app.delete(
    '/client/{client_id}',
    tags=["Client"],
    summary="Delete client",
)
@db_connection_handler
def delete_client(
        client_id: int,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Delete a specific client by ID.
    """
    client_manager = ClientManager(db=db, object_id=client_id, user_id=current_user.id)
    client = validation.get_client_from_db(client_id, client_manager.get_object)
    client_manager.delete_object()
    return JSONResponse(content={"client": client.id, "message": "Client was successfully deleted"}, status_code=200)


@app.patch(
    '/client/{client_id}',
    response_model=schemas.ClientInDb,
    tags=["Client"],
    summary="Update client information",
)
@db_connection_handler
def update_client(
        client_id: int,
        new_client_data: schemas.ClientUpdate,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Update information for a specific client by ID.
    """
    client_manager = ClientManager(db=db, object_id=client_id, user_id=current_user.id)
    validation.get_client_from_db(client_id, client_manager.get_object)
    client_manager.update_object(new_client_data)
    return JSONResponse(
        content={"message": "Client was successfully updated"},
        status_code=status.HTTP_204_NO_CONTENT
    )


@app.post(
    '/client/{client_id}/address',
    response_model=schemas.AddressInDb,
    tags=["Address", "Client"],
    summary="Add client address"
)
@db_connection_handler
def add_address(
        client_id: int,
        address: schemas.Address,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Add a new address for a specific client.
    """
    client_manager = ClientManager(db=db, object_id=client_id, user_id=current_user.id)
    address_manager = AddressManager(db=db, object_id=None, client_id=client_id)
    validation.get_client_from_db(client_id, client_manager.get_object)
    validation.validate_address_by_client(client_id, address_manager.address_relate_to_client)
    return address_manager.add_object(address)


@app.get(
    '/address/{address_id}',
    response_model=schemas.AddressInDb,
    tags=["Address"],
    summary="Get address details"
)
@db_connection_handler
def get_address(
        address_id: int,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Retrieve a specific address by ID.
    """
    address_manager = AddressManager(db, object_id=address_id)
    address = validation.get_address_from_db(address_id, address_manager.get_object)
    return address


@app.delete(
    '/address/{address_id}',
    tags=["Address"],
    summary="Delete address",
)
@db_connection_handler
def delete_address(
        address_id: int,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Delete a specific address by ID.
    """
    address_manager = AddressManager(db, object_id=address_id)
    address = validation.get_address_from_db(address_id, address_manager.get_object)
    address_manager.delete_object()
    return JSONResponse(content={"address": address.id, "message": "Address was successfully deleted"}, status_code=200)


@app.patch(
    '/address/{address_id}',
    tags=["Address"],
    summary="Update address information",
)
@db_connection_handler
def update_address(
        address_id: int,
        new_address_data: schemas.AddressUpdate,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Update information for a specific address by ID.
    """
    address_manager = AddressManager(db, object_id=address_id)
    validation.get_address_from_db(address_id, address_manager.get_object)
    address_manager.update_object(new_address_data)
    return JSONResponse(
        content={"message": "Address was successfully updated"},
        status_code=status.HTTP_204_NO_CONTENT
    )


@app.post(
    '/template/upload',
    response_model=schemas.DocumentTemplateInDb,
    tags=["Template"],
    summary="Upload document template",
)
@db_connection_handler
def upload_template(
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        file: Annotated[UploadFile, Depends(validation.validate_file)],
        template_name: Annotated[str, Depends(validation.validate_template_name)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Upload a new document template after validating the file and template name.
    """
    upload_directory = os.path.join('document_templates', str(current_user.id))
    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)
    template_manager = TemplateManager(db=db, object_id=None, user_id=current_user.id)
    validation.validate_template(template_name, template_manager.template_in_database)
    template_path = os.path.join(upload_directory, file.filename)
    validation.validate_file_name(template_path, template_manager.template_path_in_db)
    parsed_template = validation.parse_template(file)
    template_schema = schemas.DocumentTemplate(template_name=template_name, template_path=template_path)
    validation.save_file_in_directory(parsed_template, template_path)
    return template_manager.add_object(template_schema)


@app.delete(
    '/template/{template_id}',
    tags=["Template"],
    summary="Delete document template",
)
@db_connection_handler
def delete_template(
        template_id: int,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Delete a specific document template by ID.
    """
    template_manager = TemplateManager(db=db, object_id=template_id, user_id=current_user.id)
    template = validation.get_template_from_db(template_id, template_manager.get_object)
    validation.delete_file(template.template_path)
    template_manager.delete_object()
    return JSONResponse(
        content={"template": template.id, "message": "Template was successfully deleted"},
        status_code=200
    )


@app.patch(
    '/template/{template_id}',
    tags=["Template"],
    summary="Update template name"
)
@db_connection_handler
def update_template(
        template_id: int,
        new_data: schemas.DocumentTemplateName,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Update the name of a specific document template by ID.
    """
    template_manager = TemplateManager(db=db, object_id=template_id, user_id=current_user.id)
    template = validation.get_template_from_db(template_id, template_manager.get_object)
    template_manager.update_object(new_data)
    return JSONResponse(
        content={"message": "Template was successfully updated"},
        status_code=status.HTTP_204_NO_CONTENT
    )


@app.post(
    '/template/{template_id}/generate',
    tags=["Template"],
    summary="Generate document from template",
)
@db_connection_handler
def generate_file(
        template_id: int,
        context: schemas.GenContext,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """
    Generate a document file from a template using the provided context.
    """
    template_manager = TemplateManager(db=db, object_id=template_id, user_id=current_user.id)
    template = validation.get_template_from_db(template_id, template_manager.get_object)
    parsed_context = validation.parse_context(context, db)
    if not parsed_context:
        raise HTTPException(status_code=400, detail='Impossible to parse the context')
    rendered_template = validation.render_template(template.template_path, parsed_context)
    if not rendered_template:
        raise HTTPException(status_code=400, detail='Impossible to render the template')
    headers = {
        "Content-Disposition": (
            f"attachment; filename={template.template_name}"
        )
    }
    return StreamingResponse(
        rendered_template,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers=headers
    )
