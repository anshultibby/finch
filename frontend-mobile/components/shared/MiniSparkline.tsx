import React, { useEffect, useState, useMemo } from 'react';
import { View } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';
import { marketApi } from '@/lib/api';

interface MiniSparklineProps {
  symbol: string;
  width?: number;
  height?: number;
  color?: string;
  days?: number;
}

export default function MiniSparkline({
  symbol,
  width = 60,
  height = 24,
  color,
  days = 30,
}: MiniSparklineProps) {
  const [data, setData] = useState<number[]>([]);

  useEffect(() => {
    marketApi.getPrices([symbol], days)
      .then((d: any) => {
        const series = d[symbol] || d[symbol.toUpperCase()] || [];
        if (Array.isArray(series)) {
          setData(series.map((p: any) => p.close ?? p.pct ?? 0));
        }
      })
      .catch(() => {});
  }, [symbol, days]);

  const { path, lastPoint } = useMemo(() => {
    if (data.length < 2) return { path: '', lastPoint: null };
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = 2;
    const w = width - pad * 2;
    const h = height - pad * 2;

    const pathStr = data.map((v, i) => {
      const x = pad + (i / (data.length - 1)) * w;
      const y = pad + (1 - (v - min) / range) * h;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');

    const lastX = pad + w;
    const lastY = pad + (1 - (data[data.length - 1] - min) / range) * h;

    return { path: pathStr, lastPoint: { x: lastX, y: lastY } };
  }, [data, width, height]);

  const isUp = data.length >= 2 ? data[data.length - 1] >= data[0] : true;
  const lineColor = color || (isUp ? '#10b981' : '#ef4444');

  if (!path) return <View style={{ width, height }} />;

  return (
    <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <Path d={path} fill="none" stroke={lineColor} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
      {lastPoint && <Circle cx={lastPoint.x} cy={lastPoint.y} r={2} fill={lineColor} />}
    </Svg>
  );
}
