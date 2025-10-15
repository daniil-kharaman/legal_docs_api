from io import BytesIO
from fastapi import UploadFile, HTTPException
from docx import Document
from python_docx_replace import docx_replace
from docxtpl import DocxTemplate
from storage.data_manager import ClientManager
from validation.schemas import GenContext
from validation.validation import validate_file_operation


def parse_template(template_file: UploadFile) -> BytesIO:
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
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=400, detail='Something went wrong. Try again.')


def parse_context(context: GenContext, db) -> dict:
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
def render_template(buffer: BytesIO, context: dict) -> BytesIO:
    """
    Render a DOCX template with the provided context and return the result as a BytesIO buffer.
    """
    doc = DocxTemplate(buffer)
    doc.render(context)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
