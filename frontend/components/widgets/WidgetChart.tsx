'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, LineStyle, LineSeries } from 'lightweight-charts';
import type { IChartApi } from 'lightweight-charts';
import type { SeriesData } from './types';

// Multi-series line chart for widget `chart` tiles. Self-contained (the shared
// PriceRangeChart only renders a single data-series), styled to match it.
const PALETTE = ['#10b981', '#6366f1', '#f59e0b', '#ef4444', '#0ea5e9', '#ec4899'];

interface Props {
  data: SeriesData;
  height?: number;
  yFormat?: 'pct' | 'currency' | 'number';
  showLegend?: boolean;
}

const fmt = (v: number, kind: Props['yFormat']) => {
  if (kind === 'pct') return `${v.toFixed(2)}%`;
  if (kind === 'currency') return v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(2)}`;
  return v.toFixed(2);
};

export default function WidgetChart({ data, height = 220, yFormat = 'number', showLegend = true }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const series = data.series || [];
  const hasData = series.some((s) => (s.points || []).filter((p) => p.v != null).length >= 2);

  useEffect(() => {
    if (!containerRef.current || !hasData) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: 11,
      },
      localization: { priceFormatter: (p: number) => fmt(p, yFormat) },
      grid: { vertLines: { visible: false }, horzLines: { color: '#f3f4f6', style: LineStyle.Solid } },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: true, borderVisible: false, scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { visible: true, borderVisible: false },
      handleScroll: false,
      handleScale: false,
    });
    chartRef.current = chart;

    series.forEach((s, i) => {
      const line = chart.addSeries(LineSeries, {
        color: PALETTE[i % PALETTE.length],
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const points = (s.points || [])
        .filter((p) => p.v != null && p.t)
        .map((p) => ({ time: p.t.slice(0, 10), value: p.v as number }));
      line.setData(points as any);
    });
    chart.timeScale().fitContent();

    const onResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [JSON.stringify(series), height, yFormat, hasData]);

  if (!hasData) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-xs text-gray-400">
        No data
      </div>
    );
  }

  return (
    <div>
      {showLegend && series.length > 1 && (
        <div className="flex flex-wrap gap-x-3 gap-y-1 mb-2">
          {series.map((s, i) => (
            <div key={s.label} className="flex items-center gap-1.5 text-xs text-gray-600">
              <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: PALETTE[i % PALETTE.length] }} />
              {s.label}
            </div>
          ))}
        </div>
      )}
      <div ref={containerRef} style={{ height }} />
    </div>
  );
}
