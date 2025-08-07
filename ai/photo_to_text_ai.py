from google.cloud import documentai
from google.oauth2 import service_account
from fastapi import UploadFile
import os
from dotenv import load_dotenv
from datetime import datetime
import json
from typing import Dict, Optional, List, Any, MutableSequence

load_dotenv()

project_id = os.getenv('PROJECT_ID')
location = os.getenv('LOCATION')
processor_id = os.getenv('PROCESSOR_ID')
credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
credentials_info = json.loads(credentials_json)
document_ai_api_endpoint = os.getenv('DOCUMENT_AI_API_ENDPOINT')


def parse_birthdate(date: str) -> Optional[datetime.date]:
    """
    Parses a birthdate string into a datetime.date object.
    Returns None if the input is invalid or parsing fails.
    """
    try:
        if not date:
            return None
        date = date.split()
        if len(date) < 3:
            return None
        day = date[0]
        month = date[1].split('/')[1]
        year = date[2]
        formatted_date = f"{day} {month} {year}"
        parsed_date = datetime.strptime(formatted_date, '%d %b %y')
        return parsed_date.date()
    except (AttributeError, IndexError, ValueError) as e:
        print(f"Wrong format of the date: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def format_processed_data(entities: MutableSequence[documentai.Document.Entity]) -> Dict[str, Any]:
    """
    Processes and formats extracted entities into a structured dictionary.
    Handles special formatting for birth dates and groups repeated entity types into lists.
    """
    processed_data = dict()
    for entity in entities:
        key = entity.type_
        if key == 'Birth' and entity.normalized_value.text:
            text_value = entity.normalized_value.text
        elif key == 'Birth':
            text_value = parse_birthdate(entity.text_anchor.content or entity.mention_text) or ' '
        else:
            text_value = (entity.text_anchor.content.title() or entity.mention_text.title()) or ' '
        if key in processed_data:
            if isinstance(processed_data[key], str):
                processed_data[key] = processed_data[key] + '@'
                processed_data[key] = processed_data[key].split('@')
                processed_data[key].pop()
            processed_data[key].append(text_value)
        else:
            processed_data[key] = text_value
    return processed_data


async def process_id_photo(file: UploadFile) -> Optional[Dict[str, Any]]:
    """
    Processes an uploaded ID photo using Google Document AI to extract structured data.
    Sends the image to the configured Document AI processor, extracts entities, and returns formatted results.
    """
    try:
        mime_type = file.content_type
        field_mask = 'entities'
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        client_options = {"api_endpoint": document_ai_api_endpoint}
        client = documentai.DocumentProcessorServiceClient(credentials=credentials, client_options=client_options)
        name = client.processor_path(project_id, location, processor_id)
        image_content = await file.read()
        raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
        request = documentai.ProcessRequest(
            name=name,
            raw_document=raw_document,
            field_mask=field_mask
        )
        result = client.process_document(request=request)
        document = result.document
        processed_data_formatted = format_processed_data(document.entities)
        return processed_data_formatted
    except Exception as e:
        print(f"Error while processing an image: {e}")
        return None
