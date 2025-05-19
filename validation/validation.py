import functools
from fastapi import HTTPException, File, UploadFile, status, Form
from typing import Annotated
from validation.schemas import DocumentTemplateName, DocumentTemplateFileName, GenContext
from pydantic import ValidationError
import os
from docx import Document
from python_docx_replace import docx_replace
from docxtpl import DocxTemplate
from io import BytesIO
from sqlalchemy.exc import OperationalError, ArgumentError
from storage.data_manager import ClientManager


def db_connection_handler(func):
    """
    Decorator that handles database connection errors and raises HTTP 500 if the database is inaccessible.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
             return func(*args, **kwargs)
        except (OperationalError, ArgumentError) as e:
            print(f"Database cannot be accessed: {e}")
            raise HTTPException(status_code=500, detail='Database cannot be accessed')
    return wrapper


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
            raise HTTPException(status_code=500, detail='Something went wrong')
    return wrapper


def validate_username_in_db(user_username):
    """
    Raise an HTTP 400 error if the provided username already exists in the database.
    """
    if user_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Such user exists already. Choose another username.'
        )


def validate_email_in_db(user_email):
    """
    Raise an HTTP 400 error if the provided email already exists in the database.
    """
    if user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Such user exists already. Choose another email.'
        )


def get_client_from_db(client_id: int, get_client_func):
    """
    Retrieve a client by ID using the provided function; raise HTTP 400 if not found.
    """
    client = get_client_func()
    if not client:
        raise HTTPException(status_code=400, detail=f"There is no client with id {client_id}")
    return client


def get_template_from_db(template_id: int, get_template_func):
    """
    Retrieve a template by ID using the provided function; raise HTTP 400 if not found.
    """
    template = get_template_func()
    if not template:
        raise HTTPException(status_code=400, detail=f"There is no template with id {template_id}")
    return template


def validate_address_by_client(client_id: int, address_relate_to_client_func):
    """
    Check if a client already has an address; raise HTTP 400 if an address exists.
    """
    address = address_relate_to_client_func()
    if address:
        raise HTTPException(status_code=400, detail=f"Client with id {client_id} has already the address")


def get_address_from_db(address_id: int, get_client_address_func):
    """
    Retrieve an address by ID using the provided function; raise HTTP 400 if not found.
    """
    address = get_client_address_func()
    if not address:
        raise HTTPException(status_code=400, detail=f"There is no address with id {address_id}")
    return address


def validate_template(template_name: str, template_in_database_func):
    """
    Raise an HTTP 400 error if a template with the given name already exists.
    """
    doc_template = template_in_database_func(template_name)
    if doc_template:
        raise HTTPException(status_code=400, detail=f"Template {template_name} already exists")


def validate_file_name(file_path: str, template_path_in_db_func):
    """
    Raise an HTTP 400 error if a file with the given path already exists.
    """
    file_path = template_path_in_db_func(file_path)
    if file_path:
        raise HTTPException(status_code=400, detail=f"File already exists")


async def validate_template_name(template_name: Annotated[str, Form()]):
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


def validate_file(file: Annotated[UploadFile, File()]):
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


@validate_file_operation
def delete_file(path):
    """
    Delete a file at the specified path; raise an HTTP error if the operation fails.
    """
    os.remove(path)


@validate_file_operation
def save_file_in_directory(file: Document, path):
    """
    Save a Document object to the specified path; raise an HTTP error if the operation fails.
    """
    file.save(path)


def parse_template(template_file: UploadFile) -> Document:
    """
    Parse a DOCX template file and replace placeholders with Jinja2 syntax; raise HTTP 400 on error.
    """
    try:
        replacement_context = {
            'DATE': '{{date}}',
            'PARTY1_START': '{% for person in party_one %}',
            'PARTY1_END': '{% endfor %}',
            'NAME': '{{person.firstname}} {{person.second_name}} {{person.lastname}}',
            'ADDRESS': '''{{person.client_address.house_number}}, {{person.client_address.street}}, {{person.client_address.city}}, {{person.client_address.postal_code}}, {{person.client_address.country}}''',
            'BIRTH': '{{person.birthdate}}',
            'PARTY2_START': '{% for person in party_two %}',
            'PARTY2_END': '{% endfor %}'
        }
        doc = Document(template_file.file)
        docx_replace(doc, **replacement_context)
        return doc
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=400, detail='Something went wrong. Try again.')


def parse_context(context: GenContext, db):
    """
    Construct a context dictionary for template rendering by retrieving client data from the database.
    """
    party_one = []
    for person_id in context.party_one_id:
        client = ClientManager(db, person_id, user_id=None).get_object()
        if client is None:
            raise HTTPException(status_code=400, detail=f"There is no client with id {person_id}")
        client.birthdate = client.birthdate.strftime('%d %B %Y')
        party_one.append(client)
    party_two = []
    for person_id in context.party_two_id:
        client = ClientManager(db, person_id, user_id=None).get_object()
        if client is None:
            raise HTTPException(status_code=400, detail=f"There is no client with id {person_id}")
        client.birthdate = client.birthdate.strftime('%d %B %Y')
        party_two.append(client)
    date = context.date.strftime('%d %B %Y')
    parsed_context = {
        "party_one": party_one,
        "party_two": party_two,
        "date": date
    }
    return parsed_context


@validate_file_operation
def render_template(path, context):
    """
    Render a DOCX template with the provided context and return the result as a BytesIO buffer.
    """
    doc = DocxTemplate(path)
    doc.render(context)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
