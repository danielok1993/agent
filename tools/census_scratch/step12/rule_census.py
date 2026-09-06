"""The rule AS IMPLEMENTED on every corpus sheet: per floor-plan region, the
claim, the strings matched inside it, the measured scale, the gate choice;
then detection_scale with and without the dimensions."""
import sys, json
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent")
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools")
import fitz
from _corpus_page import sheet_pdf
from extraction.extractor import extract_page
from pipeline import resolve_page_regions
from scale.dimensions import page_dimensions, measured_denominator, DIM_MIN_MATCHES
from scale.factor import detection_scale, _gate_choice, _effective_denominator
from scale.resolver import resolve_page_scales
from scale.store import load_stored
from scale.viewport import viewport_scales

slugs = sys.argv[1:] or [f"s{i:02d}" for i in range(1, 21)]
for slug in slugs:
    pdf = sheet_pdf(slug)
    doc = fitz.open(pdf)
    for pno in range(doc.page_count):
        page_data = extract_page(doc, pno)
        rr = resolve_page_regions(pdf_path=pdf, page=doc[pno], page_data=page_data,
                                  gemini_client=None, skip_gemini=True,
                                  refresh_regions=False, crop_dir=None)
        if rr.skip_detection:
            print(f"{slug} p{pno+1}: skip_detection"); continue
        ps = resolve_page_scales(page_data=page_data, regions=rr.regions,
                                 viewports=viewport_scales(doc, doc[pno]),
                                 stored=load_stored(pdf, pno + 1), fallback=None,
                                 pdf_path=pdf, crop_fn=None, allow_prompt=False,
                                 suspend_display=None)
        dims = page_dimensions(page_data)
        fps = {r.region_id: r for r in rr.regions if r.region_type == "floor_plan"}
        rows = []
        for rid, info in ps.by_region.items():
            reg = fps.get(rid)
            if reg is None: continue
            inside = [m for m in dims if m.line and
                      reg.bbox[0] <= (m.line[0][0]+m.line[1][0])/2 <= reg.bbox[2] and
                      reg.bbox[1] <= (m.line[0][1]+m.line[1][1])/2 <= reg.bbox[3]]
            meas = measured_denominator(dims, reg.bbox)
            denom, how = _gate_choice(info, meas)
            rows.append(f"{rid}: claim {info.source} {_effective_denominator(info)} | strings inside {len(inside)} -> measured {None if meas is None else round(meas,2)} | gate {denom} ({how})")
        before = detection_scale(ps, rr.regions, pno + 1)
        after = detection_scale(ps, rr.regions, pno + 1, dimensions=dims)
        print(f"{slug} p{pno+1}: page strings {len(dims)} (measured page {None if after.measured is None else round(after.measured,2)})")
        for r in rows: print("    " + r)
        print(f"    before: f={before.factor:.4f} {before.source} {before.denominator} {[w['warning_code'] for w in before.warnings]}")
        print(f"    after : f={after.factor:.4f} {after.source} {after.denominator} {[w['warning_code'] for w in after.warnings]}")
        if abs(after.factor - before.factor) > 1e-9: print("    *** FACTOR CHANGED ***")
