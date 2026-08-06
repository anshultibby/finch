'use client';

import React, { useState } from 'react';
import { TileBody } from './Tiles';
import TileModal, { type WidgetMeta } from './TileModal';
import type { WidgetSpec, WidgetData, TileData, TileSize, Tile } from './types';

// Small source line so a viewer can double-check where the numbers come from.
function TileCitation({ data, dark }: { data?: TileData; dark?: boolean }) {
  if (!data || data.shape === 'error' || data.shape === 'empty') return null;
  const source = (data as any).source as { label: string; url?: string } | undefined;
  const asof = (data as any).asof as string | undefined;
  if (!source && !asof) return null;
  let time = '';
  if (asof) {
    const d = new Date(asof);
    if (!Number.isNaN(d.getTime())) time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }
  return (
    <div className={`shrink-0 mt-2 pt-2 border-t text-[10px] flex items-center gap-1 truncate ${dark ? 'border-gray-800 text-gray-500' : 'border-gray-100 text-gray-400'}`}>
      {source && (
        source.url ? (
          <a href={source.url} target="_blank" rel="noopener noreferrer" className="hover:text-emerald-600 truncate">
            {source.label}
          </a>
        ) : (
          <span className="truncate">{source.label}</span>
        )
      )}
      {source && time && <span>·</span>}
      {time && <span className="shrink-0">{time}</span>}
    </div>
  );
}

// 4-column grid on desktop; tiles span by size. Stacks on mobile.
const COL_SPAN: Record<TileSize, string> = {
  sm: 'sm:col-span-1',
  md: 'sm:col-span-2',
  lg: 'sm:col-span-2 lg:col-span-2',
  full: 'sm:col-span-2 lg:col-span-4',
};

export default function WidgetCanvas({
  spec, data, meta,
}: {
  spec: WidgetSpec;
  data?: WidgetData;
  meta?: WidgetMeta;
}) {
  const tiles = spec?.tiles || [];
  const [expanded, setExpanded] = useState<Tile | null>(null);
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {tiles.map((tile) => {
        const size = (tile.size || 'md') as TileSize;
        // Height follows tile TYPE, not size — `size` only controls width. Only
        // visual tiles get a tall min-height; text hugs its content (so a
        // full-width one-line note isn't stretched into a big empty card).
        const tall = tile.type === 'chart' || tile.type === 'chart_spec' || tile.type === 'news' || tile.type === 'table';
        const minH = tile.type === 'text' ? '' : tall ? 'min-h-[240px]' : 'min-h-[110px]';
        const dark = tile.options?.theme === 'dark';
        const expandable = tile.type !== 'text';
        return (
          <div
            key={tile.id}
            className={`${COL_SPAN[size]} ${dark ? 'bg-[#101314] border-gray-800' : 'bg-white border-gray-200'} rounded-2xl border shadow-sm p-4 flex flex-col ${minH} relative group/tile`}
          >
            {expandable && (
              <button
                onClick={() => setExpanded(tile)}
                aria-label="Expand tile"
                className={`absolute top-2.5 right-2.5 z-10 p-1.5 rounded-lg opacity-0 group-hover/tile:opacity-100 transition-opacity ${dark ? 'text-gray-500 hover:text-gray-200 hover:bg-white/10' : 'text-gray-300 hover:text-gray-600 hover:bg-gray-100'}`}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
                </svg>
              </button>
            )}
            {tile.title && (
              <div className={`text-sm font-semibold mb-3 shrink-0 pr-6 ${dark ? 'text-gray-50' : 'text-gray-900'}`}>{tile.title}</div>
            )}
            <div className="flex-1 min-h-0">
              <TileBody tile={tile} data={data?.[tile.id]} />
            </div>
            <TileCitation data={data?.[tile.id]} dark={dark} />
          </div>
        );
      })}
      {expanded && (
        <TileModal
          tile={expanded}
          data={data?.[expanded.id]}
          meta={meta || { title: '' }}
          onClose={() => setExpanded(null)}
        />
      )}
    </div>
  );
}
