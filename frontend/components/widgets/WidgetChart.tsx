'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  createChart, ColorType, LineStyle, LineSeries, AreaSeries, CrosshairMode, createSeriesMarkers,
} from 'lightweight-charts';
import type { IChartApi, ISeriesApi, MouseEventParams } from 'lightweight-charts';
import type { SeriesData } from './types';

// Categorical palette — validated (dataviz six-checks) on the white card
// surface: worst adjacent CVD ΔE 25.2. Contrast relief for the light slots is
// the legend + endpoint labels + tooltip, which every chart here ships.
export const SERIES_PALETTE = ['#10b981', '#6366f1', '#f59e0b', '#ef4444', '#0ea5e9', '#ec4899'];

interface Props {
  data: SeriesData;
  height?: number;
  yFormat?: 'pct' | 'currency' | 'number';
  showLegend?: boolean;
  // Annotations (from tile.options): quiet reference lines + event markers.
  referenceLines?: { value: number; label?: string; color?: string }[];
  markers?: { t: string; label: string; position?: 'above' | 'below' }[];
}

const fmt = (v: number, kind: Props['yFormat']) => {
  if (kind === 'pct') return `${v.toFixed(2)}%`;
  if (kind === 'currency') return v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(2)}`;
  return Math.abs(v) >= 1000 ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : v.toFixed(2);
};

export default function WidgetChart({
  data, height = 220, yFormat = 'number', showLegend = true, referenceLines, markers,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [hover, setHover] = useState<{ x: number; date: string; values: (number | null)[] } | null>(null);

  const series = data.series || [];
  const hasData = series.some((s) => (s.points || []).filter((p) => p.v != null).length >= 2);
  const single = series.length === 1;

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
        attributionLogo: false,
        textColor: '#9ca3af', // muted axis ink
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: 11,
      },
      localization: { priceFormatter: (p: number) => fmt(p, yFormat) },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: '#f3f4f6', style: LineStyle.Solid }, // hairline, solid, recessive
      },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { width: 1, color: '#d1d5db', style: LineStyle.Dashed, labelVisible: false },
        horzLine: { visible: false, labelVisible: false },
      },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: true, borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
      timeScale: { visible: true, borderVisible: false },
      handleScroll: false,
      handleScale: false,
    });
    chartRef.current = chart;

    const apis: ISeriesApi<any>[] = [];
    series.forEach((s, i) => {
      const color = SERIES_PALETTE[i % SERIES_PALETTE.length];
      // Single series → area with a ~10% wash (a wash, never a block);
      // comparisons → clean 2px lines.
      const api = single
        ? chart.addSeries(AreaSeries, {
            lineColor: color,
            lineWidth: 2,
            topColor: `${color}26`, // ~15% at top…
            bottomColor: `${color}00`, // …fading to transparent
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerRadius: 4,
            crosshairMarkerBorderColor: '#ffffff',
            crosshairMarkerBorderWidth: 2, // surface ring on the hover dot
          })
        : chart.addSeries(LineSeries, {
            color,
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerRadius: 4,
            crosshairMarkerBorderColor: '#ffffff',
            crosshairMarkerBorderWidth: 2,
          });
      const points = (s.points || [])
        .filter((p) => p.v != null && p.t)
        .map((p) => ({ time: p.t.slice(0, 10), value: p.v as number }));
      api.setData(points as any);
      apis.push(api);
    });

    // Quiet horizontal reference lines ("Fed target 4.5%", "breakeven").
    (referenceLines || []).forEach((rl) => {
      apis[0]?.createPriceLine({
        price: rl.value,
        color: rl.color || '#9ca3af',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: rl.label || '',
      });
    });

    // Event markers ("FOMC", "earnings") on the first series.
    if (markers?.length && apis[0]) {
      createSeriesMarkers(
        apis[0],
        markers.map((m) => ({
          time: m.t.slice(0, 10) as any,
          position: m.position === 'below' ? ('belowBar' as const) : ('aboveBar' as const),
          color: '#6b7280',
          shape: 'circle' as const,
          text: m.label,
          size: 0.6,
        })),
      );
    }

    chart.timeScale().fitContent();

    // Hover layer: crosshair + a compact shared tooltip.
    const onMove = (param: MouseEventParams) => {
      if (!param.time || !param.point) { setHover(null); return; }
      const values = apis.map((api) => {
        const d = param.seriesData.get(api) as any;
        return d?.value ?? d?.close ?? null;
      });
      setHover({ x: param.point.x, date: String(param.time), values });
    };
    chart.subscribeCrosshairMove(onMove);

    const onResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.unsubscribeCrosshairMove(onMove);
      chart.remove();
      chartRef.current = null;
    };
  }, [JSON.stringify(series), height, yFormat, hasData, JSON.stringify(referenceLines), JSON.stringify(markers)]);

  if (!hasData) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-xs text-gray-400">
        No data
      </div>
    );
  }

  // Endpoint labels ride the legend: name + last value + signed change over the
  // window (identity never rests on color alone — relief for the light slots).
  const legendRows = series.map((s, i) => {
    const pts = (s.points || []).filter((p) => p.v != null);
    const first = pts[0]?.v as number | undefined;
    const last = pts[pts.length - 1]?.v as number | undefined;
    const chg = first != null && last != null && first !== 0 ? ((last - first) / Math.abs(first)) * 100 : null;
    return { label: s.label, color: SERIES_PALETTE[i % SERIES_PALETTE.length], last, chg };
  });

  return (
    <div className="relative">
      {showLegend && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2">
          {legendRows.map((r) => (
            <div key={r.label} className="flex items-baseline gap-1.5 text-xs">
              <span className="inline-block w-2.5 h-2.5 rounded-sm self-center" style={{ background: r.color }} />
              <span className="text-gray-600">{r.label}</span>
              {r.last != null && (
                <span className="font-numeric text-gray-900 font-medium">{fmt(r.last, yFormat)}</span>
              )}
              {r.chg != null && (
                <span className={`font-numeric ${r.chg >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {r.chg >= 0 ? '+' : ''}{r.chg.toFixed(1)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      <div ref={containerRef} style={{ height }} />
      {hover && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg bg-gray-900 text-white text-[11px] px-2.5 py-1.5 shadow-lg"
          style={{ left: Math.min(Math.max(hover.x - 40, 0), (containerRef.current?.clientWidth || 200) - 120), top: showLegend ? 28 : 4 }}
        >
          <div className="text-gray-300">{hover.date}</div>
          {legendRows.map((r, i) => (
            hover.values[i] != null && (
              <div key={r.label} className="flex items-center gap-1.5">
                <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: r.color }} />
                <span>{series.length > 1 ? `${r.label} ` : ''}{fmt(hover.values[i] as number, yFormat)}</span>
              </div>
            )
          ))}
        </div>
      )}
    </div>
  );
}
