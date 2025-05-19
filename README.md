# Legal Docs API 📄⚖️



> **Legal Docs API** is a fast, opinionated RESTful service for **secure storage, generation and lifecycle management of legal documents**. It is built with [FastAPI](https://fastapi.tiangolo.com/) and ships with batteries‑included DX: typed Pydantic models, OpenAPI docs, JWT auth and one‑click deployment to Render.

---

## ✨ Features

|  |  Description                                                    |
|---|-----------------------------------------------------------------|
|🔐 **Authentication**| JSON Web Token (JWT) based user auth & role management          |
|📄 **Document CRUD**| Create, read, update & delete legal documents via REST endpoints |
|⬆️ **File Uploads**| Upload **DOCX template files**                  |
|📝 **Generation**| Generate documents from Jinja2/Docx‑templater templates on demand |
|✅ **Validation**| Pydantic schemas validate every request & response              |
|📚 **Interactive Docs**| Auto‑generated Swagger UI at `/docs` & Redoc at `/redoc`        |
|💾 **Persistence**| SQLAlchemy models + Alembic migrations (PostgreSQL by default)  |
|☁️ **Zero‑config Deployment**| `render.yaml` for instant deployment to [Render](https://render.com) |

---

## 📦 Tech Stack

- **Python 3.12**
- **FastAPI** + **Uvicorn** ASGI server
- **Pydantic v2** for data validation
- **SQLAlchemy 2** ORM
- **Alembic** migrations
- **PyJWT** / **fastapi‑users** for auth
- Optional: **Docker** & **Render** for hosting

*(Exact versions are pinned in `requirements.txt`)*


---

## 📐 DOCX Template Format

Only **.docx** files that follow the placeholder syntax below can be uploaded. The backend validates the template before saving it.

### Placeholder Rules

| Syntax | Description |
|--------|-------------|
|`${VARIABLE}`|Simple scalar field (e.g. `${DATE}`) replaced at render time.|
|`${PARTY1_START}` … `${PARTY1_END}`|Block that is repeated for each attribute of the first party (name, address …).|
|`${PARTY2_START}` … `${PARTY2_END}`|Same for the second party. Extend pattern for additional parties.|
|Inside a block|Use nested placeholders such as `${NAME}`, `${ADDRESS}`, `${BIRTH}`.|

*The placeholders follow **python‑docx‑template** / **Jinja2** `${...}` notation, so you may embed basic filters and conditionals if needed.*

### Minimal Example

```text
POWER OF ATTORNEY
Dated: ${DATE}

KNOW ALL MEN BY THESE PRESENTS

that I, ${PARTY1_START}${NAME}, residing at ${ADDRESS}, born on ${BIRTH}${PARTY1_END}
(hereinafter referred to as the "Principal"), do hereby appoint
${PARTY2_START}${NAME}, residing at ${ADDRESS}, born on ${BIRTH}${PARTY2_END}
(hereinafter referred to as the "Agent"), to be my true and lawful Attorney‑in‑Fact…
```

An illustrated sample lives under **`templates/PA.docx`**. Use it as a blueprint for your own contracts.

---

## 🙏 Acknowledgements

- [FastAPI  team](https://fastapi.tiangolo.com/) for the awesome framework
- [Render](https://render.com) for the generous free tier
- Inspired by the community examples in [awesome‑readme](https://github.com/matiassingers/awesome-readme)

---

> Made with ❤️ and a lot of ☕️ by **Daniil Kharaman**
