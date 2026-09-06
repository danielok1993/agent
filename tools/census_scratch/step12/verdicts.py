"""Section-wise verdict extraction from regress.py reports: the final summary block."""
import sys, re, glob, collections
def sections(path):
    lines = open(path).read().splitlines()
    # the final summary starts at the LAST line that matches '^s\d\d  ' preceded by a Done block; simpler: take all lines after the last 'Pages:' line
    idx = max((i for i, l in enumerate(lines) if l.strip().startswith("Pages:")), default=-1)
    out = collections.OrderedDict()
    cur = None
    for l in lines[idx + 1:]:
        m = re.match(r"^(s\d\d)\b", l)
        if m:
            cur = m.group(1); out[cur] = {"summary": l.strip(), "lost": [], "fp": [], "review": [], "other": []}
        elif cur and l.strip():
            s = l.strip()
            if "LOST" in s: out[cur]["lost"].append(s)
            elif "FALSE POSITIVE RETURNED" in s: out[cur]["fp"].append(s)
            elif s.startswith("REVIEW") or "REVIEW" in s: out[cur]["review"].append(s)
            elif s.startswith("exit="): pass
            else: out[cur]["other"].append(s)
    return out
if __name__ == "__main__":
    tot = collections.Counter()
    for p in sys.argv[1:]:
        for slug, d in sections(p).items():
            print(f"{d['summary']}   lost={len(d['lost'])} fp={len(d['fp'])} review={len(d['review'])}")
            for k in ("lost", "review"):
                for s in d[k]: print("     ", s)
            for s in d["other"]: print("      other:", s)
            tot["lost"] += len(d["lost"]); tot["fp"] += len(d["fp"]); tot["review"] += len(d["review"])
    print("TOTAL", dict(tot))
