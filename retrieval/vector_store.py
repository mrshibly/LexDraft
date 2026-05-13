"""
ChromaDB-backed vector store with per-document collections and a global collection.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

GLOBAL_COLLECTION = "global_all_docs"


class VectorStore:
    """Manages ChromaDB persistent storage for document embeddings.
    
    Maintains both per-document collections and a global collection
    spanning all documents for cross-doc queries.
    """

    def __init__(self, persist_dir: str):
        """Initialise the vector store with a persistent ChromaDB client."""
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"ChromaDB initialised at {persist_dir}")

    def _doc_collection_name(self, doc_id: str) -> str:
        """Generate collection name for a specific document."""
        return f"doc_{doc_id}"

    def _get_or_create_collection(self, name: str):
        """Get an existing collection or create a new one."""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_document(
        self,
        doc_id: str,
        chunks: list[str],
        embeddings: list[np.ndarray],
        metadatas: list[dict]
    ) -> int:
        """Add document chunks to both per-doc and global collections.
        
        Args:
            doc_id: Unique document identifier.
            chunks: List of text chunks.
            embeddings: List of embedding vectors.
            metadatas: List of metadata dicts.
        
        Returns:
            Number of chunks added.
        """
        if not chunks:
            logger.warning(f"No chunks to add for document {doc_id}")
            return 0

        # Convert embeddings to list[list[float]]
        emb_lists = [emb.tolist() for emb in embeddings]
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]

        # Add to per-document collection
        doc_collection = self._get_or_create_collection(self._doc_collection_name(doc_id))
        doc_collection.add(
            ids=ids,
            documents=chunks,
            embeddings=emb_lists,
            metadatas=metadatas
        )
        logger.info(f"Added {len(chunks)} chunks to per-doc collection for {doc_id}")

        # Add to global collection
        global_collection = self._get_or_create_collection(GLOBAL_COLLECTION)
        global_collection.add(
            ids=ids,
            documents=chunks,
            embeddings=emb_lists,
            metadatas=metadatas
        )
        logger.info(f"Added {len(chunks)} chunks to global collection")

        return len(chunks)

    def query(
        self,
        doc_id: str,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> list[dict]:
        """Query a per-document collection for similar chunks.
        
        Returns list of {text, score, metadata} dicts.
        """
        collection_name = self._doc_collection_name(doc_id)
        try:
            collection = self.client.get_collection(collection_name)
        except Exception:
            logger.warning(f"Collection {collection_name} not found")
            return []

        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=min(top_k, collection.count()),
            include=["documents", "distances", "metadatas"]
        )

        output = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                # ChromaDB returns distances; convert to similarity
                distance = results["distances"][0][i]
                score = 1 - distance
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                output.append({
                    "text": doc,
                    "score": round(score, 4),
                    "metadata": metadata
                })

        return output

    def query_global(
        self,
        query_embedding: np.ndarray,
        top_k: int = 8
    ) -> list[dict]:
        """Query the global collection spanning all documents."""
        try:
            collection = self.client.get_collection(GLOBAL_COLLECTION)
        except Exception:
            logger.warning("Global collection not found")
            return []

        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=min(top_k, count),
            include=["documents", "distances", "metadatas"]
        )

        output = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i]
                score = 1 - distance
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                output.append({
                    "text": doc,
                    "score": round(score, 4),
                    "metadata": metadata
                })

        return output

    def delete_document(self, doc_id: str) -> None:
        """Delete a document's per-doc collection and remove from global."""
        collection_name = self._doc_collection_name(doc_id)

        # Delete per-doc collection
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted per-doc collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Could not delete collection {collection_name}: {e}")

        # Remove entries from global collection
        try:
            global_col = self.client.get_collection(GLOBAL_COLLECTION)
            # Get all IDs for this doc
            all_results = global_col.get(
                where={"doc_id": doc_id},
                include=[]
            )
            if all_results and all_results["ids"]:
                global_col.delete(ids=all_results["ids"])
                logger.info(f"Removed {len(all_results['ids'])} entries from global collection")
        except Exception as e:
            logger.warning(f"Could not clean global collection for {doc_id}: {e}")

    def list_documents(self) -> list[str]:
        """List all indexed document IDs."""
        collections = self.client.list_collections()
        doc_ids = []
        for col in collections:
            name = col.name if hasattr(col, 'name') else str(col)
            if name.startswith("doc_"):
                doc_ids.append(name[4:])  # Strip 'doc_' prefix
        return doc_ids

    def document_exists(self, doc_id: str) -> bool:
        """Check if a document has been indexed."""
        return doc_id in self.list_documents()
