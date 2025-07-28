import json
from typing import Dict, Any, List, Tuple, Union, Generator
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from storage.database import SessionLocal
from contextlib import contextmanager
from storage import db_models
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os.path
from dotenv import load_dotenv
from sqlalchemy import exc
from sqlalchemy.orm import Session
from storage.data_manager import TokenManager
from validation.schemas import UserAuthToken
from multi_agent_system import agent_validation
from authentication.token_encryption import TokenEncryption


load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash"


@contextmanager
def get_db_session() -> Generator[Session, None, None]:

    """Context manager for database sessions with proper error handling."""

    db = None
    try:
        db = SessionLocal()
        yield db
    except exc.OperationalError as e:
        print(f"Database operational error: {e}")
        raise agent_validation.DatabaseError("Database server is unavailable. Please try again later.")
    except exc.ArgumentError as e:
        print(f"Database configuration error: {e}")
        raise agent_validation.DatabaseError("Database configuration is invalid. Please contact support.")
    finally:
        if db:
            db.close()


def parse_full_name(full_name: str) -> Tuple[str, str]:
    
    """Parse full name into first and last name."""

    name_parts = full_name.strip().split()
    if len(name_parts) < 2:
        raise ValueError("Error: Invalid full name format. Please provide first and last name.")
    return name_parts[0], name_parts[1]


@agent_validation.email_db_validation
def get_email_from_database(client_full_name: str, user_id: str, birthdate: str) -> str:

    """Retrieve client email from database by name and optional birthdate."""

    with get_db_session() as db:
        first_name, last_name = parse_full_name(client_full_name)
        query = db.query(db_models.Client).filter(
            db_models.Client.firstname == first_name,
            db_models.Client.lastname == last_name,
            db_models.Client.user_id == user_id
        )
        clients = query.all()
        validation_full_name = agent_validation.clients_validation(clients, birthdate,
                                                                   client_full_name, False)
        if validation_full_name:
            return validation_full_name

        query = query.filter(db_models.Client.birthdate == birthdate)
        clients = query.all()
        validation_birthdate = agent_validation.clients_validation(clients, birthdate,
                                                                   client_full_name, True)
        if validation_birthdate:
            return validation_birthdate

        return "Error while trying to find client's email"


@agent_validation.google_auth_validation
def auth_google(user_id: str, scopes: List[str]) -> Union[Credentials, str]:

    """Authenticate user with Google OAuth and manage tokens."""

    with get_db_session() as db:
        token_encryption = TokenEncryption()
        creds = None
        token_manager = TokenManager(db=db, object_id=None, user_id=user_id)
        token = token_manager.get_object_by_name('google_auth')
        if token:
            decrypted_token_data = token_encryption.decrypt(token.token_data)
            creds = Credentials.from_authorized_user_info(json.loads(decrypted_token_data), scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                credentials = os.getenv('GOOGLE_AUTH_CREDS')
                flow = InstalledAppFlow.from_client_config(json.loads(credentials), scopes)
                creds = flow.run_local_server(port=0)

                token_object = UserAuthToken(
                    token_name='google_auth',
                    token_data=token_encryption.encrypt(creds.to_json()),
                    user_id=int(user_id)
                )
                agent_validation.validate_add_object(token_manager, token_object, db)
        return creds


def send_gmail_message(client_email: str, email_subject: str, email_text: str, user_id: str) -> str:

    """Send email via Gmail API."""

    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    creds = auth_google(user_id, SCOPES)
    if isinstance(creds, str):
        return creds
    try:
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(email_text)
        message['to'] = client_email
        message['subject'] = email_subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {'raw': raw}
        message = service.users().messages().send(userId='me', body=message_body).execute()
        return f"Email sent successfully. Message ID: {message['id']}"
    except Exception as e:
        print(f"Gmail API error: {e}")
        return "Error: Failed to send email. Please check your Gmail permissions and try again."


def parse_agent_response(response: str) -> Dict[str, Any]:

    """Parse JSON response from agent output."""

    try:
        response_start = response.find('{')
        response_end = response.find('}')
        result = response[response_start:response_end + 1]
        result = json.loads(result)
        return result
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in agent response: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error parsing agent response: {e}")
        raise


email_fetcher_agent = LlmAgent(
    name='email_fetcher_agent',
    model=GEMINI_MODEL,
    instruction='''You are an email fetcher agent.

    You will receive information from user in JSON format with this structure:
    {
        user_request = Request of the user to write the email,
        user_full_name = Email sender full name,
        user_id = User's id
    }
    

    Your task is to:
    1. Parse the JSON data from the user.
    2. 'client_full_name' is a recipient's full name in the 'user_request'. 'birthdate' is a recipient's birthdate if it was provided. If not, 'birthdate' is an empy string. If birthday is provided, convert it in format YYYY-MM-DD.
    3. **MANDATORY**: Call the ['get_email_from_database'] function with the extracted 'client_full_name', 'user_id', and 'birthdate' to retrieve the client's email from the database.
    4. If the ['get_email_from_database'] function returns a valid email, include it in the response. If it returns an error, include it in the error message.
    5. Return the result ONLY in valid JSON string with this exact structure:
    {
        "client_email": "email from database or empty string if not found",
        "user_request": "Request of the user",
        "user_full_name": "Email sender full name in JSON data from user",
        "status": "success" if email was found, "error" if email was not found,
        "message": if email was found: "Email retrieved successfully", if not, write here error message from the function ['get_email_from_database'] 
    }
    6. If status of your result is 'success', invoke the 'email_writer_agent'. If status of your result is 'error' just return the result in JSON format.
    **IMPORTANT**:
    - You MUST call the ['get_email_from_database'] function in EVERY case.
    - Do NOT invent or guess email addresses. Use ONLY the email returned by ['get_email_from_database'] function.
    ''',
    description='''Gets client email from database using get_email_from_database function''',
    output_key='email_fetcher_agent_response',
    tools=[get_email_from_database]
)


email_writer_agent = LlmAgent(
    name='email_writer_agent',
    model=GEMINI_MODEL,
    instruction='''You are a professional email writer.
    
    Your task is to:
    1. Parse the JSON data from the state key 'email_fetcher_agent_response'.
    2. If error status in JSON data, immediately return error message in JSON format. If success status in JSON data, continue.
    3. Extract 'user_request' and 'user_full_name' from the JSON.
    4. Based *only* on the user's request write professional email. Email must be well structured. Use name of the recipient from user's request. 'user_full_name' is Email sender full name. Paste in text *only* that information that you posses. Don't use variables in brackets in text.
    5. Return the result ONLY in valid JSON string with this exact structure:
    {
        "email_text": "Created text of email here",
        "email_subject": "Created subject of email here",
        "status": "success" if you parsed the data and wrote the email, "error" if not,
        "message": if you parsed the data and wrote the email: "Email was written successfully", if not, write here what went wrong 
        
    }
    6. If status of your result is 'success', invoke the 'email_sender_agent'. If status of your result is 'error' just return the result in JSON format.
    ''',
    description='''Writes professional email''',
    output_key='email_writer_agent_response'
)


email_sender_agent = LlmAgent(
    name='email_sender_agent',
    model=GEMINI_MODEL,
    instruction='''You are an email sender agent.

    Your task is to:
    1. Parse the JSON data from the state key 'email_fetcher_agent_response' and state key 'email_writer_agent_response'
    2. If error status in JSON data, immediately return error message in JSON format. If success status in JSON data, continue.
    3. Extract 'client_email', 'email_text', 'email_subject' from JSON
    4. Use the 'send_gmail_message' tool to send the email
    
    IMPORTANT: Your response must be in JSON format with this exact structure:
    {
        "status": "success" if email was sent to the valid address or "error" if email was not sent,
        "message": "Details about the sending result"
    }
    
    **MANDATORY**: Always use 'send_gmail_message' tool.


    Call the tool 'send_gmail_message' ONLY with the extracted parameters from JSON.
    If 'client_email' is an empty string always return the error message.

    ''',
    description="Sends emails using 'send_gmail_message' tool",
    tools=[send_gmail_message],
    output_key='email_sender_agent_response'
)


root_agent = SequentialAgent(
    name='root_agent',
    sub_agents=[email_fetcher_agent, email_writer_agent, email_sender_agent]
)


async def run_agent(input_message: str, user_id: str) -> Dict[str, Any]:

    """Run the email agent pipeline with user input."""

    try:
        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name='email_app', user_id=user_id)
        runner = Runner(
            agent=root_agent,
            session_service=session_service,
            app_name='email_app'
        )
        content = types.Content(
            role="user",
            parts=[types.Part(text=input_message)]
        )
        event_stream = runner.run_async(user_id=user_id, session_id=session.id, new_message=content)
        final_response = None
        async for event in event_stream:
            if event.is_final_response():
                final_response = event
        if not final_response:
            return {"status": "error", "message": "No response from agent pipeline"}
        response = final_response.content.parts[0].text
        result = parse_agent_response(response)
        return result
    except Exception as e:
        print(f"Agent execution error: {e}")
        return {"status": "error", "message": "Agent execution failed. Please try again."}
