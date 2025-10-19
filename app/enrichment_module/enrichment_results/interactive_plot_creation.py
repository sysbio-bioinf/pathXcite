"""Provides functions to create interactive bubble and bar charts for enrichment results"""

# --- Standard Library Imports ---
import json
import uuid
from html import escape

# --- Third Party Imports ---
import pandas as pd

# --- Public Functions ---


def generate_interactive_bubble_chart_html(
    df: pd.DataFrame, output_file: str = "interactive_bubble_chart.html",
    title: str = "Overrepresentation Analysis Bubble Chart", term_col: str = "Term"
) -> None:
    """
    Enhanced interactive bubble chart with:
      - Card UI
      - Search + Top-N + sort controls
      - Adjustable bubble min/max size
      - Color scheme pickers (Viridis/Turbo/Cividis/Plasma/Magma)
      - Export PNG/CSV buttons
      - Responsive height based on Top N

    Args:
        df (pd.DataFrame): DataFrame containing enrichment results.
        output_file (str): Path to save the generated HTML file.
        title (str): Title of the plot.
        term_col (str): Name of the column containing term names.

    Returns:
        None
    """

    df = df.copy()
    if term_col not in df.columns:
        raise ValueError(f"term_col '{term_col}' not found in DataFrame")

    # Default set
    candidates = [
        "Overlap Count", "Total Genes", "Overlap Ratio", "-log10 P-value",
        "-log10 Adjusted P-value", "Odds Ratio", "Combined Score", "Gene Count"
    ]
    # Filter columns
    present_cols, numeric_cols = _filter_valid_columns(df, candidates)

    if not present_cols:
        # fallback: use all numeric columns + term
        numeric_cols = [c for c in df.columns if c !=
                        term_col and pd.api.types.is_numeric_dtype(df[c])]
        present_cols = numeric_cols[:]

    # Ensure JSON-safe
    df = df.replace({pd.NA: None}).where(pd.notnull(df), None)
    json_data = df.to_json(orient="records")
    valid_columns_json = json.dumps(present_cols)
    numeric_columns_json = json.dumps(numeric_cols)

    # Unique ID for HTML element IDs
    uid = uuid.uuid4().hex

    # The following is the complete HTML content with embedded JavaScript for interactivity
    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>{escape(title)}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
    :root {{
      --bg: #0b0c0f;
      --card: #12151b;
      --text: #e7eaf0;
      --muted: #a5adba;
      --border: #1f2430;
      --ring: rgba(76,201,240,.35);
      --shadow: 0 8px 24px rgba(0,0,0,.35);
      --accent: #4cc9f0;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f8fafc;
        --card: #ffffff;
        --text: #0f172a;
        --muted: #475569;
        --border: #e2e8f0;
        --ring: rgba(37,99,235,.25);
        --shadow: 0 6px 18px rgba(15,23,42,.08);
        --accent: #2563eb;
      }}
    }}
    *{{box-sizing:border-box}}
    body{{
      margin:0; padding:20px; color:var(--text); background:
      radial-gradient(900px 600px at 90% -10%, rgba(76,201,240,.10), transparent 60%),
      radial-gradient(700px 600px at -10% 10%, rgba(124,58,237,.10), transparent 60%),
      var(--bg);
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    }}
    .header{{
      display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:14px;
    }}
    h1{{margin:0; font-size:15px}}
    .pill{{display:inline-flex; gap:8px; align-items:center; padding:8px 12px; border-radius:999px; border:1px solid var(--border); background:var(--card)}}
    button.icon{{border:1px solid var(--border); background:var(--card); color:var(--text); border-radius:8px; padding:6px 10px; cursor:pointer; box-shadow:var(--shadow)}}
    button.icon:hover{{box-shadow:0 0 0 4px var(--ring)}}

    .layout{{
      display:grid; grid-template-columns: 320px 1fr; gap:18px;
    }}
    @media (max-width: 900px){{
      .layout{{grid-template-columns: 1fr}}
    }}

    .card{{background:var(--card); border:1px solid var(--border); border-radius:16px; box-shadow:var(--shadow); overflow:hidden}}
    .card .header-bar{{padding:10px 12px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center}}
    .card .title{{font-weight:700; font-size:14px}}
    .card .body{{padding:12px}}

    .controls .group{{display:flex; flex-direction:column; gap:6px; margin-bottom:10px}}
    label{{font-size:12px; color:var(--muted)}}
    select, input[type="number"], input[type="search"]{{
      width:100%; padding:8px; border:1px solid var(--border); border-radius:10px; background:transparent; color:var(--text)
    }}
    .row{{display:flex; gap:8px}}
    .helper{{color:var(--muted); font-size:12px}}

    .actions{{display:flex; gap:8px; flex-wrap:wrap}}
    .actions button{{padding:6px 10px; border-radius:10px}}

    .plot-wrap{{min-height:420px}}
    .mono{{font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace}}
    </style>
    </head>
    <body>
      <div class="header">
        <h1>{escape(title)}</h1>
      </div>

      <div class="layout">
        <div class="card">
          
          <div class="body controls">
            <div class="group">
              <label for="search_{uid}">Search {escape(term_col)}</label>
              <input type="search" id="search_{uid}" placeholder="type to filter...">
            </div>

            <div class="row">
              <div class="group" style="flex:1">
                <label for="x_{uid}">X-Axis</label>
                <select id="x_{uid}"></select>
              </div>
              <div class="group" style="flex:1">
                <label for="size_{uid}">Bubble Size</label>
                <select id="size_{uid}"></select>
              </div>
            </div>

            <div class="row">
              <div class="group" style="flex:1">
                <label for="color_{uid}">Color</label>
                <select id="color_{uid}"></select>
              </div>
              <div class="group" style="flex:1">
                <label for="scale_{uid}">Colorscale</label>
                <select id="scale_{uid}">
                  <option value="Viridis">Viridis</option>
                  <option value="Turbo">Turbo</option>
                  <option value="Cividis">Cividis</option>
                  <option value="Plasma">Plasma</option>
                  <option value="Magma">Magma</option>
                </select>
              </div>
            </div>

            <div class="row">
              <div class="group" style="flex:1">
                <label for="sortby_{uid}">Sort By</label>
                <select id="sortby_{uid}"></select>
              </div>
              <div class="group" style="flex:1">
                <label for="order_{uid}">Sort Order</label>
                <select id="order_{uid}">
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
            </div>

            <div class="row">
              <div class="group" style="flex:1">
                <label for="top_{uid}">Top-N</label>
                <input type="number" id="top_{uid}" min="1" value="20">
              </div>
              <div class="group" style="flex:1">
                <label for="ypos_{uid}">Y-Axis Order</label>
                <select id="ypos_{uid}">
                  <option value="top">Highest X on Top</option>
                  <option value="bottom">Highest X on Bottom</option>
                </select>
              </div>
            </div>

            <div class="row">
              <div class="group" style="flex:1">
                <label for="minsize_{uid}">Min Bubble Size</label>
                <input type="number" id="minsize_{uid}" min="1" max="300" value="10">
              </div>
              <div class="group" style="flex:1">
                <label for="maxsize_{uid}">Max Bubble Size</label>
                <input type="number" id="maxsize_{uid}" min="20" max="300" value="100">
              </div>
            </div>

            <div class="helper">Tip: drag in the plot to pan; use the modebar to zoom/reset.</div>
          </div>
        </div>

        <div class="card">
          <div class="header-bar">
            <div class="title">Chart</div>
          </div>
          <div class="body plot-wrap">
            <div id="bubble_{uid}" style="width:100%;height:100%"></div>
          </div>
        </div>
      </div>

    <script>
    (function(){{
      const RAW = {json_data};
      const VALID = {valid_columns_json};
      const NUMERIC = {numeric_columns_json};
      const TERM = {json.dumps(term_col)};

      
      

      // Controls
      const q = (id) => document.getElementById(id);
      const els = {{
        search: q("search_{uid}"),
        x: q("x_{uid}"),
        size: q("size_{uid}"),
        color: q("color_{uid}"),
        scale: q("scale_{uid}"),
        sortby: q("sortby_{uid}"),
        order: q("order_{uid}"),
        top: q("top_{uid}"),
        ypos: q("ypos_{uid}"),
        minsize: q("minsize_{uid}"),
        maxsize: q("maxsize_{uid}"),
        plot: q("bubble_{uid}")
      }};

      const populate = (sel, options) => {{
        sel.innerHTML = "";
        options.forEach(v => {{
          const o = document.createElement("option");
          o.value = v; o.textContent = v; sel.appendChild(o);
        }});
      }};
      populate(els.x, NUMERIC.length ? NUMERIC : VALID);
      populate(els.size, NUMERIC.length ? NUMERIC : VALID);
      populate(els.color, VALID);
      populate(els.sortby, VALID);

      // Defaults if present
      if (VALID.includes("Overlap Ratio")) els.x.value = "Overlap Ratio";
      if (VALID.includes("-log10 P-value")) els.color.value = "-log10 P-value";
      if (VALID.includes("-log10 Adjusted P-value")) els.sortby.value = "-log10 Adjusted P-value";


      const compute = () => {{
        const search = (els.search.value||"").trim().toLowerCase();
        const sortBy = els.sortby.value;
        const asc = els.order.value === "asc";
        let top = parseInt(els.top.value, 10);
        if (!Number.isFinite(top) || top <= 0) top = RAW.length;

        // Filter by term
        let rows = RAW.filter(r => {{
          const t = (r[TERM] ?? "").toString().toLowerCase();
          return !search || t.includes(search);
        }});

        // Stable sort (copy first)
        rows = rows.slice().sort((a,b) => {{
          const av = +a[sortBy] || 0;
          const bv = +b[sortBy] || 0;
          return asc ? av - bv : bv - av;
        }});

        rows = rows.slice(0, Math.min(top, rows.length));

        // Y order based on X values
        const xKey = els.x.value;
        const topMeans = els.ypos.value === "top";
        rows.sort((a,b) => topMeans ? (+b[xKey]||0) - (+a[xKey]||0) : (+a[xKey]||0) - (+b[xKey]||0));

        // Sizes normalization
        const sizeKey = els.size.value;
        const sizes = rows.map(r => +r[sizeKey] || 0);
        const smin = Math.min(...sizes);
        const smax = Math.max(...sizes, 1);
        const minS = Math.max(1, +els.minsize.value || 10);
        const maxS = Math.max(minS+1, +els.maxsize.value || 100);
        const scaled = sizes.map(v => {{
          return minS + (smax===smin ? 0.5 : (v - smin)/(smax - smin))*(maxS - minS);
        }});

        return {{
          rows,
          x: rows.map(r => r[xKey]),
          y: rows.map(r => r[TERM]),
          size: scaled,
          color: rows.map(r => r[els.color.value]),
        }};
      }};

      const render = () => {{
        const R = compute();
        const layout = {{
          title: {json.dumps(title)},
          xaxis: {{ title: els.x.value }},
          yaxis: {{ title: TERM, automargin: true }},
          height: Math.max(420, 35 * (R.rows.length || 1)),
          margin: {{l: 80, r: 30, t: 50, b: 50}},
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)"
        }};
        const trace = {{
          type: "scatter",
          mode: "markers",
          x: R.x,
          y: R.y,
          marker: {{
            size: R.size,
            color: R.color,
            colorscale: els.scale.value,
            showscale: true,
            sizemode: "diameter",
            opacity: 0.85,
            line: {{width: 0.5, color: "rgba(0,0,0,0.35)"}}
          }},
          hovertemplate:
            TERM + ": %{{y}}<br>" +
            els.x.value + ": %{{x}}<br>" +
            els.size.value + " (size)" + ": %{{marker.size:.2f}}<extra></extra>"
        }};
        const config = {{
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ["autoScale2d", "toggleSpikelines"]
        }};
        Plotly.newPlot(els.plot, [trace], layout, config);
      }};

      // Wire events
      ["input","change"].forEach(ev => {{
        [els.search, els.x, els.size, els.color, els.scale, els.sortby, els.order, els.top, els.ypos, els.minsize, els.maxsize]
          .forEach(el => el.addEventListener(ev, render));
      }});


      // Initial render
      render();
      window.addEventListener("resize", () => Plotly.Plots.resize(els.plot));
    }})();
    </script>
    </body>
    </html>
    """

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Interactive bubble chart saved to {output_file}")


def generate_interactive_bar_chart_html(
    df: pd.DataFrame, output_file: str = "interactive_bubble_chart.html",
    title: str = "Overrepresentation Analysis Bar Chart", term_col: str = "Term"
) -> None:
    """
    Enhanced interactive bar chart with:
      - Card UI
      - Search + Top-N + sort controls
      - Color scheme pickers (Viridis/Turbo/Cividis/Plasma/Magma)
      - Export PNG/CSV buttons
      - Responsive height based on Top N

    Args:
        df (pd.DataFrame): DataFrame containing enrichment results.
        output_file (str): Path to save the generated HTML file.
        title (str): Title of the plot.
        term_col (str): Name of the column containing term names.

    Returns:
        None
    """

    df = df.copy()
    if term_col not in df.columns:
        raise ValueError(f"term_col '{term_col}' not found in DataFrame")

    candidates = [
        "Overlap Count", "Total Genes", "Overlap Ratio", "-log10 P-value",
        "-log10 Adjusted P-value", "Odds Ratio", "Combined Score", "Gene Count"
    ]
    present_cols, numeric_cols = _filter_valid_columns(df, candidates)
    if not present_cols:
        numeric_cols = [c for c in df.columns if c !=
                        term_col and pd.api.types.is_numeric_dtype(df[c])]
        present_cols = numeric_cols[:]

    df = df.replace({pd.NA: None}).where(pd.notnull(df), None)
    json_data = df.to_json(orient="records")
    valid_columns_json = json.dumps(present_cols)
    numeric_columns_json = json.dumps(numeric_cols)
    uid = uuid.uuid4().hex

    html = f"""<!DOCTYPE html>
  <html lang="en">
  <head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{escape(title)}</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
  /* same base styles as bubble for consistency */
  :root {{
    --bg: #0b0c0f; --card: #12151b; --text: #e7eaf0; --muted: #a5adba; --border: #1f2430;
    --ring: rgba(76,201,240,.35); --shadow: 0 8px 24px rgba(0,0,0,.35); --accent:#4cc9f0;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --muted: #475569; --border: #e2e8f0;
      --ring: rgba(37,99,235,.25); --shadow: 0 6px 18px rgba(15,23,42,.08); --accent:#2563eb;
    }}
  }}
  *{{box-sizing:border-box}}
  body{{margin:0; padding:20px; color:var(--text); background:
    radial-gradient(900px 600px at 90% -10%, rgba(76,201,240,.10), transparent 60%),
    radial-gradient(700px 600px at -10% 10%, rgba(124,58,237,.10), transparent 60%),
    var(--bg);
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  }}
  .header{{display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:14px}}
  h1{{margin:0; font-size:15px}}
  .pill{{display:inline-flex; gap:8px; align-items:center; padding:8px 12px; border-radius:999px; border:1px solid var(--border); background:var(--card)}}
  button.icon{{border:1px solid var(--border); background:var(--card); color:var(--text); border-radius:8px; padding:6px 10px; cursor:pointer; box-shadow:var(--shadow)}}
  button.icon:hover{{box-shadow:0 0 0 4px var(--ring)}}

  .layout{{display:grid; grid-template-columns: 320px 1fr; gap:18px}}
  @media (max-width: 900px){{.layout{{grid-template-columns:1fr}}}}

  .card{{background:var(--card); border:1px solid var(--border); border-radius:16px; box-shadow:var(--shadow); overflow:hidden}}
  .card .header-bar{{padding:10px 12px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center}}
  .card .title{{font-weight:700; font-size:14px}}
  .card .body{{padding:12px}}

  .controls .group{{display:flex; flex-direction:column; gap:6px; margin-bottom:10px}}
  label{{font-size:12px; color:var(--muted)}}
  select, input[type="number"], input[type="search"]{{width:100%; padding:8px; border:1px solid var(--border); border-radius:10px; background:transparent; color:var(--text)}}
  .row{{display:flex; gap:8px}}
  .helper{{color:var(--muted); font-size:12px}}

  .plot-wrap{{min-height:420px}}
  </style>
  </head>
  <body>
    <div class="header">
      <h1>{escape(title)}</h1>
    </div>

    <div class="layout">
      <div class="card">
        
        <div class="body controls">
          <div class="group">
            <label for="search_{uid}">Search {escape(term_col)}</label>
            <input type="search" id="search_{uid}" placeholder="type to filter...">
          </div>

          <div class="row">
            <div class="group" style="flex:1">
              <label for="x_{uid}">X-Axis</label>
              <select id="x_{uid}"></select>
            </div>
            <div class="group" style="flex:1">
              <label for="color_{uid}">Color</label>
              <select id="color_{uid}"></select>
            </div>
          </div>

          <div class="row">
            <div class="group" style="flex:1">
              <label for="scale_{uid}">Colorscale</label>
              <select id="scale_{uid}">
                <option value="Viridis">Viridis</option>
                <option value="Turbo">Turbo</option>
                <option value="Cividis">Cividis</option>
                <option value="Plasma">Plasma</option>
                <option value="Magma">Magma</option>
              </select>
            </div>
            <div class="group" style="flex:1">
              <label for="sortby_{uid}">Sort By</label>
              <select id="sortby_{uid}"></select>
            </div>
          </div>

          <div class="row">
            <div class="group" style="flex:1">
              <label for="order_{uid}">Sort Order</label>
              <select id="order_{uid}">
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
            <div class="group" style="flex:1">
              <label for="top_{uid}">Top-N</label>
              <input type="number" id="top_{uid}" min="1" value="20">
            </div>
          </div>

          <div class="row">
            <div class="group" style="flex:1">
              <label for="ypos_{uid}">Y-Axis Order</label>
              <select id="ypos_{uid}">
                <option value="top">Highest X on Top</option>
                <option value="bottom">Highest X on Bottom</option>
              </select>
            </div>
          </div>

          <div class="helper">Bars are horizontal; highest values can be placed at the top or bottom.</div>
        </div>
      </div>

      <div class="card">
        <div class="header-bar"><div class="title">Chart</div></div>
        <div class="body plot-wrap">
          <div id="bar_{uid}" style="width:100%;height:100%"></div>
        </div>
      </div>
    </div>

  <script>
  (function(){{
    const RAW = {json_data};
    const VALID = {valid_columns_json};
    const NUMERIC = {numeric_columns_json};
    const TERM = {json.dumps(term_col)};



    const q = (id)=>document.getElementById(id);
    const els = {{
      search: q("search_{uid}"),
      x: q("x_{uid}"),
      color: q("color_{uid}"),
      scale: q("scale_{uid}"),
      sortby: q("sortby_{uid}"),
      order: q("order_{uid}"),
      top: q("top_{uid}"),
      ypos: q("ypos_{uid}"),
      plot: q("bar_{uid}"),
    }};

    const populate = (sel, options) => {{
      sel.innerHTML = "";
      options.forEach(v => {{
        const o = document.createElement("option");
        o.value = v; o.textContent = v; sel.appendChild(o);
      }});
    }};
    populate(els.x, NUMERIC.length ? NUMERIC : VALID);
    populate(els.color, VALID);
    populate(els.sortby, VALID);
    if (VALID.includes("Overlap Ratio")) els.x.value = "Overlap Ratio";
    if (VALID.includes("-log10 P-value")) els.color.value = "-log10 P-value";
    if (VALID.includes("-log10 Adjusted P-value")) els.sortby.value = "-log10 Adjusted P-value";


    const compute = () => {{
      const search = (els.search.value||"").trim().toLowerCase();
      const sortBy = els.sortby.value;
      const asc = els.order.value === "asc";
      let top = parseInt(els.top.value, 10);
      if (!Number.isFinite(top) || top <= 0) top = RAW.length;

      // Filter by term
      let rows = RAW.filter(r => {{
        const t = (r[TERM] ?? "").toString().toLowerCase();
        return !search || t.includes(search);
      }});

      // Sort then slice
      rows = rows.slice().sort((a,b) => {{
        const av = +a[sortBy] || 0;
        const bv = +b[sortBy] || 0;
        return asc ? av - bv : bv - av;
      }}).slice(0, Math.min(top, rows.length));

      // Order by X for y-axis placement
      const xKey = els.x.value;
      const topMeans = els.ypos.value === "top";
      rows.sort((a,b) => topMeans ? (+b[xKey]||0) - (+a[xKey]||0) : (+a[xKey]||0) - (+b[xKey]||0));

      return {{
        rows,
        x: rows.map(r => r[xKey]),
        y: rows.map(r => r[TERM]),
        c: rows.map(r => r[els.color.value])
      }};
    }};

    const render = () => {{
      const R = compute();
      const layout = {{
        title: {json.dumps(title)},
        xaxis: {{ title: els.x.value }},
        yaxis: {{ title: TERM, automargin: true }},
        margin: {{l: 100, r: 30, t: 50, b: 50}},
        height: Math.max(420, 30 * (R.y.length || 1)),
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)"
      }};
      const trace = {{
        type: "bar",
        orientation: "h",
        x: R.x,
        y: R.y,
        marker: {{
          color: R.c,
          colorscale: els.scale.value,
          showscale: true
        }},
        hovertemplate:
          TERM + ": %{{y}}<br>" +
          els.x.value + ": %{{x}}<extra></extra>",
        text: R.y,
        textposition: "auto"
      }};
      const config = {{
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ["autoScale2d", "toggleSpikelines"]
      }};
      Plotly.newPlot(els.plot, [trace], layout, config);
    }};

    ["input","change"].forEach(ev => {{
      [els.search, els.x, els.color, els.scale, els.sortby, els.order, els.top, els.ypos]
        .forEach(el => el.addEventListener(ev, render));
    }});


    render();
    window.addEventListener("resize", () => Plotly.Plots.resize(els.plot));
  }})();
  </script>
  </body>
  </html>
  """
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Interactive bar chart saved to {output_file}")

# --- Private Functions ---


def _filter_valid_columns(df: pd.DataFrame, candidates: list[str]) -> tuple[list[str], list[str]]:
    """Filter candidate columns to those present in the DataFrame, and identify numeric columns.

    Args:
        df (pd.DataFrame): The DataFrame to filter.
        candidates (list[str]): List of candidate column names.

    Returns:
        tuple[list[str], list[str]]: A tuple containing two lists:
            - The first list contains the valid column names present in the DataFrame.
            - The second list contains the numeric column names.
    """
    cols = [c for c in candidates if c in df.columns]

    # Keep numeric-only where needed
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    return cols, numeric_cols
