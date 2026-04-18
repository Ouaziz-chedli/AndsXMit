#!/usr/bin/env python3
"""
Compute Embeddings Script - Pre-compute embeddings for images and text.

This script processes image files and symptom text, generating embeddings
for use in ChromaDB vector similarity search.

Usage:
    python -m backend.scripts.compute_embeddings --images /path/to/images
    python -m backend.scripts.compute_embeddings --text "symptom description"
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.medgemma import get_medgemma, extract_symptoms_from_bytes
from app.core.image_processor import load_ultrasound_image, image_to_bytes


def compute_image_embedding(
    image_path: str,
    trimester: Optional[str] = None
) -> Dict:
    """
    Compute embedding for an ultrasound image.

    Args:
        image_path: Path to the ultrasound image
        trimester: Optional trimester context for symptom extraction

    Returns:
        Dictionary with embedding and extracted symptoms
    """
    medgemma = get_medgemma()

    # Load image
    image, metadata = load_ultrasound_image(image_path)

    # Determine trimester
    actual_trimester = trimester or metadata.trimester

    # Convert to bytes
    image_bytes = image_to_bytes(image)

    # Get embedding
    embedding = medgemma.embed_image(image_bytes)

    # Extract symptoms
    symptoms = medgemma.extract_symptoms_from_bytes(
        image_bytes,
        actual_trimester or "1st",
        metadata.gestational_age_weeks
    )

    return {
        "image_path": image_path,
        "embedding": embedding,
        "embedding_dim": len(embedding),
        "symptoms": symptoms.symptom_text,
        "trimester": actual_trimester,
        "gestational_age_weeks": metadata.gestational_age_weeks,
    }


def compute_text_embedding(text: str) -> Dict:
    """
    Compute embedding for symptom text.

    Args:
        text: Symptom description text

    Returns:
        Dictionary with embedding
    """
    medgemma = get_medgemma()
    embedding = medgemma.embed_symptoms(text)

    return {
        "text": text,
        "embedding": embedding,
        "embedding_dim": len(embedding),
    }


def batch_compute_embeddings(
    image_dir: Path,
    output_file: Optional[Path] = None
) -> List[Dict]:
    """
    Compute embeddings for all images in a directory.

    Args:
        image_dir: Directory containing image files
        output_file: Optional JSON file to save results

    Returns:
        List of embedding dictionaries
    """
    results = []

    # Find all supported image files
    supported_extensions = {'.dcm', '.dicom', '.jpg', '.jpeg', '.png'}
    image_files = [
        f for f in image_dir.iterdir()
        if f.is_file() and f.suffix.lower() in supported_extensions
    ]

    if not image_files:
        print(f"No supported image files found in {image_dir}")
        return results

    print(f"Found {len(image_files)} image(s) to process")

    for i, image_file in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] Processing: {image_file.name}")

        try:
            result = compute_image_embedding(str(image_file))
            results.append(result)
            print(f"  ✓ Embedding dimension: {result['embedding_dim']}")
            if result['symptoms']:
                print(f"  ✓ Symptoms: {result['symptoms'][:80]}...")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    # Save results if output file specified
    if output_file:
        # Convert embeddings to list for JSON serialization
        for result in results:
            result['embedding'] = result['embedding'].tolist()

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_file}")

    return results


def print_embedding_info(embedding: List[float], label: str = "Embedding"):
    """Print information about an embedding."""
    print(f"\n{label}:")
    print(f"  Dimension: {len(embedding)}")
    print(f"  Min value: {min(embedding):.6f}")
    print(f"  Max value: {max(embedding):.6f}")
    print(f"  Mean value: {sum(embedding) / len(embedding):.6f}")
    print(f"  First 5 values: {[f'{x:.4f}' for x in embedding[:5]]}")


def main():
    """Main entry point for embedding computation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute embeddings for images and text"
    )
    parser.add_argument(
        "--images",
        type=Path,
        help="Directory containing image files to process"
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Text to compute embedding for"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file for batch results"
    )
    parser.add_argument(
        "--trimester",
        choices=["1st", "2nd", "3rd"],
        help="Trimester context for image processing"
    )

    args = parser.parse_args()

    if args.images:
        # Batch process images
        if not args.images.exists():
            print(f"Error: Image directory not found: {args.images}")
            sys.exit(1)

        results = batch_compute_embeddings(args.images, args.output)

        if results:
            print(f"\nProcessed {len(results)} image(s) successfully")

    elif args.text:
        # Process single text
        print(f"Computing embedding for text: \"{args.text[:50]}...\"")
        result = compute_text_embedding(args.text)
        print_embedding_info(result['embedding'], "Text Embedding")

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nResult saved to: {args.output}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
