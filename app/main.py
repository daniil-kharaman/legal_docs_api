from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from storage import database
from app import routers
from storage.database import DatabaseError

database.create_tables()

app = FastAPI(
    title='Legal Docs API',
    description="""
    Comprehensive API for legal document generation, client management, and AI-powered automation.

    This API provides legal professionals with:
    * **User Management**: Complete account creation, auth, and profile management
    * **Client Operations**: Full CRUD operations for client records with address management
    * **Document Templates**: Upload, manage, and generate documents from Word templates stored in AWS S3
    * **AI-Powered Tools**: 
      - Document AI for extracting client data from ID photos
      - Intelligent email composition and automated delivery via Gmail
    * **OAuth Integration**: Google OAuth for Gmail API access and automated communications

    ## Authentication

    The API supports multiple auth methods:
    1. **JWT Authentication**: Create account via `/user/add`, obtain token via `auth/jwt/token`
    2. **Google OAuth**: Authenticate via `/auth/google/initiate` for Gmail integration
    3. Include Bearer token in Authorization header for all protected endpoints

    ## Key Features

    * **Multi-Agent AI System**: Uses Google ADK and Gemini 2.5 Flash for intelligent automation
    * **Document Processing**: Google Document AI integration for OCR and data extraction
    * **Email Automation**: AI-powered email composition with Gmail API delivery
    * **Secure Storage**: AWS S3 integration for template storage with user isolation
    * **Data Validation**: Comprehensive input validation and error handling
    """,
    version="1.2.0",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User auth endpoints for obtaining and using access tokens."
        },
        {
            "name": "Users",
            "description": "Operations related to user management, including creation, updates, and deletion."
        },
        {
            "name": "AI Tools",
            "description": "AI-powered tools for automating legal workflows"
        },
        {
            "name": "Clients",
            "description": "Client management endpoints for creating, retrieving, updating, and deleting client records."
        },
        {
            "name": "Addresses",
            "description": "Operations for managing client addresses including creation, retrieval, and updates."
        },
        {
            "name": "Templates",
            "description": "Document template operations including upload, management, and document generation."
        }
    ]
)

app.include_router(routers.auth.router)
app.include_router(routers.user.router)
app.include_router(routers.ai.router)
app.include_router(routers.client.router)
app.include_router(routers.address.router)
app.include_router(routers.template.router)


@app.exception_handler(Exception)
def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors"""
    print(f"Unexpected error: {exc}")
    return JSONResponse(status_code=500, content='Something went wrong. Try again later.')


@app.exception_handler(DatabaseError)
def db_error_handler(request: Request, exc: DatabaseError) -> None:
    """Convert DatabaseError to HTTP 500 exception."""
    raise HTTPException(status_code=500, detail=str(exc))
