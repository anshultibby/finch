'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import WidgetChart from './WidgetChart';
import PlotlyTile from './PlotlyTile';
import Sparkline from './Sparkline';
import { TableControls, applyControls, initControlState, type ControlState } from './TableControls';
import type {
  Tile, TileData, Control, SeriesData, TableData, NumberData, OddsData, NewsData, MarkdownData,
} from './types';

const num = (v: number | null | undefined, digits = 2) =>
  v == null ? '—' : v.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });

// Auto-compact for big standalone figures: 1,284 / 12.9K / $4.2M.
const compact = (v: number | null | undefined, prefix = '') => {
  if (v == null) return '—';
  const a = Math.abs(v);
  if (a >= 1e9) return `${prefix}${(v / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `${prefix}${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e4) return `${prefix}${(v / 1e3).toFixed(1)}K`;
  return `${prefix}${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};

const deltaClass = (v: number | null | undefined) =>
  v == null ? 'text-gray-400' : v >= 0 ? 'text-emerald-600' : 'text-red-500';

// Diverging wash for change columns: emerald↔red through the surface, intensity
// scales with magnitude, text stays in ink (the wash is background only).
const divergingWash = (v: number, maxAbs: number) => {
  if (!maxAbs) return undefined;
  const t = Math.min(Math.abs(v) / maxAbs, 1);
  const alpha = 0.05 + t * 0.16;
  return v >= 0 ? `rgba(16,185,129,${alpha})` : `rgba(239,68,68,${alpha})`;
};

// ── states ──────────────────────────────────────────────────────────────────
function EmptyTile({ reason }: { reason: string }) {
  const msg =
    reason === 'connect_portfolio' ? 'Connect your portfolio to see yours' :
    reason === 'empty_watchlist' ? 'Your watchlist is empty' :
    'No data';
  return <div className="flex items-center justify-center h-full min-h-[80px] text-sm text-gray-400 text-center px-4">{msg}</div>;
}

function ErrorTile({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-[80px] text-xs text-gray-400 text-center px-4">
      Couldn’t load this tile
    </div>
  );
}

// ── tiles ─────────────────────────────────────────────────────────────────
function ChartTile({ data, options }: { data: SeriesData; options?: Record<string, any> }) {
  return (
    <WidgetChart
      data={data}
      yFormat={options?.y_format || 'number'}
      showLegend={options?.show_legend !== false}
      height={options?.height || 220}
      referenceLines={options?.reference_lines}
      markers={options?.markers}
    />
  );
}

function StatTile({ data, options }: { data: NumberData; options?: Record<string, any> }) {
  const fmt = options?.format;
  const prefix = fmt === 'currency' ? '$' : '';
  const suffix = fmt === 'pct' ? '%' : '';
  const delta = data.delta_pct ?? data.delta;
  return (
    <div className="flex flex-col justify-center h-full">
      {data.label && <div className="text-xs text-gray-500 mb-1.5 truncate">{data.label}</div>}
      {/* Hero-figure treatment: big semibold, proportional figures (not tabular) */}
      <div className="text-[2.5rem] leading-none font-semibold text-gray-900 tracking-tight">
        {compact(data.value, prefix)}{suffix}
      </div>
      {delta != null && (
        <div className="mt-2 flex items-center gap-1.5">
          <span
            className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-xs font-medium ${
              delta >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'
            }`}
          >
            {delta >= 0 ? '▲' : '▼'} {data.delta != null ? num(Math.abs(data.delta)) : ''}
            {data.delta_pct != null && ` (${num(Math.abs(data.delta_pct))}%)`}
          </span>
          <span className="text-[11px] text-gray-400">today</span>
        </div>
      )}
      {options?.show_sparkline !== false && data.sparkline && data.sparkline.length > 1 && (
        <Sparkline data={data.sparkline} className="mt-3" width={140} height={36} />
      )}
    </div>
  );
}

function OddsTile({ data }: { data: OddsData }) {
  const pct = data.prob == null ? null : Math.round(data.prob * 100);
  const close = data.close_date ? new Date(data.close_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : null;
  return (
    <div className="flex flex-col justify-center h-full">
      <div className="flex items-baseline gap-2">
        {/* Hero figure */}
        <div className="text-[2.75rem] leading-none font-semibold text-gray-900 tracking-tight">
          {pct == null ? '—' : `${pct}%`}
        </div>
        <div className="text-[11px] uppercase tracking-wide text-gray-400">chance</div>
      </div>
      {/* Meter: emerald fill on a lighter step of the same ramp */}
      {pct != null && (
        <div className="mt-3 h-2 rounded-full bg-emerald-100 overflow-hidden">
          <div className="h-full rounded-full bg-emerald-500 transition-all duration-700" style={{ width: `${pct}%` }} />
        </div>
      )}
      {data.title && <div className="text-xs text-gray-600 mt-2.5 line-clamp-2 leading-snug">{data.title}</div>}
      <div className="flex items-center gap-2 mt-1.5">
        {close && <div className="text-[11px] text-gray-400">Resolves {close}</div>}
        {data.history && data.history.length > 1 && (
          <Sparkline data={data.history.map((h) => h.v ?? 0)} color="#6366f1" width={70} height={20} />
        )}
      </div>
    </div>
  );
}

function NewsTile({ data, options }: { data: NewsData; options?: Record<string, any> }) {
  if (!data.items?.length) return <EmptyTile reason="no_news" />;
  return (
    <ul className="divide-y divide-gray-100 -my-1">
      {data.items.map((n, i) => (
        <li key={i} className="py-2">
          <a
            href={n.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="block group"
          >
            <div className="text-sm text-gray-800 group-hover:text-emerald-600 line-clamp-2 leading-snug">{n.title}</div>
            {options?.compact !== true && (n.source || n.published_at) && (
              <div className="text-[11px] text-gray-400 mt-0.5">
                {n.source}{n.source && n.published_at ? ' · ' : ''}
                {n.published_at ? new Date(n.published_at).toLocaleDateString() : ''}
              </div>
            )}
          </a>
        </li>
      ))}
    </ul>
  );
}

function TableTile({ data, options, controls }: { data: TableData; options?: Record<string, any>; controls?: Control[] }) {
  const hasControls = !!controls?.length;
  // Filter state persists across data refreshes; initialized once from first data.
  const [state, setState] = useState<ControlState>(() => (hasControls ? initControlState(data, controls!) : {}));
  const shown = hasControls ? applyControls(data, controls!, state) : data;

  let cols = data.columns || [];
  let colIdx = cols.map((_, i) => i);
  if (options?.columns?.length) {
    colIdx = options.columns.map((c: string) => cols.indexOf(c)).filter((i: number) => i >= 0);
    cols = colIdx.map((i: number) => data.columns[i]);
  }
  // Prefer an explicit percent column; only fall back to 'change' if no pct
  // column exists (matching 'change' first painted dollar changes as %).
  const pctColExplicit = data.columns.findIndex((c) => c.includes('pct') || c.includes('percent'));
  const pctCol = pctColExplicit >= 0
    ? pctColExplicit
    : data.columns.findIndex((c) => c.includes('change'));
  // Diverging wash scale for the change column (max |value| over shown rows).
  const maxAbsPct =
    pctCol >= 0
      ? Math.max(0, ...shown.rows.map((r) => (typeof r[pctCol] === 'number' ? Math.abs(r[pctCol] as number) : 0)))
      : 0;
  return (
    <div className="flex flex-col h-full">
      {hasControls && (
        <TableControls
          data={data}
          controls={controls!}
          state={state}
          onChange={(id, value) => setState((s) => ({ ...s, [id]: value }))}
        />
      )}
      <div className="overflow-x-auto overflow-y-auto -mx-1 flex-1">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] uppercase tracking-wide text-gray-400 text-left">
            {cols.map((c) => <th key={c} className="font-medium px-1.5 py-1">{c.replace(/_/g, ' ')}</th>)}
          </tr>
        </thead>
        <tbody>
          {shown.rows.map((row, r) => (
            <tr key={r} className="border-t border-gray-100">
              {colIdx.map((ci: number, c: number) => {
                const val = row[ci];
                const isPct = ci === pctCol && typeof val === 'number';
                return (
                  <td
                    key={c}
                    className={`px-1.5 py-1.5 font-numeric ${isPct ? deltaClass(val as number) + ' font-medium rounded' : 'text-gray-800'} ${c === 0 ? 'font-medium' : ''}`}
                    style={isPct ? { background: divergingWash(val as number, maxAbsPct) } : undefined}
                  >
                    {typeof val === 'number' ? num(val) + (isPct ? '%' : '') : (val ?? '—')}
                  </td>
                );
              })}
            </tr>
          ))}
          {shown.rows.length === 0 && (
            <tr><td colSpan={cols.length} className="px-1 py-4 text-center text-xs text-gray-400">No matches</td></tr>
          )}
        </tbody>
      </table>
      </div>
    </div>
  );
}

function TextTile({ data }: { data: MarkdownData }) {
  return (
    <div className="prose prose-sm max-w-none text-gray-700 prose-headings:text-gray-900 prose-a:text-emerald-600">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.text || ''}</ReactMarkdown>
    </div>
  );
}

// ── dispatcher ──────────────────────────────────────────────────────────────
export function TileBody({ tile, data }: { tile: Tile; data?: TileData }) {
  // chart_spec keys off the tile (Plotly figure in options), not the data shape.
  // A self-contained figure needs no data; a bound one uses the resolved data.
  if (tile.type === 'chart_spec') {
    const figure = tile.options?.figure;
    const hasQuery = !!tile.query;
    if (hasQuery && !data) return <div className="animate-pulse h-full min-h-[200px] bg-gray-100 rounded" />;
    if (data?.shape === 'error') return <ErrorTile message={(data as any).message} />;
    return <PlotlyTile figure={figure} data={data} height={tile.options?.height} />;
  }

  if (!data) return <div className="animate-pulse h-full min-h-[80px] bg-gray-100 rounded" />;
  if (data.shape === 'error') return <ErrorTile message={(data as any).message} />;
  if (data.shape === 'empty') return <EmptyTile reason={(data as any).reason} />;

  switch (data.shape) {
    case 'series': return <ChartTile data={data} options={tile.options} />;
    case 'number': return <StatTile data={data} options={tile.options} />;
    case 'odds': return <OddsTile data={data} />;
    case 'news': return <NewsTile data={data} options={tile.options} />;
    case 'table': return <TableTile data={data} options={tile.options} controls={tile.controls} />;
    case 'markdown': return <TextTile data={data} />;
    default: return <ErrorTile message="unknown shape" />;
  }
}
