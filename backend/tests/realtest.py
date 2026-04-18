#!/usr/bin/env python3
"""
RealTest - End-to-End Diagnosis Pipeline Test

Run the full diagnosis pipeline on a real ultrasound image to test
in actual conditions with Ollama/MedGemma inference.

Usage:
    python realtest.py <image_path> [--trimester 1st|2nd|3rd] [--verbose]

Example:
    python realtest.py /path/to/ultrasound.png --trimester 2nd
"""

import sys
import os
import time
import argparse
import asyncio
from pathlib import Path
from typing import Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def print_key_value(key: str, value: str, indent: int = 0) -> None:
    """Print a key-value pair with formatting."""
    prefix = "  " * indent
    print(f"{prefix}{key}: {value}")


async def run_diagnosis(
    image_path: str,
    trimester: str,
    mother_age: int,
    gestational_age_weeks: float,
    b_hcg: Optional[float] = None,
    papp_a: Optional[float] = None,
    previous_affected_pregnancy: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Run the full diagnosis pipeline.

    Args:
        image_path: Path to ultrasound image
        trimester: Trimester ("1st", "2nd", "3rd")
        mother_age: Mother's age
        gestational_age_weeks: Gestational age in weeks
        b_hcg: Optional beta-hCG value
        papp_a: Optional PAPP-A value
        previous_affected_pregnancy: History of affected pregnancy
        verbose: Enable verbose output

    Returns:
        Dictionary with diagnosis results
    """
    from app.services.diagnosis import DiagnosisService
    from app.models.diagnosis import DiagnosisQuery
    from app.models.patient import PatientContext
    from app.core.medgemma import get_medgemma

    print_section("Configuration")
    print_key_value("Image", image_path)
    print_key_value("Trimester", trimester)
    print_key_value("Gestational Age", f"{gestational_age_weeks} weeks")
    print_key_value("Mother Age", str(mother_age))
    if b_hcg:
        print_key_value("beta-hCG", f"{b_hcg} IU/L")
    if papp_a:
        print_key_value("PAPP-A", f"{papp_a} mIU/L")
    print_key_value("Previous Affected", str(previous_affected_pregnancy))

    # Build patient context
    patient_context = PatientContext(
        b_hcg=b_hcg,
        papp_a=papp_a,
        mother_age=mother_age,
        gestational_age_weeks=gestational_age_weeks,
        previous_affected_pregnancy=previous_affected_pregnancy,
    )

    # Build query
    query = DiagnosisQuery(
        trimester=trimester,
        patient_context=patient_context,
        top_k=10,
    )

    # Initialize service
    print_section("Initializing Pipeline")
    vector_store_path = os.environ.get("CHROMA_PATH", "./data/vector_db")
    print_key_value("Vector Store", vector_store_path)

    service = DiagnosisService(vector_store_path=vector_store_path)
    print_key_value("Service", "initialized")

    # Check MedGemma
    medgemma = get_medgemma()
    medgemma._ensure_loaded()
    print_key_value("MedGemma", "loaded")

    # Run diagnosis
    print_section("Running Diagnosis")

    start_time = time.time()

    try:
        results = await service.diagnose_multiple_diseases(
            image_path=image_path,
            query=query,
        )
        elapsed = time.time() - start_time

        return {
            "success": True,
            "elapsed_seconds": elapsed,
            "results": results,
            "patient_context": patient_context,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "elapsed_seconds": elapsed,
            "error": str(e),
            "error_type": type(e).__name__,
        }


def print_results(results: dict) -> None:
    """Print diagnosis results."""
    if not results["success"]:
        print_section("ERROR")
        print(f"Error: {results['error']}")
        print(f"Type: {results['error_type']}")
        print(f"\nTime: {results['elapsed_seconds']:.1f}s")
        return

    print_section("Results")
    print(f"Total Time: {results['elapsed_seconds']:.1f}s\n")

    diagnosis_results = results["results"]

    if not diagnosis_results:
        print("No diagnosis results returned.")
        return

    print(f"Diseases Scored: {len(diagnosis_results)}\n")

    for i, result in enumerate(diagnosis_results, 1):
        print(f"{i}. {result.disease_name}")
        print(f"   Disease ID: {result.disease_id}")
        print(f"   Final Score: {result.final_score:.4f}")

        if result.confidence_interval:
            ci = result.confidence_interval
            print(f"   95% CI: [{ci[0]:.4f}, {ci[1]:.4f}]")

        if result.applied_priors:
            print(f"   Applied Priors: {', '.join(result.applied_priors)}")

        if result.matching_positive_cases:
            print(f"   Positive Matches: {len(result.matching_positive_cases)}")
            if len(result.matching_positive_cases) <= 3:
                for case in result.matching_positive_cases:
                    print(f"      - {case['case_id']}: {case['similarity']:.4f}")
            else:
                for case in result.matching_positive_cases[:3]:
                    print(f"      - {case['case_id']}: {case['similarity']:.4f}")
                print(f"      ... and {len(result.matching_positive_cases) - 3} more")

        if result.matching_negative_cases:
            print(f"   Negative Matches: {len(result.matching_negative_cases)}")

        print()


async def extract_and_show_symptoms(image_path: str, trimester: str, verbose: bool = False) -> None:
    """Extract and display symptoms from the image."""
    from app.core.medgemma import get_medgemma
    from app.core.image_processor import load_ultrasound_image, image_to_bytes
    from PIL import Image

    print_section("Symptom Extraction")

    # Load image
    image, metadata = load_ultrasound_image(image_path)
    print_key_value("Image Format", metadata.format or "unknown")
    print_key_value("Image Size", f"{metadata.width}x{metadata.height}")

    if metadata.gestational_age_weeks:
        print_key_value("Gestational Age (from metadata)", f"{metadata.gestational_age_weeks} weeks")
    if metadata.trimester:
        print_key_value("Trimester (from metadata)", metadata.trimester)

    # Convert to bytes
    image_bytes = image_to_bytes(image, format="PNG")

    # Get MedGemma
    medgemma = get_medgemma()
    medgemma._ensure_loaded()

    print_key_value("MedGemma", "extracting symptoms...")

    start_time = time.time()
    symptom_desc = await medgemma.extract_symptoms_from_bytes_async(
        image_bytes=image_bytes,
        trimester=trimester,
        gestational_age_weeks=metadata.gestational_age_weeks,
    )
    elapsed = time.time() - start_time

    print_key_value("Extraction Time", f"{elapsed:.1f}s")
    print_key_value("Overall Assessment", symptom_desc.overall)

    if symptom_desc.symptoms:
        print(f"\n  Extracted {len(symptom_desc.symptoms)} symptoms:")
        for symptom in symptom_desc.symptoms:
            normal_range = f" (normal: {symptom.normal_range})" if symptom.normal_range else ""
            confidence = f" [conf: {symptom.confidence:.2f}]" if symptom.confidence else ""
            print(f"    - {symptom.type}: {symptom.value} ({symptom.assessment}){normal_range}{confidence}")

    # Show embedding
    if verbose:
        print("\n  Generating embedding...")
        start_time = time.time()
        embedding = await medgemma.embed_symptoms_async(symptom_desc.symptom_text)
        elapsed = time.time() - start_time
        print_key_value("Embedding Time", f"{elapsed:.2f}s")
        print_key_value("Embedding Dimensions", str(len(embedding)))
        print_key_value("Embedding Sample", str(embedding[:5]))


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RealTest - End-to-End Diagnosis Pipeline Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python realtest.py /path/to/image.png --trimester 2nd --mother-age 32
  python realtest.py ultrasound.jpg --trimester 1st --ga 12 --verbose
  python realtest.py image.dcm --trimester 3rd --b-hcg 50000 --papp-a 2.5
        """,
    )

    parser.add_argument(
        "image_path",
        help="Path to the ultrasound image file",
    )

    parser.add_argument(
        "--trimester",
        "-t",
        choices=["1st", "2nd", "3rd"],
        default="2nd",
        help="Trimester (default: 2nd)",
    )

    parser.add_argument(
        "--mother-age",
        "-a",
        type=int,
        default=30,
        help="Mother's age (default: 30)",
    )

    parser.add_argument(
        "--ga",
        "--gestational-age",
        type=float,
        default=20.0,
        help="Gestational age in weeks (default: 20.0)",
    )

    parser.add_argument(
        "--b-hcg",
        type=float,
        help="beta-hCG value in IU/L",
    )

    parser.add_argument(
        "--papp-a",
        type=float,
        help="PAPP-A value in mIU/L",
    )

    parser.add_argument(
        "--previous-affected",
        action="store_true",
        help="History of previous affected pregnancy",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--skip-symptoms",
        action="store_true",
        help="Skip symptom extraction step",
    )

    args = parser.parse_args()

    # Validate image path
    if not os.path.isfile(args.image_path):
        print(f"Error: Not a valid file: {args.image_path}", file=sys.stderr)
        sys.exit(1)

    # Check file extension
    valid_extensions = {".jpg", ".jpeg", ".png", ".dcm", ".dicom"}
    ext = Path(args.image_path).suffix.lower()
    if ext and ext not in valid_extensions:
        print(f"Warning: Unusual file extension '{ext}'. Supported: {', '.join(valid_extensions)}")

    print_section("RealTest - Diagnosis Pipeline")
    print(f"Image: {args.image_path}")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Extract and show symptoms first
    if not args.skip_symptoms:
        await extract_and_show_symptoms(args.image_path, args.trimester, args.verbose)

    # Run diagnosis
    results = await run_diagnosis(
        image_path=args.image_path,
        trimester=args.trimester,
        mother_age=args.mother_age,
        gestational_age_weeks=args.ga,
        b_hcg=args.b_hcg,
        papp_a=args.papp_a,
        previous_affected_pregnancy=args.previous_affected,
        verbose=args.verbose,
    )

    # Print results
    print_results(results)

    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    asyncio.run(main())