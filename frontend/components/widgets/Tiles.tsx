'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import WidgetChart from './WidgetChart';
import Sparkline from './Sparkline';
import { TableControls, applyControls, initControlState, type ControlState } from './TableControls';
import type {
  Tile, TileData, Control, SeriesData, TableData, NumberData, OddsData, NewsData, MarkdownData,
} from './types';

const num = (v: number | null | undefined, digits = 2) =>
  v == null ? '—' : v.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });

const deltaClass = (v: number | null | undefined) =>
  v == null ? 'text-gray-400' : v >= 0 ? 'text-emerald-600' : 'text-red-500';

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
    />
  );
}

function StatTile({ data, options }: { data: NumberData; options?: Record<string, any> }) {
  const fmt = options?.format;
  const prefix = fmt === 'currency' ? '$' : '';
  const suffix = fmt === 'pct' ? '%' : '';
  return (
    <div className="flex flex-col justify-center h-full">
      {data.label && <div className="text-xs text-gray-500 mb-1 truncate">{data.label}</div>}
      <div className="text-2xl font-bold font-numeric text-gray-900">
        {prefix}{num(data.value)}{suffix}
      </div>
      {(data.delta != null || data.delta_pct != null) && (
        <div className={`text-sm font-numeric mt-0.5 ${deltaClass(data.delta_pct ?? data.delta)}`}>
          {(data.delta_pct ?? data.delta ?? 0) >= 0 ? '▲' : '▼'} {num(Math.abs(data.delta ?? 0))}
          {data.delta_pct != null && ` (${num(Math.abs(data.delta_pct))}%)`}
        </div>
      )}
      {options?.show_sparkline !== false && data.sparkline && data.sparkline.length > 1 && (
        <Sparkline data={data.sparkline} className="mt-2" width={120} height={32} />
      )}
    </div>
  );
}

function OddsTile({ data }: { data: OddsData }) {
  const pct = data.prob == null ? null : Math.round(data.prob * 100);
  const close = data.close_date ? new Date(data.close_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : null;
  return (
    <div className="flex flex-col justify-center h-full">
      <div className="text-3xl font-bold font-numeric text-gray-900">{pct == null ? '—' : `${pct}%`}</div>
      <div className="text-[11px] uppercase tracking-wide text-gray-400 mt-0.5">probability</div>
      {data.title && <div className="text-xs text-gray-600 mt-2 line-clamp-2">{data.title}</div>}
      {close && <div className="text-[11px] text-gray-400 mt-1">Closes {close}</div>}
      {data.history && data.history.length > 1 && (
        <Sparkline data={data.history.map((h) => h.v ?? 0)} className="mt-2" color="#6366f1" />
      )}
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
  const pctCol = data.columns.findIndex((c) => c.includes('pct') || c.includes('change'));
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
            {cols.map((c) => <th key={c} className="font-medium px-1 py-1">{c.replace(/_/g, ' ')}</th>)}
          </tr>
        </thead>
        <tbody>
          {shown.rows.map((row, r) => (
            <tr key={r} className="border-t border-gray-100">
              {colIdx.map((ci: number, c: number) => {
                const val = row[ci];
                const isPct = ci === pctCol && typeof val === 'number';
                return (
                  <td key={c} className={`px-1 py-1.5 font-numeric ${isPct ? deltaClass(val as number) : 'text-gray-800'} ${c === 0 ? 'font-medium' : ''}`}>
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
