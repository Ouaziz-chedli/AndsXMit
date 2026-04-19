"""
Ollama Client - Interface to Ollama for MedGemma inference.

Ollama runs MedGemma locally via REST API, enabling self-hosted AI inference.
"""

import base64
import httpx
from typing import Optional


class OllamaClient:
    """Simple Ollama API client for MedGemma inference."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "medgemma",
        timeout: float = 120.0,
    ):
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama server URL
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=timeout)

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        system: str | None = None,
    ) -> str:
        """
        Send image to Ollama for analysis.
        Works with medgemma model that supports vision.

        Args:
            image_path: Path to the image file
            prompt: Prompt/question for the model
            system: Optional system prompt

        Returns:
            Model's text response
        """
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Use base64 encoding for images (required by Ollama API)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        json_body = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }

        if system:
            json_body["system"] = system

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=json_body,
        )
        response.raise_for_status()
        return response.json()["response"]

    async def analyze_image_bytes(
        self,
        image_bytes: bytes,
        prompt: str,
        system: str | None = None,
    ) -> str:
        """
        Send image bytes to Ollama for analysis.

        Args:
            image_bytes: Image data as bytes
            prompt: Prompt/question for the model
            system: Optional system prompt

        Returns:
            Model's text response
        """
        # Use base64 encoding for images (required by Ollama API)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        json_body = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }

        if system:
            json_body["system"] = system

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=json_body,
        )
        response.raise_for_status()
        return response.json()["response"]

    async def generate_embeddings(
        self,
        text: str,
        embedding_model: str | None = None,
    ) -> list[float]:
        """
        Generate text embeddings using Ollama's embedding endpoint.

        Args:
            text: Text to embed
            embedding_model: Model to use for embeddings (defaults to OLLAMA_EMBEDDING_MODEL)

        Returns:
            Embedding vector

        Raises:
            httpx.HTTPError: If Ollama fails and no fallback is available
        """
        from app.config import settings

        model = embedding_model or settings.OLLAMA_EMBEDDING_MODEL

        try:
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            # Ollama embedding failed - caller should handle fallback
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def is_available(self) -> bool:
        """
        Check if Ollama server is available.

        Returns:
            True if server responds successfully
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def chat(
        self,
        message: str,
        system: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Send a text-only chat message to Ollama.

        Uses the /api/chat endpoint for conversational interaction.

        Args:
            message: User message
            system: Optional system prompt
            temperature: Sampling temperature

        Returns:
            Model's text response
        """
        import logging
        import os

        logger = logging.getLogger(__name__)
        debug = os.getenv("DEBUG", "false").lower() == "true"

        json_body = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            json_body["messages"].insert(
                0,
                {
                    "role": "system",
                    "content": system,
                }
            )

        if debug:
            logger.info(f"[OLLAMA] Sending chat request to {self.base_url}/api/chat")
            logger.info(f"[OLLAMA] Model: {self.model}, Messages: {len(json_body['messages'])}")

        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json=json_body,
        )

        if debug:
            logger.info(f"[OLLAMA] Response status: {response.status_code}")

        response.raise_for_status()
        result = response.json()
        content = result["message"]["content"]

        if debug:
            logger.info(f"[OLLAMA] Response content length: {len(content)} chars")

        # Post-process: strip tool_code blocks that MedGemma may generate
        content = self._clean_tool_code(content)

        return content

    def _clean_tool_code(self, text: str) -> str:
        """Remove tool_code blocks from model output.

        MedGemma sometimes generates tool_code blocks in its response,
        which are not intended for user display. This strips them.

        Args:
            text: Raw model output

        Returns:
            Cleaned text without tool_code blocks
        """
        import re

        # Remove all code blocks that contain tool_code (including nested print statements)
        # Matches ```...tool_code...``` across multiple lines
        cleaned = re.sub(r'```[^`]*tool_code[^`]*```', '', text, flags=re.DOTALL)

        # Remove any remaining triple backtick code blocks
        cleaned = re.sub(r'```[^`]+```', '', cleaned)

        # Remove standalone print statements
        cleaned = re.sub(r'print\s*\([^)]+\)', '', cleaned)

        # Clean up extra whitespace and newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        return cleaned.strip()

    async def list_models(self) -> list[dict]:
        """
        List available models on the Ollama server.

        Returns:
            List of model info dicts
        """
        response = await self.client.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])


# Global client instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client(
    base_url: str | None = None,
    model: str | None = None,
) -> OllamaClient:
    """
    Get or create the global Ollama client instance.

    Args:
        base_url: Ollama server URL (uses env OLLAMA_HOST if not provided)
        model: Model name (uses env OLLAMA_MODEL if not provided)

    Returns:
        OllamaClient instance
    """
    global _ollama_client
    if _ollama_client is None:
        from app.config import settings

        _ollama_client = OllamaClient(
            base_url=base_url or settings.OLLAMA_HOST,
            model=model or settings.OLLAMA_MODEL,
        )
    return _ollama_client


def reset_ollama_client() -> None:
    """Reset the global Ollama client instance."""
    global _ollama_client
    if _ollama_client is not None:
        import asyncio
        asyncio.create_task(_ollama_client.close())
    _ollama_client = None
