"""
Shared service singletons for API dependency injection.
Initialised once and reused across requests.
"""
from functools import lru_cache

from retrieval.embedder import Embedder
from retrieval.vector_store import VectorStore
from feedback.preference_store import PreferenceStore
from config import CHROMA_PERSIST_DIR, SQLITE_DB_PATH


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Get the singleton Embedder instance."""
    return Embedder.get_instance()


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    """Get the singleton VectorStore instance."""
    return VectorStore(CHROMA_PERSIST_DIR)


@lru_cache(maxsize=1)
def get_preference_store() -> PreferenceStore:
    """Get the singleton PreferenceStore instance."""
    return PreferenceStore(SQLITE_DB_PATH)
