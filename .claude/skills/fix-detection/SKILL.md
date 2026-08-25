---
name: fix-detection
description: Fix a detection issue in this repo's architectural-PDF extraction algorithm — a false positive (cabinets/fixtures/paving detected as walls, phantom rooms, phantom doors or windows) or a miss (a real door, window, room, label or schedule not detected) on a corpus sheet (s01…s20) or any PDF. Use this skill whenever the user says "we are incorrectly detecting X", "false positive", "phantom", "not detecting", "missed door/window/room", "refine the algorithm", "reduce false positives", names a fixture slug like s03, or attaches a screenshot of an overlay/review PNG — even if they don't say "fix". It enforces the repo's regression-testing discipline, the generic-fix rule, and the checkpoints the user expects.
---

# fix-detection

The user hands you a symptom on one sheet. Your job is to turn it into a
**generic drawing-convention rule**, prove it on the corpus, and stop at the
checkpoints the user expects. The repo already has a regression corpus, review
tooling and long-form tuning guides; this skill is the order of operations
that ties them together so nothing is skipped.

Read `references/file-map.md` first — it lists every guide, tool, constant
home and test helper by detection type, so you don't have to rediscover them.

## What "generic" means here (the rule that overrides all others)

The corpus is 20 sheets from many CAD tools. A fix that keys on anything
specific to one sheet — a pen width value, a colour, a coordinate, an entity
id, a layer name, a text string — is not a fix, it is a ground-truth edit in
disguise. Every rule in `detection/` is stated as a **drawing convention**
("a striped field pitched at wall spacing five deep is a surface pattern,
never five walls") backed by **measured margins between the false class and
the true class on at least two sheets** ("hatch pitches 4.05/4.07px on both
reference sheets, the tightest real striped field is 11.4px"). Match that:

- Ask "what does a draughtsperson *do differently* when drawing a cabinet
  versus a wall?" — then find that difference in the primitives.
- Before choosing a constant, measure the same feature on the true class
  (real walls/doors) on the target sheet AND on s01/s02. If the margin is
  thin (< ~1.5×), the discriminator is wrong, not the threshold.
- A constant lives next to its detector with a comment stating the measured
  numbers and which sheets they came from (read a few `WALL_*` /
  `DOOR_*` comments for the house style).

Read the CLAUDE.md "Room detection" paragraph and the relevant tuning guide
before diagnosing — most fixture classes (paving, hatch, tile grids, stairs,
counters, wardrobes, pillows, radiators, leader arrows) already have a rule,
and the correct fix is often that an existing rule has a gap, not a new rule.

## What counts as a win

The user judges a fix by the **before|after pictures of the target sheet**
and by the **net phantom count**, not by whether the named entity vanished.
Removing one phantom room and uncovering two new ones (a worktop, a sink
bowl) is a trade, and they will say "not great". Uncovering happens
constantly here: a bug that mis-grouped faces was also, by accident,
suppressing fixture outlines drawn in the wall pen, and fixing the bug lets
those outlines fence again. That is expected — but it is *your* job to see
it, count it, say which rule should catch the uncovered ones, and lead the
report with the net number. Never present "target gone, +N REVIEW rooms"
as a success.

## Workflow

Create a todo per phase. Phases 5 and 7 are hard stops.

### 1. Intake — extract the brief

From the prompt and any screenshot, pin down: slug/PDF, page, entity type
(door / window / room / wall-as-barrier / label / schedule), and symptom
(false positive vs miss). A screenshot of an overlay shows coloured bboxes or
room polygons; note roughly where on the page the problem sits and what the
surrounding drawing is (kitchen, stair, bay, terrace…).

Do **not** ask for page/entity ids yet — you can locate them yourself in
phase 3. Ask now only if the sheet or the symptom itself is ambiguous.

### 2. Orient — read before touching code

In this order, and actually read them (they encode a year of shipped bugs):

1. `docs/regression-testing-guide.md` — §9 (ground-truth rules), §10 (the
   loop), §12 (invariants), §13 (gotchas).
2. The tuning material for the entity type (see file-map): doors → the door
   guide incl. §8 debug playbook; windows → the window guide; rooms/walls →
   the CLAUDE.md "Room detection" paragraph + `detection/walls.py` /
   `detection/rooms.py` module docstrings.
3. `graphify query "<your question>"` to orient in the code (CLAUDE.md
   requires this before grepping when `graphify-out/` exists).
4. `git log --oneline -15` — recent fixes often touched the same rule.

### 3. Baseline and locate

```bash
source .venv/bin/activate
git checkout -b fix/<slug>-<short-symptom>      # never work on main
python tools/regress.py --sheet sNN              # must be green before you change anything
python tools/compare_sweeps.py sNN --snapshot    # so phase 6 can show before|after pictures
```

Never `git stash` — the stash list is shared by every worktree of this
repo, and parallel agents have popped each other's work. To test "does the
bug reproduce without my change", save the diff (`git diff > /tmp/x.diff`)
and `git checkout -- <file>` / `git apply` it back.

Open `outputs/regress/sNN/<ts>/pages/page_NN/overlay.png` and
`review_<type>.png`, match them to the screenshot, and name the entity ids
(`room_0004`, `d7`) you believe are the problem. Then **confirm with the
user in one message** — "I read the screenshot as room_0004 and the wall
band at ~(x, y); correct?" — and continue once confirmed. Guessing wrong
here wastes a whole sweep cycle.

If the target sheet is not green at baseline, report that first: the red
sweep is the user's work queue and they decide what is in scope.

### 4. Diagnose — measure, don't guess

Find which **stage** produces the wrong output before proposing anything:

- Doors: `python app.py extract <pdf> --no-gemini --debug --disable-windows`
  and follow the door guide §8 (`debug_trace.json` → components / swings /
  candidates / rejected).
- Walls/rooms: there is no per-face trace. Write a scratch script (in the
  scratchpad dir, never in the repo) that loads `primitives.json`, calls
  `detect_wall_network` / `detect_rooms` directly and prints the faces,
  pairs, segments and solids around the problem area — pen widths, spacing,
  fill flags, what each face paired with and why it qualified.
- Windows: same pattern against `detect_windows`, plus `candidates.json`
  evidence blocks.

Then answer, with numbers:

1. What rule/tier admitted the false entity (or rejected the real one)?
2. What is the drawing-convention difference between it and the true class?
3. What does that feature measure on the true class, on this sheet and on
   s01/s02? (This is the generic-fix test — do it now, not after coding.)
4. Which existing rule is closest, and is this a gap in it or a new tier?

Never present estimates as measurements. If you didn't run it, say so.

### 5. Fix — test first, then code, then prose

1. Write a synthetic unit test that reproduces the topology (helpers in
   the file-map: `wall_band_h`, `rect_room`, `door_candidate`, …). Coordinates
   in tests must be ≥4px apart on each axis (snap-key collisions, door guide
   §7). Run it: it must **fail** for the right reason.
2. Implement the rule. Constants go in the detector's constants home with the
   measured rationale in the comment.
3. Confirm the test passes, then **prove it bites**: revert the code, watch it
   fail, restore (regression guide §13).
4. `python -m unittest discover tests` — the fast tier stays green and must
   never touch the real pipeline or a PDF.
5. Update the prose: the tuning guide section (or the CLAUDE.md room
   paragraph for walls/rooms) gets the rule, the measured numbers and the
   sheet they came from, in the existing style. Future agents read the prose,
   not the diff.

One fix per iteration. If you discover a second, unrelated cause, note it for
the report; do not bundle it — bundled REVIEW deltas are unattributable.

### 6. Sweep — target, references, then corpus

```bash
python tools/regress.py --sheet sNN --sheet s01 --sheet s02   # fast signal first
python tools/regress.py                                       # full corpus (~3 min)
python tools/compare_sweeps.py sNN                            # before|after images
```

Sweep the unmodified tree first if the target sheet was red at baseline, so
you can diff report-to-report rather than reason about it.

Read the whole report, not just the exit code. Classify every changed line:
lost `confirmed` (regression, must fix or revert), returned `false_positive`
(regression), new REVIEW entries, `deferred` that CLOSED (a win pending the
user's confirmation).

Then do the part the exit code cannot: open `page_NN_changes.png` and
`review_room.png` and **look at every entity that appeared, vanished or
changed shape on the target sheet**, and write your own verdict for each
(`r22` — worktop outline, phantom; `r25` — sink bowl, phantom; `r7` — real
en-suite, now correctly split). Compute the net phantom delta from those
verdicts. If the net is not clearly positive, the iteration is not a win
yet: identify which rule *should* have caught the uncovered ones and put that
in the report as the proposed next iteration — do not implement it.

A `confirmed` room that merged or split because of your change is a LOST
line even when you believe the old verdict is stale (stairs-are-furniture
merges do this). Report it as a regression with your argument attached;
the user decides, and only `tools/review.py` or their hand edit retires it.

### 7. CHECKPOINT — report and stop

Write the report in `references/report-template.md`'s format and **stop**.
The before|after PNGs from `compare_sweeps.py` (plus a tight crop of the
target area if the sheet is large) are part of the deliverable, not an
optional extra — a report without pictures cannot be reviewed ("not sure
what I am reviewing here").
Do not start a second fix-and-sweep cycle, do not commit, until the user
answers. The user has been burned by autonomous iteration loops; one fix +
one sweep + a decision is the cadence they want.

Things you never do, at any phase, without an explicit go for that specific
entry:

- Edit `tests/ground_truth/*.json` or the `labeled` flag in
  `fixtures/MANIFEST.json` — verdicts are the user's, recorded through
  `tools/review.py`, and you cannot invent one.
- Propose downgrading, deferring or suppressing a failing sweep signal to
  keep a baseline green.
- Commit a PDF, or any address-bearing text (planning-portal ids).
- Commit to `main`, or add a `Co-Authored-By` / AI-attribution trailer.

### 8. After the go-ahead

Iterate (back to phase 4 with the new evidence) or finalise: commit on the
topic branch — code and prose in one commit, no attribution trailer — then
`graphify update .`. New REVIEW detections the user wants recorded go through
`python tools/review.py sNN` as a *separate data commit* the user makes or
explicitly asks for.

## Misses (increasing correct detections)

Ground truth only records verdicts on things the pipeline emitted, so a miss
never fails the sweep. A fixed miss shows up as a **new REVIEW line**; the
user confirms it via `tools/review.py`, which is what turns it into a
`confirmed` entry that future sweeps protect. Say this in the report so the
user knows the win is not yet pinned. For a door miss, the door guide §8.3
is the exact tracing order; for a room miss, find which barrier leaked
(the polygon merged with a neighbour) or which filter dropped the component
(`_free_space_components` filters: area, border contact, hole fraction,
wall-contact ratio, major-mass attachment).
