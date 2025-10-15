import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.getenv('LLM_MODEL', 'google_genai:gemini-2.5-flash')

PROMPTS_DIR = Path(__file__).parent / "prompts"

DB_URI = os.getenv('DATABASE_URL')
if not DB_URI:
    raise ValueError("DATABASE_URL environment variable is required")
