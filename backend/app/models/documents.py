"""Document models for PDF upload and vector indexing."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Metadata for an uploaded document."""
    filename: str
    file_size: int
    content_type: str = "application/pdf"
    chunk_count: int = 0
    indexed_at: datetime = Field(default_factory=datetime.utcnow)


class UploadResponse(BaseModel):
    """Response for successful document upload."""
    document_id: str
    chunks_indexed: int
    status: str = "success"
    filename: str
    message: Optional[str] = None


class UploadError(BaseModel):
    """Error response for failed upload."""
    detail: str
    document_id: Optional[str] = None