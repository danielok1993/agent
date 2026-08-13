# Step 4 — Recall audit on the 1:100 sheets (misses are invisible to ground truth)

Status: not started
Kind: audit + user review session — near-zero engineering, the deliverable is
a measured recall-gap list and (user-approved) `deferred` ground-truth
entries. This task is the instrument that ranks future recall work.

## The problem

Ground truth records verdicts on DETECTIONS (confirmed / false_positives /
deferred). A feature the detector never emitted appears nowhere — misses are
structurally invisible (`docs/scale-normalization-findings.md` §3 "Blind
spot"). The 1:100 tier is where misses concentrate (features draw at half
size), and the one direct probe ever done found s06 showing only 2 of 10
visible door swings. Findings §6 has carried "Misses audit on 1:100 sheets"
since the walls branch; nobody has run it.

Current confirmed counts to audit against (re-baseline before starting —
these move): s05 doors 8 (NO windows or rooms in ground truth at all — prime
suspect: none detected vs none existing), s06 2 doors / 8 windows / 0-of-1
rooms, s07 4/10/7, s11 13/27/17, s12 7/0/3-of-4, s16 14/24/13, s18 10/11/6-of-9,
s13 (f≈0.37) 3-of-4 doors / 11 windows / 1-of-4 rooms.

## What to do

1. **Read first:** `CLAUDE.md`; `docs/regression-testing-guide.md` in full —
   especially the ground-truth file format, the RULES FOR EDITING IT, and the
   `deferred` list's meaning (misses the user reported and consciously chose
   not to fix yet; they surface as CLOSED when a later fix catches them).
2. **Regenerate artifacts:** `python tools/regress.py --sheet s05 --sheet s06
   --sheet s07 --sheet s12` (primary set; extend to s11 s16 s18 s13 as time
   allows). Open each sheet's `outputs/regress/<slug>/<ts>/pages/page_01/
   overlay.png` (entities + rejected drawn on the render) beside `render.png`.
3. **Prepare the audit materials — the AGENT'S half:** for each sheet,
   hand-scan the floor-plan regions for doors/windows/room-boundaries visible
   in the render but absent from the overlay's entities. For each candidate
   miss produce: a crop (or exact bbox + description), the entity type, and a
   first-pass mechanism guess (below the size floor? aspect-gate reject —
   step-1's family? no wall context? curved wall — known out of scope?). Use
   `--debug` traces on a few to firm up mechanisms. Collate into a per-sheet
   checklist document with rounded bboxes.
4. **The USER'S half — do not skip or shortcut this:** the user personally
   verdicts each candidate miss (real miss / not actually a feature /
   already-known limitation). Present the checklist and STOP for their pass.
5. **Record, with explicit approval only:** for each user-confirmed miss, a
   `deferred` entry (type + bbox) drafted for that sheet's
   `tests/ground_truth/<slug>.json`. NOTE this task is the ONE sanctioned
   exception to the never-edit-ground-truth rule, and only per entry the user
   explicitly approved, following the guide's hand-editing rules (geometric
   matching, type + bbox; `deferred` never fails a sweep — it flips to CLOSED
   when detection later finds it). Commit as a data commit (`data: deferred
   misses from the 1:100 recall audit`) only after the user confirms the
   final set.
6. **Deliverable doc:** per-sheet recall table (visible vs detected vs
   deferred, by type), mechanism histogram, and a re-ranking note for the
   backlog (does the miss mass point at step-1's aspect gate, at
   curved walls, at something new?).

## Hard limits

- No detection code changes. No constant changes.
- NEVER run `tools/review.py` (it records verdicts on DETECTIONS; this task
  is about NON-detections and goes through hand-written deferred entries per
  the guide).
- Ground-truth edits ONLY as user-approved deferred entries per step 5 —
  never touch confirmed/false_positives lists, never re-review existing
  verdicts, never touch fixture bytes or `MANIFEST.json`.
- No PDFs committed; crops of NDA sheets stay in gitignored/output locations,
  never committed; no address-bearing text in the committed doc.
- `.venv/bin/python`; fixtures verified first (`tools/fetch_fixtures.py`).
- Docs/data commits on a new branch; imperative subjects; never a
  Co-Authored-By trailer.

## Acceptance

1. The per-sheet audit checklist was produced and the user verdicted it
   personally (the session stops and waits — an unreviewed checklist is an
   incomplete task, not a judgment call to make solo).
2. User-approved deferred entries committed as a data commit; the next sweep
   still exits with no NEW failures (deferred entries never fail a sweep).
3. The deliverable doc exists with the recall table + mechanism histogram +
   backlog re-ranking note, and findings §6's misses-audit entry is updated
   to DONE with a pointer.
