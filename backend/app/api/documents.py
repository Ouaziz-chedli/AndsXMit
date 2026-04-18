"""Document upload API endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.documents import UploadResponse, UploadError
from app.core.document_processor import get_document_processor

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

ALLOWED_CONTENT_TYPE = "application/pdf"


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document for vector indexing.

    Accepts PDF files, extracts text, chunks it, and stores
    embeddings in ChromaDB for similarity search.

    Args:
        file: PDF file upload

    Returns:
        UploadResponse with document_id and chunk count

    Raises:
        HTTPException: 422 if file is not a PDF
    """
    if file.content_type != ALLOWED_CONTENT_TYPE:
        raise HTTPException(
            status_code=422,
            detail="File must be a PDF",
        )

    try:
        contents = await file.read()
        file_size = len(contents)

        if file_size == 0:
            raise HTTPException(
                status_code=422,
                detail="Empty file",
            )

        processor = get_document_processor()
        document_id, chunk_count = processor.process_and_index(
            pdf_bytes=contents,
            filename=file.filename or "unknown.pdf",
        )

        return UploadResponse(
            document_id=document_id,
            chunks_indexed=chunk_count,
            status="success",
            filename=file.filename or "unknown.pdf",
            message=None if chunk_count > 0 else "No text content extracted from PDF",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid PDF format: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}",
        )


@router.get("/search")
async def search_documents(query: str, top_k: int = 5):
    """Search indexed documents by similarity.

    Args:
        query: Search query text
        top_k: Number of results to return

    Returns:
        List of matching document chunks with scores
    """
    processor = get_document_processor()
    results = processor.search_documents(query=query, top_k=top_k)
    return {"query": query, "results": results, "count": len(results)}