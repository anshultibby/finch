---
name: visualization
description: Generate interactive HTML/JS visualizations rendered in the Charts tab. Write a .js file — auto-wrapped in an HTML shell with Finch theming.
homepage:
metadata:
  emoji: "📊"
  category: visualization
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Visualization Skill

Write a `.js` file to `chat_files/visualizations/`. The backend wraps it in an HTML shell with Finch theming and renders it in the Charts tab. Full creative freedom — any JS library, any technique.

## Quick Start

Write one script that fetches data and outputs the visualization (don't split into multiple files):

```python
write_chat_file(filename="build_viz.py", file_content="""
import json
from skills.financial_modeling_prep.scripts.quote.price import get_price

prices = {t: get_price(symbol=t) for t in ['AAPL', 'MSFT', 'GOOGL']}
data = [{"name": t, "price": p[0]["price"]} for t, p in prices.items()]

js = f\"\"\"// @lib d3
const data = {json.dumps(data)};
const svg = d3.select('#root').append('svg').attr('viewBox', '0 0 600 400');
svg.selectAll('rect').data(data).enter().append('rect')
  .attr('x', (d, i) => i * 150 + 50).attr('y', d => 380 - d.price)
  .attr('width', 100).attr('height', d => d.price)
  .attr('fill', 'var(--accent)').attr('rx', 4);
\"\"\"

with open('chat_files/visualizations/prices.js', 'w') as f:
    f.write(js)
""")
bash(command="python3 chat_files/build_viz.py")
```

Reference in reply:
```
{{visualization:visualizations/returns.js}}
```

## Environment

Your JS runs in an HTML page with:
- **`#root`** — empty `<div>` filling the viewport
- **CDN libraries** — auto-loaded from `// @lib` comments
- **`window.finch.fetch(url, body?)`** — postMessage bridge for live API calls
- **Finch CSS variables** — `--accent` `--pos` `--neg` `--blue` `--purple` `--amber` `--surface` `--text` `--text-2` `--bg` `--border` `--radius` `--radius-lg`
- **Base classes** — pre-built utility classes for common patterns (see below)

## Base Classes

Layout:
- `.card` — white card with border + 20px padding + large radius
- `.card-sm` — compact card (12px padding, smaller radius)
- `.grid` `.grid-2` `.grid-3` `.grid-4` — CSS grid with gap
- `.flex` `.flex-col` `.gap-sm` `.gap-md` `.gap-lg` `.items-center` `.justify-between`

Typography:
- `.kpi` — large bold number (28px), tabular nums
- `.kpi-sm` — medium bold number (20px), tabular nums
- `.label` — uppercase small muted label (11px)
- `.title` — section title (16px semibold)
- `.subtitle` — secondary text (13px muted)
- `.tabular` — tabular-nums for aligned columns
- `.mono` — monospace font (12px)

Color:
- `.positive` `.negative` — semantic green/red text
- `.badge` `.badge-pos` `.badge-neg` `.badge-accent` — pill badges

Other:
- `.tooltip` — absolute-positioned dark tooltip (pair with mouse events)

## Libraries

Add `// @lib` at the top of your JS:
```javascript
// @lib d3
// @lib https://cdn.jsdelivr.net/npm/topojson@3/dist/topojson.min.js
```

Shortnames: `d3`, `three` (ES module), `chartjs`, `plotly`, `leaflet` (+CSS), `maplibre` (+CSS), `mermaid`, `anime`, `gsap`, `katex` (+CSS), `marked`, `tone`. Or any full CDN URL.

## Data

**Static:** Embed via Python f-strings with `json.dumps()`.

**Live:** Call any backend API directly from the JS via the postMessage bridge:
```javascript
const movers = await window.finch.fetch('/api/market/movers');
const holdings = await window.finch.fetch('/api/portfolio/holdings');
```

For custom data processing, write a companion `.py` script and call it via `run-script`:
```javascript
const data = await window.finch.fetch('/api/visualizations/run-script',
  {script: 'visualizations/fetch_data.py'});
```

## Finch Design Principles

- **Data-dense, not cluttered.** Every pixel should communicate. No decorative borders, gradients, or chrome. White space is structure.
- **Light and clean.** White cards (`var(--surface)`) on warm gray (`var(--bg)`). Subtle 1px borders (`var(--border)`), no heavy shadows.
- **Typography does the work.** System font stack. Large bold numbers for KPIs. Small muted labels. Tabular nums for financial data (`font-variant-numeric: tabular-nums`).
- **Color is semantic.** Green = gain/positive. Red = loss/negative. Use `var(--pos)` and `var(--neg)`. Accent green (`var(--accent)`) for brand/primary. Muted palette otherwise — reserve saturated color for data.
- **Responsive and full-bleed.** Fill the viewport. Use `viewBox` for SVGs. No fixed pixel widths that break on mobile.
- **Interactive but not noisy.** Hover states, tooltips, click-to-filter. No autoplaying animations or scroll-jacking.
- **Professional financial aesthetic.** Think Bloomberg terminal meets modern SaaS, not playful or whimsical. Clean axes, gridlines, proper number formatting ($, %, commas).

## File Naming

Descriptive: `portfolio_treemap.js` not `chart1.js`. The filename becomes the gallery title.
