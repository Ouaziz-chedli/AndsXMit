#!/bin/bash
# PrenatalAI — Test Ollama with First Trimester Image
# ===================================================
#
# Usage:
#   bash scripts/test-ollama.sh [image_path]
#
# Default image: docs/nuchal-translucency-2.png
#

IMAGE_PATH="${1:-docs/nuchal-translucency-2.png}"
PROMPT_FILE="docs/first-trimester-test-prompt.txt"

echo "============================================"
echo "PrenatalAI — Ollama Test"
echo "============================================"
echo "Image: $IMAGE_PATH"
echo ""

# Check if image exists
if [ ! -f "$IMAGE_PATH" ]; then
    echo "Error: Image not found: $IMAGE_PATH"
    exit 1
fi

# Check if prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "Error: Prompt file not found: $PROMPT_FILE"
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama server..."
    ollama serve &
    sleep 3
fi

# Load prompt and run
PROMPT=$(cat "$PROMPT_FILE")

echo "Running MedGemma analysis..."
echo ""

ollama run medgemma "$PROMPT" --image "$IMAGE_PATH"

echo ""
echo "============================================"
echo "Test complete"
echo "============================================"
