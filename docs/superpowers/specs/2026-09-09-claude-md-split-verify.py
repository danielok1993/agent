#!/usr/bin/env python3
"""Prove the split lost nothing.

Reads ONLY (a) CLAUDE.md at the map's source_ref, via git, and (b) the
written documents. Never imports the generator.

Two independent proofs:
  COVERAGE  every character of each touched source line belongs to exactly
            one span -- no gap, no overlap, no duplication.
  CONTENT   each written section, with its repairs inverted and whitespace
            normalised, is byte-identical to its source span; and its
            non-whitespace character count matches exactly.

Plus two positional checks that the character proofs cannot make:
  RETAINED     the fragments that stay in CLAUDE.md are still on one line, in
               order, at the right end of it.
  REACHABILITY every target document is still cited BY PATH in the working-tree
               CLAUDE.md -- surviving content nothing routes to is lost content.
"""
import json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
MAP = HERE / "2026-09-09-claude-md-split-map.json"

ok = True


def fail(msg):
    global ok
    ok = False
    print("FAIL: " + msg)


def norm(s):
    return " ".join(s.split())


def invert(text, repairs, src):
    for r in reversed(repairs):
        op = r["op"]
        if op == "append_period":
            if not text.endswith("."):
                fail(f"append_period recorded but no trailing '.': {text[-40:]!r}")
                return text
            text = text[:-1]
        elif op == "capitalize_first":
            text = text[0].lower() + text[1:]
        elif op == "drop_leading_word":
            text = r["word"] + " " + text
        elif op == "replace":
            # Inverse of the generator's `replace`. The NEW text must occur
            # exactly once, or the document does not carry the repair the map
            # claims: an unrecorded replace leaves `new` absent and the
            # inversion returns text that no longer matches the source, so
            # CONTENT fails either way (measured with a bogus entry).
            c = text.count(r["new"])
            if c != 1:
                fail(f"replace recorded but {r['new']!r} occurs {c} times, need 1")
                return text
            text = text.replace(r["new"], r["old"])
    return text


def sections_of(path):
    """Split a generated doc into {heading: body} on '## ' headings.

    A target document that does not exist yet is a proof failure, not a
    crash: Tasks 1 and 2 deliberately run the verifier before the documents
    exist, and an uncaught traceback would abort before COVERAGE and
    RETAINED finish printing.
    """
    try:
        text = (REPO / path).read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"{path}: does not exist")
        return {}
    out, heading, buf = {}, None, []
    for line in text.split("\n"):
        if line.startswith("## "):
            if heading is not None:
                out[heading] = "\n".join(buf).strip()
            heading, buf = line[3:].strip(), []
        elif heading is not None:
            buf.append(line)
    if heading is not None:
        out[heading] = "\n".join(buf).strip()
    return out


def main():
    spec = json.loads(MAP.read_text(encoding="utf-8"))
    src = subprocess.run(
        ["git", "show", f"{spec['source_ref']}:{spec['source_file']}"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    lines = src.split("\n")

    # ---- COVERAGE ----
    spans = {}
    for sec in spec["sections"]:
        for ln, a, b in sec["spans"]:
            spans.setdefault(ln, []).append((a, b, sec["id"]))
    for ln in sorted(spans):
        got = sorted(spans[ln])
        n = len(lines[ln - 1])
        cursor = 0
        line_ok = True
        for a, b, sid in got:
            if a != cursor:
                fail(f"line {ln}: {'gap' if a > cursor else 'overlap'} at {cursor}..{a} (before {sid})")
                line_ok = False
            cursor = b
        if cursor != n:
            fail(f"line {ln}: covered {cursor} of {n} chars")
            line_ok = False
        if line_ok:
            print(f"COVERAGE line {ln}: {n} chars, {len(got)} spans, exact")

    # ---- CONTENT ----
    cache = {}
    for sec in spec["sections"]:
        if sec["doc"] is None:
            continue
        cache.setdefault(sec["doc"], sections_of(sec["doc"]))
        written = cache[sec["doc"]].get(sec["heading"])
        if written is None:
            fail(f"{sec['id']}: heading {sec['heading']!r} not in {sec['doc']}")
            continue
        expect = norm(" ".join(lines[ln - 1][a:b] for ln, a, b in sec["spans"]))
        actual = norm(invert(norm(written), sec["repairs"], expect))
        if actual != expect:
            i = next((k for k in range(min(len(actual), len(expect)))
                      if actual[k] != expect[k]), min(len(actual), len(expect)))
            fail(f"{sec['id']}: diverges at {i}\n"
                 f"    expected: {expect[max(0,i-60):i+60]!r}\n"
                 f"    actual  : {actual[max(0,i-60):i+60]!r}")
            continue
        se = len(re.sub(r"\s", "", expect))
        sa = len(re.sub(r"\s", "", actual))
        if se != sa:
            fail(f"{sec['id']}: non-whitespace count {sa} != {se}")
        else:
            print(f"CONTENT  {sec['id']:<5} {sec['doc']:<34} {se} chars exact")

    # ---- RETAINED ----
    # Characters that stay in CLAUDE.md get COVERAGE but no CONTENT proof, so
    # they are checked here BY POSITION, never by global substring search: the
    # line-245 tail is just "Detection", which occurs twice in the file, so
    # `frag in text` passes even when the line-245 occurrence is deleted
    # (measured). A retained span touching offset 0 must be its line's PREFIX,
    # one touching the line end must be its SUFFIX, and all of a line's
    # fragments must appear in order on ONE line, which must be unique.
    cur_lines = (REPO / spec["source_file"]).read_text(encoding="utf-8").split("\n")
    retained = {}
    for sec in spec["sections"]:
        if sec["doc"] is not None:
            continue
        for ln, a, b in sec["spans"]:
            if lines[ln - 1][a:b].strip():
                retained.setdefault(ln, []).append((a, b, lines[ln - 1][a:b], sec["id"]))

    for ln, frags in sorted(retained.items()):
        frags.sort()
        need_prefix = frags[0][0] == 0
        need_suffix = frags[-1][1] == len(lines[ln - 1])
        hits = []
        for cl in cur_lines:
            pos, okline = 0, True
            for _, _, frag, _ in frags:
                i = cl.find(frag, pos)
                if i < 0:
                    okline = False
                    break
                pos = i + len(frag)
            if not okline:
                continue
            if need_prefix and not cl.startswith(frags[0][2]):
                continue
            if need_suffix and not cl.endswith(frags[-1][2]):
                continue
            hits.append(cl)
        ids = ",".join(f[3] for f in frags)
        if len(hits) == 1:
            print(f"RETAINED line {ln}: {len(frags)} fragment(s) [{ids}] anchored in order "
                  f"on one line (prefix={need_prefix}, suffix={need_suffix})")
        else:
            fail(f"line {ln}: retained fragments [{ids}] matched {len(hits)} lines, need "
                 f"exactly 1 (prefix={need_prefix}, suffix={need_suffix}) — a fragment was "
                 f"deleted, reordered, or moved off its line")

    # ---- REACHABILITY ----
    # COVERAGE + CONTENT + RETAINED prove the characters SURVIVE; none of them
    # proves they are still REACHABLE. Lines 197/199/201 have no retained
    # fragment, so blanking CLAUDE.md's pointer to a document leaves every
    # proof above green while 126,362 characters sit on disk with nothing in
    # the auto-loaded file routing to them -- measured: VERIFIED, exit 0.
    # That is this split's actual failure mode, so every target document's
    # path must appear in the WORKING-TREE CLAUDE.md.
    claude = "\n".join(cur_lines)
    for path in sorted(spec["docs"]):
        if path in claude:
            print(f"REACHABLE {path}: cited in {spec['source_file']}")
        else:
            fail(f"{path}: no reference in the working-tree {spec['source_file']} — "
                 f"the content survives but nothing auto-loaded routes to it")

    print()
    print("VERIFIED: every character accounted for exactly once." if ok else "VERIFICATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
