from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile
from ai.photo_to_text_ai import process_id_photo
from auth import user_login
from multi_agent_system import agent
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


@router.post(
    '/send_email',
    summary="Send email to the client by entering just client's name",
)
async def send_email(
        user_request: schemas.UserRequestAI,
        current_user: Annotated[schemas.UserInDB, Depends(user_login.get_current_active_user)]
) -> dict:
    """
    Send an email to a client using AI agent to compose and send the message.
    """
    input_message = '{' + f"""
    "user_request": "{user_request}",
    "user_full_name": "{current_user.full_name}",
    "user_id": "{current_user.id}"
""" + '}'
    result = await agent.run_agent(input_message, str(current_user.id))
    return validation.email_sender_validation(result)
