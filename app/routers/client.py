from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from auth import user_login
from storage.data_manager import ClientManager, AddressManager
from storage.database import get_db
from validation import schemas, validation

router = APIRouter(
    prefix='/client',
    tags=['Clients']
)

@router.post(
    '/add',
    response_model=schemas.ClientInDb,
    summary="Add new client"
)
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


@router.get(
    '/{client_id}',
    response_model=schemas.ClientResponse,
    summary="Get client details"
)
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


@router.delete(
    '/{client_id}',
    summary="Delete client",
)
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


@router.patch(
    '/{client_id}',
    response_model=schemas.ClientInDb,
    summary="Update client information",
)
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


@router.post(
    '/{client_id}/address',
    response_model=schemas.AddressInDb,
    summary="Add client address"
)
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
