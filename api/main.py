"""
FastAPI application initialisation for LexDraft.
Sets up CORS, lifespan events, and route registration.
"""
from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
os.makedirs("./logs", exist_ok=True)
logging.basicConfig(
    filename="./logs/lexdraft.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(console_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: validate config and pre-load models on startup."""
    from config import validate
    validate()

    # Pre-load embedding model on startup
    from retrieval.embedder import Embedder
    logging.getLogger(__name__).info("Pre-loading embedding model...")
    Embedder.get_instance()
    logging.getLogger(__name__).info("Embedding model ready")

    yield


app = FastAPI(
    title="LexDraft API",
    version="1.0.0",
    description="AI-Powered Legal Document Processing & Grounded Drafting System",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register routes
from api.routes import ingest, draft, feedback, status
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(draft.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(status.router, prefix="/api/v1")
