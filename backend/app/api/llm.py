"""LLM chat API endpoints."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.ollama_client import get_ollama_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])

DEBUG = os.getenv("DEBUG", "false").lower() == "true"


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
    if DEBUG:
        logger.info(f"[LLM] Received chat request: message='{request.message[:100]}...' system={request.system is not None} temperature={request.temperature}")

    try:
        client = get_ollama_client()

        if not await client.is_available():
            if DEBUG:
                logger.warning("[LLM] Ollama not available")
            raise HTTPException(
                status_code=503,
                detail="LLM service not available. Please ensure Ollama is running."
            )

        if DEBUG:
            logger.info(f"[LLM] Calling Ollama chat with model={client.model_name}")

        response = await client.chat(
            message=request.message,
            system=request.system or "You are MedGemma, an AI assistant specialized in prenatal ultrasound analysis. Provide helpful, accurate information about prenatal conditions and ultrasound findings.",
            temperature=request.temperature,
        )

        if DEBUG:
            logger.info(f"[LLM] Received response: length={len(response)}")

        return ChatResponse(
            response=response,
            model=client.model_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LLM] Error: {str(e)}")
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
