#!/usr/bin/env python3
"""
Seed Mock Data Script - Populate ChromaDB with mock disease cases.

This script reads mock case JSON files and populates the ChromaDB vector store
with symptom embeddings for testing and development.

Usage:
    python -m backend.scripts.seed_mock_data
    python -m backend.scripts.seed_mock_data --data-dir /path/to/data
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict
import hashlib

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.vector_store import VectorStore, StoredCase
from app.core.medgemma import get_medgemma


def load_mock_data(file_path: str) -> Dict:
    """
    Load mock cases from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary with disease data including positive_cases and negative_cases
    """
    with open(file_path, 'r') as f:
        return json.load(f)


def text_to_embedding(text: str) -> List[float]:
    """
    Convert symptom text to embedding vector.

    Uses MedGemma's text embedding capability.
    For now, uses a hash-based mock embedding.

    Args:
        text: Symptom description text

    Returns:
        Embedding vector as list of floats
    """
    # TODO: Replace with actual MedGemma embedding
    medgemma = get_medgemma()
    return medgemma.embed_symptoms(text)


def create_stored_cases(
    disease_id: str,
    disease_name: str,
    trimester: str,
    cases: List[Dict],
    is_positive: bool
) -> List[StoredCase]:
    """
    Convert mock case dictionaries to StoredCase objects.

    Args:
        disease_id: Disease identifier
        disease_name: Disease name
        trimester: Trimester ("1st", "2nd", "3rd")
        cases: List of case dictionaries
        is_positive: True for positive cases, False for negative

    Returns:
        List of StoredCase objects with embeddings
    """
    stored_cases = []

    for case_data in cases:
        # Generate embedding from symptom text
        embedding = text_to_embedding(case_data["symptom_text"])

        # Create metadata
        metadata = {
            "disease_name": disease_name,
            "equipment_manufacturer": case_data.get("equipment_manufacturer"),
            "description": case_data.get("description"),
        }

        stored_case = StoredCase(
            case_id=case_data["case_id"],
            disease_id=disease_id,
            trimester=trimester,
            is_positive=is_positive,
            embedding=embedding,
            symptom_text=case_data["symptom_text"],
            gestational_age_weeks=case_data["gestational_age_weeks"],
            b_hcg_mom=case_data.get("b_hcg_mom"),
            papp_a_mom=case_data.get("papp_a_mom"),
            metadata=metadata,
        )

        stored_cases.append(stored_case)

    return stored_cases


def seed_disease_cases(
    vector_store: VectorStore,
    mock_data: Dict
) -> None:
    """
    Seed ChromaDB with disease cases from mock data.

    Args:
        vector_store: VectorStore instance
        mock_data: Dictionary with disease data
    """
    disease_id = mock_data["disease_id"]
    disease_name = mock_data["disease_name"]
    trimester = mock_data["trimester"]

    print(f"  Disease: {disease_name} ({disease_id})")
    print(f"  Trimester: {trimester}")

    # Process positive cases
    positive_cases = mock_data.get("positive_cases", [])
    if positive_cases:
        print(f"  Positive cases: {len(positive_cases)}")
        stored_positive = create_stored_cases(
            disease_id=disease_id,
            disease_name=disease_name,
            trimester=trimester,
            cases=positive_cases,
            is_positive=True
        )
        vector_store.add_cases(stored_positive)

    # Process negative cases
    negative_cases = mock_data.get("negative_cases", [])
    if negative_cases:
        print(f"  Negative cases: {len(negative_cases)}")
        stored_negative = create_stored_cases(
            disease_id=disease_id,
            disease_name=disease_name,
            trimester=trimester,
            cases=negative_cases,
            is_positive=False
        )
        vector_store.add_cases(stored_negative)

    # Verify count
    total_count = vector_store.get_case_count(disease_id, trimester)
    print(f"  Total cases in DB: {total_count}")
    print()


def main():
    """Main entry point for seeding mock data."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed ChromaDB with mock disease cases"
    )
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).parent.parent / "data" / "mock_cases"),
        help="Directory containing mock case JSON files"
    )
    parser.add_argument(
        "--chroma-path",
        default="/data/vector_db",
        help="Path to ChromaDB persistent storage"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collections before seeding"
    )

    args = parser.parse_args()

    # Initialize vector store
    print(f"Initializing vector store at: {args.chroma_path}")
    vector_store = VectorStore(persist_directory=args.chroma_path)

    # Find all JSON files in data directory
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: Data directory not found: {args.data_dir}")
        sys.exit(1)

    json_files = list(data_dir.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {args.data_dir}")
        sys.exit(0)

    print(f"Found {len(json_files)} mock data file(s)\n")

    # Process each file
    for json_file in json_files:
        print(f"Processing: {json_file.name}")

        # Clear collection if requested
        if args.clear:
            try:
                with open(json_file, 'r') as f:
                    mock_data = json.load(f)
                vector_store.delete_collection(
                    disease_id=mock_data["disease_id"],
                    trimester=mock_data["trimester"]
                )
                print(f"  Cleared existing collection")
            except Exception as e:
                print(f"  Warning: Could not clear collection: {e}")

        # Load and seed data
        mock_data = load_mock_data(json_file)
        seed_disease_cases(vector_store, mock_data)

    # Summary
    print("Seeding complete!")
    print("\nCollections:")
    for collection_name in vector_store.list_collections():
        parts = collection_name.split("_")
        disease_id = "_".join(parts[:-1])
        trimester = parts[-1]
        count = vector_store.get_case_count(disease_id, trimester)
        print(f"  {collection_name}: {count} cases")


if __name__ == "__main__":
    main()
