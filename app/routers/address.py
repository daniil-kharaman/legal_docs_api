from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from auth import user_login
from storage.data_manager import AddressManager
from storage.database import get_db
from validation import schemas, validation

router = APIRouter(
    prefix='/address',
    tags=['Addresses']
)

@router.get(
    '/address/{address_id}',
    response_model=schemas.AddressInDb,
    summary="Get address details"
)
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


@router.delete(
    '/address/{address_id}',
    summary="Delete address",
)
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


@router.patch(
    '/address/{address_id}',
    summary="Update address information",
)
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
