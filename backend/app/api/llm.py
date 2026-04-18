"""LLM chat API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.ollama_client import get_ollama_client

router = APIRouter(prefix="/api/llm", tags=["llm"])


class ChatRequest(BaseModel):
    message: str
    system: str | None = None
    temperature: float = 0.1


class ChatResponse(BaseModel):
    response: str
    model: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message to the LLM (MedGemma).

    Args:
        request: Chat request with message and optional system prompt

    Returns:
        ChatResponse with LLM response text
    """
    try:
        client = get_ollama_client()

        if not await client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM service not available. Please ensure Ollama is running."
            )

        response = await client.chat(
            message=request.message,
            system=request.system or "You are MedGemma, an AI assistant specialized in prenatal ultrasound analysis. Provide helpful, accurate information about prenatal conditions and ultrasound findings.",
            temperature=request.temperature,
        )

        return ChatResponse(
            response=response,
            model=client.model_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM error: {str(e)}"
        )


@router.get("/models")
async def list_models():
    """List available Ollama models."""
    try:
        client = get_ollama_client()
        models = await client.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )
