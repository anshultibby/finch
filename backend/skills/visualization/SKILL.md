---
name: visualization
description: Generate rich, interactive HTML visualizations — charts, dashboards, and data explorers — rendered in the Charts tab. Covers chart type selection, design system, interaction patterns, and library guidance.
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

You generate self-contained HTML files that render in the user's Visualizations panel. Each file is a complete interactive visualization — no external dependencies except CDN-loaded libraries.

The sandbox renders a full browser environment — CSS animations, WebGL, Canvas, SVG, requestAnimationFrame, pointer events, CSS 3D transforms all work. Make every visualization polished and useful. Design north stars: Linear, Stripe, Vercel dashboards.

## Output Pattern

Save to `visualizations/` directory, reference in your reply:

```
[visualization:visualizations/visualization_name.html]
```

For inline preview AND panel link:

```
[file:/home/user/visualizations/name.html]
Open full-screen: [visualization:visualizations/name.html]
```

Files auto-sync to the database via `<title>` extraction. Same filename = upsert.

## Live Data Bridge

Visualizations can fetch live data via postMessage bridge. Include this snippet:

```html
<script>
window.finch={_cb:{},fetch(url,body){return new Promise((resolve,reject)=>{const id=Math.random().toString(36).slice(2);this._cb[id]={resolve,reject};parent.postMessage({type:'finch-fetch',url,body,id},'*');setTimeout(()=>{if(this._cb[id]){delete this._cb[id];reject(new Error('timeout'))}},30000)})}};
addEventListener('message',e=>{if(e.data?.type==='finch-response'&&finch._cb[e.data.id]){const h=finch._cb[e.data.id];delete finch._cb[e.data.id];e.data.error?h.reject(new Error(e.data.error)):h.resolve(e.data.data)}});
</script>
```

Usage: `const data = await finch.fetch('/api/portfolio');`

For live data, write a Python script to `_data/{name}.py` that prints JSON to stdout, then call `finch.fetch('/api/visualizations/run-script', { script: '_data/{name}.py' })`. Always embed static data as fallback.

## Libraries

Load from CDN. Pick the right tool:

- **Plotly.js** (default) — line, bar, scatter, candlestick, heatmap, 3D. `plotly-2.35.2.min.js`
- **D3.js** — custom/novel visualizations, force graphs, treemaps. `d3.v7.min.js`
- **Chart.js** — lightweight simple charts. `chart.js@4.4.7`
- **Lightweight Charts** — financial time series, candlesticks. `lightweight-charts@4.2.2`
- **Three.js** — 3D visualizations. `three@0.170.0`
- **GSAP** — polished timeline animations. `gsap@3.12.7`
- **Raw SVG/Canvas** — gauges, sparklines, simple precise visuals

Multiple libraries in one file is fine.

## Design System

Finch uses a **light theme**. Every visualization must match.

### Color Palette

```css
:root {
  --bg-primary: #fafaf9;
  --bg-surface: #ffffff;
  --bg-surface-raised: #f5f5f4;
  --bg-surface-overlay: #fafaf9;
  --border-subtle: rgba(0, 0, 0, 0.06);
  --border-default: rgba(0, 0, 0, 0.1);

  --text-primary: #0f172a;
  --text-secondary: #64748b;
  --text-tertiary: #94a3b8;
  --text-muted: #cbd5e1;

  --accent: #10b981;
  --accent-hover: #059669;
  --accent-subtle: rgba(16, 185, 129, 0.1);

  --positive: #16a34a;
  --positive-subtle: rgba(22, 163, 74, 0.08);
  --negative: #dc2626;
  --negative-subtle: rgba(220, 38, 38, 0.08);
  --warning: #d97706;
  --info: #2563eb;

  --series-1: #10b981;
  --series-2: #6366f1;
  --series-3: #f59e0b;
  --series-4: #ef4444;
  --series-5: #3b82f6;
  --series-6: #a855f7;
  --series-7: #ec4899;
  --series-8: #14b8a6;
}
```

### Base Styles

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
  font-size: 14px; line-height: 1.5;
  color: var(--text-primary); background: var(--bg-primary);
  margin: 0; padding: 0;
  -webkit-font-smoothing: antialiased;
}
.viz-container { width: 100%; min-height: 100vh; padding: 24px; box-sizing: border-box; }
.viz-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px; padding: 20px; margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.02);
}
.viz-grid { display: grid; gap: 16px; }
```

Typography: page title 20px/600, section header 15px/600, chart title 14px/500, axis labels 12px/400, KPI value 28px/700. Use `font-variant-numeric: tabular-nums` on all numbers.

### Plotly Theme

```javascript
const layout = {
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  font: { family: '-apple-system, BlinkMacSystemFont, Inter, sans-serif', color: '#64748b', size: 12 },
  margin: { t: 40, r: 20, b: 50, l: 60 },
  xaxis: { gridcolor: 'rgba(0,0,0,0.05)', linecolor: 'rgba(0,0,0,0.1)', tickfont: { size: 11, color: '#94a3b8' } },
  yaxis: { gridcolor: 'rgba(0,0,0,0.05)', linecolor: 'rgba(0,0,0,0.1)', tickfont: { size: 11, color: '#94a3b8' } },
  hoverlabel: { bgcolor: '#fff', bordercolor: 'rgba(0,0,0,0.1)', font: { size: 13, color: '#0f172a' } },
  legend: { bgcolor: 'transparent', font: { size: 12, color: '#64748b' } },
};
// Always: Plotly.newPlot(el, data, layout, { responsive: true, displayModeBar: false });
```

### Chart.js Theme

```javascript
Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = 'rgba(0,0,0,0.06)';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, Inter, sans-serif';
```

## Hard Rules

1. Hide Plotly modebar — always `displayModeBar: false`
2. Animate entrances — fadeInUp with staggered delays
3. Gradient fills on area charts — 20% opacity to 0% at baseline
4. Custom tooltips — white bg, subtle border + shadow, 8px radius
5. Hover states on interactive elements — cards lift, rows highlight
6. Style scrollbars — thin, light gray, matching theme
7. `font-variant-numeric: tabular-nums` on all numbers
8. Never use library default colors — always use the palette above
9. Never leave axes unstyled
10. Never use serif fonts

## Number Formatting

Include in every visualization:

```javascript
const fmt = {
  dollar: (n) => {
    if (n == null) return '-';
    const abs = Math.abs(n), sign = n < 0 ? '-' : '';
    if (abs >= 1e9) return sign + '$' + (abs/1e9).toFixed(1) + 'B';
    if (abs >= 1e6) return sign + '$' + (abs/1e6).toFixed(1) + 'M';
    if (abs >= 1e4) return sign + '$' + Math.round(abs).toLocaleString();
    return sign + '$' + abs.toFixed(2);
  },
  pct: (n) => n == null ? '-' : (n >= 0 ? '+' : '') + n.toFixed(2) + '%',
  num: (n) => n == null ? '-' : n.toLocaleString(),
  date: (d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
};
```

## Chart Type Selection

**Comparisons:** <8 categories = horizontal bar (sorted); 8-30 = treemap; paired = dumbbell.
**Time series:** single metric = line+area; multi = multi-line (max 5); OHLC = candlestick via lightweight-charts.
**Distributions:** histogram/violin, box plot for >3 groups, scatter + R^2 for correlation.
**Part-to-whole:** donut (never pie), stacked area over time, treemap for hierarchy.

**Dashboards:** KPI cards on top (big numbers + sparklines), primary chart in middle, supporting charts/tables below.

## Charts Manifest

Update `/home/user/charts.json` whenever you create/update/delete a visualization. Read-modify-write, don't overwrite.

```json
{ "charts": [{ "filename": "name.html", "title": "Title", "description": "One-liner", "group": "Portfolio" }] }
```

## File Naming

Descriptive: `portfolio_overview.html` not `chart1.html`, `sector_allocation.html` not `pie.html`.
