# Legal Docs API 📄 ⚖️ 

[![Python](https://img.shields.io/badge/Python-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-green.svg)](https://fastapi.tiangolo.com)
[![Deploy](https://img.shields.io/badge/Render-purple.svg)](https://render.com)

> 🚀 **Fast, opinionated RESTful service + MCP Server for secure storage, generation and lifecycle management of legal documents**

Built with modern Python stack featuring FastAPI, Pydantic v2, SQLAlchemy 2.0, and ships with batteries-included developer experience: typed models, auto-generated OpenAPI docs, JWT authentication, Google Document AI for automatic data extraction, and multi-agent AI system powered by LangGraph for intelligent workflow automation and real-time conversational AI.

---

## ✨ Highlights

🔐 **JWT Authentication** — Secure user management with role-based access control
📄 **Document CRUD** — Complete REST API for legal document operations
⬆️ **File Upload System** — DOCX template processing with validation
📝 **Smart Generation** — Dynamic document creation from Jinja2/Docx templates
🤖 **AI-Powered OCR** — Google Document AI for automatic passport data extraction
🤖 **Multi-Agent AI System** — LangGraph supervisor architecture with stateful conversations
💬 **Real-Time AI Chat** — WebSocket-based conversational AI for legal workflow automation
🔌 **MCP Server** — Model Context Protocol integration for AI assistant access
☁️ **AWS Storage** — Secure document template storage and management
✅ **Type Safety** — Pydantic v2 schemas validate all requests & responses
📚 **Interactive Docs** — Auto-generated Swagger UI & ReDoc documentation
💾 **Robust Persistence** — SQLAlchemy 2.0 with PostgreSQL checkpointing 
 

[🔗 **Live Demo and API Documentation**](https://legal-docs-api.onrender.com/docs)

---

## 🛠️ Tech Stack

| Category | Technologies                         |
|----------|--------------------------------------|
| **Backend** | Python, FastAPI                      |
| **Data & ORM** | SQLAlchemy 2.0, PostgreSQL           |
| **Authentication** | PyJWT, OAuth2                        |
| **Validation** | Pydantic v2                          |
| **Document Processing** | python-docx-template, Jinja2         |
| **AI/ML** | Google Document AI, Gemini 2.5 Flash |
| **Multi-Agent System** | LangGraph, LangChain, LangMem        |
| **Cloud Storage** | AWS S3                               |
| **Integrations** | Gmail API, Google Calendar API, MCP Server |
| **Real-Time Communication** | WebSocket                            |
| **Deployment** | Render                               |

---

## 🤖 Multi-Agent AI System

### Intelligent Supervisor-Based Architecture

The API features a sophisticated **multi-agent AI system** built with **LangGraph** and **Gemini 2.5 Flash** that provides conversational AI for legal workflow automation.

#### 🎯 Key Features

- **Supervisor Architecture**: Intelligent coordinator that routes tasks to specialized sub-agents
- **Real-Time Streaming**: WebSocket-based communication for instant responses
- **Stateful Conversations**: PostgreSQL-backed checkpointing for persistent conversation history
- **Memory Management**: Automatic conversation summarization using LangMem
- **Human-in-the-loop**: Request user input mid-conversation when needed
- **Natural Language Understanding**: Convert user requests into actionable tasks

#### 🔧 System Architecture

The system uses a **Supervisor Multi-Agent** pattern with specialized sub-agents:

```
User Message → Supervisor Agent → [Email Agent | Calendar Agent | Legal Docs Agent] → Response
                    ↓
              State Checkpointing (PostgreSQL)
                    ↓
            Conversation Summarization (LangMem)
```

| Component | Responsibility |
|-----------|----------------|
| **Supervisor Agent** | Orchestrates workflow, routes tasks to appropriate sub-agents, manages conversation flow |
| **Email Agent** | Handles email composition and sending via Gmail API |
| **Calendar Agent** | Manages calendar events and scheduling via Google Calendar API |
| **Legal Docs Agent** | Manages document generation, client data, and template operations |
| **Checkpointer** | Persists conversation state and enables resume/interrupt functionality |
| **Summarization Node** | Compresses conversation history to maintain context efficiency |

#### 🔌 MCP Server Integration

The API exposes select endpoints as a **Model Context Protocol (MCP)** server, enabling seamless integration with AI assistants:

**Exposed Endpoints:**
- Users (creation, retrieval, updates)
- Clients (CRUD operations)
- Addresses (client address management)
- Templates (document template operations)

**Authentication:** JWT-based with automatic token validation

This allows AI assistants to directly interact with your legal database while maintaining security.

#### 🛡️ Security & Error Handling

- **Encrypted Token Storage**: All OAuth tokens encrypted using Fernet symmetric encryption
- **State Persistence**: Secure conversation checkpointing in PostgreSQL
- **Comprehensive Validation**: Input validation with Pydantic schemas
- **Error Recovery**: Graceful handling of authentication, database, and API errors
- **Thread Isolation**: Each conversation thread is isolated per user

#### 🔐 Authentication Flow

1. **JWT Authentication**: Obtain token via `/auth/jwt/token` endpoint
2. **Google OAuth** (optional): Authenticate via `/auth/google/initiate` for Gmail/Calendar features
3. **WebSocket Connection**: Connect with JWT token for real-time AI chat
4. **Persistent Sessions**: Conversations persist across reconnections using thread IDs

---

## 🤖 AI-Powered Passport Recognition

### Automated Data Extraction
The API integrates **Google Document AI** for intelligent passport data extraction, eliminating manual data entry and reducing errors.

#### Supported Documents
- 🇺🇦 **Ukrainian Internal Passports**
- 🌍 **Ukrainian International Passports**

#### Extracted Fields
- **Full Name** (Surname, First Name, Patronymic)
- **Date of Birth** (automatically formatted)

#### How It Works

1. **Upload passport image** via `/client/upload_photo_id` endpoint
2. **Google Document AI** processes the image using custom-trained model
3. **Structured data** is returned in JSON format

#### Model Accuracy

- **Accuracy Rate**: 95%+ for clear, well-lit images
- **Supported Formats**: JPG, PNG (first page)

---

## 📄 Document Template System

### Supported Format
Only `.docx` files following our placeholder syntax are supported. Templates are validated before storage.

### Template Syntax

| Syntax | Description |
|--------|-------------|
| `${VARIABLE}` | Simple scalar field (e.g., `${DATE}`) replaced at render time |
| `${PARTY1_START} ... ${PARTY1_END}` | Block repeated for each attribute of the first party |
| `${PARTY2_START} ... ${PARTY2_END}` | Block repeated for each attribute of the second party |
| **Inside blocks** | Use nested placeholders: `${NAME}`, `${ADDRESS}`, `${BIRTH}` |

### Example Template

```
POWER OF ATTORNEY
Dated: ${DATE}

KNOW ALL MEN BY THESE PRESENTS
that I, ${PARTY1_START}${NAME}, residing at ${ADDRESS}, born on ${BIRTH}${PARTY1_END}
(hereinafter referred to as the "Principal"), do hereby appoint
${PARTY2_START}${NAME}, residing at ${ADDRESS}, born on ${BIRTH}${PARTY2_END}
(hereinafter referred to as the "Agent"), to be my true and lawful Attorney-in-Fact...
```

📁 **Sample template**: Check `templates/PA.docx` for a complete example.

---

## 🙏 Acknowledgments

- [FastAPI team](https://fastapi.tiangolo.com/) for the awesome framework
- [LangGraph](https://github.com/langchain-ai/langgraph) for the powerful multi-agent framework
- [Google Gemini](https://deepmind.google/technologies/gemini/) for the powerful AI models
- [Render](https://render.com) for the generous free tier
- Inspired by the community examples in [awesome-readme](https://github.com/matiassingers/awesome-readme)

---

> Made with ❤️ and a lot of ☕️ by **Daniil Kharaman**