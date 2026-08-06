'use client';

import React, { useMemo } from 'react';
import dynamic from 'next/dynamic';
import type { TileData } from './types';

// Plotly is ~4MB — load it only when a chart_spec tile actually renders.
const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <div className="h-full min-h-[200px] animate-pulse bg-gray-50 rounded" />,
});

// The LLM emits a Plotly figure ({data, layout}) in tile.options.figure. If the
// tile also has a data query, we bind the resolved live data into the traces by
// substituting $-refs (so the chart is live + cached, not a snapshot):
//   $t              → shared time axis (first series' timestamps)
//   $series.LABEL   → that series' values      (series payloads)
//   $col.NAME       → that column's values     (table payloads)
//   $value          → the number               (number payloads)
function lutFor(data: any, prefix: string, lut: Record<string, any>) {
  if (data.shape === 'series') {
    const series = data.series || [];
    if (series[0]) lut[`${prefix}t`] = series[0].points.map((p: any) => p.t);
    for (const s of series) {
      const vals = s.points.map((p: any) => p.v);
      const times = s.points.map((p: any) => p.t);
      lut[`${prefix}series.${s.label}`] = vals;
      // Accept the natural extrapolations LLMs write: .v for values, .t for
      // that series' own timestamps (observed in the wild: $series.Nvidia.t).
      lut[`${prefix}series.${s.label}.v`] = vals;
      lut[`${prefix}series.${s.label}.t`] = times;
    }
  } else if (data.shape === 'table') {
    (data.columns || []).forEach((c: string, i: number) => {
      lut[`${prefix}col.${c}`] = data.rows.map((r: any[]) => r[i]);
    });
  } else if (data.shape === 'number') {
    lut[`${prefix}value`] = data.value;
  } else if (data.shape === 'odds') {
    lut[`${prefix}t`] = (data.history || []).map((p: any) => p.t);
    lut[`${prefix}odds`] = (data.history || []).map((p: any) => p.v);
    lut[`${prefix}value`] = data.prob != null ? data.prob * 100 : null;
  }
}

function bindFigure(figure: any, data?: TileData): any {
  if (!figure) return { data: [], layout: {} };
  if (!data || data.shape === 'static' || data.shape === 'error' || data.shape === 'empty') {
    return figure;
  }
  const lut: Record<string, any> = {};
  if (data.shape === 'multi') {
    // Multi-source: namespaced refs — $partname.t / $partname.series.LABEL /
    // $partname.col.NAME / $partname.odds / $partname.value
    for (const [name, part] of Object.entries((data as any).parts || {})) {
      lutFor(part, `$${name}.`, lut);
    }
  } else {
    lutFor(data as any, '$', lut);
  }
  const sub = (v: any): any => {
    if (typeof v === 'string' && v.startsWith('$')) return v in lut ? lut[v] : v;
    if (Array.isArray(v)) return v.map(sub);
    if (v && typeof v === 'object') {
      const o: any = {};
      for (const k in v) o[k] = sub(v[k]);
      return o;
    }
    return v;
  };
  return { ...figure, data: sub(figure.data || []) };
}

// Finch chart theme — applied under the LLM's layout so charts read as one
// system (transparent bg, validated emerald-led colorway, hairline gridlines).
const THEME_LAYOUT = {
  autosize: true,
  margin: { l: 44, r: 16, t: 28, b: 36 },
  font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', size: 11, color: '#57534e' },
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  colorway: ['#10b981', '#6366f1', '#f59e0b', '#ef4444', '#0ea5e9', '#ec4899'],
  bargap: 0.3,
  xaxis: { gridcolor: '#f3f4f6', zerolinecolor: '#e5e7eb', automargin: true },
  yaxis: { gridcolor: '#f3f4f6', zerolinecolor: '#e5e7eb', automargin: true },
  legend: { orientation: 'h', y: -0.2, font: { size: 10 } },
  hoverlabel: { bgcolor: '#1c1917', font: { color: '#fff', size: 11 } },
};

// Mark hygiene applied per trace: 2px surface gap on bars (white outline), 2px
// lines, ≥8px markers with a white surface ring.
function applyMarkSpecs(traces: any[]): any[] {
  return traces.map((t) => {
    const out = { ...t };
    if (t.type === 'bar') {
      out.marker = { line: { color: '#ffffff', width: 2 }, ...(t.marker || {}) };
    }
    if (t.type === 'scatter' || t.type === 'scattergl' || !t.type) {
      if (t.mode?.includes('lines')) out.line = { width: 2, ...(t.line || {}) };
      if (t.mode?.includes('markers')) {
        out.marker = { size: 9, line: { color: '#ffffff', width: 2 }, ...(t.marker || {}) };
      }
    }
    return out;
  });
}

export default function PlotlyTile({ figure, data, height = 260 }: { figure: any; data?: TileData; height?: number }) {
  const bound = useMemo(() => bindFigure(figure, data), [figure, data]);

  if (!bound?.data?.length) {
    return <div className="flex items-center justify-center text-xs text-gray-400" style={{ height }}>No chart data</div>;
  }

  const layout = { ...THEME_LAYOUT, ...(bound.layout || {}) };

  return (
    <Plot
      data={applyMarkSpecs(bound.data)}
      layout={layout as any}
      config={{ displaylogo: false, displayModeBar: false, responsive: true } as any}
      useResizeHandler
      style={{ width: '100%', height }}
    />
  );
}
