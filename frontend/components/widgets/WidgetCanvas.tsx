'use client';

import React from 'react';
import { TileBody } from './Tiles';
import type { WidgetSpec, WidgetData, TileData, TileSize } from './types';

// Small source line so a viewer can double-check where the numbers come from.
function TileCitation({ data }: { data?: TileData }) {
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
    <div className="shrink-0 mt-2 pt-2 border-t border-gray-100 text-[10px] text-gray-400 flex items-center gap-1 truncate">
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

export default function WidgetCanvas({ spec, data }: { spec: WidgetSpec; data?: WidgetData }) {
  const tiles = spec?.tiles || [];
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
        return (
          <div
            key={tile.id}
            className={`${COL_SPAN[size]} ${dark ? 'bg-[#101314] border-gray-800' : 'bg-white border-gray-200'} rounded-2xl border shadow-sm p-4 flex flex-col ${minH}`}
          >
            {tile.title && (
              <div className={`text-sm font-semibold mb-3 shrink-0 ${dark ? 'text-gray-50' : 'text-gray-900'}`}>{tile.title}</div>
            )}
            <div className="flex-1 min-h-0">
              <TileBody tile={tile} data={data?.[tile.id]} />
            </div>
            <TileCitation data={data?.[tile.id]} />
          </div>
        );
      })}
    </div>
  );
}
