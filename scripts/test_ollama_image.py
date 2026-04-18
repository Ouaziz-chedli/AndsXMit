#!/usr/bin/env python3
"""
PrenatalAI — Test Ollama with First Trimester Ultrasound
========================================================

This script tests MedGemma's ability to analyze first trimester
ultrasound images for prenatal screening markers.

Usage:
    python scripts/test_ollama_image.py [image_path]
    python scripts/test_ollama_image.py docs/nuchal-translucency-2.png
"""

import asyncio
import base64
import os
import sys
from pathlib import Path


# Bypass full backend import by setting path directly to modules we need
BACKEND_CORE = Path(__file__).parent.parent / "backend" / "app" / "core"
sys.path.insert(0, str(BACKEND_CORE.parent))


# Force Settings to not use .env (avoid Node.js API env vars)
os.environ.setdefault("DATA_DIR", "/tmp/data")
os.environ.setdefault("CHROMA_PATH", "/tmp/vector_db")
os.environ.setdefault("DB_PATH", "/tmp/db.sqlite")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "medgemma")
os.environ.setdefault("IMAGE_DIR", "/tmp/images")


FIRST_TRIMESTER_PROMPT = """You are a medical assistant specialized in prenatal ultrasound interpretation, focused exclusively on FIRST TRIMESTER screening (11-14 weeks).

IMPORTANT:
- You DO NOT make a definitive diagnosis
- You perform a rule-based risk classification based on visible findings
- You must NOT hallucinate or infer missing data

Analyze this ultrasound image for first trimester markers:

First Trimester Markers:
- Nuchal Translucency (NT): normal <3.0mm, elevated >3.0mm
- Nasal Bone: present or absent/hypoplastic
- Cardiac Flow: normal or tricuspid regurgitation
- Ductus Venosus: normal or abnormal

Decision Rules:
- NT > 3.0mm OR absent nasal bone OR flow abnormality → RISK
- No markers visible → NORMAL

Respond with:
1. What is visible in the image
2. Detected markers (if any)
3. Classification: NORMAL or RISK_INDICATOR
4. Confidence level
5. Brief justification

Output as structured text."""


class OllamaClient:
    """Direct Ollama client without full backend deps."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "medgemma:4b"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        import httpx
        self.client = httpx.AsyncClient(timeout=180.0)

    async def analyze_image_bytes(self, image_bytes: bytes, prompt: str, system: str = None) -> str:
        """Send image bytes to Ollama for analysis."""
        import httpx
        # Use base64 encoding for images (required by Ollama API)
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

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

    async def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


MOCK_RESPONSES = {
    "1st": {
        "symptoms": [
            {"type": "nuchal_translucency", "value": "2.5mm", "assessment": "normal", "normal_range": "1.5-2.5mm"},
            {"type": "nasal_bone", "value": "present", "assessment": "normal"},
            {"type": "cardiac_flow", "value": "normal", "assessment": "normal"},
        ],
        "overall": "Normal first trimester ultrasound. NT within normal limits.",
    },
    "2nd": {
        "symptoms": [
            {"type": "cardiac", "value": "four_chamber_normal", "assessment": "normal"},
            {"type": "femur_length", "value": "45mm", "assessment": "normal"},
        ],
        "overall": "Normal second trimester morphology scan.",
    },
    "3rd": {
        "symptoms": [
            {"type": "growth", "value": "normal_percentile", "assessment": "normal"},
            {"type": "placenta", "value": "posterior_grade_2", "assessment": "normal"},
        ],
        "overall": "Normal third trimester growth scan.",
    },
}


def mock_analysis(trimester: str) -> dict:
    """Return mock analysis result."""
    key = trimester if trimester in MOCK_RESPONSES else "1st"
    return MOCK_RESPONSES[key]


async def test_ollama_image(image_path: str):
    """Test Ollama with an ultrasound image."""
    print("=" * 50)
    print("PrenatalAI — Ollama Test")
    print("=" * 50)
    print(f"Image: {image_path}")
    print()

    if not Path(image_path).exists():
        print(f"Error: Image not found: {image_path}")
        return

    client = OllamaClient()

    if not await client.is_available():
        print("Error: Ollama is not running.")
        print()
        print("Options:")
        print("  1. Start Ollama: ollama serve")
        print("  2. Run setup: bash scripts/setup-ollama.sh")
        print("  3. Use mock mode: python scripts/test_ollama_image.py --mock")
        await client.close()
        return

    print("Ollama is available.")
    print(f"Using model: {client.model}")
    print("Running MedGemma analysis...")
    print()

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        print(f"Image size: {len(image_bytes) / 1024:.1f} KB")
        print()

        response = await client.analyze_image_bytes(
            image_bytes=image_bytes,
            prompt=FIRST_TRIMESTER_PROMPT,
            system="You are a medical ultrasound expert. Be precise and clinical.",
        )

        print("=" * 50)
        print("ANALYSIS RESULT")
        print("=" * 50)
        print(response)
        print()

    except Exception as e:
        print(f"Error during analysis: {e}")
        print()
        print("Make sure MedGemma model is installed:")
        print("  ollama pull medgemma")

    finally:
        await client.close()


def test_mock(image_path: str):
    """Test with mock mode (no Ollama required)."""
    print("=" * 50)
    print("PrenatalAI — Mock Mode Test")
    print("=" * 50)
    print(f"Image: {image_path}")
    print()

    for trimester in ["1st", "2nd", "3rd"]:
        result = mock_analysis(trimester)
        print(f"--- Mock result ({trimester} trimester) ---")
        print(f"Overall: {result['overall']}")
        print(f"Symptoms: {[s['type'] + '=' + s['value'] for s in result['symptoms']]}")
        print()


def main():
    args = sys.argv[1:]

    if "--mock" in args:
        args.remove("--mock")
        image_path = args[0] if args else "docs/nuchal-translucency-2.png"
        test_mock(image_path)
        return

    image_path = args[0] if args else "docs/nuchal-translucency-2.png"

    asyncio.run(test_ollama_image(image_path))


if __name__ == "__main__":
    main()
