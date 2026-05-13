"""
Central configuration module for LexDraft.
All environment variables are loaded here. No other module should use os.getenv() directly.
Uses OpenRouter API for LLM access (OpenAI-compatible endpoint).
"""
from dotenv import load_dotenv
import os

load_dotenv()

# OpenRouter API (OpenAI-compatible)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Persistence
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/lexdraft.db")

# OCR
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")

# Embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# LLM
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# Retrieval
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "8"))

# OCR confidence threshold
MIN_OCR_CONFIDENCE = float(os.getenv("MIN_OCR_CONFIDENCE", "60.0"))


def validate():
    """Validate that all required environment variables are set."""
    if not OPENROUTER_API_KEY:
        raise EnvironmentError(
            "OPENROUTER_API_KEY is not set in .env. "
            "Get one at https://openrouter.ai/keys"
        )
