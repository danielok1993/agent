# Batch PDF Extraction Script Design

**Date:** 2026-07-03  
**Scope:** Interactive Python CLI for parallel batch extraction of architectural PDFs

## Overview

A single Python script (`batch_extract.py`) that discovers all PDFs in the `plans/` folder, prompts the user for detection options interactively, then runs up to 5 extract commands in parallel with real-time progress reporting.

## User Interaction

### Interactive Prompts (Sequential)

The script prompts the user for three boolean options, in this order:

```
Enable window detection? (Y/n): 
Enable wall detection? (Y/n): 
Use Gemini for validation? (Y/n): 
```

Behavior:
- Each prompt defaults to `Y` (enabled) if the user presses Enter without typing
- User can type `y`, `Y`, `n`, or `N` (case-insensitive)
- After all three prompts, the script confirms the chosen options and displays the count of PDFs discovered

Example confirmation:
```
Configuration:
  Window detection: enabled
  Wall detection: disabled
  Gemini validation: disabled (offline mode)
  
Found 17 PDFs in plans/. Starting extraction...
```

**Note:** Door detection is always enabled and non-configurable.

## PDF Discovery

- Scan the `plans/` folder in the project root (non-recursive)
- Collect all files matching `*.pdf` (case-insensitive)
- If no PDFs found, exit with a helpful message
- Display count before prompting user to start

## Parallel Execution Model

- Use `concurrent.futures.ProcessPoolExecutor(max_workers=5)` to manage worker pool
- For each discovered PDF, construct a full extract command: `python app.py extract <pdf_path> [--flags]`
- Flags depend on user choices:
  - If windows disabled: add `--disable-windows`
  - If walls disabled: add `--disable-walls`
  - If offline mode: add `--no-gemini`
- Each subprocess runs with the activated venv in its shell environment
- Capture subprocess stdout/stderr for progress reporting

### Environment Setup

The script will:
1. Verify that `.venv/` directory exists in the project root; if not, exit with setup instructions
2. Run each extract subprocess as a shell command: `source .venv/bin/activate && python app.py extract ...`
   - This ensures the venv is active in the subprocess's environment
   - Preserves the current working directory context

## Progress Output

As each PDF is processed, the script prints a line for each completed extraction (in the order they complete):

```
[1/17] ✓ EXISTING_FIRST_FLOOR_PLAN-4103493.pdf → outputs/2026-07-03_10-30-45/
[2/17] ✓ PROPOSED_FLOOR_PLANS-574477.pdf → outputs/2026-07-03_10-30-45/
[3/17] ✗ BROKEN_FILE.pdf (exit code 1: error details here)
[4/17] ✓ LOCATION_PLAN_AND_ALL_EXISTING_INFORMATION-772263.pdf → outputs/2026-07-03_10-30-45/
```

Details:
- `[N/Total]` shows progress counter
- `✓` indicates success; `✗` indicates failure
- On success, include the output directory timestamp (extracted from the extract command or inferred from the first run)
- On failure, print a brief error message (first line of stderr or exit code)

### Summary at Completion

After all PDFs finish, print a summary line:

```
Done! 15 succeeded, 2 failed. Check outputs/ for results.
```

## Error Handling

- **Missing venv:** If `.venv/` doesn't exist, print helpful error and exit:
  ```
  Error: .venv not found. Run: source .venv/bin/activate && pip install -r requirements.txt
  ```

- **No PDFs found:** If `plans/` folder is empty or contains no `.pdf` files:
  ```
  No PDFs found in plans/ folder. Exiting.
  ```

- **Extract failure:** If a subprocess exits non-zero, catch the exception, print the error inline, and continue processing other PDFs (do not halt the batch)

- **Ctrl+C handling:** If user presses Ctrl+C during parallel execution, gracefully cancel remaining tasks and print:
  ```
  Interrupted. Waiting for in-flight tasks to finish...
  [output of any in-progress PDFs]
  Batch cancelled.
  ```

## Output

- All results go to the default `outputs/` directory (as per app.py's default behavior)
- The script does not create its own output directory; it delegates output management to each extract command
- A timestamp-based subdirectory is created by app.py for each run (e.g., `outputs/2026-07-03_10-30-45/`)

## File Organization

```
batch_extract.py          # The script itself (new file)
plans/                    # Input PDFs (existing)
.venv/                    # Python venv (must exist before running)
outputs/                  # Results (created by extract command)
```

## Implementation Notes

- Script should be executable: `chmod +x batch_extract.py` (optional, can also run as `python batch_extract.py`)
- Use `argparse` if CLI flags are added in the future; for now, interactive prompts only
- Keep venv activation simple: shell command `source .venv/bin/activate` in the subprocess invocation
- Parallel execution is wall-clock bound by the 5 slowest PDFs, not the sum of all PDFs
