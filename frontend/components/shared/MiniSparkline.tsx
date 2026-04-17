'use client';

import React, { useEffect, useState, useMemo } from 'react';

interface MiniSparklineProps {
  symbol: string;
  width?: number;
  height?: number;
  color?: string;
  className?: string;
  days?: number;
}

export default function MiniSparkline({
  symbol,
  width = 60,
  height = 24,
  color,
  className = '',
  days = 30,
}: MiniSparklineProps) {
  const [data, setData] = useState<number[]>([]);

  useEffect(() => {
    fetch(`/api/market-prices?symbols=${symbol}&days=${days}`)
      .then(r => r.json())
      .then(d => {
        const series = d[symbol] || d[symbol.toUpperCase()] || [];
        if (Array.isArray(series)) {
          setData(series.map((p: any) => p.pct ?? 0));
        }
      })
      .catch(() => {});
  }, [symbol, days]);

  const path = useMemo(() => {
    if (data.length < 2) return '';
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = 2;
    const w = width - pad * 2;
    const h = height - pad * 2;

    return data.map((v, i) => {
      const x = pad + (i / (data.length - 1)) * w;
      const y = pad + (1 - (v - min) / range) * h;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  }, [data, width, height]);

  const isUp = data.length >= 2 ? data[data.length - 1] >= data[0] : true;
  const lineColor = color || (isUp ? '#10b981' : '#ef4444');

  if (!path) return <div style={{ width, height }} className={className} />;

  return (
    <svg width={width} height={height} className={className} viewBox={`0 0 ${width} ${height}`}>
      <path d={path} fill="none" stroke={lineColor} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
      {/* Dot at the end */}
      {data.length >= 2 && (() => {
        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1;
        const pad = 2;
        const w = width - pad * 2;
        const h = height - pad * 2;
        const lastX = pad + w;
        const lastY = pad + (1 - (data[data.length - 1] - min) / range) * h;
        return <circle cx={lastX} cy={lastY} r={2} fill={lineColor} />;
      })()}
    </svg>
  );
}
