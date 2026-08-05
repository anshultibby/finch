'use client';

import React from 'react';
import { TileBody } from './Tiles';
import type { WidgetSpec, WidgetData, TileSize } from './types';

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
        const isTall = size === 'lg' || size === 'full' || tile.type === 'chart' || tile.type === 'news';
        return (
          <div
            key={tile.id}
            className={`${COL_SPAN[size]} bg-white rounded-2xl border border-gray-200 shadow-sm p-4 flex flex-col ${isTall ? 'min-h-[240px]' : 'min-h-[120px]'}`}
          >
            {tile.title && (
              <div className="text-sm font-semibold text-gray-900 mb-3 shrink-0">{tile.title}</div>
            )}
            <div className="flex-1 min-h-0">
              <TileBody tile={tile} data={data?.[tile.id]} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
