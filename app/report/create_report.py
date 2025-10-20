"""Generates an interactive HTML report with charts using Chart.js"""

# -- Standard Library Imports ---
import json
import uuid
from html import escape

# -- Public Functions ---


def generate_interactive_html_report(data):
    """
    Generates an interactive HTML report with charts (using Chart.js).

    Args:
        data: A dictionary containing datasets for the report.
              Expected keys include:
                - keyword_frequencies
                - mesh_term_frequencies
                - entity_document_frequencies
                - entity_annotation_frequencies
                - journal_frequencies
                - publication_years
                - publications_by_year
                - selected_pubmed_ids
                - num_docs_with_keywords
                - num_docs_with_meshterms
                - num_docs_with_pmc_id
    Returns:
        A string containing the complete HTML report.
    """

    # ----- Build card plan -----
    cards = [
        _card_spec("Keyword Frequency", "keyword_frequencies",
                   "Keyword Frequency"),
        _card_spec("MeSH Term Frequency", "mesh_term_frequencies",
                   "MeSH Term Frequency"),
        _card_spec("Gene Document Frequency",
                   "entity_document_frequencies", "Document Frequency of Entity"),
        _card_spec("Gene Annotation Frequency",
                   "entity_annotation_frequencies", "Annotation Count of Entity"),
        _card_spec("Journal Frequency", "journal_frequencies",
                   "Journal Frequency"),
        _card_spec("Publications Per Year", "publication_years", "Publications",
                   chart_type="line", allow_topn=False, allow_search=False),
    ]

    # ----- Serialize datasets for JS -----
    ds: dict = {}
    pubs_by_year_in = data.get("publications_by_year", {}) or {}

    # Normalize publications_by_year into {int_year: [{"pmid": str, "title": str}, ...]}
    norm_pubs_by_year: dict = {}
    for y, lst in pubs_by_year_in.items():
        try:
            yi = int(y)
        except Exception:
            continue
        entries = []
        for it in (lst or []):
            pmid = str(it.get("pmid", "")).strip()
            title = str(it.get("title", "")).strip()
            if pmid or title:
                entries.append({"pmid": pmid, "title": title})
        norm_pubs_by_year[yi] = entries

    for c in cards:
        items = _safe_items(data.get(c["key"], {}))

        if c["key"] == "publication_years":
            # Build counts by year (int)
            counts: dict = {}
            years_from_counts: list = []
            for k, v in items:
                try:
                    yi = int(k)
                except Exception:
                    continue
                counts[yi] = counts.get(yi, 0.0) + float(v)
                years_from_counts.append(yi)

            # Include years that exist only in publications_by_year (with zero count)
            years_from_pubs = list(norm_pubs_by_year.keys())
            all_years = years_from_counts + years_from_pubs
            if all_years:
                y_min, y_max = min(all_years), max(all_years)
                years_full = list(range(y_min, y_max + 1))
                values_full = [counts.get(y, 0.0) for y in years_full]
            else:
                years_full, values_full = [], []

            ds[c["key"]] = {
                "labels": [str(y) for y in years_full],  # ascending
                "values": values_full,
            }

        else:
            # default sort for other charts: value desc
            items = sorted(((str(k), float(v)) for k, v in items),
                           key=lambda kv: kv[1], reverse=True)
            ds[c["key"]] = {"labels": [k for k, _ in items],
                            "values": [v for _, v in items]}

    selected_pmids = ", ".join(map(escape, data.get(
        "selected_pubmed_ids", []))) if data.get("selected_pubmed_ids") else "—"
    stats_bits: list = []
    for k, label in [
        ("num_docs_with_keywords", "Documents with Keywords"),
        ("num_docs_with_meshterms", "Documents with MeSH Terms"),
        ("num_docs_with_pmc_id", "Documents with PMC ID"),
    ]:
        val = data.get(k, 0)
        if isinstance(val, (int, float)) and val > 0:
            stats_bits.append(
                f'''<div class="stat">
                <div class="stat-value">{int(val)}</div>
                <div class="stat-label">{escape(label)}</div>
                </div>''')
    default_html = '''<div class="stat muted">
                      <div class="stat-value">0</div>
                      <div class="stat-label">No summary stats provided</div>
                      </div>
                      '''
    stats_html = "".join(stats_bits) if stats_bits else default_html

    uid = uuid.uuid4().hex
    dataset_json = json.dumps(ds)
    years_map_json = json.dumps(
        {str(k): v for k, v in sorted(norm_pubs_by_year.items())})

    # --- Build final HTML -----
    html = f"""<!DOCTYPE html>
  <html lang="en">
  <head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Interactive Data Report</title>

  <!-- Chart.js + Zoom -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2"></script>

  <style>
  :root {{
    --bg: white /*#F6F8F8;        App background */
    --card: #FFFFFF;      /* Surfaces / cards */
    --text: #25323E;      /* Primary text */
    --muted: #6A7A89;     /* Muted text */
    --accent: #17806E;    /* Teal primary */
    --accent-2: #116D63;  /* Teal hover/deeper */
    --ring: rgba(23,128,110,.25); /* Focus ring */
    --border: #D5DDE3;    /* Control/card borders */
    --shadow: 0 2px 8px rgba(0,0,0,.06); /* Subtle clinical shadow */
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #25323E;       /* fallback dark mode */
      --card: #2F3C47;
      --text: #E7EAF0;
      --muted: #A5B0BA;
      --accent: #4CC9F0;
      --accent-2: #F72585;
      --ring: rgba(76,201,240,.35);
      --border: #3C4B57;
      --shadow: 0 4px 12px rgba(0,0,0,.4);
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; }}
  body {{
    margin: 0; padding: 24px;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    background: var(--bg);
    color: var(--text);
  }}
  .header {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; margin-bottom: 18px; }}
  h1 {{ margin: 0; font-size: 22px; letter-spacing: .2px; }}
  .small {{ font-size: 12px; color: var(--muted); }}

  .stats {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin: 14px 0 22px; }}
  .stat {{ background: var(--card); border:1px solid var(--border); border-radius: 3px; padding: 14px 16px; box-shadow: var(--shadow); }}
  .stat-value {{ font-size: 22px; font-weight: 700; }}
  .stat-label {{ color: var(--muted); font-size: 12px; margin-top: 6px; }}
  .muted {{ color: var(--muted); }}

  /* ---- FLEX LAYOUT: no overlap when cards are resized ---- */
  .card-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    align-items: stretch;
  }}

  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 3px;
    box-shadow: var(--shadow);
    overflow: auto;
    display: flex;
    flex-direction: column;
    min-height: 320px;
    min-width: 340px;
    max-width: 100%;
    flex: 0 0 auto;    /* allow manual resize */
    width: 420px;
    resize: both;
  }}

  .card-header {{
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    display:flex; align-items:center; gap:10px; justify-content: space-between;
  }}
  .card-title {{ font-weight: 700; font-size: 15px; }}
  .controls {{ display:flex; flex-wrap: wrap; gap: 8px; align-items:center; }}
  .control {{
    display:flex; align-items:center; gap:6px; font-size: 12px; color: var(--muted);
    background: var(--card);
    border:1px solid var(--border);
    padding: 6px 8px; border-radius: 3px;
  }}
  .control input[type="number"], .control input[type="search"] {{
    width: 80px; font-size: 12px; color: var(--text); background: transparent; border: none; outline: none;
  }}
  .control input[type="search"] {{ width: 140px; }}
  .control button {{
    font-size: 12px; padding:6px 8px; border-radius: 3px; border:1px solid var(--border);
    background: #FFFFFF; color: var(--text); cursor:pointer;
  }}
  .control button:hover {{ border-color: var(--accent); box-shadow: 0 0 0 2px var(--ring); }}

  .card-body {{ padding: 12px; display:flex; flex-direction: column; flex: 1; }}
  .canvas-wrap {{ position: relative; width: 100%; flex: 1; min-height: 220px; }}
  .empty {{ padding: 24px; color: var(--muted); text-align:center; }}

  .footer {{
    margin-top: 28px; display:flex; justify-content: space-between; align-items:center; gap: 12px; flex-wrap: wrap;
    color: var(--muted); font-size: 12px;
  }}
  .code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}

  /* ---- Modal for PubMed list ---- */
  .modal-backdrop {{
    position: fixed; inset: 0;
    background: rgba(0,0,0,.45);
    display: none;
    align-items: center; justify-content: center;
    z-index: 9999;
  }}
  .modal-backdrop.show {{ display: flex; }}
  .modal {{
    background: var(--card);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 3px;
    box-shadow: var(--shadow);
    width: min(960px, 92vw);
    max-height: 80vh;
    display: flex; flex-direction: column;
  }}
  .modal-header {{
    padding: 12px 14px; border-bottom: 1px solid var(--border);
    display:flex; align-items:center; justify-content: space-between; gap: 12px;
  }}
  .modal-title {{ font-weight: 700; }}
  .modal-close {{ appearance:none; border:1px solid var(--border); background:transparent; color:var(--text); border-radius: 3px; padding: 6px 10px; cursor: pointer; }}
  .modal-body {{ padding: 12px 14px; overflow: auto; }}
  .pub-list {{ list-style: none; padding: 0; margin: 0; }}
  .pub-list li {{ padding: 8px 0; border-bottom: 1px dashed var(--border); }}
  .pub-list a {{ color: var(--accent); text-decoration: none; }}
  .pub-list a:hover {{ text-decoration: underline; }}
  .pub-pmid {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
  </style>

  </head>

  <body>

  <div class="header">
    <div>
      <h1>Statistics for Selected Documents</h1>
      <div class="small">Selected PubMed IDs: <span class="code">{escape(selected_pmids)}</span></div>
    </div>
  </div>

  <div class="stats">
    {stats_html}
  </div>

  <div class="card-grid" id="grid_{uid}">
    <!-- Cards injected here -->
  </div>

  <!-- Modal -->
  <div class="modal-backdrop" id="modal_{uid}">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal_title_{uid}">
      <div class="modal-header">
        <div class="modal-title" id="modal_title_{uid}">Publications in <span id="modal_year_{uid}"></span></div>
        <button class="modal-close" id="modal_close_{uid}">Close</button>
      </div>
      <div class="modal-body">
        <ul class="pub-list" id="pub_list_{uid}"></ul>
      </div>
    </div>
  </div>

  <div class="footer">
    <div>Charts are interactive: drag to zoom, click “Reset” to return. Drag card corners to resize. Export PNG/CSV per card. Click a year to see PubMed IDs.</div>
    <div class="small">Built with Chart.js</div>
  </div>

  <script>
  (function() {{
    const DS = {dataset_json};
    const YEARS_MAP = {years_map_json}; // {{ "YYYY": [{{pmid,title}}], ... }}

    // Utilities
    const throttle = (fn, wait=120) => {{
      let t=0; return (...args) => {{ const now=Date.now(); if (now - t > wait) {{ t=now; fn(...args); }} }}
    }};
    const toCSV = (labels, values) => {{
      const lines = ["label,value", ...labels.map((l,i)=>`"${{String(l).replaceAll('"','""')}}",${{values[i]}}`)];
      return lines.join("\\n");
    }};
    const downloadBlob = (filename, blob) => {{
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(()=>URL.revokeObjectURL(url), 0);
    }};

    // Color helpers
    const baseColor = (i, total) => {{
      const h = 200 - Math.round(160 * (i/(Math.max(1,total-1))));
      return `hsl(${{h}} 80% 55%)`;
    }};

    // Label helpers
    const wrapLabel = (text, max=16) => {{
      const words = String(text).split(/\\s+/);
      const lines = [];
      let line = "";
      for (const w of words) {{
        if ((line + " " + w).trim().length <= max) {{
          line = (line ? line + " " : "") + w;
        }} else {{
          if (line) lines.push(line);
          if (w.length > max) {{
            for (let i=0;i<w.length;i+=max) lines.push(w.slice(i, i+max));
            line = "";
          }} else {{
            line = w;
          }}
        }}
      }}
      if (line) lines.push(line);
      return lines;
    }};
    const trimForTick = (text, max=60) => {{
      const s = String(text);
      return s.length > max ? s.slice(0, max-1) + "…" : s;
    }};

    // Axis auto-sizing plugin
    const labelSizer = {{
      id: 'labelSizer',
      afterFit(scale) {{
        if (scale.type !== 'category') return;
        const opts = scale.options;
        const fontSize = (opts.ticks && opts.ticks.font && opts.ticks.font.size) || 12;
        const lineH = Math.round(fontSize * 1.25);
        const padding = (opts.ticks && opts.ticks.padding) || 8;

        let maxLines = 1;
        for (const t of scale.ticks) {{
          const arr = wrapLabel(trimForTick(t.label || t.value || ""), 16);
          if (arr.length > maxLines) maxLines = arr.length;
        }}

        if (scale.isHorizontal()) {{
          const needed = maxLines * lineH + padding * 2;
          if (scale.height < needed) scale.height = needed;
        }} else {{
          const charWidth = Math.round(fontSize * 0.65);
          let maxWidthChars = 0;
          for (const t of scale.ticks) {{
            const arr = wrapLabel(trimForTick(t.label || t.value || ""), 16);
            for (const line of arr) maxWidthChars = Math.max(maxWidthChars, line.length);
          }}
          const needed = Math.min(420, maxWidthChars * charWidth + padding * 2);
          if (scale.width < needed) scale.width = needed;
        }}
      }}
    }};

    // Modal helpers
    const modal = document.getElementById("modal_{uid}");
    const modalYear = document.getElementById("modal_year_{uid}");
    const modalList = document.getElementById("pub_list_{uid}");
    const modalClose = document.getElementById("modal_close_{uid}");
    const openModal = (year) => {{
      modalYear.textContent = year;
      const arr = YEARS_MAP[String(year)] || [];
      modalList.innerHTML = "";
      if (!arr.length) {{
        const li = document.createElement('li');
        li.textContent = "No publications found for this year.";
        modalList.appendChild(li);
      }} else {{
        for (const it of arr) {{
          const li = document.createElement('li');
          const pmid = (it.pmid||"").trim();
          const title = (it.title||"").trim();
          const link = pmid ? `https://pubmed.ncbi.nlm.nih.gov/${{encodeURIComponent(pmid)}}/` : null;
          li.innerHTML = link
            ? `<div><a href="${{link}}" target="_blank" rel="noopener noreferrer" class="pub-pmid">PMID ${{pmid}}</a></div><div>${{title||'(untitled)'}}</div>`
            : `<div class="pub-pmid">${{pmid||'(no PMID)'}}</div><div>${{title||'(untitled)'}}</div>`;
          modalList.appendChild(li);
        }}
      }}
      modal.classList.add("show");
    }};
    const closeModal = () => modal.classList.remove("show");
    modal.addEventListener("click", (e)=>{{ if(e.target === modal) closeModal(); }});
    modalClose.addEventListener("click", closeModal);
    window.addEventListener("keydown", (e)=>{{ if(e.key === "Escape") closeModal(); }});

    class ChartCard {{
      constructor(opts) {{
        this.title = opts.title;
        this.yLabel = opts.yLabel;
        this.key = opts.key;
        this.type = opts.type || 'bar';
        this.allowTopN = !!opts.allowTopN;
        this.allowSearch = !!opts.allowSearch;
        this.labels = (DS[this.key]?.labels)||[];
        this.values = (DS[this.key]?.values)||[];
        this.sortDesc = true;
        this.isYears = (this.key === 'publication_years');  // special handling
        this.mount(opts.target);
      }}
      currentFiltered() {{
        let lbls = [...this.labels];
        let vals = [...this.values];

        // Keep chronological order for years; ignore search/sort/topN
        if (this.isYears) return [lbls, vals];

        const q = (this.search?.value||"").trim().toLowerCase();
        if (q) {{
          const both = lbls.map((l,i)=>[l, vals[i]]).filter(([l]) => l.toLowerCase().includes(q));
          lbls = both.map(x=>x[0]); vals = both.map(x=>x[1]);
        }}
        const idxs = lbls.map((_,i)=>i);
        idxs.sort((a,b)=> this.sortDesc ? (vals[b]-vals[a]) : (vals[a]-vals[b]));
        lbls = idxs.map(i=>lbls[i]); vals = idxs.map(i=>vals[i]);

        let n = parseInt(this.topn?.value||"");
        if (!isFinite(n) || n <= 0) n = lbls.length;
        lbls = lbls.slice(0, n); vals = vals.slice(0, n);
        return [lbls, vals];
      }}
      mount(target) {{
        const card = document.createElement('div'); card.className='card';
        const header = document.createElement('div'); header.className='card-header';
        const titleEl = document.createElement('div'); titleEl.className='card-title'; titleEl.textContent = this.title;
        const controls = document.createElement('div'); controls.className='controls';

        if (this.allowTopN && !this.isYears) {{
          const c = document.createElement('div'); c.className='control';
          c.innerHTML = `<span>Top</span><input type="number" min="1" step="1" value="10" />`;
          this.topn = c.querySelector('input');
          controls.appendChild(c);
        }}
        if (this.allowSearch && !this.isYears) {{
          const c = document.createElement('div'); c.className='control';
          c.innerHTML = `<span>Search</span><input type="search" placeholder="filter labels..." />`;
          this.search = c.querySelector('input');
          controls.appendChild(c);
        }}
        if (!this.isYears) {{
          const sortBtn = document.createElement('div'); sortBtn.className='control';
          sortBtn.innerHTML = `<button title="Toggle sort">Sort: <strong>Desc</strong></button>`;
          this.sortToggle = sortBtn.querySelector('button');
          controls.appendChild(sortBtn);
        }}

        const reset = document.createElement('div'); reset.className='control';
        reset.innerHTML = `<button title="Reset zoom">Reset</button>`;
        this.resetBtn = reset.querySelector('button');
        controls.appendChild(reset);

        /*const exportPng = document.createElement('div'); exportPng.className='control';
        exportPng.innerHTML = `<button title="Export PNG">PNG</button>`;
        this.pngBtn = exportPng.querySelector('button');
        controls.appendChild(exportPng);

        const exportCsv = document.createElement('div'); exportCsv.className='control';
        exportCsv.innerHTML = `<button title="Export CSV">CSV</button>`;
        this.csvBtn = exportCsv.querySelector('button');
        controls.appendChild(exportCsv);*/

        header.appendChild(titleEl); header.appendChild(controls);
        card.appendChild(header);

        const body = document.createElement('div'); body.className='card-body';
        if (!this.labels.length) {{
          const empty = document.createElement('div'); empty.className='empty';
          empty.textContent = 'No data available';
          body.appendChild(empty);
          card.appendChild(body);
          target.appendChild(card);
          return;
        }}
        const wrap = document.createElement('div'); wrap.className='canvas-wrap';
        const canvas = document.createElement('canvas');
        wrap.appendChild(canvas);
        body.appendChild(wrap);
        card.appendChild(body);
        target.appendChild(card);
        this.wrap = wrap;

        // chart build
        const ctx = canvas.getContext('2d');
        const [lbls, vals] = this.currentFiltered();
        const cfg = this.buildConfig(lbls, vals);
        this.chart = new Chart(ctx, cfg);

        // events
        const rerender = throttle(()=>this.update(), 120);
        this.topn && this.topn.addEventListener('input', rerender);
        this.search && this.search.addEventListener('input', rerender);
        if (this.sortToggle) {{
          this.sortToggle.addEventListener('click', ()=>{{
            this.sortDesc = !this.sortDesc;
            this.sortToggle.innerHTML = `Sort: <strong>${{this.sortDesc?'Desc':'Asc'}}</strong>`;
            this.update(true);
          }});
        }}
        this.resetBtn.addEventListener('click', ()=> this.chart.resetZoom());
        /*this.pngBtn.addEventListener('click', ()=> {{
          const name = this.title.toLowerCase().replace(/\\s+/g,'_') + '.png';
          const canvas = this.chart.canvas;
          if (canvas.toBlob) {{
            canvas.toBlob(blob => downloadBlob(name, blob));
          }} else {{
            const dataUrl = canvas.toDataURL('image/png');
            const a = document.createElement('a'); a.href = dataUrl; a.download = name;
            document.body.appendChild(a); a.click(); a.remove();
          }}
        }});
        this.csvBtn.addEventListener('click', ()=> {{
          const [l, v] = this.currentFiltered();
          const csv = toCSV(l, v);
          const name = this.title.toLowerCase().replace(/\\s+/g,'_') + '.csv';
          downloadBlob(name, new Blob([csv], {{type: 'text/csv;charset=utf-8'}}));
        }});*/

        // Click to open modal for years
        if (this.isYears) {{
          canvas.addEventListener('click', (evt) => {{
            const pts = this.chart.getElementsAtEventForMode(evt, 'nearest', {{intersect: true}}, true);
            if (!pts || !pts.length) return;
            const idx = pts[0].index;
            const dp = this.chart.data.datasets[0].data[idx];
            const year = dp && (typeof dp.x !== 'undefined') ? Number(dp.x) : Number(this.chart.data.labels[idx]);
            if (!Number.isFinite(year)) return;
            openModal(year);
          }});
        }}

        // Keep chart in sync with user-resized card (and window)
        const resizeObs = new ResizeObserver(()=> this.chart && this.chart.resize());
        resizeObs.observe(wrap);
        resizeObs.observe(card);
        window.addEventListener('resize', ()=> this.chart && this.chart.resize());
      }}

      // Decide orientation based on item count
      orientationFor(count) {{
        return (this.type === 'bar' && count >= 12) ? 'y' : 'x';
      }}

      buildConfig(labels, values) {{
        const total = labels.length;
        const indexAxis = this.orientationFor(total); // 'x' or 'y'

        const tickAxisKey = indexAxis === 'y' ? 'y' : 'x';
        const otherAxisKey = indexAxis === 'y' ? 'x' : 'y';

        const commonOpts = {{
          indexAxis,
          responsive: true,
          maintainAspectRatio: false,
          animation: {{ duration: 250 }},
          layout: {{ padding: 8 }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              mode: 'index',
              intersect: false,
              callbacks: {{
                title: (items) => items.map(it => it.label),
              }}
            }},
            zoom: {{
              pan: {{ enabled: true, mode: 'xy' }},
              zoom: {{
                drag: {{ enabled: true }},
                wheel: {{ enabled: false }},
                pinch: {{ enabled: true }},
                mode: 'xy'
              }}
            }},
            labelSizer,
          }},
          scales: {{
            [tickAxisKey]: {{
              ticks: {{
                autoSkip: false,
                stepSize: 1,  // one tick per category when category scale is used
                padding: 8,
                maxRotation: (indexAxis === 'x') ? 45 : 0,
                minRotation: 0,
                callback: function(value) {{
                  const raw = this.getLabelForValue(value);
                  const wrapped = wrapLabel(trimForTick(raw, 60), 16);
                  return wrapped;
                }},
              }},
              grid: {{ display: (indexAxis === 'x') ? false : true }}
            }},
            [otherAxisKey]: {{
              beginAtZero: true,
              title: {{ display: true, text: this.yLabel }},
            }}
          }}
        }};

        if (this.type === 'line' && this.isYears) {{
          // Publications per Year: numeric x-axis with {{x: year, y: value}} points
          const points = labels.map((y, i) => ({{ x: Number(y), y: values[i] }}));
          return {{
            type: 'line',
            data: {{
              labels, // kept for tooltip title fallback
              datasets: [{{
                label: this.yLabel,
                data: points,
                parsing: false,
                fill: true,
                tension: 0.25,
                borderColor: baseColor(0,1),
                backgroundColor: 'rgba(76, 201, 240, 0.15)',
                spanGaps: true
              }}]
            }},
            options: {{
              ...commonOpts,
              scales: {{
                x: {{
                  type: 'linear',
                  ticks: {{
                    stepSize: 1,
                    callback: (v) => Number.isInteger(v) ? v : '',
                    padding: 8
                  }},
                  grid: {{ display: false }}
                }},
                y: {{
                  beginAtZero: true,
                  title: {{ display: true, text: this.yLabel }}
                }}
              }},
              plugins: {{
                ...commonOpts.plugins,
                tooltip: {{
                  ...commonOpts.plugins.tooltip,
                  callbacks: {{
                    title: (items) => items.map(it => String(it.raw.x))
                  }}
                }}
              }}
            }}
          }};
        }} else if (this.type === 'line') {{
          
          return {{
            type: 'line',
            data: {{
              labels,
              datasets: [{{
                label: this.yLabel,
                data: values,
                fill: true,
                tension: 0.25,
                borderColor: baseColor(0,1),
                backgroundColor: 'rgba(76, 201, 240, 0.15)'
              }}]
            }},
            options: {{
              ...commonOpts,
              scales: {{
                x: {{
                  type: 'category',
                  ticks: {{ autoSkip: false, stepSize: 1, padding: 8, maxRotation: 0, minRotation: 0 }},
                  grid: {{ display: false }}
                }},
                y: {{ beginAtZero: true, title: {{ display: true, text: this.yLabel }} }}
              }}
            }}
          }};
        }} else {{
          // Bars
          return {{
            type: 'bar',
            data: {{
              labels,
              datasets: [{{
                label: this.yLabel,
                data: values,
                backgroundColor: labels.map((_,i)=> baseColor(i,total)),
                borderWidth: 1
              }}]
            }},
            options: commonOpts
          }};
        }}
      }}

      update(forceRebuild=false) {{
        if (!this.chart) return;
        const [lbls, vals] = this.currentFiltered();

        const currentIndexAxis = this.chart.options.indexAxis || 'x';
        const desiredIndexAxis = this.orientationFor(lbls.length);
        const orientationChanged = currentIndexAxis !== desiredIndexAxis;

        if (forceRebuild || orientationChanged) {{
          const ctx = this.chart.ctx;
          this.chart.destroy();
          this.chart = new Chart(ctx, this.buildConfig(lbls, vals));
          return;
        }}

        // For years line chart, rebuild data points
        if (this.isYears && this.type === 'line') {{
          this.chart.data.labels = lbls;
          this.chart.data.datasets[0].data = lbls.map((y,i)=> ({{x: Number(y), y: vals[i]}}));
        }} else {{
          this.chart.data.labels = lbls;
          this.chart.data.datasets[0].data = vals;
          if (this.type === 'bar') {{
            const total = lbls.length;
            this.chart.data.datasets[0].backgroundColor = lbls.map((_,i)=> baseColor(i,total));
          }}
        }}
        this.chart.update();
      }}
    }}

    // Build grid
    const grid = document.getElementById("grid_{uid}");
    const make = (title, key, yLabel, type, allowTopN, allowSearch) => new ChartCard({{
      title, key, yLabel, type, allowTopN, allowSearch, target: grid
    }});

    // Card plan from Python:
    const plan = {json.dumps(cards)};
    plan.forEach(c => make(c.title, c.key, c.y_label, c.chart_type, c.allow_topn, c.allow_search));
  }})();
  </script>

  </body>
  </html>
"""
    return html

# --- Private Functions ---


def _safe_items(d):
    return [(str(k), float(v)) for k, v in (d or {}).items() if v is not None]


def _card_spec(title, key, y_label, chart_type="bar", allow_topn=True, allow_search=True):
    return {
        "title": title,
        "key": key,
        "y_label": y_label,
        "chart_type": chart_type,
        "allow_topn": allow_topn,
        "allow_search": allow_search,
    }
