#!/usr/bin/env python3
"""Generate the split documents from the section map.

The prose is SLICED out of CLAUDE.md, never retyped. Re-runnable: it
rewrites each target document from scratch every time -- which is exactly why
it REFUSES to overwrite a create-mode document whose CONTENT differs, in ANY
way, from what the map rebuilds (see `check_divergence`). Pass `--force` to
rebuild anyway; it prints what it discards.
"""
import collections, json, pathlib, re, subprocess, sys, textwrap

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
MAP = HERE / "2026-09-09-claude-md-split-map.json"


def load_source(spec):
    """Read CLAUDE.md at the map's PINNED ref, never the working tree.

    LOAD-BEARING: the cut task shortens the source lines. A generator reading the
    working tree would slice pointers or empty offsets on any later re-run,
    so the committed generator would not be reproducible.
    """
    out = subprocess.run(
        ["git", "show", f"{spec['source_ref']}:{spec['source_file']}"],
        cwd=REPO, capture_output=True, text=True, check=True)
    return out.stdout.split("\n")


def upsert(path, heading, body, after=None):
    """Append-mode: replace this heading's section in an existing document,
    insert it after the `after` heading, or append it if neither applies.

    `after` is LOAD-BEARING for discoverability: a section appended past the
    end of a long document is content nothing routes to. F1 belongs inside the
    findings document's §4 sequence, which is where every pointer aims.

    Idempotent -- the generator is re-run by several tasks, and a
    non-idempotent upsert accumulated a trailing newline per run. Verified in
    all three positions: section last, section followed by another heading, and
    inserted mid-document after an anchor.
    """
    f = REPO / path
    text = f.read_text(encoding="utf-8")
    marker = f"\n## {heading}\n"
    block = f"## {heading}\n\n{body.rstrip()}\n"
    if marker in text:                       # already present: replace in place
        i = text.index(marker)
        j = text.find("\n## ", i + len(marker))
        tail = text[j:] if j > 0 else ""
        text = text[:i] + marker + "\n" + body.rstrip() + "\n" + tail
    elif after is not None:                  # insert after the anchor heading
        a = text.index(f"\n## {after}\n")
        j = text.find("\n## ", a + 1)
        text = (text.rstrip() + "\n\n" + block) if j < 0 else \
               (text[:j + 1] + block + "\n" + text[j + 1:])
    else:
        text = text.rstrip() + "\n\n" + block
    f.write_text(text, encoding="utf-8")


# --- `replace` token guard (mirrored in the verifier; the two files stay
# independent by construction, so the check is written out twice) -------------
_NUM = re.compile(r"\d+(?:[.,]\d+)*")
_TICK = re.compile(r"`[^`]*`")


def _tokens(text):
    """The numbers and backticked tokens of a string, as a multiset."""
    return (collections.Counter(_NUM.findall(text))
            + collections.Counter(_TICK.findall(text)))


def _strip_refs(text, doc_paths):
    """Remove the ROUTING REFERENCES a repoint is allowed to add: a target
    document's backticked path, with the section clause and step number that
    belong to it. What is left is the prose the repoint must not have touched.
    """
    if not doc_paths:
        return text
    ref = (r"`(?:" + "|".join(re.escape(p) for p in sorted(doc_paths)) + r")`"
           r'(?:\s*\u00a7"[^"]*")?(?:,\s*step\s+\d+)?')
    return re.sub(ref, "", text)


def check_replace_tokens(old, new, doc_paths):
    """A `replace` may only REPOINT a reference -- never restate a measurement.

    The verifier's `invert` restores new->old before CONTENT compares, so ANY
    consistent (map, document) pair passes the character proofs: a `replace`
    recording "0.65" -> "0.95" ships a falsified constant in the document and
    still verifies (measured by the reviewer -- VERIFIED, exit 0). The other
    three ops are structurally constrained (append_period adds one ".",
    capitalize_first changes one letter's case, drop_leading_word is inverted
    from the map's own `word`); `replace` is free text on both sides, so it
    carries trust the map did not have before, and needs its own guard.

    The guard: `old` and `new` must carry IDENTICAL MULTISETS of numbers and
    backticked tokens, once the routing reference the repoint exists to add is
    stripped out of `new`. A repoint may therefore only ADD a target document's
    path, its section clause and a step number -- never drop, alter or invent a
    measurement, constant name, identifier, path or sheet slug in the prose
    around it.

    Stripping is what makes equality achievable: two of the nine shipped
    references carry digits of their own (W1's §"Iteration 1-3 summary, moved
    from CLAUDE.md (2026-09-09)", step 6; the ninth op's §"4g. The
    detection-scale factor (moved from CLAUDE.md, 2026-09-09)"), and every one
    adds a backticked `docs/...md` path. Measured against all nine: each
    passes, and 0.65 -> 0.95 -- the reviewer's demonstrated hole -- fails.
    """
    o = _tokens(old)
    n = _tokens(_strip_refs(new, doc_paths))
    if o != n:
        raise AssertionError(
            "replace changes the moved prose's numbers/backticked tokens: "
            f"dropped {dict(o - n)}, added {dict(n - o)} "
            "(outside the routing reference)")


def apply_repairs(text, repairs, doc_paths):
    for r in repairs:
        op = r["op"]
        if op == "drop_leading_word":
            w = r["word"]
            assert text.startswith(w + " "), f"{w!r} not leading: {text[:60]!r}"
            text = text[len(w) + 1:]
        elif op == "capitalize_first":
            text = text[0].upper() + text[1:]
        elif op == "append_period":
            assert not text.rstrip().endswith("."), \
                f"append_period on a span that already ends with a period: {text[-40:]!r}"
            text = text.rstrip() + "."
        elif op == "replace":
            # Repoint a directional reference the MOVE ITSELF falsified ("the
            # gates paragraph below" now lives in another file). Never a number,
            # constant, path, identifier, sheet slug or measurement -- only the
            # directional wording, and only where the move broke it. `old` must
            # occur EXACTLY ONCE in the span: an ambiguous match would make the
            # verifier's inversion non-deterministic.
            o, n = r["old"], r["new"]
            check_replace_tokens(o, n, doc_paths)
            c = text.count(o)
            assert c == 1, f"replace: {o!r} occurs {c} times in the span, need 1"
            text = text.replace(o, n)
        else:
            raise SystemExit(f"unknown repair op {op!r}")
    return text


def headings_of(text):
    """The '## ' headings of a document's text, in order."""
    return [ln[3:].strip() for ln in text.split("\n") if ln.startswith("## ")]


def _excerpt(line, width=64):
    """One differing line, safely quoted, for the refusal message."""
    if line is None:
        return "(end of file)"
    line = line.strip()
    return repr(line if len(line) <= width else line[:width] + "…")


def characterise(on_disk, would_write):
    """How the document on disk diverges from the rebuild, most useful first.

    Unmapped `## ` headings by NAME when there are any -- that is the
    actionable message, and it names the operator's fix (add the section to the
    map). Otherwise the first differing LINE with both sides, which is what
    catches every other shape of hand-edit: prose added under an existing
    heading, a `### ` sub-heading, trailing unheaded prose, a reworded
    sentence.
    """
    mapped = set(headings_of(would_write))
    unmapped = [h for h in headings_of(on_disk) if h not in mapped]
    if unmapped:
        return unmapped, [f"§{h} — not in the map, would be DESTROYED"
                          for h in unmapped]
    a, b = on_disk.split("\n"), would_write.split("\n")
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else None
        y = b[i] if i < len(b) else None
        if x != y:
            return [], [f"line {i + 1} differs:",
                        f"        on disk: {_excerpt(x)}",
                        f"        rebuild: {_excerpt(y)}"]
    return [], []          # identical: never reached, the caller filters first


def check_divergence(built, force):
    """Refuse to overwrite a create-mode document that DIFFERS from the rebuild.

    LOAD-BEARING, and the reason is the whole point of this branch. A
    create-mode document is rebuilt from the pinned source on every run and
    written with `write_text`, so anything the map does not describe is
    destroyed -- silently, since the run prints the same "wrote ... N sections"
    line either way. Meanwhile `.claude/skills/fix-detection/SKILL.md` tells
    every future agent that "a NEW rule gets its OWN `##` heading in the
    document for its stage; an EXTENSION to an existing rule goes under that
    rule's heading", and the verifier's proofs (COVERAGE, CONTENT, RETAINED,
    REACHABILITY) all read the map as their oracle and ignore anything outside
    it -- so the hand-edit verifies green, then vanishes on the next re-run
    with no signal anywhere. Reproduced by the reviewer both ways: append a
    `## ` section, and add prose under an existing heading; verify (exit 0),
    generate, edit gone.

    The check is on CONTENT, not on headings: the would-be output is built in
    memory and compared to the file byte for byte, so it covers BOTH clauses of
    the skill's instruction and every other hand-edit besides -- a `### `
    sub-heading, trailing unheaded prose, a reworded sentence, a re-flowed
    paragraph. A heading comparison saw only the first clause (measured: the
    three other shapes were silently overwritten at exit 0), and content
    subsumes it, so there is ONE mechanism here, not two; `characterise` keeps
    the heading-specific wording for the case where headings ARE the
    divergence.

    A re-runnable generator plus an instruction to hand-edit its outputs is a
    data-loss trap; this guard is what reconciles them. The operator's two
    ways out are both explicit: fold the edit into the map so the proofs cover
    it, or re-run with `--force`, which prints what it discards.

    Append-mode targets are exempt and never reach here: `upsert` edits one
    heading in place and leaves the rest of an existing document untouched by
    construction.
    """
    diverged = []
    for path in sorted(built):
        f = REPO / path
        if not f.exists() or f.read_text(encoding="utf-8") == built[path]:
            continue
        diverged.append((path,) + characterise(f.read_text(encoding="utf-8"),
                                               built[path]))
    if not diverged:
        return
    if force:
        for path, unmapped, desc in diverged:
            if unmapped:
                print(f"--force: DISCARDING {len(unmapped)} unmapped "
                      f"section(s) from {path}:")
                for h in unmapped:
                    print(f"    discarding §{h}")
            else:
                print(f"--force: DISCARDING on-disk edits to {path}:")
                for line in desc:
                    print(f"    {line}")
        return
    print("REFUSING TO WRITE: create-mode document(s) have diverged from the "
          "section map.", file=sys.stderr)
    for path, _unmapped, desc in diverged:
        for line in desc:
            print(f"    {path} {line}" if not line.startswith(" ")
                  else f"    {line}", file=sys.stderr)
    print("\nA rebuild would overwrite these edits and print nothing.\n"
          "Either fold each edit into the section map, so the verifier's "
          "proofs cover it:\n"
          f"    {MAP.relative_to(REPO)}\n"
          "or re-run with --force to rebuild from the map and discard them.",
          file=sys.stderr)
    raise SystemExit(2)


def render_create_doc(meta, secs):
    """The exact bytes a create-mode rebuild would write for one document.

    Split out of `main` so the guard can compare the rebuild to the file
    WITHOUT writing it -- the content check has to see the output it is about
    to produce, and there must be exactly one renderer producing it.
    """
    out = [f"# {meta['title']}", "", wrap(meta["preamble"]).rstrip(), ""]
    for heading, body, _ in secs:
        out += [f"## {heading}", "", wrap(body).rstrip(), ""]
    return "\n".join(out).rstrip() + "\n"


def wrap(text):
    """Re-flow one long line into 79-column paragraphs. Whitespace only.

    break_on_hyphens=False is LOAD-BEARING: the default splits
    "already-slanted" across lines, and re-joining inserts a space that was
    never in the source. Caught by the verifier during plan validation.
    break_long_words=False keeps long paths and identifiers intact.
    """
    return "\n".join(textwrap.wrap(" ".join(text.split()), width=79,
                                   break_on_hyphens=False,
                                   break_long_words=False)) + "\n"


def main():
    spec = json.loads(MAP.read_text(encoding="utf-8"))
    lines = load_source(spec)

    bydoc = {}
    for sec in spec["sections"]:
        if sec["doc"] is None:
            continue
        parts = [lines[ln - 1][a:b] for ln, a, b in sec["spans"]]
        body = apply_repairs(" ".join(parts).strip(), sec["repairs"],
                             spec["docs"])
        bydoc.setdefault(sec["doc"], []).append(
            (sec["heading"], body, sec.get("insert_after")))

    built = {path: render_create_doc(spec["docs"][path], secs)
             for path, secs in bydoc.items()
             if spec["docs"][path].get("mode", "create") != "append"}

    # Before ANY write: a diverged create-mode target aborts the whole run, so
    # a refusal never leaves half the documents rebuilt.
    check_divergence(built, "--force" in sys.argv[1:])

    for path, secs in bydoc.items():
        meta = spec["docs"][path]
        if meta.get("mode", "create") == "append":
            for heading, body, after in secs:
                upsert(path, heading, wrap(body).rstrip(), after)
            print(f"upserted {path}: {len(secs)} section(s)")
            continue
        (REPO / path).write_text(built[path], encoding="utf-8")
        print(f"wrote {path}: {len(secs)} sections")


if __name__ == "__main__":
    main()
