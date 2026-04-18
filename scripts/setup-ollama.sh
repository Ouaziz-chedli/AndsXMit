#!/bin/bash
# PrenatalAI — Ollama Setup Script
# ==================================
#
# This script installs Ollama and pulls the MedGemma model
# for PrenatalAI's AI pipeline.
#
# Usage:
#   bash scripts/setup-ollama.sh
#

set -e

echo "============================================"
echo "PrenatalAI — Ollama Setup"
echo "============================================"

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux*)     PLATFORM="linux" ;;
    Darwin*)    PLATFORM="macos" ;;
    *)          echo "Unsupported OS: $OS"; exit 1 ;;
esac

# Check if Ollama is installed
if command -v ollama &> /dev/null; then
    echo "✓ Ollama already installed: $(ollama --version)"
else
    echo ""
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo ""
echo "Starting Ollama server in background..."
ollama serve &

# Wait for server to start
sleep 3

echo ""
echo "Pulling MedGemma model (4B, ~3.3GB)..."
echo "This may take several minutes on first run."
echo ""

ollama pull medgemma:4b

echo ""
echo "============================================"
echo "✓ Ollama setup complete!"
echo "============================================"
echo ""
echo "Available models:"
ollama list
echo ""
echo "To verify MedGemma works:"
echo "  ollama run medgemma 'Hello, analyze this ultrasound' --image /path/to/image.jpg"
echo ""
echo "Or start an interactive session:"
echo "  ollama run medgemma"
echo ""
