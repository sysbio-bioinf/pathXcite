"""Generates an interactive HTML comparison of two ORA TSV files"""

# --- Standard Library Imports ---
import base64
import csv
import json
import os
import re
from pathlib import Path

# --- Private Functions ---
from app.utils import resource_path

# --- Constants ---
HEADER = [
    "Term", "Overlap", "P-value", "Odds Ratio", "Z-Score",
    "Combined Score", "Adjusted P-value", "Genes"
]

_OVERLAP_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
_SCI_FLOAT_RE = re.compile(
    r"""^[+-]?
        (?:\d+(?:\.\d*)?|\.\d+)        # 123 or 123. or .123 or 123.456
        (?:[eE][+-]?\d+)? 
        $""",
    re.X,
)
# permissive but disallows blanks/whitespace
_GENE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_INF_RE = re.compile(r"^[+-]?inf$", re.I)  # matches inf, -inf, +INF, etc.


# --- Public Functions ---
def create_comparison_html(tsv_a_path: str, tsv_b_path: str, label_a: str,
                           label_b: str, library: str) -> str:
    """
    Return a complete HTML string that visualizes and compares two ORA TSVs.
    The TSV contents are embedded into the HTML and loaded automatically.

    Args:
        tsv_a_path: Path to TSV for condition A
        tsv_b_path: Path to TSV for condition B
        label_a: Label to display for A
        label_b: Label to display for B
        library: Library name to display (e.g., "GO:BP")

    Returns:
        HTML content as a string.
    """
    # Read TSVs and escape for safe embedding in JS (as proper JS string literals)
    tsv_a_text = Path(tsv_a_path).read_text(encoding="utf-8")
    tsv_b_text = Path(tsv_b_path).read_text(encoding="utf-8")

    # Use json.dumps to produce safe JS strings (handles quotes, newlines, etc.)
    TSV_A_JS = json.dumps(tsv_a_text)
    TSV_B_JS = json.dumps(tsv_b_text)
    LABEL_A_JS = json.dumps(label_a)
    LABEL_B_JS = json.dumps(label_b)
    LIB_JS = json.dumps(library)

    colors = {
        "bg": "#ffffff",
        "fg": "#0b2830",
        "muted": "#5f7a82",
        "border": "#e6eff3",
        "pill": "#eaf7f8",
        "pillHi": "#dbf1f3",
        "pillText": "#0b6e6a",
        "stroke": "#7ccfd1",
        "strokeHi": "#4fb3b8",
        "up": "rgba(16,140,136,0.70)",
        "dn": "rgba(12,110,140,0.65)",
        "neu": "rgba(100,116,139,0.35)",
        "primary": "#0b6e6a",
        "primaryHi": "#0a5f5c",
        "primaryLo": "#0c7e79",
        "focus": " rgba(75, 150, 155, .35)",
        "r": "10px",
        "r2": "14px",
        "s3": "10px",
        "s4": "11px",
        "s5": "12px",
        "s6": "13px",
        "s7": "14px",
        "s8": "16px",
        "s9": "18px",
        "shadow1": "0 6px 18px rgba(0,0,0,.06)",
        "shadow2": "0 14px 34px rgba(0,0,0,.12)"
    }

    icons_folder_path = resource_path("assets/icons")

    icons_paths = {
        "plot": {
            "base": f"{icons_folder_path}/compare_plot_inactive.svg",
            "hover": f"{icons_folder_path}/compare_plot_hover.svg",
            "active": f"{icons_folder_path}/compare_plot_active.svg"
        },
        "table": {
            "base": f"{icons_folder_path}/compare_table_inactive.svg",
            "hover": f"{icons_folder_path}/compare_table_hover.svg",
            "active": f"{icons_folder_path}/compare_table_active.svg"
        },
        "apply": {
            "base": f"{icons_folder_path}/reload_light_inactive.svg",
            "hover": f"{icons_folder_path}/reload_light_hover.svg",
            "active": f"{icons_folder_path}/reload_light_active.svg"
        },
        "close": {
            "base": f"{icons_folder_path}/close_inactive.svg",
            "hover": f"{icons_folder_path}/close_hover.svg",
            "active": f"{icons_folder_path}/close_active.svg"
        },
        "sliders": {
            "base": f"{icons_folder_path}/sliders_inactive.svg",
            "hover": f"{icons_folder_path}/sliders_hover.svg",
            "active": f"{icons_folder_path}/sliders_active.svg"
        }
    }

    # Build a JS-ready dict with data URIs instead of file paths
    icons_data = {
        key: {
            "base": _svg_data_uri(val["base"]),
            "hover": _svg_data_uri(val["hover"]),
            "active": _svg_data_uri(val["active"]),
        }
        for key, val in icons_paths.items()
    }
    icons_data_json = json.dumps(icons_data)

    colors_style_string = "".join(
        [f"    --{k}:{v};" for k, v in colors.items()])
    html = """<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>ORA Term Comparison (TSV-only)</title>

    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">

    <!-- DataTables -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/datatables.net-dt@1.13.8/css/jquery.dataTables.min.css">
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/datatables.net@1.13.8/js/jquery.dataTables.min.js"></script>

    <!-- Papa Parse -->
    <script src="https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js"></script>

    <style>
    :root{"""+colors_style_string+"""
    }

    *{box-sizing:border-box}
    html,body{height:100%}
    body{
    margin:0;background:var(--bg);color:var(--fg);
    font-family:"Inter",system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
    font-size:var(--s7); line-height:1.45;
    -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
    padding:24px
    }

    h1,h2,h3,h4{margin:0 0 6px;font-weight:700;letter-spacing:-.01em}
    h1{font-size:22px} h2{font-size:20px}
    h3{font-size:var(--s8); color:var(--muted)}
    h4{font-size:var(--s8)}
    .sub{color:var(--muted);margin-bottom:12px}
    .small{font-size:var(--s4);color:var(--muted)}

    .container{max-width:1200px;margin-inline:auto}

    /* shells */
    .panel,.bar,.controls,.loader{
    background:#fff;border:1px solid var(--border);border-radius:var(--r2);
    padding:14px;box-shadow:var(--shadow1);margin-bottom:14px
    }
    .loader,.controls,.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center}

    /* inputs + buttons */
    label.inline{display:inline-flex;align-items:center;gap:8px;color:var(--muted);white-space:nowrap}

    input[type="text"],input[type="number"],select{
    border:1px solid var(--border);border-radius:var(--r);
    padding:8px 12px;background:#fff;font:inherit;min-width:160px;
    transition:border-color .15s ease, box-shadow .15s ease, background .15s ease;
    outline:none
    }
    input[type="text"]:focus,input[type="number"]:focus,select:focus{
    border-color:var(--strokeHi); box-shadow:0 0 0 3px var(--focus)
    }

    /* file input — looks like our button without HTML changes */
    input[type="file"]{
    font:inherit; border:1px dashed var(--border);
    padding:6px 8px; border-radius:var(--r); min-width:220px; color:var(--muted);
    background:#fff; transition:border-color .15s ease, box-shadow .15s ease
    }
    input[type="file"]:focus{border-color:var(--strokeHi); box-shadow:0 0 0 3px var(--focus)}
    /* style the inner button */
    input[type="file"]::file-selector-button{
    border:1px solid var(--primary); border-radius:8px; padding:8px 12px; margin-right:10px;
    background:var(--primary); color:#fff; cursor:pointer; font:inherit;
    transition:transform .06s ease, filter .15s ease, background .15s ease
    }
    input[type="file"]::file-selector-button:hover{filter:brightness(1.06)}
    input[type="file"]::file-selector-button:active{transform:translateY(1px)}
    /* Safari/old WebKit */
    input[type="file"]::-webkit-file-upload-button{
    border:1px solid var(--primary); border-radius:8px; padding:8px 12px; margin-right:10px;
    background:var(--primary); color:#fff; cursor:pointer; font:inherit
    }

    .btn{
    border:1px solid var(--border); border-radius:10px; padding:8px 12px;
    background:#fff; cursor:pointer; font:inherit; line-height:1; user-select:none;
    display:inline-flex; align-items:center; gap:8px; height:36px;
    transition:transform .06s ease, box-shadow .15s ease, background .15s ease, border-color .15s ease
    }
    .btn:hover{background:#f7fbfb}
    .btn:active{transform:translateY(1px)}
    .btn:focus-visible{outline:none; box-shadow:0 0 0 3px var(--focus)}
    .btn.primary{
    background:var(--primary); color:#fff; border-color:var(--primary)
    }
    .btn.primary:hover{background:var(--primaryLo)}
    .btn.primary:active{filter:brightness(.98)}

    .warn{color:#b45309}

    /* drop area (kept compact + modern) */
    .drop{
    flex:1 1 280px;min-height:84px;border:2px dashed var(--border);border-radius:12px;
    display:grid;place-items:center;text-align:center;color:var(--muted);
    transition:border-color .15s ease, background .15s ease
    }
    .drop[data-active="true"]{border-color:var(--strokeHi);background:var(--pill)}

    /* nav tabs */
    .nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}
    .nav .btn{height:34px;padding:6px 10px}
    .nav .btn.active{background:var(--primary);color:#fff;border-color:var(--primary)}
    .nav .btn:not(.active):hover{border-color:var(--stroke)}

    .badge{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--muted)}
    .badge .dot{width:10px;height:10px;border-radius:50%;display:inline-block}
    .dot-up{background:var(--up)} .dot-dn{background:var(--dn)} .dot-neu{background:var(--neu)}

    /* KPI cards */
    .cards{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:12px;width:100%}
    .card,.card2{
    border:1px solid var(--border);border-radius:12px;padding:12px;background:#fff;box-shadow:var(--shadow1);
    grid-column:span 3; min-width:0
    }
    .card2{grid-column:span 4}
    .card h3{margin:0 0 6px;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.06em}
    .card .num{font-weight:700; font-size:var(--s8)}
    .spark{height:36px}

    /* responsive grid */
    @media (max-width:960px){ .cards{grid-template-columns:repeat(6,1fr)} .card,.card2{grid-column:span 3} }
    @media (max-width:640px){ .cards{grid-template-columns:repeat(2,1fr)} .card,.card2{grid-column:span 2} }

    /* plot + svg */
    #wrap{position:relative;min-height:420px}
    svg{display:block;width:100%;height:100%}
    .title{font-size:11px;fill:var(--muted);text-anchor:middle}
    .rankBadge{font-size:11px;font-weight:700;fill:var(--pillText);dominant-baseline:middle}
    .link{stroke:var(--neu);stroke-width:2;fill:none}
    .pillText{display:flex;align-items:center;height:100%;font-size:11px;font-weight:600;color:var(--pillText)}

    /* controls */
    .controls label.inline{gap:10px}
    .controls input[type="number"]{width:88px}
    .controls input[type="checkbox"]{accent-color:var(--primary)}
    .controls select{min-width:180px}

    /* range inputs */
    input[type="range"]{
    -webkit-appearance:none; width:180px; height:28px; background:transparent
    }
    input[type="range"]::-webkit-slider-runnable-track{
    height:4px; background:linear-gradient(90deg,var(--stroke),var(--strokeHi));
    border-radius:999px
    }
    input[type="range"]::-webkit-slider-thumb{
    -webkit-appearance:none; margin-top:-6px; width:16px; height:16px; border-radius:50%;
    background:#fff; border:2px solid var(--strokeHi); box-shadow:0 1px 2px rgba(0,0,0,.08)
    }
    input[type="range"]::-moz-range-track{
    height:4px; background:linear-gradient(90deg,var(--stroke),var(--strokeHi)); border-radius:999px
    }
    input[type="range"]::-moz-range-thumb{
    width:16px; height:16px; border-radius:50%; background:#fff; border:2px solid var(--strokeHi)
    }

    /* table view */
    .table-panel{font-size:11px}
    .table-panel table.dataTable tbody tr:hover{background:rgba(148,163,184,.12)}
    .table-panel th, .table-panel td{vertical-align:middle}

    /* tooltip */
    .tooltip{
    position:fixed; pointer-events:none; z-index:10; background:#05343a; color:#fff; border-radius:8px;
    padding:8px 10px; font-size:11px; display:none; box-shadow:var(--shadow2); max-width:560px
    }

    /* modal */
    .modal{position:fixed; inset:0; display:none; align-items:center; justify-content:center; background:rgba(0,0,0,.4); padding:24px; z-index:100}
    .modal[open]{display:flex}
    .dialog{
    width:min(1000px,96vw); max-height:90vh; overflow:auto; background:#fff;
    border:1px solid var(--border); border-radius:12px; padding:16px; box-shadow:var(--shadow2)
    }
    .kv{display:grid;grid-template-columns:160px 1fr;gap:8px;font-size:11px}
    .kv b{color:var(--muted)}
    pre.genes{background:#f8fafc;border:1px solid var(--border);border-radius:8px;padding:10px;font-size:11px;max-height:220px;overflow:auto}

    /* focus-visible everywhere */
    :where(button, [type="button"], [type="submit"], [role="button"], a, input, select){
    outline:none
    }
    :where(button, [type="button"], [type="submit"], [role="button"], a, input, select):focus-visible{
    box-shadow:0 0 0 3px var(--focus)
    }

    /* subtle transitions for panels */
    .panel,.bar,.controls,.loader{transition:box-shadow .2s ease, transform .06s ease}
    .panel:hover{box-shadow:var(--shadow2)}

    
    /* --- Compact toolbar and icon buttons --- */
.toolbar {
  display:flex; align-items:center; justify-content:space-between;
  padding:6px 8px; border:1px solid var(--border); border-radius:var(--r2);
  background:#fff; position:sticky; top:0; z-index:20; gap:8px; box-shadow:var(--shadow1);
}
.tool-left { display:flex; align-items:center; gap:6px; }
.tool-right.legend .badge { opacity:.85; margin-left:6px; }

.iconbtn {
  --size:34px;
  width:var(--size); height:var(--size);
  border:0; background:transparent; border-radius:8px; padding:0;
  display:inline-grid; place-items:center; cursor:pointer;
}
.iconbtn:hover { background:rgba(0,0,0,.05); }
.iconbtn:active { transform: translateY(1px); }
.iconbtn.primary { background:var(--primary); }
.iconbtn.primary:hover { filter:brightness(0.97); }
/*.iconbtn.primary img { filter: invert(1) brightness(1.1); }*/ 
.iconbtn.ghost { opacity:.8; }
.iconbtn.active { outline:2px solid var(--primary); }

/* Ensure the <img> inside icon buttons fits */
.iconbtn > img { width:20px; height:20px; pointer-events:none; }

/* --- Popover shell --- */
.popover {
  position:absolute;
  top:calc(0%+150px);
  left:8px;
  z-index:100; 
  width:min(920px, calc(100vw - 24px));
  background:#fff;
  border:1px solid var(--border);
  box-shadow:var(--shadow2);
  border-radius:12px;
  padding:10px;
}


/* Popover header */
.popover-header { display:flex; align-items:center; justify-content:space-between; padding:4px 6px 8px; }

/* Condensed controls grid inside popover */
.controls-grid { display:grid; gap:10px; }
.controls-grid .row { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:10px; }
.controls-grid label { display:grid; gap:4px; font-size:12px; }
.controls-grid input[type="number"],
.controls-grid select { height:30px; padding:4px 8px; font-size:12px; }
.controls-grid input[type="range"] { width:100%; }
.controls-grid .check { align-items:center; grid-auto-flow:column; grid-auto-columns:max-content; }
.val { font-size:11px; opacity:.7; }

/* Mobile: popover becomes bottom sheet */
@media (max-width: 880px) {
  .popover { position:fixed; left:12px; right:12px; top:auto; bottom:12px; width:auto; }
  .controls-grid .row { grid-template-columns:1fr 1fr; }
}

/* Hide any legacy .controls section if still present (safety) */
section.controls { display:none !important; }


    /* dark mode */
    /*@media (prefers-color-scheme: dark){
    :root{
        --bg:#0b1417; --fg:#e9f1f3; --muted:#9fb3bb; --border:#203036;
        --pill:#0f2226; --pillHi:#143037; --pillText:#89e0de;
        --stroke:#2e7e83; --strokeHi:#43a2a7;
        --primary:#0fa29d; --primaryHi:#0d8d88; --primaryLo:#13b3ad;
        --shadow1:0 6px 18px rgba(0,0,0,.35); --shadow2:0 18px 36px rgba(0,0,0,.6);
        --focus: rgba(67,162,167,.35)
    }
    .panel,.bar,.controls,.loader,.card,.card2,.dialog{background:#0f1a1d}
    input,select,.btn{background:#0f1a1d;color:var(--fg);border-color:var(--border)}
    pre.genes{background:#0f1a1d}
    .table-panel table.dataTable tbody tr:hover{background:rgba(148,163,184,.12)}
    }*/
    </style>

    </head>
    <body class="container">
    <header>
        <h4>ORA Term Comparison</h4>
        <div class="sub" id="subtitle">Two independent over-representation analyses on the same library (TSV only)</div>
        <div class="small">Upload: results from Condition A and B. Each row = enriched term with metrics (AdjP, P, Odds, Z, Combined, and hit genes for the query). Explore how the top terms and ranks agree or differ across conditions.</div>
    </header>

    <!-- Loader (hidden; we auto-load from embedded TSV) -->
    <section class="loader" id="loader" style="display:none">
        <label class="inline">File A: <input id="fileA" type="file" accept=".tsv,.tab" /></label>
        <label class="inline">Label A: <input id="labelA" type="text" placeholder="e.g., Condition A"></label>
        <label class="inline">File B: <input id="fileB" type="file" accept=".tsv,.tab" /></label>
        <label class="inline">Label B: <input id="labelB" type="text" placeholder="e.g., Condition B"></label>
        <label class="inline">Library: <input id="libraryName" type="text" placeholder="e.g., GO:BP"></label>
        <button id="loadBtn" class="btn primary">Load</button>
        <span class="warn" id="loadMsg"></span>
    </section>

    <!-- Tabs + legend -->
    <!--<div class="nav" id="tabs" style="display:none;">
        <button id="btnPlot" class="btn active">Plot</button>
        <button id="btnTable" class="btn">Table</button>
        <span class="badge"><span class="dot dot-up"></span> Δmetric ≥ 0</span>
        <span class="badge"><span class="dot dot-dn"></span> Δmetric &lt; 0</span>
        <span class="badge"><span class="dot dot-neu"></span> metric NA</span>
    </div>-->

    <!-- Compact toolbar (icons + legend) -->
    <div class="toolbar" id="tabs" style="display:none;">
    <div class="tool-left">
        <button id="btnPlot"  class="iconbtn active" aria-pressed="true"  data-icon="plot"  aria-label="Plot"></button>
        <button id="btnTable" class="iconbtn"        aria-pressed="false" data-icon="table" aria-label="Table"></button>

        <!-- Apply stays accessible always -->
        <button id="applyBtn" class="iconbtn primary" data-icon="apply" aria-label="Apply"></button>

        <!-- Opens advanced controls popover -->
        <button id="btnControls" class="iconbtn ghost" data-icon="sliders" aria-haspopup="dialog"
                aria-controls="controlsPopover" aria-expanded="false" aria-label="Adjust layout & filters"></button>
    </div>

    <div class="tool-right small legend">
        <span class="badge"><span class="dot dot-up"></span> Δmetric ≥ 0</span>
        <span class="badge"><span class="dot dot-dn"></span> Δmetric &lt; 0</span>
        <span class="badge"><span class="dot dot-neu"></span> metric NA</span>
    </div>
    </div>


    <!-- Popover: advanced controls -->
<div id="controlsPopover" class="popover" role="dialog" aria-modal="false" aria-labelledby="controlsTitle" hidden>
  <div class="popover-header">
    <h4 id="controlsTitle">Layout &amp; Filters</h4>
    <button class="iconbtn ghost" id="closeControls" aria-label="Close" data-icon="close"></button>
  </div>

  <div class="controls-grid">
    <div class="row">
      <label>Top K
        <input id="ctrlTopN" type="number" min="1" value="30" inputmode="numeric">
      </label>
      <label>Rank metric
        <select id="ctrlMetric"></select>
      </label>
      <label>Direction
        <select id="ctrlDir">
          <option value="auto">Auto</option>
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </label>
    </div>

    <div class="row">
      <label class="check"><input id="ctrlWrap" type="checkbox" checked> Wrap inside pills</label>
      <label>Column gap
        <input id="ctrlGap" type="range" min="40" max="640" step="10" value="100">
        <span id="gapVal" class="val"></span>
      </label>
      <label>Pill width
        <input id="ctrlPillW" type="range" min="260" max="640" step="10" value="420">
        <span id="pillVal" class="val"></span>
      </label>
    </div>

    <div class="row">
      <label>Pill height
        <input id="ctrlPillH" type="range" min="28" max="84" step="2" value="40">
        <span id="pillHVal" class="val"></span>
      </label>
      <label>Row spacing
        <input id="ctrlRowGap" type="range" min="0" max="40" step="1" value="12">
        <span id="rowGapVal" class="val"></span>
      </label>
    </div>

    <div class="row">
      <label class="check"><input id="ctrlSharedOnly" type="checkbox"> Links for shared only</label>
      <label>Quick subset
        <select id="ctrlQuickFilter">
          <option value="all">All</option>
          <option value="shared">Shared Top</option>
          <option value="aonly">A-only Top</option>
          <option value="bonly">B-only Top</option>
        </select>
      </label>
    </div>
  </div>
</div>


    <!-- Insights -->
    <section class="bar" id="insights" style="display:none;">
        <div class="cards" id="kpiCards">
        <div class="card">
            <h3>Top-K Overlap</h3>
            <div class="num" id="k_overlap">-</div>
            <canvas class="spark" id="sparkOverlap" width="300" height="36"></canvas>
        </div>
        <div class="card"><h3>Jaccard</h3><div class="num" id="k_jaccard">-</div></div>
        <div class="card"><h3>Dice</h3><div class="num" id="k_dice">-</div></div>
        <div class="card"><h3>Overlap Coef</h3><div class="num" id="k_overlapcoef">-</div></div>
        <div class="card"><h3>Shared | A-only | B-only</h3><div class="num" id="k_sets">-</div></div>
        <div class="card"><h3>RBO (p=0.9)</h3><div class="num" id="k_rbo">-</div></div>
        <div class="card"><h3>Spearman ρ</h3><div class="num" id="k_spearman">-</div></div>
        <div class="card"><h3>Kendall τ</h3><div class="num" id="k_kendall">-</div></div>
        <div class="card"><h3>Sig terms (AdjP)</h3><div class="num" id="k_sig">-</div></div>
        <div class="card2"><h3>Top movers |Δrank|</h3><div class="num" id="k_movers">-</div></div>
        </div>
    </section>

    <!-- Plot -->
    <section id="plotView" class="panel" style="display:none;">
        <h4>Slopegraph of Top-K ORA terms</h4>
        <div id="wrap"><svg id="svg"></svg></div>
    </section>

    <!-- Table -->
    <section id="tableView" class="panel table-panel" style="display:none; font-size:11px;">
        <h3>Comparison table</h3>
        <div class="nav" style="margin-bottom:8px">
        <span class="small">Subset:</span>
        <button class="btn" id="fltAll">All</button>
        <button class="btn" id="fltShared">Shared</button>
        <button class="btn" id="fltAonly">A-only</button>
        <button class="btn" id="fltBonly">B-only</button>
        </div>
        <table id="cmpTable" class="display" style="width:100%;">
        <thead>
        <tr>
            <th>Term</th>
            <th>In A</th><th>Top Rank A</th><th>Global Rank A</th><th>-log10(adjP) A</th><th>-log10(P) A</th><th>Combined A</th><th>Odds A</th><th>Z A</th>
            <th>In B</th><th>Top Rank B</th><th>Global Rank B</th><th>-log10(adjP) B</th><th>-log10(P) B</th><th>Combined B</th><th>Odds B</th><th>Z B</th>
            <th>Δrank (B-A)</th><th>Δmetric (B-A)</th>
            <th>Hit Jaccard</th><th>Hits ∩</th><th>Hits A-only</th><th>Hits B-only</th>
        </tr>
        </thead>
        </table>
    </section>

    <!-- Modal -->
    <div class="modal" id="modal">
        <div class="dialog">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
            <div>
            <h4 id="mTitle">Term</h4>
            <div class="sub" id="mSubtitle"></div>
            </div>
            <button class="btn" onclick="closeModal()">Close</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
            <div class="card">
            <h3 id="hdrA" style="margin:0 0 6px">A</h3>
            <div class="kv" id="kvA"></div>
            </div>
            <div class="card">
            <h3 id="hdrB" style="margin:0 0 6px">B</h3>
            <div class="kv" id="kvB"></div>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
            <div class="card">
            <b>Hits Intersection (<span id="cntInter"></span>)</b>
            <pre class="genes" id="genesInter"></pre>
            </div>
            <div class="card">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                <b>Hits only in A (<span id="cntAonly"></span>)</b>
                <pre class="genes" id="genesAonly"></pre>
                </div>
                <div>
                <b>Hits only in B (<span id="cntBonly"></span>)</b>
                <pre class="genes" id="genesBonly"></pre>
                </div>
            </div>
            </div>
        </div>
        <div class="small" style="margin-top:10px">
            Note: “hits” = query genes from A or B that fall in this term's gene set (same library). Metrics are those reported by your ORA (AdjP, P, Odds, Z, Combined).
        </div>
        </div>
    </div>

    <div class="tooltip" id="tooltip"></div>""" + f"""<script>
    /* ====== Embedded initial data (auto-loaded) ====== */
    const INIT = {{
    labelA: {LABEL_A_JS},
    labelB: {LABEL_B_JS},
    library: {LIB_JS},
    tsvA: {TSV_A_JS},
    tsvB: {TSV_B_JS}
    }};
    </script>""" + r"""<script>
    /* ========= Config ========= */
    const CFG = {
    pseudocount: 1e-300,
    max_terms_render: 14000,
    slope: { top:56, bottom:40, column_gap:360, pill_width:420, pill_height:40, pill_radius:7, row_gap:12 }
    };

    let DATA=null; let table=null; let LAST_ROWS=null; let CURRENT_METRIC="neglog10AdjP";

    
    /* === Icon assets and UI wiring (SVG swap) === */""" + """
const ICONS = """ + icons_data_json + """;

""" + r"""
function hydrateIconButtons(){
  document.querySelectorAll('.iconbtn').forEach(btn=>{
    const key = btn.dataset.icon;
    const img = document.createElement('img');
    img.alt = ''; img.decoding='async'; img.draggable=false; img.width=20; img.height=20;
    img.src = ICONS[key]?.base || '';
    btn.appendChild(img);

    const setBase = () => img.src = ICONS[key].base;
    const setHover = () => img.src = ICONS[key].hover;
    const setActive= () => img.src = ICONS[key].active;

    btn.addEventListener('mouseenter', ()=> btn.classList.contains('active') || document.activeElement===btn ? setActive() : setHover());
    btn.addEventListener('mouseleave', ()=> btn.classList.contains('active') || document.activeElement===btn ? setActive() : setBase());
    btn.addEventListener('focus', setActive);
    btn.addEventListener('blur',  setBase);
    btn.addEventListener('mousedown', setActive);
    btn.addEventListener('mouseup', ()=> (document.activeElement===btn ? setActive() : setHover()));
  });
}

function wireViews(){
  const btnPlot  = document.getElementById('btnPlot');
  const btnTable = document.getElementById('btnTable');
  const plotView = document.getElementById('plotView');
  const tableView= document.getElementById('tableView');

  function setActive(btn){
    [btnPlot, btnTable].forEach(b=>{
      const is = b===btn;
      b.classList.toggle('active', is);
      b.setAttribute('aria-pressed', is ? 'true':'false');
      const key=b.dataset.icon, img=b.querySelector('img');
      if (img && ICONS[key]) img.src = is ? ICONS[key].active : ICONS[key].base;
    });
  }

  btnPlot.addEventListener('click', ()=>{
    plotView.style.display='block'; tableView.style.display='none'; setActive(btnPlot);
  });
  btnTable.addEventListener('click', ()=>{
    plotView.style.display='none'; tableView.style.display='block'; setActive(btnTable);
  });
}

function wireControlsPopover(){
  const trigger = document.getElementById('btnControls');
  const pop = document.getElementById('controlsPopover');
  const closeBtn = document.getElementById('closeControls');

  function open(){
    pop.hidden = false;
    trigger.setAttribute('aria-expanded','true');
    const r = trigger.getBoundingClientRect();
    if (window.matchMedia('(min-width: 881px)').matches) {
      pop.style.left = r.left + 'px';
    }
  }
  function close(){
    pop.hidden = true;
    trigger.setAttribute('aria-expanded','false');
  }

  // prevent "open then instantly close" due to bubbling + img target
  trigger.addEventListener('click', (e)=>{
    e.stopPropagation();
    pop.hidden ? open() : close();
  });
  closeBtn.addEventListener('click', (e)=>{ e.stopPropagation(); close(); });

  // clicks inside the popover shouldn't bubble to the outside-closer
  pop.addEventListener('click', (e)=> e.stopPropagation());

  // close only when clicking truly outside BOTH the popover AND the trigger
  document.addEventListener('click', (e)=>{
    if (pop.hidden) return;
    if (!pop.contains(e.target) && !trigger.contains(e.target)) close();
  });

  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !pop.hidden) close(); });
}


function wireRangeValueMirrors(){
  const pairs = [
    ['ctrlGap','gapVal', v=>v+' px'],
    ['ctrlPillW','pillVal', v=>v+' px'],
    ['ctrlPillH','pillHVal', v=>v+' px'],
    ['ctrlRowGap','rowGapVal', v=>v+' px'],
  ];
  pairs.forEach(([i,s,fmt])=>{
    const input=document.getElementById(i), span=document.getElementById(s);
    if(!input || !span) return;
    const update=()=> span.textContent = fmt(input.value);
    input.addEventListener('input', update); update();
  });
}


    /* ========= Helpers ========= */
    const esc = s => (s??"").toString().replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
    function splitGenes(s){ if(!s||!s.trim) return []; return s.split(/[;,]\s*/).map(x=>x.trim()).filter(Boolean); }
    function coerceNum(x){ if (x==null || x==="") return null; const v=Number(x); return Number.isFinite(v)?v:null; }
    function neglog10(x){ if (x==null) return null; const v=Math.max(x, CFG.pseudocount); return -Math.log10(v); }
    function fmt(x,d=3){ if(x==null||!isFinite(x)) return x==null?"":String(x); const a=Math.abs(x); if(a!==0 && a<1e-3){const e=Math.floor(Math.log10(a));const m=x/Math.pow(10,e);return `${(Math.abs(m)<1?m.toPrecision(3):m.toFixed(3))}×10^${e}`;} return a>=1000?x.toFixed(0):x.toFixed(d); }
    function defaultDirForMetric(m){ return (m==="AdjP"||m==="P")? "asc":"desc"; }

    /* Column mapping (lenient but TSV-only) */
    const SYN = {
    term:new Set(["term","description","pathway","name"]),
    adjp:new Set(["adjustedpvalue","padj","adjp","fdr","qvalue","qvaluebh","bhqvalue"]),
    pval:new Set(["pvalue","p","p.val","p_val","pval"]),
    comb:new Set(["combinedscore","combined_score"]),
    odds:new Set(["oddsratio","or"]),
    z:new Set(["zscore","z"]),
    genes:new Set(["genes","members","geneids","list","leadingedge"])
    };
    function slug(s){ return (s||"").toLowerCase().replace(/[^a-z0-9]+/g,""); }
    function mapCols(cols){
    const got=new Map(cols.map(c=>[slug(c), c]));
    const m={};
    for (const [key,set] of Object.entries(SYN)){ for(const s of set){ if(got.has(s)){ m[key]=got.get(s); break; } } }
    if(!m.term) throw new Error("Missing Term column.");
    return m;
    }

    /* IO (TSV-only) */
    async function readFileAsText(file){
    if(!file) return "";
    const ext=file.name.toLowerCase().split(".").pop();
    if(!["tsv","tab"].includes(ext)) throw new Error("Only .tsv or .tab files are accepted.");
    return new Promise((res,rej)=>{ const fr=new FileReader(); fr.onerror=()=>rej(new Error("Failed to read file.")); fr.onload=()=>res(fr.result); fr.readAsText(file); });
    }
    function parseTSV(text){
    return new Promise((res)=>{
        Papa.parse(text,{ delimiter: "\t", header: true, skipEmptyLines: true, dynamicTyping: false, worker: false,
        complete: r => res({ rows:r.data, fields:r.meta.fields||[] }) });
    });
    }

    /* Normalize rows into common schema */
    function normalize(rows,cmap){
    const out=[];
    for(const r of rows){
        const Term=(r[cmap.term]??"").toString().trim(); if(!Term) continue;
        const AdjP = cmap.adjp ? coerceNum(r[cmap.adjp]) : null;
        const P    = cmap.pval ? coerceNum(r[cmap.pval]) : null;
        const Combined = cmap.comb ? coerceNum(r[cmap.comb]) : null;
        const Odds = cmap.odds ? coerceNum(r[cmap.odds]) : null;
        const Z = cmap.z ? coerceNum(r[cmap.z]) : null;
        const GenesRaw = cmap.genes ? (r[cmap.genes] ?? "") : "";
        const GenesSet = cmap.genes ? splitGenes(GenesRaw) : [];
        out.push({ Term, AdjP, P, Combined, Odds, Z, GenesRaw, GenesSet, neglog10AdjP: AdjP==null?null:neglog10(AdjP), neglog10P: P==null?null:neglog10(P) });
    }
    return out;
    }

    /* Ranking */
    function chooseRankMetric(A,B){
    const has=k=> A.some(r=>r[k]!=null)||B.some(r=>r[k]!=null);
    if(has("AdjP")) return "AdjP";
    if(has("P")) return "P";
    if(has("Combined")) return "Combined";
    return "P";
    }
    function sortKey(chosen,rec){
    if(chosen==="AdjP"||chosen==="P") return rec[chosen]==null?1.0:rec[chosen];
    if(chosen==="Combined") return -(rec["Combined"]??-Infinity);
    return rec["P"]==null?1.0:rec["P"];
    }

    /* Value access */
    function valueFor(row,side,m){
    const map={"AdjP":["AdjPA","AdjPB"],"P":["PA","PB"],"Combined":["CombinedA","CombinedB"],"Odds":["OddsA","OddsB"],"Z":["ZA","ZB"],"neglog10AdjP":["neglog10AdjPA","neglog10AdjPB"],"neglog10P":["neglog10PA","neglog10PB"]};
    const k=map[m]?.[side==="A"?0:1]; return k ? (row[k]??null) : null;
    }

    /* Stats: RBO (Rank-Biased Overlap) for two top lists */
    function rbo(listA, listB, p=0.9){
    if(!listA.length || !listB.length) return 0;
    let Aset=new Set(), Bset=new Set(); let sum=0; const K=Math.max(listA.length, listB.length);
    for(let d=1; d<=K; d++){
        if(d<=listA.length) Aset.add(listA[d-1]);
        if(d<=listB.length) Bset.add(listB[d-1]);
        const inter=[...Aset].filter(x=>Bset.has(x)).length;
        const Ad= d<=listA.length? d : listA.length;
        const Bd= d<=listB.length? d : listB.length;
        const x_d = inter / Math.max(Ad, Bd);
        sum += Math.pow(p, d-1) * x_d;
    }
    return (1-p)*sum;
    }

    /* Kendall tau (naive for shared items with unique ranks) */
    function kendallTau(x, y){
    const n=x.length; if(n<2) return null;
    let c=0, d=0;
    for(let i=0;i<n;i++){
        for(let j=i+1;j<n;j++){
        const sgn = (x[i]-x[j])*(y[i]-y[j]);
        if(sgn>0) c++; else if(sgn<0) d++;
        }
    }
    return (c-d)/(0.5*n*(n-1));
    }

    /* ===== Core processor extracted so we can call from BTN and INIT ===== */
    async function processPairs(tA, tB, labelA, labelB, library){
    const msg=document.getElementById("loadMsg"); if(msg) msg.textContent="";
    try{
        const [{rows:ra,fields:fa},{rows:rb,fields:fb}]=await Promise.all([parseTSV(tA), parseTSV(tB)]);

        const cmapA=mapCols(fa), cmapB=mapCols(fb);
        const A=normalize(ra,cmapA), B=normalize(rb,cmapB);

        const chosen=chooseRankMetric(A,B);
        const sortA=A.slice().sort((x,y)=> sortKey(chosen,x)-sortKey(chosen,y));
        const sortB=B.slice().sort((x,y)=> sortKey(chosen,x)-sortKey(chosen,y));
        const uniqA=new Map(), uniqB=new Map();
        for(const r of sortA){ if(!uniqA.has(r.Term)) uniqA.set(r.Term,r); }
        for(const r of sortB){ if(!uniqB.has(r.Term)) uniqB.set(r.Term,r); }

        const A_best=[...uniqA.values()], B_best=[...uniqB.values()];
        A_best.forEach((r,i)=> r.InitRank=i+1);
        B_best.forEach((r,i)=> r.InitRank=i+1);

        const terms=new Set([...A_best.map(r=>r.Term), ...B_best.map(r=>r.Term)]);
        const Amap=new Map(A_best.map(r=>[r.Term,r]));
        const Bmap=new Map(B_best.map(r=>[r.Term,r]));

        const rows=[];
        for(const t of terms){
        const a=Amap.get(t), b=Bmap.get(t);
        const genesA=a?.GenesSet??[], genesB=b?.GenesSet??[];
        const setA=new Set(genesA), setB=new Set(genesB);
        const inter=genesA.filter(x=>setB.has(x)).sort();
        const onlyA=genesA.filter(x=>!setB.has(x)).sort();
        const onlyB=genesB.filter(x=>!setA.has(x)).sort();
        const denom=new Set([...genesA,...genesB]).size;

        rows.push({
            Term:t, inA:!!a, inB:!!b,
            AdjPA:a?.AdjP??null, PA:a?.P??null, CombinedA:a?.Combined??null, OddsA:a?.Odds??null, ZA:a?.Z??null,
            neglog10AdjPA:a?.neglog10AdjP??null, neglog10PA:a?.neglog10P??null,
            GenesRawA:a?.GenesRaw??"", RankA0:a?.InitRank??null,
            AdjPB:b?.AdjP??null, PB:b?.P??null, CombinedB:b?.Combined??null, OddsB:b?.Odds??null, ZB:b?.Z??null,
            neglog10AdjPB:b?.neglog10AdjP??null, neglog10PB:b?.neglog10P??null,
            GenesRawB:b?.GenesRaw??"", RankB0:b?.InitRank??null,
            GenesInter:inter, GenesOnlyA:onlyA, GenesOnlyB:onlyB, GenesJaccard: denom? (inter.length/denom):null
        });
        }

        // metric choices present
        const choices=[
        ["neglog10AdjP","-log10(AdjP)"],["neglog10P","-log10(P)"],["AdjP","AdjP"],["P","P"],["Combined","Combined"],["Odds","Odds Ratio"],["Z","Z-score"]
        ];
        const present=[]; const hascol=(ak,bk)=> rows.some(r=>r[ak]!=null)||rows.some(r=>r[bk]!=null);
        const mapA={AdjP:"AdjPA",P:"PA",Combined:"CombinedA",Odds:"OddsA",Z:"ZA",neglog10AdjP:"neglog10AdjPA",neglog10P:"neglog10PA"};
        const mapB={AdjP:"AdjPB",P:"PB",Combined:"CombinedB",Odds:"OddsB",Z:"ZB",neglog10AdjP:"neglog10AdjPB",neglog10P:"neglog10PB"};
        for(const [k,lab] of choices){ if(hascol(mapA[k],mapB[k])) present.push({key:k,label:lab}); }
        function defaultMetric(){ const keys=present.map(m=>m.key); if(keys.includes("neglog10AdjP")) return "neglog10AdjP"; if(keys.includes("neglog10P")) return "neglog10P"; if(keys.includes("Combined")) return "Combined"; return keys[0]; }

        DATA={
        meta:{ labelA, labelB, library, fileA:labelA, fileB:labelB, defaultMetric:defaultMetric() },
        rows: rows.slice(0, CFG.max_terms_render),
        metrics: present
        };

        document.getElementById("subtitle").textContent=`${library || "Library"} - ORA comparison: ${labelA} vs ${labelB}`;
        // populate metric select
        const sel=document.getElementById("ctrlMetric"); sel.innerHTML="";
        DATA.metrics.forEach(m=>{ const o=document.createElement("option"); o.value=m.key; o.textContent=m.label; sel.appendChild(o); });
        sel.value=DATA.meta.defaultMetric;
        document.getElementById("ctrlDir").value="auto";

        showApp();

        // tabs
        function showApp(){
            // reveal toolbar and default to plot view
            document.getElementById("tabs").style.display = "flex";
            document.getElementById("insights").style.display = "none";
            document.getElementById("plotView").style.display = "block";
            document.getElementById("tableView").style.display = "none";
            // ensure popover starts closed
            const pop = document.getElementById("controlsPopover");
            if (pop) pop.hidden = true;
            }


        // controls
        document.getElementById("applyBtn").onclick=applyAll;
        ["ctrlWrap","ctrlGap","ctrlPillW","ctrlPillH","ctrlRowGap","ctrlDir","ctrlTopN","ctrlMetric","ctrlSharedOnly","ctrlQuickFilter"].forEach(id=>{
        document.getElementById(id).addEventListener("input", applyAll);
        });
        window.addEventListener("resize", applyAll);

        // initial UI values
        document.getElementById("gapVal").textContent=CFG.slope.column_gap+"px";
        document.getElementById("pillVal").textContent=CFG.slope.pill_width+"px";
        document.getElementById("pillHVal").textContent=CFG.slope.pill_height+"px";
        document.getElementById("rowGapVal").textContent=CFG.slope.row_gap+"px";

        applyAll();
    }catch(err){ console.error(err); if(msg) msg.textContent=err.message || "Failed to load files."; }
    }

    /* ========= UI: KPIs + spark ========= */
    function drawSpark(curve){
    const c=document.getElementById('sparkOverlap'); if(!c) return;
    const ctx=c.getContext('2d'); const W=c.width, H=c.height;
    ctx.clearRect(0,0,W,H);
    if(!curve || !curve.length){ return; }
    ctx.lineWidth=1; ctx.strokeStyle='rgba(100,116,139,0.25)';
    ctx.beginPath(); ctx.moveTo(0,H-0.5); ctx.lineTo(W,H-0.5); ctx.stroke();
    const N = curve[curve.length-1].k;
    ctx.beginPath(); ctx.lineWidth=2; ctx.strokeStyle='rgba(16,140,136,0.8)';
    for(let i=0;i<curve.length;i++){
        const x = (i/(N-1))*W;
        const y = H - curve[i].frac*H;
        if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.stroke();
    }
    function updateKPI(k){
    document.getElementById("k_overlap").textContent = k.overlap;
    document.getElementById("k_jaccard").textContent = (k.jacc??0).toFixed(3);
    document.getElementById("k_dice").textContent = (k.dice??0).toFixed(3);
    document.getElementById("k_overlapcoef").textContent = (k.overlapCoef??0).toFixed(3);
    document.getElementById("k_sets").textContent = k.sets;
    document.getElementById("k_rbo").textContent = (k.rbo??0).toFixed(3);
    document.getElementById("k_spearman").textContent = (k.rho==null? '-' : k.rho.toFixed(3));
    document.getElementById("k_kendall").textContent = (k.tau==null? '-' : k.tau.toFixed(3));
    document.getElementById("k_sig").textContent = k.sig;
    document.getElementById("k_movers").textContent = k.movers || '-';
    drawSpark(k.curve);
    }

    /* ========= Plot (pure renderer; receives precomputed res & UI) ========= */
    function renderSlope(res, ui){
    CURRENT_METRIC = ui.metric;

    const svg=document.getElementById("svg");
    const wrap=document.getElementById("wrap");
    const M=CFG.slope;

    const H=M.top+M.bottom+(ui.N*ui.PILLH)+((ui.N-1)*ui.ROWG);
    wrap.style.height = H+"px";
    const W = wrap.clientWidth;
    svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
    svg.innerHTML="";

    document.getElementById("gapVal").textContent=ui.GAP+"px";
    document.getElementById("pillVal").textContent=ui.PILLW+"px";
    document.getElementById("pillHVal").textContent=ui.PILLH+"px";
    document.getElementById("rowGapVal").textContent=ui.ROWG+"px";

    const CX=W/2, colA_x=CX-ui.GAP/2-ui.PILLW, colB_x=CX+ui.GAP/2;

    // titles
    /*const tA=document.createElementNS("http://www.w3.org/2000/svg","text");
    tA.setAttribute("x", CX - (ui.GAP/2)); 
    tA.setAttribute("y", 18); 
    tA.setAttribute("class","title"); 
    tA.textContent=DATA.meta.labelA; 
    svg.appendChild(tA);

    const tB=document.createElementNS("http://www.w3.org/2000/svg","text");
    tB.setAttribute("x", CX + (ui.GAP/2)); 
    tB.setAttribute("y", 18); 
    tB.setAttribute("class","title"); 
    tB.textContent=DATA.meta.labelB; 
    svg.appendChild(tB);*/

    // titles with extra spacing outward
    // titles with symmetric edge anchoring (length-independent)
    const extra = Math.max(16, ui.GAP * 0.08); // outward offset; scales with GAP

    const tA = document.createElementNS("http://www.w3.org/2000/svg","text");
    tA.setAttribute("x", CX - (ui.GAP/2) - extra);   // fixed anchor point (left side)
    tA.setAttribute("y", 18);
    tA.setAttribute("class","title");
    tA.style.textAnchor = "end";                      // right edge aligns to x
    tA.textContent = DATA.meta.labelA;
    svg.appendChild(tA);

    const tB = document.createElementNS("http://www.w3.org/2000/svg","text");
    tB.setAttribute("x", CX + (ui.GAP/2) + extra);   // fixed anchor point (right side)
    tB.setAttribute("y", 18);
    tB.setAttribute("class","title");
    tB.style.textAnchor = "start";                    // left edge aligns to x
    tB.textContent = DATA.meta.labelB;
    svg.appendChild(tB);






    // filter pass function (single definition)
    function passFilter(r){
        if(ui.QFILT==="all") return true;
        if(ui.QFILT==="shared") return r.SharedTop;
        if(ui.QFILT==="aonly") return r.RankA!=null && r.RankB==null;
        if(ui.QFILT==="bonly") return r.RankB!=null && r.RankA==null;
        return true;
    }

    const left  = res.rows.filter(r=>r.RankA!==null && passFilter(r)).sort((a,b)=>a.RankA-b.RankA);
    const right = res.rows.filter(r=>r.RankB!==null && passFilter(r)).sort((a,b)=>a.RankB-b.RankB);

    const posA=new Map(), posB=new Map();
    const tooltip=document.getElementById("tooltip");

    function showTip(ev, term, arow, brow){
        const metricsA = `AdjP=${fmt(arow.AdjPA)} | -log10P=${fmt(arow.neglog10PA)} | OR=${fmt(arow.OddsA)} | Z=${fmt(arow.ZA)} | Comb=${fmt(arow.CombinedA)}`;
        const metricsB = `AdjP=${fmt(brow.AdjPB)} | -log10P=${fmt(brow.neglog10PB)} | OR=${fmt(brow.OddsB)} | Z=${fmt(brow.ZB)} | Comb=${fmt(brow.CombinedB)}`;
        const va=valueFor(arow,"A",ui.metric), vb=valueFor(brow,"B",ui.metric);
        const dRank=(brow.RankB ?? 0) - (arow.RankA ?? 0);
        const dVal=(vb==null||va==null)? null : (vb-va);
        const bits=[];
        bits.push(`<b>${esc(term)}</b>`);
        bits.push(`<span class="small">${esc(DATA.meta.library)}</span>`);
        bits.push(`${esc(DATA.meta.labelA)}: <b>${fmt(va)}</b> (#${arow.RankA})`);
        bits.push(`<span class="small">${metricsA}</span>`);
        bits.push(`${esc(DATA.meta.labelB)}: <b>${fmt(vb)}</b> (#${brow.RankB})`);
        bits.push(`<span class="small">${metricsB}</span>`);
        bits.push(`Δmetric=${dVal==null?"NA":fmt(dVal)}, Δrank=${isFinite(dRank)?(dRank>0?("+"+dRank):dRank):"NA"}`);
        tooltip.innerHTML = bits.join("<br>"); tooltip.style.display="block";
        tooltip.style.left=(ev.clientX+12)+"px"; tooltip.style.top=(ev.clientY+12)+"px";
    }
    function hideTip(){ tooltip.style.display="none"; }

    function addPill(r, side, i){
        const isA=side==="A";
        const cy=M.top+(ui.PILLH/2)+ i*(ui.PILLH+ui.ROWG);
        const x = isA? colA_x : colB_x;
        const y = cy - ui.PILLH/2;
        const hi = r.SharedTop;

        const rect=document.createElementNS("http://www.w3.org/2000/svg","rect");
        rect.setAttribute("x",x); rect.setAttribute("y",y);
        rect.setAttribute("rx",CFG.slope.pill_radius); rect.setAttribute("ry",CFG.slope.pill_radius);
        rect.setAttribute("width",ui.PILLW); rect.setAttribute("height",ui.PILLH);
        rect.setAttribute("fill", hi? "var(--pillHi)": "var(--pill)");
        rect.setAttribute("stroke", hi? "var(--strokeHi)": "var(--stroke)");
        rect.setAttribute("stroke-width", hi? "3":"2");
        rect.style.cursor="pointer";
        rect.addEventListener("click", ()=> openModal(r));
        svg.appendChild(rect);

        const fo=document.createElementNS("http://www.w3.org/2000/svg","foreignObject");
        fo.setAttribute("x",x+10); fo.setAttribute("y",y+5);
        fo.setAttribute("width",ui.PILLW-20); fo.setAttribute("height",ui.PILLH-10);
        const div=document.createElement("div"); div.setAttribute("xmlns","http://www.w3.org/1999/xhtml");
        div.className="pillText";
        div.style.justifyContent = isA? "flex-end":"flex-start";
        div.style.whiteSpace = ui.WRAP? "normal":"nowrap";
        div.style.paddingRight = isA? "34px":"10px";
        div.style.paddingLeft  = isA? "10px":"34px";
        div.textContent = r.Term;
        fo.appendChild(div); svg.appendChild(fo);
        fo.style.cursor="pointer"; fo.addEventListener("click", ()=> openModal(r));

        const rb=document.createElementNS("http://www.w3.org/2000/svg","text");
        rb.setAttribute("class","rankBadge"); rb.setAttribute("y",cy);
        rb.textContent = "#" + (isA? r.RankA : r.RankB);
        if(isA){ rb.setAttribute("x", x + ui.PILLW - 8); rb.setAttribute("text-anchor","end"); }
        else   { rb.setAttribute("x", x + 8);           rb.setAttribute("text-anchor","start"); }
        rb.style.cursor="pointer"; rb.addEventListener("click", ()=> openModal(r));
        svg.appendChild(rb);

        if(isA) posA.set(r.Term,{x:x+ui.PILLW,y:cy,row:r});
        else    posB.set(r.Term,{x:x,y:cy,row:r});
    }

    left.forEach((r,i)=> addPill(r,"A",i));
    right.forEach((r,i)=> addPill(r,"B",i));

    // links (respect single SHOW_SHARED_ONLY and QFILT from ui)
    const maxDelta = Math.max(1, ...res.rows.filter(r=>r.DeltaRank!=null).map(r=>Math.abs(r.DeltaRank)));
    for(const [term, a] of posA.entries()){
        if(!posB.has(term)) continue;
        const b=posB.get(term);
        const row=a.row; if(ui.SHOW_SHARED_ONLY && !row.SharedTop) continue;
        const cx=(a.x+b.x)/2;
        const path=document.createElementNS("http://www.w3.org/2000/svg","path");
        const d=`M ${a.x},${a.y} C ${cx},${a.y} ${cx},${b.y} ${b.x},${b.y}`;
        path.setAttribute("d",d);
        const va=valueFor(row,"A",ui.metric), vb=valueFor(row,"B",ui.metric);
        const dVal=(vb==null||va==null)? null : (vb-va);
        const dRank=row.DeltaRank;
        const w = dRank==null? 2 : (2 + 3*Math.abs(dRank)/maxDelta);
        path.setAttribute("class","link");
        path.setAttribute("stroke-width", w.toFixed(2));
        path.setAttribute("stroke", dVal==null? "var(--neu)" : (dVal>=0 ? "var(--up)":"var(--dn)"));
        path.addEventListener("mouseenter", (ev)=> showTip(ev, term, a.row, b.row));
        path.addEventListener("mouseleave", hideTip);
        svg.appendChild(path);
    }
    }

    /* ========= Table ========= */
    function barHTML(val, maxAbs){
    if(val==null || !isFinite(val)) return "";
    const pct = Math.min(100, Math.round(Math.abs(val)/Math.max(1e-9,maxAbs)*100));
    const clr = val>=0? "var(--up)" : "var(--dn)";
    return `<div style="display:flex;
                            align-items:center;
                            gap:6px">
            <div style="width:60px;
                        height:6px;
                        background:linear-gradient(to right, ${clr} ${pct}%, transparent ${pct}%);
                        border-radius:999px">
            </div><span class="small">${val>0?'+':''}${fmt(val,2)}</span></div>`;
    }

    function makeTable(allRows){
    const maxAbsRank=Math.max(1, ...allRows.filter(r=>r.DeltaRank!=null).map(r=>Math.abs(r.DeltaRank)));
    const maxAbsMetric=Math.max(1e-9, ...allRows.filter(r=>r.DeltaMetric!=null).map(r=>Math.abs(r.DeltaMetric)));

    const rows = allRows.map(r=>({
        Term:r.Term,inA:r.inA,inB:r.inB,
        RankA:r.RankA??'', GlobalRankA:r.GlobalRankA??'',
        RankB:r.RankB??'', GlobalRankB:r.GlobalRankB??'',
        neglog10AdjPA:r.neglog10AdjPA, neglog10PA:r.neglog10PA,
        CombinedA:r.CombinedA, OddsA:r.OddsA, ZA:r.ZA,
        neglog10AdjPB:r.neglog10AdjPB, neglog10PB:r.neglog10PB,
        CombinedB:r.CombinedB, OddsB:r.OddsB, ZB:r.ZB,
        DeltaRank:r.DeltaRank, DeltaMetric:r.DeltaMetric,
        GenesJaccard:r.GenesJaccard,
        GenesInterCount:(r.GenesInter||[]).length,
        GenesOnlyACount:(r.GenesOnlyA||[]).length,
        GenesOnlyBCount:(r.GenesOnlyB||[]).length,
        _full:r, _maxAbsRank:maxAbsRank, _maxAbsMetric:maxAbsMetric
    }));

    if(table){ table.clear().rows.add(rows).draw(); return; }

    table = $('#cmpTable').DataTable({
        data: rows, pageLength: 25,
        columns: [
        { data:'Term' },
        { data:'inA', render:d=> d?'✓':'' },
        { data:'RankA' },
        { data:'GlobalRankA' },
        { data:'neglog10AdjPA', render:d=> d==null? '': fmt(d) },
        { data:'neglog10PA',    render:d=> d==null? '': fmt(d) },
        { data:'CombinedA',     render:d=> d==null? '': fmt(d) },
        { data:'OddsA',         render:d=> d==null? '': fmt(d) },
        { data:'ZA',            render:d=> d==null? '': fmt(d) },
        { data:'inB', render:d=> d?'✓':'' },
        { data:'RankB' },
        { data:'GlobalRankB' },
        { data:'neglog10AdjPB', render:d=> d==null? '': fmt(d) },
        { data:'neglog10PB',    render:d=> d==null? '': fmt(d) },
        { data:'CombinedB',     render:d=> d==null? '': fmt(d) },
        { data:'OddsB',         render:d=> d==null? '': fmt(d) },
        { data:'ZB',            render:d=> d==null? '': fmt(d) },
        { data:null, render:(d)=> d.DeltaRank==null? '' : barHTML(d.DeltaRank, d._maxAbsRank) },
        { data:null, render:(d)=> d.DeltaMetric==null? '' : barHTML(d.DeltaMetric, d._maxAbsMetric) },
        { data:'GenesJaccard',  render:d=> d==null? '': fmt(d) },
        { data:'GenesInterCount' },
        { data:'GenesOnlyACount' },
        { data:'GenesOnlyBCount' },
        ]
    });

    $('#cmpTable tbody').on('click', 'tr', function(){
        const row = table.row(this).data();
        if(row && row._full) { openModal(row._full); }
    });
    }

    /* ========= Modal ========= */
    function openModal(row){
    document.getElementById("mTitle").textContent=row.Term;
    document.getElementById("mSubtitle").textContent=`${DATA.meta.labelA} vs ${DATA.meta.labelB} — ${DATA.meta.library || 'Library'}`;
    document.getElementById("hdrA").textContent=DATA.meta.labelA;
    document.getElementById("hdrB").textContent=DATA.meta.labelB;

    function kv(side){
        const inFlag = side==="A" ? row.inA : row.inB;
        const topRank = side==="A" ? row.RankA : row.RankB;
        const gRank   = side==="A" ? row.GlobalRankA : row.GlobalRankB;
        const adjp = side==="A" ? row.AdjPA : row.AdjPB;
        const p    = side==="A" ? row.PA    : row.PB;
        const comb = side==="A" ? row.CombinedA : row.CombinedB;
        const odds = side==="A" ? row.OddsA     : row.OddsB;
        const z    = side==="A" ? row.ZA        : row.ZB;
        const nlp  = side==="A" ? row.neglog10PA : row.neglog10PB;
        const nladj= side==="A" ? row.neglog10AdjPA : row.neglog10AdjPB;
        const pairs=[["Present", inFlag? "✓":"-"], ["Top Rank", topRank==null? "-":"#"+topRank], ["Global Rank", gRank==null? "-":"#"+gRank],
        ["AdjP", fmt(adjp)], ["P", fmt(p)], ["-log10(AdjP)", fmt(nladj)], ["-log10(P)", fmt(nlp)],
        ["Combined", fmt(comb)], ["Odds Ratio", fmt(odds)], ["Z-score", fmt(z)]];
        return pairs.map(([k,v])=>`<b>${esc(k)}</b><div>${esc(v)}</div>`).join("");
    }
    document.getElementById("kvA").innerHTML=kv("A");
    document.getElementById("kvB").innerHTML=kv("B");

    const inter=row.GenesInter||[], onlyA=row.GenesOnlyA||[], onlyB=row.GenesOnlyB||[];
    document.getElementById("cntInter").textContent=inter.length;
    document.getElementById("cntAonly").textContent=onlyA.length;
    document.getElementById("cntBonly").textContent=onlyB.length;
    document.getElementById("genesInter").textContent=inter.join("; ");
    document.getElementById("genesAonly").textContent=onlyA.join("; ");
    document.getElementById("genesBonly").textContent=onlyB.join("; ");

    document.getElementById("modal").setAttribute("open","true");
    }
    function closeModal(){ document.getElementById("modal").removeAttribute("open"); }

    /* ========= Wiring ========= */
    function showApp(){
    document.getElementById("tabs").style.display="flex";
    document.getElementById("controls").style.display="flex";
    document.getElementById("insights").style.display="none";
    document.getElementById("plotView").style.display="block";
    document.getElementById("tableView").style.display="none";
    }

    /* Keep original button path working (hidden) */
    document.getElementById("loadBtn")?.addEventListener("click", async ()=>{
    const fA=document.getElementById("fileA").files[0];
    const fB=document.getElementById("fileB").files[0];

    let labelA = document.getElementById("labelA").value.trim();
    let labelB = document.getElementById("labelB").value.trim();

    if (!labelA && fA) labelA = fA.name.replace(/\.(tsv|tab)$/i, "") || "A";
    if (!labelB && fB) labelB = fB.name.replace(/\.(tsv|tab)$/i, "") || "B";

    const library=(document.getElementById("libraryName").value||"").trim();

    const msg=document.getElementById("loadMsg"); if(!fA || !fB){ if(msg) msg.textContent="Please choose both TSV files."; return; }

    try{
        const [tA,tB]=await Promise.all([readFileAsText(fA), readFileAsText(fB)]);
        await processPairs(tA, tB, labelA || "A", labelB || "B", library || "");
    }catch(err){ console.error(err); if(msg) msg.textContent=err.message || "Failed to load files."; }
    });

    /* Auto-boot from embedded INIT */
    document.addEventListener("DOMContentLoaded", ()=> {
        hydrateIconButtons();
        wireViews();
        wireControlsPopover();
        wireRangeValueMirrors();

        if(INIT && INIT.tsvA && INIT.tsvB){
            processPairs(INIT.tsvA, INIT.tsvB, INIT.labelA || "A", INIT.labelB || "B", INIT.library || "");
        }
        });


    
    function sortRows(rows, side, mkey, asc){
        return rows.slice().sort((a,b)=>{
            const va = valueFor(a, side, mkey);
            const vb = valueFor(b, side, mkey);
            const aa = (va==null ? (asc?Infinity:-Infinity) : va);
            const bb = (vb==null ? (asc?Infinity:-Infinity) : vb);
            return asc ? (aa-bb) : (bb-aa);
        });
    }

    /* ======= applyAll + remaining helpers from original ======= */
    function computeTopN(N,mkey,dir){
    const dirEff = dir==="auto" ? defaultDirForMetric(mkey) : dir;
    const asc = dirEff==="asc";

    /*const rowsA = DATA.rows.filter(r=>r.inA).slice().sort((a,b)=>{
        const xa=valueFor(a,"A",mkey); const xb=valueFor(b,"A",mkey);
        const aa = (xa==null ? (asc?Infinity:-Infinity) : xa);
        const bb = (xb==null ? (asc?Infinity:-Infinity) : xb);
        return asc ? (aa-bb) : (bb-aa);
    });
    const rowsB = DATA.rows.filter(r=>r.inB).slice().sort((a,b)=>{
        const xa=valueFor(b,"B",mkey); const xb=valueFor(a,"B",mkey);
        const aa = (xa==null ? (asc?Infinity:-Infinity) : xa);
        const bb = (xb==null ? (asc?Infinity:-Infinity) : xb);
        return asc ? (aa-bb) : (bb-aa);
    });*/
    
    const rowsA = sortRows(DATA.rows.filter(r=>r.inA), "A", mkey, asc);
    const rowsB = sortRows(DATA.rows.filter(r=>r.inB), "B", mkey, asc);


    const topA = rowsA.slice(0,N), topB = rowsB.slice(0,N);
    const setA = new Set(topA.map(r=>r.Term)), setB=new Set(topB.map(r=>r.Term));
    const inter=[...setA].filter(t=>setB.has(t));
    const union=[...new Set([...setA,...setB])];

    const allRows=DATA.rows.filter(r=>setA.has(r.Term)||setB.has(r.Term));
    const idxA=new Map(topA.map((r,i)=>[r.Term,i+1])), idxB=new Map(topB.map((r,i)=>[r.Term,i+1]));
    const rankA=new Map(rowsA.map((r,i)=>[r.Term,i+1])), rankB=new Map(rowsB.map((r,i)=>[r.Term,i+1]));
    allRows.forEach(r=>{
        r.RankA = idxA.get(r.Term) ?? null;
        r.GlobalRankA = r.inA ? (rankA.get(r.Term) ?? null) : null;
        r.RankB = idxB.get(r.Term) ?? null;
        r.GlobalRankB = r.inB ? (rankB.get(r.Term) ?? null) : null;
        r.SharedTop = setA.has(r.Term) && setB.has(r.Term);
        r.DeltaRank = (r.RankA!=null && r.RankB!=null) ? (r.RankB - r.RankA) : null;
        const va=valueFor(r,"A",mkey), vb=valueFor(r,"B",mkey);
        r.DeltaMetric = (va!=null && vb!=null) ? (vb - va) : null;
    });

    const jacc = inter.length/(union.length||1);
    const dice = (2*inter.length)/((setA.size+setB.size)||1);
    const overlapCoef = inter.length / Math.max(1, Math.min(setA.size, setB.size));
    const aonly = [...setA].filter(t=>!setB.has(t)).length;
    const bonly = [...setB].filter(t=>!setA.has(t)).length;
    const rboScore = rbo(topA.map(r=>r.Term), topB.map(r=>r.Term), 0.9);

    const sharedAll = DATA.rows.filter(r=>r.inA && r.inB && r.GlobalRankA!=null && r.GlobalRankB!=null);
    const xr=sharedAll.map(r=>r.GlobalRankA), yr=sharedAll.map(r=>r.GlobalRankB);
    const rho = xr.length>1 ? (()=>{
        const n=xr.length; let s=0; for(let i=0;i<n;i++){ const d=yr[i]-xr[i]; s+=d*d; } return 1 - (6*s)/(n*(n*n-1));
    })() : null;
    const tau = xr.length>1 ? kendallTau(xr,yr) : null;

    const sigCount = (side,thr)=> allRows.filter(r=> (side==="A"? r.AdjPA : r.AdjPB) != null && (side==="A"? r.AdjPA : r.AdjPB) < thr).length;
    const sigA05=sigCount("A",0.05), sigB05=sigCount("B",0.05);
    const sigA01=sigCount("A",0.01), sigB01=sigCount("B",0.01);

    const movers = allRows.filter(r=>r.DeltaRank!=null)
                            .sort((a,b)=> Math.abs(b.DeltaRank)-Math.abs(a.DeltaRank))
                            .slice(0,3).map(r=>`${r.Term} (${r.DeltaRank>0?'+':''}${r.DeltaRank})`);

    const curve=[]; const seenA=new Set(), seenB=new Set();
    let c=0;
    for(let k=1;k<=N;k++){
        if(k<=topA.length) seenA.add(topA[k-1].Term);
        if(k<=topB.length) seenB.add(topB[k-1].Term);
        c=[...seenA].filter(t=>seenB.has(t)).length;
        curve.push({k, frac: c/Math.max(1, Math.min(seenA.size, seenB.size))});
    }

    return {
        rows: allRows,
        dirEff,
        kpis: {
        overlap:`${inter.length} / ${N} (${Math.round((inter.length/(N||1))*100)}%)`,
        jacc, dice, overlapCoef,
        sets:`${inter.length} | ${aonly} | ${bonly}`,
        rbo:rboScore,
        rho, tau,
        sig:`A: ${sigA05}/${sigA01}  |  B: ${sigB05}/${sigB01}`,
        movers: movers.join('; '),
        curve
        },
        lists:{topA, topB}
    };
    }

    function applyAll(){
    if(!DATA) return;

    const ui = {
        N: parseInt(document.getElementById("ctrlTopN").value||30,10),
        metric: document.getElementById("ctrlMetric").value || DATA.meta.defaultMetric,
        dir: document.getElementById("ctrlDir").value || "auto",
        WRAP: document.getElementById("ctrlWrap").checked,
        GAP: parseInt(document.getElementById("ctrlGap").value||CFG.slope.column_gap,10),
        PILLW: parseInt(document.getElementById("ctrlPillW").value||CFG.slope.pill_width,10),
        PILLH: parseInt(document.getElementById("ctrlPillH").value||CFG.slope.pill_height,10),
        ROWG: parseInt(document.getElementById("ctrlRowGap").value||CFG.slope.row_gap,10),
        SHOW_SHARED_ONLY: document.getElementById("ctrlSharedOnly").checked,
        QFILT: document.getElementById("ctrlQuickFilter").value
    };

    const res = computeTopN(ui.N, ui.metric, ui.dir);
    LAST_ROWS = res.rows;
    updateKPI(res.kpis);

    renderSlope(res, ui);
    makeTable(res.rows);
    }

    /* drag & drop kept (hidden) */
    function setupDrop(zoneId, inputId){
    const z=document.getElementById(zoneId); const inp=document.getElementById(inputId);
    if(!z || !inp) return;
    z.addEventListener('dragover', e=>{ e.preventDefault(); z.dataset.active="true"; });
    z.addEventListener('dragleave', ()=>{ z.dataset.active="false"; });
    z.addEventListener('drop', e=>{ e.preventDefault(); z.dataset.active="false"; if(e.dataTransfer.files?.length){ const f=e.dataTransfer.files[0]; const ext=f.name.toLowerCase().split(".").pop(); if(!["tsv","tab"].includes(ext)){ alert("Only .tsv or .tab accepted."); return; } inp.files=e.dataTransfer.files; }});
    z.addEventListener('click', ()=> inp.click());
    }
    setupDrop("dropA","fileA");
    setupDrop("dropB","fileB");

    /* quick filters mirrored */
    function setQuickFilter(v){ const el=document.getElementById("ctrlQuickFilter"); if(el){ el.value=v; applyAll(); } }
    document.getElementById("fltAll").onclick = ()=> setQuickFilter("all");
    document.getElementById("fltShared").onclick = ()=> setQuickFilter("shared");
    document.getElementById("fltAonly").onclick = ()=> setQuickFilter("aonly");
    document.getElementById("fltBonly").onclick = ()=> setQuickFilter("bonly");

    /* modal close */
    document.getElementById("modal").addEventListener("click", e=>{ if(e.target.id==="modal") closeModal(); });
    window.addEventListener("keydown", e=>{ if(e.key==="Escape") closeModal(); });
    </script>
    </body>
    </html>
    """

    return html


def validate_tsv_file(filepath: str) -> tuple[bool, list[str]]:
    """
    Validate that a TSV file:
      1) exists and has .tsv extension
      2) has the exact expected header
      3) each row's values match required types and consistency rules.

    Returns (is_valid, errors)
    - is_valid: True only if all checks pass
    - errors: list of human-readable errors with row numbers (1-based in file, including header)
    """
    errors: list[str] = []

    # 1) path and extension
    if not os.path.isfile(filepath):
        return False, [f"File not found: {filepath}"]
    if not filepath.lower().endswith(".tsv"):
        return False, [f"Not a .tsv file: {filepath}"]

    # 2) read & header
    try:
        with open(filepath, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter="\t")
            header = next(reader, None)
            if header != HEADER:
                return False, [f"Header mismatch.\nExpected: {HEADER}\nFound:    {header}"]

            # 3) validate rows
            # line numbers (header is line 1)
            for idx, row in enumerate(reader, start=2):
                if len(row) != len(HEADER):
                    errors.append(
                        f"Line {idx}: expected {len(HEADER)} columns, found {len(row)}.")
                    continue

                (
                    term,
                    overlap,
                    pval,
                    odds_ratio,
                    zscore,
                    combined_score,
                    adj_pval,
                    genes,
                ) = row

                # count = row[1]  # Overlap 'a/b' -> count is 'a'
                term_size = overlap.split(
                    "/")[1] if overlap and "/" in overlap else None
                query_size = overlap.split(
                    "/")[0] if overlap and "/" in overlap else None
                # background_size
                # Term
                if not term or not term.strip():
                    errors.append(f"Line {idx}: 'Term' is empty.")

                # Overlap 'a/b'
                m = _OVERLAP_RE.match(overlap or "")
                if not m:
                    errors.append(
                        f"Line {idx}: 'Overlap' must be of form 'a/b' with integers. Got '{overlap}'.")
                    a = b = None
                else:
                    a, b = int(m.group(1)), int(m.group(2))

                # Int columns
                for col_name, val in [
                    # ("Count", count),
                    ("Term Size", term_size),
                    ("Query Size", query_size)  # ,
                    # ("Background Size", background_size),
                ]:
                    if not _is_int(val):
                        errors.append(
                            f"Line {idx}: '{col_name}' must be an integer. Got '{val}'.")
                # Only convert after recording type errors
                try:
                    # count_i = int(count)
                    term_size_i = int(term_size)
                    query_size_i = int(query_size)
                    # background_size_i = int(background_size)
                except Exception:
                    # Skip further relational checks for this row
                    continue

                # Non-negative checks
                for col_name, val in [
                    # ("Count", count_i),
                    ("Term Size", term_size_i),
                    ("Query Size", query_size_i)  # ,
                    # ("Background Size", background_size_i),
                ]:
                    if val < 0:
                        errors.append(
                            f"Line {idx}: '{col_name}' must be ≥ 0. Got {val}.")

                # Overlap consistency if parsed
                if m:
                    # if a != count_i:
                    #    errors.append(f"Line {idx}: Overlap numerator ({a}) != Count ({count_i}).")
                    if b != term_size_i:
                        errors.append(
                            f"Line {idx}: Overlap denominator ({b}) != Term Size ({term_size_i}).")
                    if a > b:
                        errors.append(
                            f"Line {idx}: Overlap numerator ({a}) cannot exceed denominator ({b}).")

                # Floats (no NaN/Inf via regex)
                for col_name, val in [
                    ("P-value", pval),
                    ("Odds Ratio", odds_ratio),
                    ("Z-Score", zscore),
                    ("Combined Score", combined_score),
                    ("Adjusted P-value", adj_pval),
                ]:
                    if not _is_float(val):
                        errors.append(
                            f"Line {idx}: '{col_name}' must be numeric (supports scientific notation). Got '{val}'.")

                # Genes: semicolon-separated tokens, no empties
                gene_tokens = [g.strip() for g in (genes or "").split(";")]
                if len(gene_tokens) == 0 or any(g == "" for g in gene_tokens):
                    errors.append(
                        f"Line {idx}: 'Genes' must be a ';'-separated list with no empty entries.")
                else:
                    for g in gene_tokens:
                        if not _GENE_TOKEN_RE.match(g):
                            errors.append(
                                f"Line {idx}: gene token '{g}' contains invalid characters.")

    except Exception as e:
        return False, [f"Failed to read/parse file: {e}"]

    return (len(errors) == 0), errors

# --- Private Functions ---


def _svg_data_uri(p: str) -> str:
    # robust against any characters; avoids escaping issues
    data = Path(p).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except Exception:
        return False


def _is_float(s: str) -> bool:
    s = s.strip()
    # accept normal/scientific notation
    if _SCI_FLOAT_RE.match(s):
        return True
    # accept inf/-inf/+inf
    if _INF_RE.match(s):
        return True
    return False
