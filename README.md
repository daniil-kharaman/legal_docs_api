# Legal Docs API 📄 ⚖️ 

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![Deploy](https://img.shields.io/badge/deploy-Render-purple.svg)](https://render.com)

> 🚀 **Fast, opinionated RESTful service for secure storage, generation and lifecycle management of legal documents**

Built with modern Python stack featuring FastAPI, Pydantic v2, SQLAlchemy 2.0, and ships with batteries-included developer experience: typed models, auto-generated OpenAPI docs, JWT authentication, Google Document AI for automatic data extraction, and multi-agent AI system powered by Google Agent Development Kit for intelligent email automation.

---

## ✨ Highlights

🔐 **JWT Authentication** — Secure user management with role-based access control  
📄 **Document CRUD** — Complete REST API for legal document operations  
⬆️ **File Upload System** — DOCX template processing with validation  
📝 **Smart Generation** — Dynamic document creation from Jinja2/Docx templates  
🤖 **AI-Powered OCR** — Google Document AI for automatic passport data extraction  
🤖 **AI Email Agents** — Google Agent Development Kit framework for intelligent email automation  
☁️ **AWS Storage** — Secure document template storage and management  
✅ **Type Safety** — Pydantic v2 schemas validate all requests & responses  
📚 **Interactive Docs** — Auto-generated Swagger UI & ReDoc documentation  
💾 **Robust Persistence** — SQLAlchemy 2.0 
 

[🔗 **Live Demo and API Documentation**](https://legal-docs-api.onrender.com/docs)

---

## 🛠️ Tech Stack

| Category | Technologies                 |
|----------|------------------------------|
| **Backend** | Python 3.12, FastAPI         |
| **Data & ORM** | SQLAlchemy 2.0, PostgreSQL   |
| **Authentication** | PyJWT                        |
| **Validation** | Pydantic v2                  |
| **Document Processing** | python-docx-template, Jinja2 |
| **AI/ML** | Google Document AI, Google Agent Development Kit |
| **Cloud Storage** | AWS S3                       |
| **Email Automation** | Gmail API, AI Agents         |
| **Deployment** | Render                       |

---

## 🤖 AI-Powered Email Automation

### Intelligent Multi-Agent Email System

The API features a sophisticated **multi-agent AI system** built with **Google Agent Development Kit (ADK)** and **Gemini 2.5 Flash** that automates the entire email workflow for legal communications.

#### 🎯 Key Features

- **Natural Language Processing**: Convert user requests into professional legal emails
- **Client Database Integration**: Automatically retrieve client email addresses from your database
- **Smart Recipient Resolution**: Handle multiple clients with same name using birthdate disambiguation
- **Secure Authentication**: OAuth2 integration with Gmail API and encrypted token storage
- **Professional Email Generation**: AI-crafted emails with appropriate legal tone and structure

#### 🔧 System Architecture

The email automation uses a **Sequential Agent** pipeline with specialized sub-agents:

```
User Request → Email Fetcher Agent → Email Writer Agent → Email Sender Agent → Sent Email
```

| Agent | Responsibility |
|-------|----------------|
| **Email Fetcher Agent** | Parses user request, extracts recipient info, queries database for email |
| **Email Writer Agent** | Generates professional email content and subject line |
| **Email Sender Agent** | Sends email via Gmail API with error handling |

#### 📝 Usage Examples

**Simple Request:**
```json
{
    "user_request": "Send email to John Doe about the power of attorney document being ready"
}
```

**With Birthdate Disambiguation:**
```json
{
    "user_request": "Send contract reminder to Maria Rodriguez born on 1985-03-15"
}
```

#### 🛡️ Security & Error Handling

- **Encrypted Token Storage**: All OAuth tokens encrypted using Fernet symmetric encryption
- **Comprehensive Validation**: Input validation with Pydantic schemas
- **Error Recovery**: Graceful handling of authentication, database, and API errors

#### 🔐 Authentication Flow

1. **Initial Authorization**: User must first authenticate via `/auth/google/initiate` endpoint
2. **Token Storage**: Encrypted credentials automatically saved to database after authorization
3. **Auto-Refresh**: Automatic token renewal for seamless operation
4. **Secure Access**: All subsequent emails sent without user intervention

#### 📊 Response Format

The system returns structured JSON responses for all operations:

```json
{
    "status": "success",
    "message": "Email sent successfully. Message ID: 18c5f2a3b4d7e8f9"
}
```

Error responses include detailed information for troubleshooting:

```json
{
    "status": "error",
    "message": "Error: There are several persons with name John Smith. Specify the birthdate."
}
```

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
- [Google Agent Development Kit](https://ai.google.dev/adk) for the powerful AI agent framework
- [Render](https://render.com) for the generous free tier
- Inspired by the community examples in [awesome-readme](https://github.com/matiassingers/awesome-readme)

---

> Made with ❤️ and a lot of ☕️ by **Daniil Kharaman**