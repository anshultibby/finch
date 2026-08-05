'use client';

import React, { useMemo } from 'react';

// Tiny data[]-driven sparkline (MiniSparkline is symbol-fetching only).
interface Props {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

export default function Sparkline({ data, width = 80, height = 28, color, className = '' }: Props) {
  const { path, up } = useMemo(() => {
    const pts = (data || []).filter((v) => typeof v === 'number' && !Number.isNaN(v));
    if (pts.length < 2) return { path: '', up: true };
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = max - min || 1;
    const pad = 2;
    const w = width - pad * 2;
    const h = height - pad * 2;
    const d = pts
      .map((v, i) => {
        const x = pad + (i / (pts.length - 1)) * w;
        const y = pad + (1 - (v - min) / range) * h;
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
    return { path: d, up: pts[pts.length - 1] >= pts[0] };
  }, [data, width, height]);

  if (!path) return <div style={{ width, height }} className={className} />;
  const stroke = color || (up ? '#10b981' : '#ef4444');
  return (
    <svg width={width} height={height} className={className} viewBox={`0 0 ${width} ${height}`}>
      <path d={path} fill="none" stroke={stroke} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
