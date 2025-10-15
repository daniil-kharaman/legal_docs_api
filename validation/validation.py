import functools
from fastapi import HTTPException, File, UploadFile, status, Form
from typing import Annotated
from validation.schemas import DocumentTemplateName, DocumentTemplateFileName, GenContext
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError, ArgumentError
from botocore.exceptions import ClientError, BotoCoreError
import imghdr


def validate_file_operation(func):
    """
    Decorator that handles file operation errors and raises appropriate HTTP exceptions.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (IOError, OSError) as e:
            print(f"Error: {e}")
            raise HTTPException(status_code=400, detail='The file cannot be processed')
        except Exception as e:
            print(f"Error: {e}")
            raise HTTPException(status_code=500, detail='Something went wrong processing the file')
    return wrapper


def validate_username_in_db(user_username: str | None) -> None:
    """
    Raise an HTTP 400 error if the provided username already exists in the database.
    """
    if user_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Such user exists already. Choose another username.'
        )


def validate_email_in_db(user_email: str | None) -> None:
    """
    Raise an HTTP 400 error if the provided email already exists in the database.
    """
    if user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Such user exists already. Choose another email.'
        )


def get_client_from_db(client_id: int, get_client_func) -> object:
    """
    Retrieve a client by ID using the provided function; raise HTTP 400 if not found.
    """
    client = get_client_func()
    if not client:
        raise HTTPException(status_code=400, detail=f"There is no client with id {client_id}")
    return client


def get_template_from_db(template_id: int, get_template_func) -> object:
    """
    Retrieve a template by ID using the provided function; raise HTTP 400 if not found.
    """
    template = get_template_func()
    if not template:
        raise HTTPException(status_code=400, detail=f"There is no template with id {template_id}")
    return template


def validate_address_by_client(client_id: int, address_relate_to_client_func) -> None:
    """
    Check if a client already has an address; raise HTTP 400 if an address exists.
    """
    address = address_relate_to_client_func()
    if address:
        raise HTTPException(status_code=400, detail=f"Client with id {client_id} has already the address")


def get_address_from_db(address_id: int, get_client_address_func) -> object:
    """
    Retrieve an address by ID using the provided function; raise HTTP 400 if not found.
    """
    address = get_client_address_func()
    if not address:
        raise HTTPException(status_code=400, detail=f"There is no address with id {address_id}")
    return address


def validate_template(template_name: str, template_in_database_func) -> None:
    """
    Raise an HTTP 400 error if a template with the given name already exists.
    """
    doc_template = template_in_database_func(template_name)
    if doc_template:
        raise HTTPException(status_code=400, detail=f"Template {template_name} already exists")


def validate_file_name(file_path: str, template_path_in_db_func) -> None:
    """
    Raise an HTTP 400 error if a file with the given path already exists.
    """
    file_path = template_path_in_db_func(file_path)
    if file_path:
        raise HTTPException(status_code=400, detail=f"File already exists")


async def validate_template_name(template_name: Annotated[str, Form()]) -> str:
    """
    Validate the template name using a Pydantic schema; raise HTTP 422 on validation error.
    """
    try:
        validator = DocumentTemplateName(template_name=template_name)
        return validator.template_name
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=e.errors()
        )


def validate_file(file: Annotated[UploadFile, File()]) -> UploadFile:
    """
    Validate that the uploaded file is a DOCX file and has a valid filename; raise appropriate HTTP errors.
    """
    content_type = file.content_type
    if content_type != 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Wrong format of the file {file.filename}. Only DOCX files are allowed"
        )
    try:
        validator = DocumentTemplateFileName(file_name=file.filename)
        return file
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=e.errors()
        )


def aws_validation(func):
    """
    Decorator that handles AWS and boto3 errors.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise HTTPException(status_code=400, detail=f"AWS Error: {error_code} - {error_message}")
        except BotoCoreError as e:
            raise HTTPException(status_code=400, detail=f"boto3 Error: {e}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error: {e}")
    return wrapper


async def validate_process_id_photo(file: UploadFile, process_photo_func) -> dict:
    """
    Raise an HTTP 500 error if the process of fetching data from image fails.
    """
    processed_data = await process_photo_func(file)
    if processed_data is None:
        raise HTTPException(status_code=500, detail='Error while processing an image. Try again later.')
    return processed_data


async def validate_image(file: Annotated[UploadFile, File()]) -> UploadFile:
    """
    Validate that the uploaded file is a jpeg or png file; raise appropriate HTTP errors.
    """
    allowed_images_types = ['jpeg', 'png']
    content = await file.read()
    await file.seek(0)
    actual_type = imghdr.what(None, h=content)
    if actual_type is None:
        raise HTTPException(status_code=400, detail='File is not an image')
    if actual_type not in allowed_images_types:
        raise HTTPException(status_code=400, detail=f"Type {actual_type} is not allowed")
    return file
