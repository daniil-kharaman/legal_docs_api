from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile
from ai.photo_to_text_ai import process_id_photo
from auth import user_login
from validation import schemas, validation

router = APIRouter(
    prefix='/ai',
    tags=['AI Tools']
)

@router.post(
    '/upload_photo_id',
    summary="Upload a photo of client ID to fetch client's data",
)

async def upload_photo_id(
        file: Annotated[UploadFile, Depends(validation.validate_image)],
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)]
) -> dict:
    """
    Upload a client's ID image and extract personal data using Document AI.
    """
    processed_data = validation.validate_process_id_photo(file, process_id_photo)
    return await processed_data

