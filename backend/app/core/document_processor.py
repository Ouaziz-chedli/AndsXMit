"""Document processing module for PDF extraction, chunking, and embedding."""

import re
import uuid
from typing import List, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

DEFAULT_CHROMA_PATH = "/data/vector_db"
MEDICAL_DOCS_COLLECTION = "medical_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class DocumentProcessor:
    """Handles PDF text extraction, chunking, and ChromaDB indexing."""

    def __init__(
        self,
        chroma_path: str = DEFAULT_CHROMA_PATH,
        embed_model: str = EMBED_MODEL,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.embed_model = SentenceTransformer(embed_model)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            ValueError: If PDF cannot be read
        """
        try:
            reader = PdfReader(pdf_path)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    def extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes.

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            Extracted text content

        Raises:
            ValueError: If PDF cannot be read
        """
        import io
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks at sentence boundaries.

        Args:
            text: Raw text to chunk

        Returns:
            List of text chunks
        """
        text = text.strip()
        if not text:
            return []

        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                current_chunk += (" " if current_chunk else "") + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + " " + sentence if current_chunk else sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return [c for c in chunks if len(c) > 10]

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using punctuation markers."""
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        return sentence_endings.split(text)

    def process_and_index(
        self,
        pdf_bytes: bytes,
        filename: str,
        collection_name: str = MEDICAL_DOCS_COLLECTION,
    ) -> Tuple[str, int]:
        """Process a PDF and index its chunks into ChromaDB.

        Args:
            pdf_bytes: PDF content as bytes
            filename: Original filename for metadata
            collection_name: ChromaDB collection name

        Returns:
            Tuple of (document_id, chunk_count)
        """
        text = self.extract_text_from_bytes(pdf_bytes)

        if not text.strip():
            doc_id = str(uuid.uuid4())
            return doc_id, 0

        chunks = self.chunk_text(text)

        if not chunks:
            doc_id = str(uuid.uuid4())
            return doc_id, 0

        doc_id = str(uuid.uuid4())
        chunk_ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        embeddings = self.embed_model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)

        collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]

        collection.upsert(
            documents=chunks,
            ids=chunk_ids,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )

        return doc_id, len(chunks)

    def search_documents(
        self,
        query: str,
        collection_name: str = MEDICAL_DOCS_COLLECTION,
        top_k: int = 5,
    ) -> List[dict]:
        """Search indexed documents by similarity.

        Args:
            query: Search query text
            collection_name: ChromaDB collection name
            top_k: Number of results to return

        Returns:
            List of search results with scores
        """
        collection = self.chroma_client.get_or_create_collection(name=collection_name)

        query_embedding = self.embed_model.encode([query], show_progress_bar=False, convert_to_numpy=True)

        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k,
        )

        search_results = []
        if results and results["ids"]:
            for i, case_id in enumerate(results["ids"][0]):
                search_results.append({
                    "id": case_id,
                    "content": results["documents"][0][i],
                    "score": 1.0 - results["distances"][0][i],
                    "metadata": results["metadatas"][0][i],
                })

        return search_results


_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """Get or create the global document processor instance."""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor


def reset_document_processor() -> None:
    """Reset the global document processor instance."""
    global _processor
    _processor = None