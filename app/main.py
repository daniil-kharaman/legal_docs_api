import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from starlette import status
from auth.oauth import OAuthError
from auth.user_login import get_current_active_user
from storage import database
from app import routers
from storage.database import DatabaseError
from fastapi_mcp import FastApiMCP, AuthConfig
from contextlib import asynccontextmanager
from multi_agent_system import get_checkpointer, close_checkpointer


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.create_tables()
    checkpointer = await get_checkpointer()
    logger.info(f"✓ Checkpointer initialized at startup")
    yield
    # Shutdown: cleanup
    await close_checkpointer()
    logger.info(f"✓ Checkpointer closed")


app = FastAPI(
    lifespan=lifespan,
    title='Legal Docs API',
    description="""
    Comprehensive API for legal document generation, client management, and AI-powered automation.

    This API provides legal professionals with:
    * **User Management**: Complete account creation, auth, and profile management
    * **Client Operations**: Full CRUD operations for client records with address management
    * **Document Templates**: Upload, manage, and generate documents from Word templates stored in AWS S3
    * **AI Chat**: Interactive conversational AI powered by multi-agent system for legal workflow automation
    * **AI-Powered Tools**:
      - Document AI for extracting client data from ID photos
      - Multi-agent system for intelligent task automation
    * **OAuth Integration**: Google OAuth for Gmail API and Google Calendar access
    * **MCP Server**: Exposed as Model Context Protocol server for AI assistant integration

    ## Authentication

    The API supports multiple auth methods:
    1. **JWT Authentication**: Create account via `/user/add`, obtain token via `auth/jwt/token`
    2. **Google OAuth**: Authenticate via `/auth/google/initiate` for Gmail and Google Calendar integration
    3. Include Bearer token in Authorization header for all protected endpoints

    ## Key Features

    * **Multi-Agent AI System**: Uses LangGraph with stateful conversation management and persistent checkpointing
    * **AI Models**: Powered by Gemini 2.5 Flash for intelligent task processing and automation
    * **Document Processing**: Google Document AI integration for OCR and data extraction
    * **MCP Server Integration**: Exposes Users, Clients, Addresses, and Templates endpoints via Model Context Protocol for seamless AI assistant access
    * **Secure Storage**: AWS S3 integration for template storage with user isolation
    * **Data Validation**: Comprehensive input validation and error handling
    """,
    version="2.0.0",
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
            "name": "AI Chat",
            "description": "Interactive AI chat with multi-agent system via WebSocket for real-time conversational automation"
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
app.include_router(routers.ai_chat_ws.router)


mcp = FastApiMCP(
    app,
    include_tags=["Users", "Clients", "Addresses", "Templates"],
    auth_config=AuthConfig(
        dependencies=[Depends(get_current_active_user)]
        )

)
mcp.mount_http()


@app.exception_handler(Exception)
def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={'detail': 'Something went wrong. Try again later.'})


@app.exception_handler(DatabaseError)
def db_error_handler(_request: Request, exc: DatabaseError) -> None:
    """Convert DatabaseError to HTTP 500 exception."""
    raise HTTPException(status_code=500, detail=str(exc))


@app.exception_handler(OAuthError)
def oauth_error_handler(_request: Request, exc: OAuthError) -> None:
    """Convert OAuthError to HTTP 401 exception."""
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
