"""
finch_viz — Dashboard builder for the Finch sandbox.

Model writes pure Python (Plotly figures + data), this module handles
all HTML/CSS/JS rendering into a dark-themed responsive grid.

Usage:
    from finch_viz import Dashboard
    import plotly.graph_objects as go

    fig = go.Figure(go.Bar(x=["AAPL","MSFT"], y=[195, 430]))
    fig.update_layout(title="Revenue ($B)")

    dash = Dashboard("Earnings Overview", subtitle="Q2 2026")
    dash.kpi([("Revenue", "$45.2B", "green"), ("EPS Beat", "78%", "blue")])
    dash.plot(fig)
    dash.plot([fig2, fig3])  # side by side in one row
    dash.table(["Ticker", "Price", "Change"], [["AAPL", "$195", "+2.3%"], ...])
    dash.save("chat_files/visualizations/earnings.html")
"""

import json
import os
from html import escape

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

_COLORS = {
    "blue": "#3b82f6", "green": "#22c55e", "red": "#ef4444",
    "amber": "#f59e0b", "purple": "#a855f7", "pink": "#ec4899",
    "teal": "#14b8a6",
}

_BASE_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #0a0e17; --surface: #111827; --border: #1e293b;
  --text: #e2e8f0; --text-muted: #64748b; --text-secondary: #94a3b8;
  --blue: #3b82f6; --green: #22c55e; --red: #ef4444;
  --amber: #f59e0b; --purple: #a855f7;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', system-ui, sans-serif;
  background: var(--bg); color: var(--text);
  padding: 24px; min-height: 100vh; -webkit-font-smoothing: antialiased;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.dash-header { margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
.dash-header h1 {
  font-size: 24px; font-weight: 700;
  background: linear-gradient(135deg, #f5f5f5, #94a3b8);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.dash-header .subtitle { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
.kpi-row { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.kpi {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px 20px; text-align: center; flex: 1; min-width: 120px;
}
.kpi .value { font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; }
.kpi .label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
.grid-row { display: grid; gap: 20px; margin-bottom: 24px; }
.cell {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden; min-width: 0;
}
.cell-title {
  padding: 14px 20px 0; font-size: 14px; font-weight: 600; color: var(--text);
}
.cell .plotly-chart { width: 100%; }
.cell table { width: 100%; border-collapse: collapse; }
.cell th {
  text-align: left; padding: 10px 16px; font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.5px; color: var(--text-muted); border-bottom: 1px solid var(--border); font-weight: 600;
}
.cell td { padding: 10px 16px; font-size: 13px; border-bottom: 1px solid rgba(30,41,59,0.4); }
.cell tr:hover { background: rgba(59,130,246,0.04); }
.cell .num { text-align: right; font-variant-numeric: tabular-nums; font-family: 'SF Mono', ui-monospace, monospace; }
.cell .ticker { font-weight: 700; color: var(--blue); }
.text-green { color: var(--green); } .text-red { color: var(--red); }
.text-blue { color: var(--blue); } .text-amber { color: var(--amber); }
.source { font-size: 11px; color: #475569; padding: 8px 20px 12px; }
@media (max-width: 800px) { .grid-row { grid-template-columns: 1fr !important; } }
"""

_DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", size=12, family="-apple-system, BlinkMacSystemFont, 'Inter', sans-serif"),
    margin=dict(t=36, r=16, b=40, l=48),
    xaxis=dict(gridcolor="#1e293b", linecolor="#1e293b", zerolinecolor="#1e293b"),
    yaxis=dict(gridcolor="#1e293b", linecolor="#1e293b", zerolinecolor="#1e293b"),
    colorway=["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#ec4899", "#14b8a6", "#6366f1"],
    legend=dict(font=dict(color="#94a3b8")),
)


class Dashboard:
    """Build a dark-themed dashboard from Plotly figures and data tables."""

    def __init__(self, title: str, subtitle: str = ""):
        self.title = title
        self.subtitle = subtitle
        self._sections: list[str] = []
        self._plot_counter = 0
        self._scripts: list[str] = []
        self._needs_plotly = False

    def kpi(self, items: list[tuple]):
        """Add a row of KPI cards.

        Args:
            items: List of (label, value) or (label, value, color) tuples.
                   color is one of: blue, green, red, amber, purple.
        """
        cards = []
        for item in items:
            label, value = item[0], item[1]
            color = item[2] if len(item) > 2 else None
            style = f' style="color:{_COLORS[color]}"' if color and color in _COLORS else ""
            cards.append(
                f'<div class="kpi">'
                f'<div class="value"{style}>{escape(str(value))}</div>'
                f'<div class="label">{escape(str(label))}</div>'
                f"</div>"
            )
        self._sections.append(f'<div class="kpi-row">{"".join(cards)}</div>')

    def plot(self, figs, title: str = "", height: int = 400, widths: list[int] | None = None):
        """Add one or more Plotly figures as a grid row.

        Args:
            figs: A single Plotly figure or a list of figures (shown side by side).
            title: Optional title shown above the chart(s).
            height: Chart height in pixels.
            widths: Relative column widths, e.g. [2,1] for 2:1 ratio.
                    Defaults to equal widths.
        """
        if not isinstance(figs, list):
            figs = [figs]

        self._needs_plotly = True
        if widths and len(widths) == len(figs):
            col_css = " ".join(f"{w}fr" for w in widths)
        else:
            col_css = " ".join(["1fr"] * len(figs))
        cells = []
        for fig in figs:
            self._plot_counter += 1
            div_id = f"plot{self._plot_counter}"

            fig_layout = {**_DARK_LAYOUT, "height": height}
            if fig.layout.title and fig.layout.title.text:
                fig_layout["title"] = dict(text=fig.layout.title.text, font=dict(color="#e2e8f0", size=15))
            fig.update_layout(**fig_layout)

            fig_json = fig.to_json()
            self._scripts.append(
                f"(function() {{"
                f"  var d = JSON.parse('{_escape_js(fig_json)}');"
                f"  Plotly.newPlot('{div_id}', d.data, d.layout, {{responsive:true, displayModeBar:false}});"
                f"}})();"
            )
            cells.append(
                f'<div class="cell">'
                f'<div id="{div_id}" class="plotly-chart"></div>'
                f"</div>"
            )

        title_html = f'<div class="cell-title" style="margin-bottom:8px">{escape(title)}</div>' if title else ""
        self._sections.append(
            f'{title_html}<div class="grid-row" style="grid-template-columns:{col_css}">{"".join(cells)}</div>'
        )

    def table(self, headers: list[str], rows: list[list], title: str = ""):
        """Add a data table.

        Args:
            headers: Column header strings.
            rows: List of rows, each a list of cell values.
                  Cell values can be strings or (value, css_class) tuples.
            title: Optional title above the table.
        """
        ths = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
        trs = []
        for row in rows:
            tds = []
            for cell in row:
                if isinstance(cell, tuple):
                    val, cls = cell[0], cell[1]
                    tds.append(f'<td class="{cls}">{escape(str(val))}</td>')
                else:
                    tds.append(f"<td>{escape(str(cell))}</td>")
            trs.append(f"<tr>{''.join(tds)}</tr>")

        title_html = f'<div class="cell-title">{escape(title)}</div>' if title else ""
        self._sections.append(
            f'<div class="cell">'
            f"{title_html}"
            f'<div style="overflow-x:auto;padding:0 0 12px">'
            f"<table><thead><tr>{ths}</tr></thead>"
            f"<tbody>{''.join(trs)}</tbody></table>"
            f"</div></div>"
        )

    def html(self, content: str):
        """Add raw HTML for anything the built-in components don't cover."""
        self._sections.append(content)

    def save(self, output: str = "chat_files/visualizations/output.html"):
        """Render the dashboard to an HTML file."""
        cdn = f'<script src="{_PLOTLY_CDN}"></script>' if self._needs_plotly else ""

        header = f'<div class="dash-header"><h1>{escape(self.title)}</h1>'
        if self.subtitle:
            header += f'<div class="subtitle">{escape(self.subtitle)}</div>'
        header += "</div>"

        body = "\n".join(self._sections)
        scripts = "\n".join(self._scripts)

        html = (
            f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            f"<meta charset=\"UTF-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>{escape(self.title)}</title>\n"
            f"{cdn}\n<style>\n{_BASE_CSS}</style>\n</head>\n"
            f"<body>\n{header}\n{body}\n"
            f"<script>\n{scripts}\n</script>\n"
            f"</body>\n</html>"
        )

        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w") as f:
            f.write(html)
        return output


def _escape_js(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
