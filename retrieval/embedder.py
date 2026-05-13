"""
Encodes text chunks into dense vector embeddings using sentence-transformers.
Singleton model instance to avoid reloading on every call.
"""
from __future__ import annotations

import logging
import time

import numpy as np

logger = logging.getLogger(__name__)


class Embedder:
    """Singleton sentence-transformers embedding encoder.
    
    Loads the model once and keeps it in memory for the process lifetime.
    Normalises all output embeddings to unit length.
    """
    _instance = None
    _model = None

    @classmethod
    def get_instance(cls) -> Embedder:
        """Get or create the singleton Embedder instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._load_model()
        return cls._instance

    @classmethod
    def _load_model(cls):
        """Load the sentence-transformers model."""
        from sentence_transformers import SentenceTransformer
        from config import EMBEDDING_MODEL

        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}...")
        start = time.time()
        cls._model = SentenceTransformer(EMBEDDING_MODEL)
        elapsed = time.time() - start
        logger.info(f"Embedding model loaded in {elapsed:.2f}s")

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Encode a list of texts into normalised embeddings.
        
        Args:
            texts: List of text strings to encode.
            batch_size: Number of texts per batch.
        
        Returns:
            np.ndarray of shape (len(texts), 384) with unit-length embeddings.
        """
        from tqdm import tqdm

        if not texts:
            return np.array([])

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embs = self._model.encode(
                batch,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            all_embeddings.append(embs)

        embeddings = np.vstack(all_embeddings)

        # Normalise to unit length
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        embeddings = embeddings / norms

        return embeddings

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text string into a normalised embedding vector."""
        return self.encode([text])[0]
