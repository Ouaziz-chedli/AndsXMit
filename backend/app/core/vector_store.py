"""
Vector Store Module - ChromaDB abstraction for similarity search.

Provides a clean interface to ChromaDB for storing and retrieving
disease case embeddings.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


# Default path for ChromaDB persistent storage
DEFAULT_CHROMA_PATH = "/data/vector_db"


@dataclass
class RetrievedCase:
    """A case retrieved from vector similarity search."""
    case_id: str
    similarity: float
    is_positive: bool
    disease_id: str
    trimester: str
    symptom_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StoredCase:
    """A case to be stored in the vector database."""
    case_id: str
    disease_id: str
    trimester: str
    is_positive: bool
    embedding: List[float]
    symptom_text: str
    gestational_age_weeks: Optional[float] = None
    b_hcg_mom: Optional[float] = None
    papp_a_mom: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class VectorStore:
    """ChromaDB wrapper for disease case storage and retrieval."""

    def __init__(self, persist_directory: str = DEFAULT_CHROMA_PATH):
        """
        Initialize the vector store with persistent storage.

        Args:
            persist_directory: Path to store ChromaDB data
        """
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

    def _get_collection_name(self, disease_id: str, trimester: str) -> str:
        """
        Generate a standardized collection name.

        Args:
            disease_id: Disease identifier
            trimester: "1st", "2nd", or "3rd"

        Returns:
            Collection name string
        """
        return f"{disease_id}_{trimester}"

    def get_or_create_collection(
        self,
        disease_id: str,
        trimester: str
    ):
        """
        Get or create a collection for a specific disease and trimester.

        Args:
            disease_id: Disease identifier
            trimester: "1st", "2nd", or "3rd"

        Returns:
            ChromaDB collection object
        """
        collection_name = self._get_collection_name(disease_id, trimester)

        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )

        return collection

    def add_case(self, case: StoredCase) -> None:
        """
        Add a single case to the vector store.

        Args:
            case: StoredCase object with embedding and metadata
        """
        collection = self.get_or_create_collection(
            disease_id=case.disease_id,
            trimester=case.trimester
        )

        # Build metadata dictionary
        metadata = {
            "case_id": case.case_id,
            "disease_id": case.disease_id,
            "trimester": case.trimester,
            "is_positive": case.is_positive,
        }
        if case.gestational_age_weeks is not None:
            metadata["gestational_age_weeks"] = case.gestational_age_weeks

        if case.b_hcg_mom is not None:
            metadata["b_hcg_mom"] = case.b_hcg_mom
        if case.papp_a_mom is not None:
            metadata["papp_a_mom"] = case.papp_a_mom

        if case.metadata:
            metadata.update(case.metadata)

        collection.add(
            ids=[case.case_id],
            embeddings=[case.embedding],
            documents=[case.symptom_text],
            metadatas=[metadata]
        )

    def add_cases(self, cases: List[StoredCase]) -> None:
        """
        Add multiple cases to the vector store (batch operation).

        Args:
            cases: List of StoredCase objects
        """
        # Group by collection to batch inserts
        from collections import defaultdict
        grouped: dict = defaultdict(list)
        for case in cases:
            grouped[(case.disease_id, case.trimester)].append(case)

        for (disease_id, trimester), group in grouped.items():
            collection = self.get_or_create_collection(disease_id, trimester)
            ids, embeddings, documents, metadatas = [], [], [], []
            for case in group:
                meta = {
                    "case_id": case.case_id,
                    "disease_id": case.disease_id,
                    "trimester": case.trimester,
                    "is_positive": case.is_positive,
                    "gestational_age_weeks": case.gestational_age_weeks,
                }
                if case.b_hcg_mom is not None:
                    meta["b_hcg_mom"] = case.b_hcg_mom
                if case.papp_a_mom is not None:
                    meta["papp_a_mom"] = case.papp_a_mom
                if case.metadata:
                    meta.update(case.metadata)
                ids.append(case.case_id)
                embeddings.append(case.embedding)
                documents.append(case.symptom_text)
                metadatas.append(meta)
            collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def search_disease(
        self,
        query_embedding: List[float],
        disease_id: str,
        trimester: str,
        top_k: int = 10,
        filter_positive: Optional[bool] = None,
    ) -> List[RetrievedCase]:
        """
        Search for similar cases in the vector store.

        Args:
            query_embedding: Query embedding vector
            disease_id: Disease identifier
            trimester: "1st", "2nd", or "3rd"
            top_k: Number of results to return
            filter_positive: If set, only return positive (True) or negative (False) cases

        Returns:
            List of RetrievedCase objects, sorted by similarity

        Raises:
            ValueError: If collection doesn't exist or has no data
        """
        collection = self.get_or_create_collection(
            disease_id=disease_id,
            trimester=trimester
        )

        # Build where filter if specified
        where_filter = None
        if filter_positive is not None:
            where_filter = {"is_positive": filter_positive}

        # Guard: ChromaDB raises if n_results > collection size
        count = collection.count()
        if count == 0:
            return []
        actual_k = min(top_k, count)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            where=where_filter,
        )

        if not results or not results["ids"][0]:
            return []

        retrieved_cases = []
        for i, case_id in enumerate(results["ids"][0]):
            retrieved_cases.append(
                RetrievedCase(
                    case_id=case_id,
                    similarity=1.0 - results["distances"][0][i],  # Convert distance to similarity
                    is_positive=results["metadatas"][0][i]["is_positive"],
                    disease_id=results["metadatas"][0][i]["disease_id"],
                    trimester=results["metadatas"][0][i]["trimester"],
                    symptom_text=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                )
            )

        return retrieved_cases

    def get_case_count(
        self,
        disease_id: str,
        trimester: str,
    ) -> int:
        """
        Get the total number of cases for a disease and trimester.

        Args:
            disease_id: Disease identifier
            trimester: "1st", "2nd", or "3rd"

        Returns:
            Number of cases in the collection
        """
        try:
            collection = self.client.get_collection(
                name=self._get_collection_name(disease_id, trimester)
            )
            return collection.count()
        except Exception:
            return 0

    def list_collections(self) -> List[str]:
        """
        List all available collection names.

        Returns:
            List of collection name strings
        """
        return [col.name for col in self.client.list_collections()]

    def delete_collection(self, disease_id: str, trimester: str) -> None:
        """
        Delete a collection.

        Args:
            disease_id: Disease identifier
            trimester: "1st", "2nd", or "3rd"
        """
        collection_name = self._get_collection_name(disease_id, trimester)
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            # Collection might not exist
            pass


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(persist_directory: str = DEFAULT_CHROMA_PATH) -> VectorStore:
    """
    Get or create the global vector store instance.

    Args:
        persist_directory: Path to store ChromaDB data

    Returns:
        VectorStore instance
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(persist_directory=persist_directory)
    return _vector_store


def reset_vector_store() -> None:
    """Reset the global vector store instance."""
    global _vector_store
    _vector_store = None
