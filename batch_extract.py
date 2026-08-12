#!/usr/bin/env python3
"""
Batch PDF extraction script — discovers all PDFs in fixtures/sheets/ folder,
prompts for detection options, and runs extraction in parallel (5 at a time).
"""
from __future__ import annotations
import argparse
import os
import signal
import sys
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO_ROOT = Path(__file__).parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
DEFAULT_TIMEOUT_MINUTES = 30


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
) -> list[str]:
    """Build the extract argv for a single PDF (no shell involved)."""
    cmd = [str(VENV_PYTHON), "app.py", "extract", str(pdf_path)]
    if not enable_windows:
        cmd.append("--disable-windows")
    if not enable_walls:
        cmd.append("--disable-walls")
    if not use_gemini:
        cmd.append("--no-gemini")
    # Unconditional: batch is never interactive, and the child inherits this
    # terminal's stdin, so the tty gate alone would not stop it prompting.
    cmd.append("--no-scale-prompt")
    return cmd


def _run_with_group_kill(
    cmd: list[str], timeout_seconds: float, cwd: Path | None = None
) -> tuple[bool, str]:
    """
    Run cmd in its own process group; on timeout SIGKILL the whole group.
    Killing only the direct child leaves grandchildren burning CPU (the
    shell=True orphan bug — see docs/2026-08-04 findings, Part 2).
    Returns (success, error_message).
    """
    with subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        start_new_session=True,
    ) as proc:
        try:
            _, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass  # group already gone
            proc.wait()
            minutes = timeout_seconds / 60
            return (False, f"timeout ({minutes:g} minutes)")
    if proc.returncode == 0:
        return (True, "")
    error_msg = stderr.split("\n")[0] if stderr else f"exit code {proc.returncode}"
    return (False, error_msg)


def run_extract(
    pdf_path: Path,
    enable_windows: bool,
    enable_walls: bool,
    use_gemini: bool,
    timeout_seconds: float = DEFAULT_TIMEOUT_MINUTES * 60,
) -> tuple[Path, bool, str]:
    """
    Run extract command for a single PDF.
    Returns (pdf_path, success: bool, output_or_error: str)
    """
    cmd = build_extract_command(pdf_path, enable_windows, enable_walls, use_gemini)
    try:
        success, error_msg = _run_with_group_kill(cmd, timeout_seconds, cwd=REPO_ROOT)
        return (pdf_path, success, error_msg)
    except Exception as e:
        return (pdf_path, False, str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout-minutes",
        type=float,
        default=DEFAULT_TIMEOUT_MINUTES,
        help=f"per-PDF timeout in minutes (default {DEFAULT_TIMEOUT_MINUTES})",
    )
    args = parser.parse_args()
    timeout_seconds = args.timeout_minutes * 60

    # Check venv exists
    if not VENV_PYTHON.exists():
        print("Error: .venv not found. Run:", file=sys.stderr)
        print("  source .venv/bin/activate && pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    # Find PDFs
    plans_dir = Path("fixtures/sheets")
    if not plans_dir.exists():
        print("Error: fixtures/sheets/ not found. Run: python tools/fetch_fixtures.py",
              file=sys.stderr)
        sys.exit(1)

    pdfs = find_pdfs(plans_dir)
    if not pdfs:
        print("No PDFs found in fixtures/sheets/. Exiting.")
        sys.exit(0)

    print(f"\nFound {len(pdfs)} PDFs in fixtures/sheets/\n")

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
                    timeout_seconds,
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
