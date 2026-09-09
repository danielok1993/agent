#!/usr/bin/env python3
"""Generate the split documents from the section map.

The prose is SLICED out of CLAUDE.md, never retyped. Re-runnable: it
rewrites each target document from scratch every time.
"""
import json, pathlib, re, subprocess, sys, textwrap

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


def apply_repairs(text, repairs):
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
        else:
            raise SystemExit(f"unknown repair op {op!r}")
    return text


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
        body = apply_repairs(" ".join(parts).strip(), sec["repairs"])
        bydoc.setdefault(sec["doc"], []).append(
            (sec["heading"], body, sec.get("insert_after")))

    for path, secs in bydoc.items():
        meta = spec["docs"][path]
        if meta.get("mode", "create") == "append":
            for heading, body, after in secs:
                upsert(path, heading, wrap(body).rstrip(), after)
            print(f"upserted {path}: {len(secs)} section(s)")
            continue
        out = [f"# {meta['title']}", "", wrap(meta["preamble"]).rstrip(), ""]
        for heading, body, _ in secs:
            out += [f"## {heading}", "", wrap(body).rstrip(), ""]
        (REPO / path).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
        print(f"wrote {path}: {len(secs)} sections")


if __name__ == "__main__":
    main()
