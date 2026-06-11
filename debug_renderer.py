"""Generate a self-contained HTML debug viewer for door detection traces."""
from __future__ import annotations
import base64
import json
import struct
from pathlib import Path


def generate_debug_viewer(
    render_png_path: str,
    debug_trace_path: str,
    output_html_path: str,
) -> None:
    """Write a single-file HTML viewer embedding the render image and trace JSON."""
    render_bytes = Path(render_png_path).read_bytes()
    img_b64 = base64.b64encode(render_bytes).decode("ascii")
    # PNG IHDR chunk: bytes 16-20 = width, 20-24 = height
    img_w = struct.unpack(">I", render_bytes[16:20])[0]
    img_h = struct.unpack(">I", render_bytes[20:24])[0]

    trace = json.loads(Path(debug_trace_path).read_text(encoding="utf-8"))
    trace_json = json.dumps(trace, separators=(",", ":"))

    html = _HTML_TEMPLATE
    html = html.replace("__PAGE_NUMBER__", str(trace.get("page_number", "?")))
    html = html.replace("__IMG_W__", str(img_w))
    html = html.replace("__IMG_H__", str(img_h))
    html = html.replace("__IMG_B64__", img_b64)
    html = html.replace("__TRACE_JSON__", trace_json)

    Path(output_html_path).write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML / CSS / JS template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Debug Viewer — Page __PAGE_NUMBER__</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{display:flex;height:100vh;font-family:"SF Mono",Consolas,monospace;font-size:12px;background:#111;color:#ccc;overflow:hidden}
#viewer-panel{flex:0 0 70%;display:flex;flex-direction:column;overflow:hidden}
#toolbar{display:flex;align-items:center;gap:6px;padding:6px 8px;background:#1a1a1a;border-bottom:1px solid #333;flex-shrink:0}
#toolbar button{padding:3px 10px;background:#2a2a2a;color:#ccc;border:1px solid #444;cursor:pointer;border-radius:3px}
#toolbar button:hover{background:#383838}
#zoom-info{color:#666;font-size:11px;min-width:40px}
#legend{display:flex;gap:8px;flex-wrap:wrap;margin-left:8px}
.leg{display:flex;align-items:center;gap:3px;font-size:10px;color:#888}
.leg-dot{width:10px;height:10px;border-radius:2px;flex-shrink:0}
#scroll-area{flex:1;overflow:hidden;position:relative;cursor:crosshair}
#canvas-wrap{position:absolute;transform-origin:top left}
#base-canvas{display:block}
#overlay-canvas{position:absolute;top:0;left:0;pointer-events:none}
#hit-canvas{position:absolute;top:0;left:0;opacity:0}
#sidebar{flex:0 0 30%;overflow-y:auto;background:#1a1a1a;border-left:1px solid #333;padding:10px}
#hint{color:#555;font-size:11px;padding:8px 0}
.sec{margin-bottom:10px}
.sec-title{color:#666;text-transform:uppercase;font-size:9px;letter-spacing:1px;margin-bottom:3px;padding-bottom:2px;border-bottom:1px solid #2a2a2a}
.kv{display:flex;justify-content:space-between;padding:1px 0;gap:8px}
.k{color:#666;flex-shrink:0}
.v{text-align:right;word-break:break-all;color:#ccc}
.pass{color:#5cb85c}
.fail{color:#d9534f}
.warn{color:#f0ad4e}
.null{color:#444;font-style:italic}
.badge{padding:1px 5px;border-radius:2px;font-size:9px;font-weight:bold}
.b-gold{background:#3d3000;color:#FFD700}
.b-orange{background:#3d1500;color:#FFA500}
.b-blue{background:#0d2040;color:#4A90E2}
.b-green{background:#0d2a0d;color:#5CB85C}
.b-gray{background:#2a2a2a;color:#888}
.attempt{margin:3px 0;padding:4px 6px;background:#222;border-radius:2px}
.attempt.paired{border-left:2px solid #5cb85c}
.attempt.rejected{border-left:2px solid #555}
</style>
</head>
<body>
<div id="viewer-panel">
  <div id="toolbar">
    <button onclick="adj(1.25)">+</button>
    <button onclick="adj(0.8)">−</button>
    <button onclick="reset()">Reset</button>
    <span id="zoom-info">100%</span>
    <div id="legend">
      <span class="leg"><span class="leg-dot" style="background:#FFD700"></span>door assembly</span>
      <span class="leg"><span class="leg-dot" style="background:#FFA500"></span>fallback cand.</span>
      <span class="leg"><span class="leg-dot" style="background:#4A90E2"></span>polyline arc</span>
      <span class="leg"><span class="leg-dot" style="background:#5CB85C"></span>linework leaf</span>
      <span class="leg"><span class="leg-dot" style="background:#C87D7D"></span>eval'd / failed</span>
      <span class="leg"><span class="leg-dot" style="background:#444"></span>untouched</span>
    </div>
  </div>
  <div id="scroll-area">
    <div id="canvas-wrap">
      <canvas id="base-canvas"></canvas>
      <canvas id="overlay-canvas"></canvas>
    </div>
  </div>
</div>
<div id="sidebar">
  <p id="hint">Click a primitive to inspect it.</p>
  <div id="info"></div>
</div>
<script>
const TRACE = __TRACE_JSON__;
const IMG_B64 = "__IMG_B64__";
const IMG_W = __IMG_W__;
const IMG_H = __IMG_H__;

// Lookup tables
const bySwing = {}, byLeaf = {}, byPoly = {}, byLW = {}, byCand = {};
TRACE.swings.forEach(s => bySwing[s.swing_id] = s);
TRACE.leaves.forEach(l => byLeaf[l.leaf_id] = l);
TRACE.polyline_components.forEach(c => byPoly[c.component_id] = c);
TRACE.linework_components.forEach(c => byLW[c.component_id] = c);
TRACE.candidates.forEach(c => byCand[c.candidate_id] = c);

// Fate colours
const FATES = [
  'untouched','poly_eval','lw_eval','arc_eval','leaf_eval',
  'poly_rejected','lw_rejected',
  'poly_collected','lw_collected',
  'arc_passed','leaf_passed',
  'leaf_fallback','arc_fallback','assembly'
];
const STYLE = {
  assembly:      {fill:'rgba(255,215,0,0.25)',  stroke:'#FFD700', lw:2.5},
  arc_fallback:  {fill:'rgba(255,165,0,0.2)',   stroke:'#FFA500', lw:2},
  leaf_fallback: {fill:'rgba(255,179,71,0.2)',  stroke:'#FFB347', lw:2},
  poly_collected:{fill:'rgba(74,144,226,0.15)', stroke:'#4A90E2', lw:1.5},
  lw_collected:  {fill:'rgba(92,184,92,0.15)',  stroke:'#5CB85C', lw:1.5},
  arc_passed:    {fill:'rgba(74,144,226,0.1)',  stroke:'#4A90E2', lw:1},
  leaf_passed:   {fill:'rgba(92,184,92,0.1)',   stroke:'#5CB85C', lw:1},
  poly_rejected: {fill:'rgba(100,149,237,0.06)',stroke:'#6495ED', lw:0.5},
  lw_rejected:   {fill:'rgba(144,238,144,0.06)',stroke:'#90EE90', lw:0.5},
  arc_eval:      {fill:'rgba(200,100,100,0.08)',stroke:'#C87D7D', lw:0.5},
  leaf_eval:     {fill:'rgba(200,100,100,0.08)',stroke:'#C87D7D', lw:0.5},
  poly_eval:     {fill:'rgba(200,200,80,0.05)', stroke:'#C8C850', lw:0.3},
  lw_eval:       {fill:'rgba(80,80,80,0.03)',   stroke:'#555',    lw:0.3},
  untouched:     {fill:'rgba(60,60,60,0.04)',   stroke:'#444',    lw:0.3},
};

function fate(e) {
  if (e.candidate_id) {
    const c = byCand[e.candidate_id];
    if (c) {
      if (c.method==='door_assembly') return 'assembly';
      if (c.method==='arc_fallback')  return 'arc_fallback';
      if (c.method==='leaf_fallback') return 'leaf_fallback';
    }
  }
  if (e.polyline_component_id) {
    const co = byPoly[e.polyline_component_id];
    if (co) return co.result==='collected' ? 'poly_collected' : 'poly_rejected';
  }
  if (e.linework_component_id) {
    const co = byLW[e.linework_component_id];
    if (co) return co.result==='collected' ? 'lw_collected' : 'lw_rejected';
  }
  if (e.arc_filter  && e.arc_filter.passed)   return 'arc_passed';
  if (e.leaf_filter && e.leaf_filter.passed)  return 'leaf_passed';
  if (e.arc_filter  && e.arc_filter.evaluated) return 'arc_eval';
  if (e.leaf_filter && e.leaf_filter.evaluated) return 'leaf_eval';
  if (e.polyline_eval && e.polyline_eval.evaluated) return 'poly_eval';
  return 'untouched';
}

// Canvas setup
const base = document.getElementById('base-canvas');
const over = document.getElementById('overlay-canvas');
const bc = base.getContext('2d');
const oc = over.getContext('2d');
base.width = over.width = IMG_W;
base.height = over.height = IMG_H;

const img = new Image();
img.onload = () => { bc.drawImage(img,0,0); drawAll(); };
img.src = 'data:image/png;base64,' + IMG_B64;

// Sort entries by fate order (draw important last = on top)
const entries = Object.values(TRACE.by_path_index);
const byFate = {};
FATES.forEach(f => byFate[f] = []);
entries.forEach(e => { const f=fate(e); (byFate[f]||byFate['untouched']).push(e); });

function drawAll(highlightIdx) {
  oc.clearRect(0,0,IMG_W,IMG_H);
  FATES.forEach(f => {
    const st = STYLE[f] || STYLE.untouched;
    oc.fillStyle = st.fill;
    oc.strokeStyle = st.stroke;
    oc.lineWidth = st.lw;
    byFate[f].forEach(e => drawEntry(e, st));
  });
  if (highlightIdx !== undefined) {
    const e = TRACE.by_path_index[highlightIdx];
    if (e) {
      const [x0,y0,x1,y1] = e.bbox;
      oc.strokeStyle = '#FF00AA';
      oc.lineWidth = 3;
      oc.strokeRect(x0-3, y0-3, (x1-x0)+6, (y1-y0)+6);
    }
  }
}

function drawEntry(e, st) {
  const [x0,y0,x1,y1] = e.bbox;
  const w = Math.max(x1-x0, 1), h = Math.max(y1-y0, 1);
  oc.beginPath();
  if (e.item_type === 'l') {
    // Expand thin lines so they're clickable
    oc.rect(x0-1, y0-1, w+2, h+2);
  } else {
    oc.rect(x0, y0, w, h);
  }
  oc.fill(); oc.stroke();
}

// Zoom / pan
let scale=1, ox=0, oy=0;
let drag=false, dsx=0, dsy=0, dox=0, doy=0;
const wrap = document.getElementById('canvas-wrap');
const scroll = document.getElementById('scroll-area');

function applyXform() {
  wrap.style.transform = `translate(${ox}px,${oy}px) scale(${scale})`;
  document.getElementById('zoom-info').textContent = Math.round(scale*100)+'%';
}
function adj(f) { scale=Math.max(0.1,Math.min(20,scale*f)); applyXform(); }
function reset() { scale=1; ox=oy=0; applyXform(); }

scroll.addEventListener('wheel', e => {
  e.preventDefault();
  const rect = scroll.getBoundingClientRect();
  const mx = e.clientX - rect.left - ox;
  const my = e.clientY - rect.top  - oy;
  const f = e.deltaY < 0 ? 1.15 : 0.87;
  const ns = Math.max(0.1, Math.min(20, scale*f));
  ox += mx*(scale-ns); oy += my*(scale-ns);
  scale = ns; applyXform();
}, {passive:false});

scroll.addEventListener('mousedown', e => {
  if (e.button!==0) return;
  drag=true; dsx=e.clientX; dsy=e.clientY; dox=ox; doy=oy;
});
window.addEventListener('mousemove', e => {
  if (!drag) return;
  ox=dox+(e.clientX-dsx); oy=doy+(e.clientY-dsy); applyXform();
});
window.addEventListener('mouseup', () => drag=false);

// Click → inspect
let moved=false;
scroll.addEventListener('mousedown', ()=>moved=false);
scroll.addEventListener('mousemove', ()=>moved=true);
scroll.addEventListener('click', e => {
  if (moved) return;
  const rect = base.getBoundingClientRect();
  const cx = (e.clientX - rect.left) / scale;
  const cy = (e.clientY - rect.top)  / scale;
  let best=null, bestArea=Infinity;
  for (const [pi, en] of Object.entries(TRACE.by_path_index)) {
    const [x0,y0,x1,y1] = en.bbox;
    const pad = en.item_type==='l' ? 3 : 1;
    if (cx>=x0-pad && cx<=x1+pad && cy>=y0-pad && cy<=y1+pad) {
      const area = Math.max((x1-x0)*(y1-y0), 4);
      if (area < bestArea) { bestArea=area; best=en; }
    }
  }
  if (best) { drawAll(best.path_index); showInfo(best); }
});

// ---------- Sidebar ----------
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function kv(k, v, cls) {
  const vc = (v===null||v===undefined)
    ? '<span class="null">null</span>'
    : `<span class="v ${cls||''}">${esc(v)}</span>`;
  return `<div class="kv"><span class="k">${esc(k)}</span>${vc}</div>`;
}
function checkRow(name, ch) {
  if (!ch) return kv(name, 'not reached', 'null');
  const cls = ch.passed ? 'pass' : 'fail';
  const mark = ch.passed ? '✓' : '✗';
  let bound = '';
  if (ch.range)    bound = ` [${ch.range[0]}–${ch.range[1]}]`;
  else if (ch.min!==undefined) bound = ` ≥${ch.min}`;
  else if (ch.max!==undefined) bound = ` ≤${ch.max}`;
  else if (ch.required!==undefined) bound = ` = ${JSON.stringify(ch.required)}`;
  const actual = ch.actual!==undefined ? ch.actual : (ch.value!==undefined ? ch.value : ch.overlaps);
  return kv(name, `${mark} ${actual}${bound}`, cls);
}
function badge(f) {
  const MAP = {
    assembly:['b-gold','DOOR ASSEMBLY'], arc_fallback:['b-orange','ARC FALLBACK'],
    leaf_fallback:['b-orange','LEAF FALLBACK'], poly_collected:['b-blue','POLYLINE ARC'],
    lw_collected:['b-green','LW LEAF'], poly_rejected:['b-gray','POLY REJECTED'],
    lw_rejected:['b-gray','LW REJECTED'], arc_passed:['b-blue','ARC PASSED'],
    leaf_passed:['b-green','LEAF PASSED'], arc_eval:['b-gray','ARC FAILED'],
    leaf_eval:['b-gray','LEAF FAILED'], poly_eval:['b-gray','POLY SEG'],
    untouched:['b-gray','UNTOUCHED'],
  };
  const [c,l] = MAP[f] || ['b-gray', f.toUpperCase()];
  return `<span class="badge ${c}">${l}</span>`;
}
function sec(title, content) {
  return `<div class="sec"><div class="sec-title">${title}</div>${content}</div>`;
}

function showInfo(e) {
  document.getElementById('hint').style.display='none';
  const f = fate(e);
  let html = '';

  // Primitive
  html += sec(`Primitive ${badge(f)}`,
    kv('path_index', e.path_index) +
    kv('item_type',  e.item_type) +
    kv('bbox', e.bbox.map(v=>v.toFixed(1)).join(', ')) +
    kv('layer',       e.layer) +
    kv('stroke_width',e.stroke_width) +
    kv('color', e.color ? 'rgb('+e.color.map(v=>(v*255).toFixed(0)).join(',')+')' : null)
  );

  // Arc filter
  if (e.arc_filter) {
    let body = '';
    if (!e.arc_filter.evaluated) {
      body += kv('evaluated', 'no — '+e.arc_filter.fail_reason, 'null');
    } else {
      const r = e.arc_filter.passed ? 'PASS' : 'FAIL — '+(e.arc_filter.fail_reason||'');
      body += kv('result', r, e.arc_filter.passed?'pass':'fail');
      if (e.arc_filter.checks)
        Object.entries(e.arc_filter.checks).forEach(([k,v]) => body += checkRow(k,v));
    }
    html += sec('Arc Filter', body);
  }

  // Polyline eval
  if (e.polyline_eval) {
    const pe = e.polyline_eval;
    let body = kv('length_px', pe.length_px!==undefined ? pe.length_px.toFixed(2) : null) +
               kv('range', pe.length_range.join(' – ')) +
               kv('length_ok', pe.passed_length_filter ? 'yes':'no — '+pe.fail_reason,
                               pe.passed_length_filter?'pass':'fail');
    if (pe.polyline_component_id) {
      body += kv('component_id', pe.polyline_component_id);
      const co = byPoly[pe.polyline_component_id];
      if (co) {
        body += kv('result', co.result, co.result==='collected'?'pass':'fail');
        if (co.fail_reason) body += kv('fail_reason', co.fail_reason, 'fail');
        if (co.checks) Object.entries(co.checks).forEach(([k,v]) => body += checkRow(k,v));
      }
    }
    html += sec('Polyline Segment', body);
  }

  // Leaf filter
  if (e.leaf_filter) {
    let body = '';
    if (!e.leaf_filter.evaluated) {
      body += kv('evaluated', 'no — '+e.leaf_filter.fail_reason, 'null');
    } else {
      const r = e.leaf_filter.passed ? 'PASS' : 'FAIL — '+(e.leaf_filter.fail_reason||'');
      body += kv('result', r, e.leaf_filter.passed?'pass':'fail');
      if (e.leaf_filter.checks)
        Object.entries(e.leaf_filter.checks).forEach(([k,v]) => body += checkRow(k,v));
    }
    html += sec('Leaf Filter', body);
  }

  // Linework component
  if (e.linework_component_id) {
    const co = byLW[e.linework_component_id];
    if (co) {
      let body = kv('component_id', co.component_id) +
                 kv('segments', co.path_indices.length) +
                 kv('result', co.result, co.result==='collected'?'pass':'fail');
      if (co.path_used)   body += kv('path_used', co.path_used);
      if (co.fail_reason) body += kv('fail_reason', co.fail_reason, 'fail');
      if (co.clean_loop_result) {
        const cl = co.clean_loop_result;
        body += kv('clean_loop', cl.passed?'passed':'failed — '+cl.fail_reason, cl.passed?'pass':'fail');
      }
      if (co.subgraph_result && co.subgraph_result.tried) {
        const sg = co.subgraph_result;
        body += kv('subgraph', sg.passed?'passed':'failed — '+sg.fail_reason, sg.passed?'pass':'fail');
      }
      html += sec('Linework Component', body);
    }
  }

  // Swing
  if (e.swing_id) {
    const s = bySwing[e.swing_id];
    if (s) {
      let body = kv('swing_id', s.swing_id) +
                 kv('source', s.source) +
                 kv('radius_px', s.radius_px!==null ? s.radius_px.toFixed(1) : null) +
                 kv('sweep_deg', s.sweep_est_deg!==null ? s.sweep_est_deg.toFixed(1) : null) +
                 kv('layer_hint', s.layer_hint?'yes':'no', s.layer_hint?'pass':'');
      if (s.hu_eval) {
        body += '<div class="sec-title" style="margin-top:5px">Hu Moments</div>';
        const hu = s.hu_eval;
        body += kv('distance', hu.distance!==null ? hu.distance.toFixed(4) : null) +
                kv('result', hu.result, hu.result==='verified'?'pass':hu.result==='far'?'fail':'warn') +
                kv('boost', (hu.boost_applied>=0?'+':'')+hu.boost_applied);
      }
      if (s.pairing_attempts && s.pairing_attempts.length) {
        body += `<div class="sec-title" style="margin-top:5px">Pairing Attempts (${s.pairing_attempts.length})</div>`;
        s.pairing_attempts.forEach(a => {
          body += `<div class="attempt ${a.result}">` +
            kv(a.leaf_id, a.result, a.result==='paired'?'pass':'fail') +
            kv('dist_px', a.distance_px.toFixed(1)+' / '+a.distance_bound) +
            kv('radius_ratio', a.radius_ratio.toFixed(3)+' / '+a.radius_ratio_bound) +
            (a.fail_reason ? kv('reason', a.fail_reason, 'fail') : '') +
            '</div>';
        });
      } else {
        body += kv('pairing_attempts', 'none — all leaves outside 15 px', 'fail');
      }
      html += sec('Swing', body);
    }
  }

  // Leaf
  if (e.leaf_id) {
    const l = byLeaf[e.leaf_id];
    if (l) {
      html += sec('Leaf',
        kv('leaf_id', l.leaf_id) +
        kv('source', l.source) +
        kv('length_px', l.length_px!==null ? l.length_px.toFixed(1) : null) +
        kv('width_px', l.width_px!==null ? l.width_px.toFixed(1) : null) +
        kv('aspect_ratio', l.aspect_ratio!==null ? l.aspect_ratio.toFixed(2) : null) +
        kv('layer_hint', l.layer_hint?'yes':'no', l.layer_hint?'pass':'')
      );
    }
  }

  // Candidate
  if (e.candidate_id) {
    const c = byCand[e.candidate_id];
    if (c) {
      let body = kv('candidate_id', c.candidate_id) +
                 kv('method', c.method) +
                 kv('confidence', c.confidence!==undefined ? c.confidence.toFixed(3) : null);
      if (c.confidence_breakdown) {
        body += '<div class="sec-title" style="margin-top:5px">Confidence Breakdown</div>';
        const bd = c.confidence_breakdown;
        body += kv('base', bd.base);
        if (bd.label_boost)     body += kv('+ label',     bd.label_boost + (bd.label_found?' ('+bd.label_found+')':''));
        if (bd.layer_boost)     body += kv('+ layer',     bd.layer_boost);
        if (bd.threshold_boost) body += kv('+ threshold', bd.threshold_boost);
        if (bd.opening_boost)   body += kv('+ opening',   bd.opening_boost);
        if (bd.opening_penalty) body += kv('− obstructed',bd.opening_penalty);
        if (bd.hu_boost)        body += kv('+ hu_match',  bd.hu_boost);
        if (bd.hu_penalty)      body += kv('− hu_far',    bd.hu_penalty);
        if (bd.total_before_cap!==undefined) body += kv('before_cap', bd.total_before_cap.toFixed?bd.total_before_cap.toFixed(3):bd.total_before_cap);
        body += kv('total', bd.total!==undefined ? bd.total.toFixed(3) : null);
      }
      html += sec('Candidate', body);
    }
  }

  document.getElementById('info').innerHTML = html;
}
</script>
</body>
</html>"""
