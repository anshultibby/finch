import React, { useMemo } from 'react';
import { View } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';

// Data-driven sparkline (takes a number[], unlike the symbol-fetching
// MiniSparkline). Used by stat & odds tiles.
export default function WidgetSparkline({
  data,
  width = 120,
  height = 32,
  color,
}: {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}) {
  const { path, last } = useMemo(() => {
    const d = (data || []).filter((v) => typeof v === 'number') as number[];
    if (d.length < 2) return { path: '', last: null as null | { x: number; y: number } };
    const min = Math.min(...d);
    const max = Math.max(...d);
    const range = max - min || 1;
    const pad = 2;
    const w = width - pad * 2;
    const h = height - pad * 2;
    const pts = d.map((v, i) => ({
      x: pad + (i / (d.length - 1)) * w,
      y: pad + (1 - (v - min) / range) * h,
    }));
    const p = pts.map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt.x.toFixed(1)},${pt.y.toFixed(1)}`).join(' ');
    return { path: p, last: pts[pts.length - 1] };
  }, [data, width, height]);

  const isUp = data && data.length >= 2 ? data[data.length - 1] >= data[0] : true;
  const stroke = color || (isUp ? '#10b981' : '#ef4444');

  if (!path) return <View style={{ width, height }} />;

  return (
    <Svg width={width} height={height}>
      <Path d={path} fill="none" stroke={stroke} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
      {last && <Circle cx={last.x} cy={last.y} r={2} fill={stroke} />}
    </Svg>
  );
}
