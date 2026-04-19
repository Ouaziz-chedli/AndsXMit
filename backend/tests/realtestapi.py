#!/usr/bin/env python3
"""
RealTestAPI - End-to-End Diagnosis Pipeline Test via HTTP API

Run the full diagnosis pipeline by calling the FastAPI endpoint,
which properly saves results to the /save directory.

Usage:
    # Start server and run test (server runs in background)
    python realtestapi.py /path/to/image.png --trimester 1st

    # Run against already-running server
    python realtestapi.py /path/to/image.png --trimester 1st --reuse-server

    # With custom port
    python realtestapi.py /path/to/image.png --port 9000

Example:
    python realtestapi.py ../../docs/omphalocele-6.jpg --trimester 1st --ga 20 -a 30
"""

import sys
import os
import time
import argparse
import json
import subprocess
import signal
import requests
from pathlib import Path
from typing import Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


DEFAULT_PORT = 8000
DEFAULT_HOST = "http://localhost"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def print_key_value(key: str, value: str, indent: int = 0) -> None:
    """Print a key-value pair with formatting."""
    prefix = "  " * indent
    print(f"{prefix}{key}: {value}")


class RealTestAPI:
    """RealTest via HTTP API."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        reuse_server: bool = False,
    ):
        self.base_url = f"{host}:{port}"
        self.reuse_server = reuse_server
        self.server_process: Optional[subprocess.Popen] = None

    def _wait_for_server(self, timeout: int = 60) -> bool:
        """Wait for server to be ready."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(f"{self.base_url}/health", timeout=2)
                if resp.status_code == 200:
                    print_key_value("Server", "ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        return False

    def _start_server(self) -> bool:
        """Start the FastAPI server in a subprocess."""
        if self.reuse_server:
            print_key_value("Server", "reusing existing")
            return self._wait_for_server()

        print_key_value("Server", "starting in background...")

        # Find the backend directory
        backend_dir = Path(__file__).parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(backend_dir.parent)

        # Start uvicorn
        self.server_process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", str(self.base_url.split(":")[-1]),
                "--log-level", "warning",
            ],
            cwd=str(backend_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        return self._wait_for_server()

    def _stop_server(self):
        """Stop the server if we started it."""
        if self.server_process and not self.reuse_server:
            print_key_value("Server", "shutting down...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

    def run_diagnosis(
        self,
        image_path: str,
        trimester: str,
        mother_age: int,
        gestational_age_weeks: float,
        b_hcg: Optional[float] = None,
        papp_a: Optional[float] = None,
        previous_affected_pregnancy: bool = False,
    ) -> dict:
        """
        Run diagnosis via HTTP API.

        Returns:
            Dictionary with diagnosis results and save info
        """
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
        print_key_value("API Endpoint", f"{self.base_url}/api/v1/diagnosis")

        # Prepare multipart form data
        files = {
            "images": open(image_path, "rb"),
        }
        data = {
            "trimester": trimester,
            "mother_age": str(mother_age),
            "gestational_age_weeks": str(gestational_age_weeks),
            "previous_affected_pregnancy": str(previous_affected_pregnancy).lower(),
        }
        if b_hcg is not None:
            data["b_hcg"] = str(b_hcg)
        if papp_a is not None:
            data["papp_a"] = str(papp_a)

        print_section("Running Diagnosis via API")

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/diagnosis",
                files=files,
                data=data,
                timeout=300,  # 5 min timeout for slow MedGemma
            )
            elapsed = time.time() - start_time

            if response.status_code != 200:
                return {
                    "success": False,
                    "elapsed_seconds": elapsed,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }

            result = response.json()
            return {
                "success": True,
                "elapsed_seconds": elapsed,
                "response": result,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "elapsed_seconds": time.time() - start_time,
                "error": "Request timed out (MedGemma may be slow)",
            }
        except Exception as e:
            return {
                "success": False,
                "elapsed_seconds": time.time() - start_time,
                "error": str(e),
            }
        finally:
            files["images"].close()


def print_results(results: dict, verbose: bool = False) -> None:
    """Print diagnosis results."""
    if not results["success"]:
        print_section("ERROR")
        print(f"Error: {results['error']}")
        print(f"\nTime: {results['elapsed_seconds']:.1f}s")
        return

    print_section("Results")
    print(f"Total Time: {results['elapsed_seconds']:.1f}s\n")

    response = results["response"]
    fast_track = response.get("fast_track", [])

    if not fast_track:
        print("No diagnosis results returned.")
        return

    print(f"Diseases Scored: {len(fast_track)}\n")

    for i, result in enumerate(fast_track, 1):
        disease_name = result.get("disease_name", result.get("disease_id", "Unknown"))
        disease_id = result.get("disease_id", "unknown")
        final_score = result.get("final_score", 0.0)
        confidence_interval = result.get("confidence_interval")
        applied_priors = result.get("applied_priors", [])

        print(f"{i}. {disease_name}")
        print(f"   Disease ID: {disease_id}")
        print(f"   Final Score: {final_score:.4f}")

        if confidence_interval:
            print(f"   95% CI: [{confidence_interval[0]:.4f}, {confidence_interval[1]:.4f}]")

        if applied_priors:
            print(f"   Applied Priors: {', '.join(applied_priors)}")

        print()


def print_save_info(response: dict) -> None:
    """Print where results were saved."""
    if not response.get("fast_track"):
        return

    # Get timestamp from the save directory
    # The API saves to save/{timestamp}/{task_id}/
    # We can infer this from the response if available
    task_id = response.get("fast_track", [{}])[0].get("task_id", "unknown")

    print_section("Save Information")
    print("Results are automatically saved to:")
    print("  save/{timestamp}/{task_id}/")
    print(f"    - image.{{ext}}    (uploaded image copy)")
    print(f"    - results.json    (diagnosis results)")
    print(f"    - context.json    (anonymized patient context)")
    print()
    print(f"Task ID: {task_id}")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RealTestAPI - End-to-End Diagnosis Pipeline Test via HTTP API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python realtestapi.py /path/to/image.png --trimester 2nd
  python realtestapi.py ultrasound.jpg --trimester 1st --ga 12 -a 32
  python realtestapi.py image.dcm --trimester 3rd --reuse-server
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
        "--port",
        "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"API server port (default: {DEFAULT_PORT})",
    )

    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_HOST,
        help=f"API server host (default: {DEFAULT_HOST})",
    )

    parser.add_argument(
        "--reuse-server",
        action="store_true",
        help="Don't start a new server; assume one is already running",
    )

    parser.add_argument(
        "--skip-server",
        action="store_true",
        help="Skip server startup/shutdown (use with --reuse-server)",
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

    print_section("RealTestAPI - Diagnosis via HTTP API")
    print(f"Image: {args.image_path}")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    tester = RealTestAPI(host=args.host, port=args.port, reuse_server=args.reuse_server)

    # Start or connect to server
    if not args.skip_server:
        if not tester._start_server():
            print("Error: Could not start or connect to server")
            sys.exit(1)

    try:
        # Run diagnosis
        results = tester.run_diagnosis(
            image_path=args.image_path,
            trimester=args.trimester,
            mother_age=args.mother_age,
            gestational_age_weeks=args.ga,
            b_hcg=args.b_hcg,
            papp_a=args.papp_a,
            previous_affected_pregnancy=args.previous_affected,
        )

        # Print results
        print_results(results)

        if results["success"]:
            print_save_info(results["response"])

        # Exit with appropriate code
        sys.exit(0 if results["success"] else 1)

    finally:
        if not args.skip_server:
            tester._stop_server()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
