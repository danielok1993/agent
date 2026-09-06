"""Per sheet/page from the latest sweep run: how the scale resolved, what drives the gates, and the plausibility verdict."""
import json, glob, os, sys
ROOT = "/Users/danielszweda/Documents/GitHub/UD/agent/outputs/regress"
slugs = sys.argv[1:] or sorted(os.listdir(ROOT))
for slug in slugs:
    runs = sorted(glob.glob(f"{ROOT}/{slug}/*/"))
    if not runs: print(slug, "no run"); continue
    run = runs[-1]
    summ = json.load(open(run + "summary.json"))
    for pg in summ.get("pages", []):
        sc = pg.get("scales") or {}
        det = sc.get("detection") or {}
        regs = {rid: (v["source"], v["denominator"], v["nominal"]) for rid, v in (sc.get("by_region") or {}).items()}
        ps = sc.get("page_scale")
        pss = None if ps is None else (ps["source"], ps["denominator"], ps["nominal"])
        pn = pg.get("page_number")
        tk = f"{run}pages/page_{pn:02d}/takeoff.json"
        plaus = None; verified = None
        if os.path.exists(tk):
            t = json.load(open(tk))
            s = t.get("scale") or {}
            plaus = s.get("plausibility"); verified = s.get("verified")
        codes = sorted({w["warning_code"] for w in (pg.get("warnings") or []) if "SCALE" in w["warning_code"]})
        print(f"{slug} p{pn}: det factor={det.get('factor')} denom={det.get('denominator')} src={det.get('source')} | regions={regs} | page_scale={pss} | verified={verified} plaus={plaus} | {codes}")
