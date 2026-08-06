import React from 'react';
import { View, Text } from 'react-native';
import { TileBody } from './Tiles';
import type { WidgetSpec, WidgetData, TileData } from '@/lib/types';

// Mobile is a single column, so tiles stack vertically (mirrors the web grid at
// its `grid-cols-1` mobile breakpoint). `size` only nudges min-height.
const MIN_H: Record<string, number> = { sm: 96, md: 120, lg: 200, full: 120 };

function citation(data?: TileData): string | null {
  if (!data || !('source' in data)) return null;
  const src = (data as any).source as { label?: string } | undefined;
  const asof = (data as any).asof as string | undefined;
  const parts: string[] = [];
  if (src?.label) parts.push(src.label);
  if (asof) {
    const d = new Date(asof);
    if (!isNaN(d.getTime())) parts.push(d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }));
  }
  return parts.length ? parts.join(' · ') : null;
}

export default function WidgetCanvas({ spec, data }: { spec: WidgetSpec; data?: WidgetData }) {
  const tiles = spec?.tiles || [];
  return (
    <View style={{ gap: 12 }}>
      {tiles.map((tile) => {
        const tileData = data?.[tile.id];
        const cite = citation(tileData);
        const isText = tile.type === 'text';
        return (
          <View
            key={tile.id}
            style={{
              backgroundColor: '#ffffff',
              borderRadius: 16,
              borderWidth: 1,
              borderColor: '#e5e7eb',
              padding: 16,
              minHeight: isText ? undefined : MIN_H[tile.size || 'md'],
            }}
          >
            {!!tile.title && (
              <Text style={{ fontSize: 13, fontFamily: 'DMSans-Bold', color: '#111827', marginBottom: 12 }}>
                {tile.title}
              </Text>
            )}
            <TileBody tile={tile} data={tileData} />
            {!!cite && (
              <Text style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'DMSans', marginTop: 10 }} numberOfLines={1}>
                {cite}
              </Text>
            )}
          </View>
        );
      })}
    </View>
  );
}
