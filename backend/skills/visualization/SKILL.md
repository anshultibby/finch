---
name: visualization
description: Generate rich, interactive HTML visualizations — charts, dashboards, and data explorers — rendered in the Charts tab. Covers chart type selection, design system, interaction patterns, and library guidance.
homepage:
metadata:
  emoji: "���"
  category: visualization
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Visualization Skill

You generate self-contained HTML files that render in the user's Charts tab. Each file is a complete interactive visualization — no external dependencies except CDN-loaded libraries.

**You have no limits.** The sandbox renders a full browser environment — anything that runs in a modern browser works: CSS animations, WebGL, Canvas, SVG, Web Audio, requestAnimationFrame, pointer events, scroll-driven animations, CSS 3D transforms, HTML5 drag-and-drop. Use the full power of the web platform.

**Make every visualization impressive and useful.** Don't just show data — make it come alive. Smooth animated transitions, satisfying hover effects, fluid interactions. The goal is visualizations that are as polished as the best data products (Bloomberg Terminal, Robinhood, Linear, Stripe Dashboard) — not generic chart library output. When a user sees your visualization, they should feel like they're using a premium product.

**Be opinionated about what looks good.** Don't default to the boring option. If an animated entrance makes the chart more engaging, add it. If a custom tooltip with sparklines would be more informative, build it. If the data would be stunning as a 3D surface or animated flow, go for it. Push the boundaries of what the user expects from an AI assistant.

## When to Use This Skill

- User asks for any chart, graph, plot, dashboard, or visual analysis
- User says "show me", "visualize", "plot", "chart", "compare visually", "dashboard"
- You have data that would be better understood visually than as a table
- After running an analysis, when the results have a visual story to tell

## Output Pattern

Every visualization is a single `.html` file saved to the sandbox:

```bash
cat > /home/user/visualization_name.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visualization Title</title>
  <!-- libraries loaded from CDN -->
  <style>/* all styles inline */</style>
</head>
<body>
  <!-- visualization markup -->
  <script>/* all logic inline */</script>
</body>
</html>
HTMLEOF
```

Then reference it in your reply using the visualization marker:

```
[visualization:visualization_name.html]
```

This renders as a clickable chip in the chat. When the user clicks it, it navigates them directly to the Charts tab with that visualization open.

You can also still use `[file:/home/user/visualization_name.html]` to show an inline preview in the chat itself. Use both when you want to give the user an inline preview AND a link to the full Charts tab view:

```
Here's your portfolio breakdown:

[file:/home/user/portfolio_overview.html]

Open it full-screen: [visualization:portfolio_overview.html]
```

The Charts tab renders visualizations in a full-width, full-height iframe. Design for that context — no fixed widths, use the full viewport.

## Library Selection

Pick the right tool for the job. Load from CDN.

**Plotly.js** — Default choice for most charts. Interactive out of the box (hover, zoom, pan). Best for: line charts, bar charts, scatter plots, candlesticks, heatmaps, 3D surfaces.
```html
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
```

**D3.js** — For custom, novel visualizations that don't fit standard chart types. Best for: force-directed graphs, treemaps, custom network diagrams, unusual data shapes.
```html
<script src="https://d3js.org/d3.v7.min.js"></script>
```

**Chart.js** — Lightweight, fast. Best for: simple charts where you want snappy load times and don't need Plotly's interactivity depth.
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
```

**Lightweight Charts (TradingView)** — Purpose-built for financial time series. Best for: candlestick charts, price charts with volume, financial overlays.
```html
<script src="https://unpkg.com/lightweight-charts@4.2.2/dist/lightweight-charts.standalone.production.js"></script>
```

**Three.js** — For 3D visualizations: 3D scatter plots, surface plots, globe visualizations, 3D network graphs.
```html
<script src="https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.min.js"></script>
```

**GSAP** — For polished, timeline-based animations: staggered entrances, scroll-triggered reveals, morphing shapes, complex sequenced transitions.
```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.7/dist/gsap.min.js"></script>
```

**Raw SVG/Canvas** — For simple, precise visualizations where a library is overkill: gauges, single metrics, progress rings, sparklines. Also for custom animations via requestAnimationFrame.

**Multiple libraries in one file** — Totally fine. A dashboard might use Plotly for the main chart, GSAP for entrance animations, and raw SVG for KPI cards.

## Design System

Every visualization must follow these principles. This is what separates "AI-generated chart" from "professional data product."

### Color Palette

```css
:root {
  /* Background & Surface */
  --bg-primary: #0a0a0a;
  --bg-surface: #141414;
  --bg-surface-raised: #1a1a1a;
  --bg-surface-overlay: #222222;
  --border-subtle: #2a2a2a;
  --border-default: #333333;

  /* Text */
  --text-primary: #f5f5f5;
  --text-secondary: #a0a0a0;
  --text-tertiary: #666666;
  --text-muted: #4a4a4a;

  /* Accent (use sparingly — only for primary actions and key data) */
  --accent: #6366f1;
  --accent-hover: #818cf8;
  --accent-subtle: rgba(99, 102, 241, 0.15);

  /* Semantic — for data */
  --positive: #22c55e;
  --positive-subtle: rgba(34, 197, 94, 0.15);
  --negative: #ef4444;
  --negative-subtle: rgba(239, 68, 68, 0.15);
  --warning: #f59e0b;
  --warning-subtle: rgba(245, 158, 11, 0.15);
  --info: #3b82f6;
  --info-subtle: rgba(59, 130, 246, 0.15);

  /* Chart series colors — ordered for visual distinction */
  --series-1: #6366f1;
  --series-2: #22c55e;
  --series-3: #f59e0b;
  --series-4: #ef4444;
  --series-5: #3b82f6;
  --series-6: #a855f7;
  --series-7: #ec4899;
  --series-8: #14b8a6;
}
```

Dark mode is the default. All charts use these colors. Never use library default colors.

### Typography

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  background: var(--bg-primary);
  margin: 0;
  padding: 0;
  -webkit-font-smoothing: antialiased;
}
```

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Page title | 20px | 600 | --text-primary |
| Section header | 15px | 600 | --text-primary |
| Chart title | 14px | 500 | --text-secondary |
| Axis labels | 12px | 400 | --text-tertiary |
| Tick labels | 11px | 400 | --text-muted |
| Tooltip text | 13px | 400 | --text-primary |
| KPI value | 28px | 700 | --text-primary |
| KPI label | 12px | 500 | --text-secondary |

### Spacing & Layout

```css
/* Container for the full visualization */
.viz-container {
  width: 100%;
  min-height: 100vh;
  padding: 24px;
  box-sizing: border-box;
}

/* Card for individual chart/section */
.viz-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

/* Grid for dashboards */
.viz-grid {
  display: grid;
  gap: 16px;
}
```

Use 8px spacing increments: 8, 16, 24, 32, 48.

### Plotly Theme Override

When using Plotly, always apply this layout:

```javascript
const darkLayout = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { family: '-apple-system, BlinkMacSystemFont, Inter, sans-serif', color: '#a0a0a0', size: 12 },
  margin: { t: 40, r: 20, b: 50, l: 60 },
  xaxis: {
    gridcolor: '#2a2a2a',
    linecolor: '#333333',
    zerolinecolor: '#333333',
    tickfont: { size: 11, color: '#666666' },
  },
  yaxis: {
    gridcolor: '#2a2a2a',
    linecolor: '#333333',
    zerolinecolor: '#333333',
    tickfont: { size: 11, color: '#666666' },
  },
  hoverlabel: {
    bgcolor: '#1a1a1a',
    bordercolor: '#333333',
    font: { size: 13, color: '#f5f5f5', family: '-apple-system, BlinkMacSystemFont, Inter, sans-serif' },
  },
  legend: {
    bgcolor: 'transparent',
    font: { size: 12, color: '#a0a0a0' },
  },
};
```

### Chart.js Theme Override

```javascript
Chart.defaults.color = '#a0a0a0';
Chart.defaults.borderColor = '#2a2a2a';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, Inter, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.plugins.tooltip.backgroundColor = '#1a1a1a';
Chart.defaults.plugins.tooltip.borderColor = '#333333';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.titleFont = { size: 13 };
Chart.defaults.plugins.tooltip.bodyFont = { size: 13 };
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyleWidth = 8;
```

## Chart Type Selection

Choose based on what the data is saying, not what's easiest.

### Comparisons
| Data Shape | Chart Type | Notes |
|-----------|-----------|-------|
| Few categories (<8) | Horizontal bar | Easier to read labels. Sort by value. |
| Many categories (8-30) | Treemap or packed bubbles | Shows hierarchy and proportion |
| Two measures to compare | Grouped bar or dumbbell | Dumbbell is cleaner for paired comparisons |
| Ranking | Horizontal bar, sorted | Always sort. Add rank numbers. |

### Time Series
| Data Shape | Chart Type | Notes |
|-----------|-----------|-------|
| Single metric over time | Line chart | Area fill below for emphasis |
| Multiple metrics, same scale | Multi-line | Max 5 lines before it gets noisy |
| Multiple metrics, different scales | Dual-axis or small multiples | Small multiples are usually clearer |
| High-low-open-close | Candlestick | Use lightweight-charts for financial |
| Event markers on timeline | Line + vertical annotations | Mark earnings, splits, news events |

### Distributions
| Data Shape | Chart Type | Notes |
|-----------|-----------|-------|
| Single distribution | Histogram or violin | Show mean/median markers |
| Compare distributions | Box plot or overlaid histograms | Box plots for >3 groups |
| Correlation | Scatter plot | Add regression line + R² |
| Multi-variable correlation | Heatmap | Correlation matrix |

### Part-to-Whole
| Data Shape | Chart Type | Notes |
|-----------|-----------|-------|
| Simple proportions (<6 parts) | Donut chart | Never pie. Donut with center metric. |
| Proportions over time | Stacked area or 100% stacked bar | |
| Hierarchical | Treemap or sunburst | |

### Dashboards
When multiple related metrics need to be shown together, compose a dashboard:
- **Top row**: KPI cards (big numbers with sparklines or delta indicators)
- **Main area**: Primary chart (the story)
- **Bottom or sidebar**: Supporting charts, tables, or filters

## Interaction Patterns

Every chart should reward exploration. These patterns are ordered by priority — implement at least the first two for any chart.

### 1. Rich Tooltips (mandatory)
Tooltips should provide full context, not just the hovered value:
- Show the data point value, formatted with units
- Show relevant context (date, category, percentage of total)
- For financial data: show change from previous period
- Style: dark background, subtle border, 8px border-radius, slight shadow

### 2. Responsive Sizing (mandatory)
```javascript
// Plotly: responsive
Plotly.newPlot(el, data, layout, { responsive: true });

// Chart.js: responsive
new Chart(ctx, { options: { responsive: true, maintainAspectRatio: false } });

// D3: use viewBox
svg.attr('viewBox', `0 0 ${width} ${height}`).attr('width', '100%');
```

### 3. Zoom & Pan (when appropriate)
For time series and scatter plots with many data points. Plotly has this by default. For D3/Canvas, implement brush-to-zoom.

### 4. Click to Drill Down
When data has hierarchy (sector → industry → stock), clicking a segment should zoom in. Use breadcrumbs for navigation back.

### 5. Filters & Controls
For dashboards, add filter controls:
```html
<div class="viz-controls" style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap;">
  <button class="viz-btn active" onclick="filterData('all')">All</button>
  <button class="viz-btn" onclick="filterData('stocks')">Stocks</button>
  <button class="viz-btn" onclick="filterData('etfs')">ETFs</button>
</div>

<style>
.viz-btn {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.viz-btn:hover { border-color: var(--accent); color: var(--text-primary); }
.viz-btn.active { background: var(--accent-subtle); border-color: var(--accent); color: var(--accent-hover); }
</style>
```

### 6. Animated Transitions
When data changes (filter, drill-down), animate smoothly:
- Plotly: `Plotly.animate()` with `transition: { duration: 400, easing: 'cubic-in-out' }`
- D3: `.transition().duration(400).ease(d3.easeCubicInOut)`
- Chart.js: built-in transitions are fine

### 7. Data Tables (for detail)
Complex dashboards should include a sortable data table below or alongside the chart. The user often wants the exact numbers after seeing the visual pattern.

```html
<table class="viz-table">...</table>

<style>
.viz-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}
.viz-table th {
  text-align: left;
  padding: 10px 12px;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border-default);
  position: sticky;
  top: 0;
  background: var(--bg-surface);
  cursor: pointer;
}
.viz-table th:hover { color: var(--text-primary); }
.viz-table td {
  padding: 8px 12px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
}
.viz-table tr:hover td { background: var(--bg-surface-overlay); }
.viz-table .num { font-variant-numeric: tabular-nums; text-align: right; }
.viz-table .positive { color: var(--positive); }
.viz-table .negative { color: var(--negative); }
</style>
```

## Data Formatting Rules

| Data Type | Format | Example |
|-----------|--------|---------|
| Dollar amounts | `$X,XXX.XX` (2 decimals for <$1000, 0 for larger) | $1,234.56 or $1,234,567 |
| Percentages | `X.XX%` (2 decimals) | 12.34% |
| Large numbers | Abbreviated with suffix | 1.2M, 3.4B |
| Dates (axes) | `MMM DD` or `MMM 'YY` depending on range | Jan 15, Mar '24 |
| Dates (tooltips) | Full: `MMM DD, YYYY` | Jan 15, 2025 |
| Share counts | Comma-separated integers | 1,234 shares |
| Ratios (P/E etc) | 1-2 decimals, no % | 24.5x |

### Number Formatting Helper
Include this in every visualization:
```javascript
const fmt = {
  dollar: (n) => {
    if (n == null) return '—';
    const abs = Math.abs(n);
    const sign = n < 0 ? '-' : '';
    if (abs >= 1e9) return sign + '$' + (abs/1e9).toFixed(1) + 'B';
    if (abs >= 1e6) return sign + '$' + (abs/1e6).toFixed(1) + 'M';
    if (abs >= 1e4) return sign + '$' + Math.round(abs).toLocaleString();
    return sign + '$' + abs.toFixed(2);
  },
  pct: (n) => n == null ? '—' : (n >= 0 ? '+' : '') + n.toFixed(2) + '%',
  num: (n) => n == null ? '—' : n.toLocaleString(),
  date: (d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
  dateShort: (d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
};
```

## KPI Cards Pattern

For dashboards, lead with big numbers:

```html
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-label">Total Value</div>
    <div class="kpi-value">$142,350</div>
    <div class="kpi-delta positive">+$2,340 (1.67%) today</div>
  </div>
  <!-- more cards -->
</div>

<style>
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px 20px;
}
.kpi-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}
.kpi-delta {
  font-size: 13px;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
.kpi-delta.positive { color: var(--positive); }
.kpi-delta.negative { color: var(--negative); }
</style>
```

## Charts Manifest

The Charts tab uses a manifest file (`charts.json`) to organize visualizations with titles, descriptions, and groups. **Every time you create, update, or delete a visualization, update the manifest.**

The manifest lives at `/home/user/charts.json`:

```json
{
  "charts": [
    {
      "filename": "portfolio_overview.html",
      "title": "Portfolio Overview",
      "description": "Holdings breakdown with sector allocation and performance",
      "group": "Portfolio"
    },
    {
      "filename": "sector_allocation.html",
      "title": "Sector Allocation",
      "description": "Current sector weights vs S&P 500 benchmark",
      "group": "Portfolio"
    },
    {
      "filename": "aapl_vs_msft.html",
      "title": "AAPL vs MSFT Correlation",
      "description": "6-month price correlation and relative performance",
      "group": "Analysis"
    },
    {
      "filename": "tlh_opportunities.html",
      "title": "Tax Loss Harvesting",
      "description": "Harvestable losses with swap candidates",
      "group": "Tax"
    }
  ]
}
```

### Manifest Rules

- **`filename`** (required): The `.html` filename in the sandbox. Must match the actual file.
- **`title`** (required): Human-readable name shown in the sidebar. Keep it short and clear.
- **`description`** (optional): One-line description shown below the title. Helps users find what they need.
- **`group`** (optional): Groups charts into collapsible sections in the sidebar. Use logical categories like "Portfolio", "Analysis", "Research", "Tax", "Watchlist".
- **Order matters**: Charts appear in the order listed. Put the most important/recent charts first within each group.

### Updating the Manifest

**Always read-modify-write** — don't overwrite the whole file blindly:

```python
import json

# Read existing manifest
try:
    with open('/home/user/charts.json', 'r') as f:
        manifest = json.load(f)
except FileNotFoundError:
    manifest = {"charts": []}

# Add a new chart
manifest["charts"].append({
    "filename": "new_chart.html",
    "title": "New Chart Title",
    "description": "What this chart shows",
    "group": "Analysis"
})

# Write back
with open('/home/user/charts.json', 'w') as f:
    json.dump(manifest, f, indent=2)
```

When removing a visualization, remove its entry from the manifest too. When renaming, update both the file and the manifest entry.

If no manifest exists, the Charts tab falls back to listing all `.html` files alphabetically — but always prefer creating a manifest for a better user experience.

## File Naming

Name files descriptively:
- `portfolio_overview.html` not `chart1.html`
- `sector_allocation.html` not `pie.html`
- `aapl_vs_msft_correlation.html` not `comparison.html`
- `tlh_opportunities_dashboard.html` not `dashboard.html`

## Common Patterns

### Embedding Data

Embed the data directly in the HTML as a JS variable. Never fetch from external URLs.

```html
<script>
const DATA = [
  { date: '2025-01-02', value: 100.5, symbol: 'AAPL' },
  // ... generated from your Python analysis
];
</script>
```

For large datasets (>500 rows), consider aggregating in Python first and only embedding the summary.

### Multiple Charts in One File (Dashboard)

```html
<div class="viz-container">
  <h1 style="font-size:20px; font-weight:600; margin-bottom:20px;">Dashboard Title</h1>
  
  <div class="kpi-row"><!-- KPIs --></div>
  
  <div class="viz-grid" style="grid-template-columns: 2fr 1fr;">
    <div class="viz-card">
      <h3 style="font-size:14px; color:var(--text-secondary); margin-bottom:12px;">Main Chart</h3>
      <div id="main-chart" style="height:400px;"></div>
    </div>
    <div class="viz-card">
      <h3 style="font-size:14px; color:var(--text-secondary); margin-bottom:12px;">Breakdown</h3>
      <div id="side-chart" style="height:400px;"></div>
    </div>
  </div>
  
  <div class="viz-card">
    <h3 style="font-size:14px; color:var(--text-secondary); margin-bottom:12px;">Detail Table</h3>
    <div style="overflow-x:auto;">
      <table class="viz-table" id="detail-table"></table>
    </div>
  </div>
</div>
```

### Generating HTML from Python

The typical workflow is:
1. Fetch/compute data in Python
2. Format it as a JSON string
3. Inject it into an HTML template
4. Write the complete HTML file

```python
import json

# After your analysis...
data_json = json.dumps(results)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Analysis Title</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"><\/script>
  <style>
    /* ... design system styles ... */
  </style>
</head>
<body>
  <div class="viz-container">
    <div id="chart" style="height:500px;"></div>
  </div>
  <script>
    const DATA = {data_json};
    // ... build chart from DATA ...
  </script>
</body>
</html>"""

with open('/home/user/analysis_title.html', 'w') as f:
    f.write(html)
```

## Advanced Techniques

Use these to make visualizations that feel alive and premium. Don't hold back.

### Animated Entrances
Charts that fade/slide in are more engaging than ones that just appear:
```css
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.viz-card { animation: fadeInUp 0.5s ease-out both; }
.viz-card:nth-child(2) { animation-delay: 0.1s; }
.viz-card:nth-child(3) { animation-delay: 0.2s; }
```

For data-driven entrances (bars growing, lines drawing, numbers counting up):
```javascript
// Count-up animation for KPI numbers
function animateValue(el, start, end, duration) {
  const range = end - start;
  const startTime = performance.now();
  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    el.textContent = fmt.dollar(start + range * eased);
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

// Line drawing animation via SVG stroke-dasharray
path.style.strokeDasharray = path.getTotalLength();
path.style.strokeDashoffset = path.getTotalLength();
path.style.transition = 'stroke-dashoffset 1.5s ease-out';
requestAnimationFrame(() => path.style.strokeDashoffset = '0');
```

### Micro-interactions
Small details that make the experience feel polished:
- **Hover glow on data points**: `filter: drop-shadow(0 0 6px var(--accent))`
- **Smooth cursor tracking**: Use `mousemove` to draw crosshairs on charts
- **Active state on buttons**: `transform: scale(0.97)` on click
- **Skeleton loading states**: Show animated placeholder before data renders
- **Number transitions**: Animate between values when filters change

### Sparklines in KPI Cards
Tiny inline charts that show trend context next to a big number:
```javascript
function sparkline(canvas, data, color = '#6366f1') {
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  ctx.clearRect(0, 0, w, h);
  ctx.beginPath();
  data.forEach((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}
```

### Gradient Fills for Area Charts
More visually striking than solid fills:
```javascript
// Plotly
fill: 'tozeroy',
fillgradient: {
  type: 'vertical',
  colorscale: [[0, 'rgba(99,102,241,0.3)'], [1, 'rgba(99,102,241,0)']],
},

// Canvas
const gradient = ctx.createLinearGradient(0, 0, 0, height);
gradient.addColorStop(0, 'rgba(99, 102, 241, 0.3)');
gradient.addColorStop(1, 'rgba(99, 102, 241, 0)');
ctx.fillStyle = gradient;
```

### 3D Visualizations
For data with three dimensions — correlation cubes, surface plots, geographic data:
```javascript
// Three.js scene boilerplate
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, w/h, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(w, h);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);
// Add orbit controls for mouse interaction
// Animate with requestAnimationFrame
```

### Particle Effects and Flow Visualizations
For showing movement, flow, or energy — portfolio cash flow, market momentum, trade volume:
- Use Canvas with requestAnimationFrame for smooth particles
- D3-force for interactive network/relationship visualizations
- CSS animations for simple floating/pulsing effects on key data points

### Responsive Dashboard Layouts
Dashboards should adapt to the viewport, not just scale:
```css
.viz-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
}

/* Breakpoints for different layouts */
@media (min-width: 1200px) {
  .viz-grid-featured { grid-template-columns: 2fr 1fr; }
}
@media (max-width: 800px) {
  .viz-grid-featured { grid-template-columns: 1fr; }
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}
```

## Quality Checklist

Before saving any visualization, verify:

- [ ] Chart type fits the data story (not just the first thing that came to mind)
- [ ] All axes labeled with units
- [ ] Title is descriptive and specific (not "Chart" or "Data")
- [ ] Colors follow the design system — no library defaults
- [ ] Dark theme applied consistently
- [ ] Tooltips show useful detail on hover
- [ ] Numbers are formatted correctly (dollars, percentages, dates)
- [ ] Responsive — uses full width, no fixed pixel widths on the main container
- [ ] Data makes sense visually (no weird spikes, gaps, or obviously wrong values)
- [ ] File is self-contained (no external fetches, all data embedded)
- [ ] File name is descriptive
- [ ] `charts.json` manifest is updated with the new chart's entry
- [ ] Animations and transitions feel smooth, not janky
- [ ] The visualization is something you'd be proud to show — not just functional, but impressive
