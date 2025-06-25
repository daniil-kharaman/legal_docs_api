# Legal Docs API 📄 ⚖️ 

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Deploy](https://img.shields.io/badge/deploy-Render-purple.svg)](https://render.com)

> 🚀 **Fast, opinionated RESTful service for secure storage, generation and lifecycle management of legal documents**

Built with modern Python stack featuring FastAPI, Pydantic v2, SQLAlchemy 2.0, and ships with batteries-included developer experience: typed models, auto-generated OpenAPI docs, JWT authentication, and Google Document AI for automatic data extraction.

---

## ✨ Highlights

🔐 **JWT Authentication** — Secure user management with role-based access control  
📄 **Document CRUD** — Complete REST API for legal document operations  
⬆️ **File Upload System** — DOCX template processing with validation  
📝 **Smart Generation** — Dynamic document creation from Jinja2/Docx templates  
🤖 **AI-Powered OCR** — Google Document AI for automatic passport data extraction  
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
| **AI/ML** | Google Document AI           |
| **Deployment** | Render                       |


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
- [Render](https://render.com) for the generous free tier
- Inspired by the community examples in [awesome-readme](https://github.com/matiassingers/awesome-readme)

---

> Made with ❤️ and a lot of ☕️ by **Daniil Kharaman**