#!/usr/bin/env python3
"""
Batch PDF extraction script — discovers all PDFs in plans/ folder,
prompts for detection options, and runs extraction in parallel (5 at a time).
"""
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed


def prompt_bool(question: str, default: bool = True) -> bool:
    """Prompt user for a yes/no question, return bool."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{question} ({default_str}): ").strip().lower()
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        elif response == "":
            return default
        else:
            print("Please enter 'y' or 'n'.")


def find_pdfs(plans_dir: Path) -> list[Path]:
    """Find all PDF files in plans_dir (non-recursive)."""
    pdfs = sorted(plans_dir.glob("*.pdf"))
    return pdfs


def build_extract_command(
    pdf_path: Path,
    enable_windows: bool,
    enable_walls: bool,
    use_gemini: bool,
) -> str:
    """Build the extract command for a single PDF."""
    flags = []
    if not enable_windows:
        flags.append("--disable-windows")
    if not enable_walls:
        flags.append("--disable-walls")
    if not use_gemini:
        flags.append("--no-gemini")

    flags_str = " ".join(flags)
    cmd = f"source .venv/bin/activate && python app.py extract '{pdf_path}'{' ' + flags_str if flags_str else ''}"
    return cmd


def run_extract(
    pdf_path: Path,
    enable_windows: bool,
    enable_walls: bool,
    use_gemini: bool,
) -> tuple[Path, bool, str]:
    """
    Run extract command for a single PDF.
    Returns (pdf_path, success: bool, output_or_error: str)
    """
    cmd = build_extract_command(pdf_path, enable_windows, enable_walls, use_gemini)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=300,  # 5-minute timeout per PDF
        )
        if result.returncode == 0:
            return (pdf_path, True, "")
        else:
            error_msg = result.stderr.split("\n")[0] if result.stderr else f"exit code {result.returncode}"
            return (pdf_path, False, error_msg)
    except subprocess.TimeoutExpired:
        return (pdf_path, False, "timeout (5 minutes)")
    except Exception as e:
        return (pdf_path, False, str(e))


def main() -> None:
    # Check venv exists
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("Error: .venv not found. Run:", file=sys.stderr)
        print("  source .venv/bin/activate && pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    # Find PDFs
    plans_dir = Path("plans")
    if not plans_dir.exists():
        print("Error: plans/ folder not found.", file=sys.stderr)
        sys.exit(1)

    pdfs = find_pdfs(plans_dir)
    if not pdfs:
        print("No PDFs found in plans/ folder. Exiting.")
        sys.exit(0)

    print(f"\nFound {len(pdfs)} PDFs in plans/\n")

    # Prompt user for options
    enable_windows = prompt_bool("Enable window detection?", default=True)
    enable_walls = prompt_bool("Enable wall detection?", default=True)
    use_gemini = prompt_bool("Use Gemini for validation?", default=True)

    # Confirm settings
    print("\nConfiguration:")
    print(f"  Window detection: {'enabled' if enable_windows else 'disabled'}")
    print(f"  Wall detection: {'enabled' if enable_walls else 'disabled'}")
    print(f"  Gemini validation: {'enabled' if use_gemini else 'disabled (offline mode)'}")
    print(f"\nStarting extraction of {len(pdfs)} PDFs (5 at a time)...\n")

    # Run in parallel
    completed = 0
    succeeded = 0
    failed = 0

    try:
        with ProcessPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    run_extract,
                    pdf,
                    enable_windows,
                    enable_walls,
                    use_gemini,
                ): pdf
                for pdf in pdfs
            }

            for future in as_completed(futures):
                completed += 1
                pdf_path, success, error_msg = future.result()
                pdf_name = pdf_path.name

                if success:
                    succeeded += 1
                    print(f"[{completed}/{len(pdfs)}] ✓ {pdf_name}")
                else:
                    failed += 1
                    print(f"[{completed}/{len(pdfs)}] ✗ {pdf_name} ({error_msg})")

    except KeyboardInterrupt:
        print("\n\nInterrupted. Waiting for in-flight tasks to finish...", file=sys.stderr)
        sys.exit(1)

    # Summary
    print(f"\nDone! {succeeded} succeeded, {failed} failed. Check outputs/ for results.")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
