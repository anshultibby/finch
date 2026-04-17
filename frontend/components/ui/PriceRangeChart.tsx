'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';

export interface PriceSeriesConfig {
  symbol: string;
  color: string;
  label?: string;
}

export interface RangeOption {
  label: string;
  days: number;
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export const DEFAULT_RANGES: RangeOption[] = [
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: 'All', days: 3650 },
];

// YTD varies by current date, so recompute on each call rather than freezing at module load.
export const ytdDays = () =>
  Math.ceil((Date.now() - new Date(new Date().getFullYear(), 0, 1).getTime()) / 86400000);

export const getStockRanges = (): RangeOption[] => [
  { label: '1D', days: 1 },
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: 'YTD', days: ytdDays() },
  { label: '1Y', days: 365 },
  { label: 'MAX', days: 3650 },
];

const PAD_T = 12;
const PAD_B = 8;
const PAD_L = 2;
const PAD_R = 2;

type BaseProps = {
  height?: number;
  className?: string;
  ranges?: RangeOption[];
  format?: 'pct' | 'currency';
  hideHeader?: boolean;
  hideRangeTabs?: boolean;
  onHoverChange?: (info: { date: string; value: number } | null) => void;
  headerRight?: React.ReactNode;
};

type SymbolProps = BaseProps & {
  series: PriceSeriesConfig[];
  defaultDays?: number;
  data?: undefined;
};

type DataProps = BaseProps & {
  data: SeriesPoint[];
  color?: string;
  label?: string;
  series?: undefined;
  // Controlled range (parent drives fetch, chart reflects state)
  selectedDays?: number;
  onRangeChange?: (days: number, label: string) => void;
};

type Props = SymbolProps | DataProps;

const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
const fmtCurrency = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);

/**
 * Two modes:
 *   • Symbol: pass `series`; chart fetches /api/market-prices and displays %.
 *   • Data:   pass `data` (+ optional `selectedDays`/`onRangeChange`); parent owns
 *             data + range; chart renders currency or % based on `format`.
 */
export default function PriceRangeChart(props: Props) {
  const {
    height = 200,
    className = '',
    ranges = DEFAULT_RANGES,
    format = 'pct',
    hideHeader,
    hideRangeTabs,
    onHoverChange,
    headerRight,
  } = props;

  const isSymbolMode = 'series' in props && !!props.series;

  const [internalDays, setInternalDays] = useState(isSymbolMode ? (props as SymbolProps).defaultDays ?? 365 : 365);
  const days = isSymbolMode ? internalDays : (props as DataProps).selectedDays ?? internalDays;
  const setDays = (d: number, label: string) => {
    if (isSymbolMode) setInternalDays(d);
    else {
      (props as DataProps).onRangeChange?.(d, label);
      setInternalDays(d);
    }
  };

  const [fetched, setFetched] = useState<Record<string, SeriesPoint[]> | null>(null);
  const [fetchLoading, setFetchLoading] = useState(isSymbolMode);
  const symbolsKey = isSymbolMode ? (props as SymbolProps).series.map(s => s.symbol).join(',') : '';
  useEffect(() => {
    if (!isSymbolMode) return;
    setFetched(null);
    setFetchLoading(true);
    fetch(`/api/market-prices?symbols=${symbolsKey}&days=${days}`)
      .then(r => r.json())
      .then((d: Record<string, Array<{ date: string; pct: number }>>) => {
        const mapped: Record<string, SeriesPoint[]> = {};
        for (const [sym, pts] of Object.entries(d || {})) {
          mapped[sym] = (pts ?? []).map(p => ({ date: p.date, value: p.pct }));
        }
        setFetched(mapped);
        setFetchLoading(false);
      })
      .catch(() => setFetchLoading(false));
  }, [isSymbolMode, symbolsKey, days]);

  type Line = { label: string; color: string; data: SeriesPoint[] };
  const lines: Line[] = useMemo(() => {
    if (isSymbolMode) {
      const s = (props as SymbolProps).series;
      return s.map(cfg => ({
        label: cfg.label ?? cfg.symbol,
        color: cfg.color,
        data: fetched?.[cfg.symbol] ?? [],
      }));
    }
    const dp = props as DataProps;
    const first = dp.data[0]?.value ?? 0;
    const last = dp.data[dp.data.length - 1]?.value ?? 0;
    const isUp = last >= first;
    return [{
      label: dp.label ?? '',
      color: dp.color ?? (isUp ? '#10b981' : '#ef4444'),
      data: dp.data,
    }];
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSymbolMode, fetched, isSymbolMode ? symbolsKey : (props as DataProps).data]);

  const singleSeries = lines.length === 1;
  const loading = isSymbolMode && fetchLoading;
  const hasData = lines.some(l => l.data.length >= 2);

  const containerRef = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(600);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setW(entry.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const H = height;
  const chartW = Math.max(1, W - PAD_L - PAD_R);
  const chartH = Math.max(1, H - PAD_T - PAD_B);

  const allValues = lines.flatMap(l => l.data.map(p => p.value));
  const minY = allValues.length ? Math.min(...allValues) : 0;
  const maxY = allValues.length ? Math.max(...allValues) : 1;
  const rangeY = maxY - minY || 1;

  const refPts = lines[0]?.data ?? [];
  const n = refPts.length;

  const toX = (i: number, count: number) =>
    PAD_L + (i / Math.max(count - 1, 1)) * chartW;
  const toY = (v: number) => PAD_T + (1 - (v - minY) / rangeY) * chartH;

  const makeLinePath = (pts: SeriesPoint[]) =>
    pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${toX(i, pts.length).toFixed(1)},${toY(p.value).toFixed(1)}`).join(' ');

  const makeAreaPath = (pts: SeriesPoint[]) => {
    if (pts.length < 2) return '';
    const line = makeLinePath(pts);
    const lastX = toX(pts.length - 1, pts.length).toFixed(1);
    const firstX = toX(0, pts.length).toFixed(1);
    const bottomY = (H - PAD_B).toFixed(1);
    return `${line} L${lastX},${bottomY} L${firstX},${bottomY} Z`;
  };

  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const handleMouseMove = (e: React.MouseEvent<SVGElement>) => {
    if (!n) return;
    const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
    const x = e.clientX - rect.left - PAD_L;
    setHoverIdx(Math.max(0, Math.min(n - 1, Math.round((x / chartW) * (n - 1)))));
  };
  const handleMouseLeave = () => setHoverIdx(null);

  useEffect(() => {
    if (!onHoverChange) return;
    if (hoverIdx === null || !refPts[hoverIdx]) {
      onHoverChange(null);
    } else {
      onHoverChange({ date: refPts[hoverIdx].date, value: refPts[hoverIdx].value });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hoverIdx]);

  const isIntraday = refPts.length > 0 && (refPts[0].date.includes('T') || refPts[0].date.includes(' '));
  const parseDate = (s: string) => new Date(isIntraday ? s.replace(' ', 'T') : s + 'T12:00:00');
  const fmtHover = (s: string) => {
    const d = parseDate(s);
    if (isNaN(d.getTime())) return s;
    if (isIntraday) return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };
  const hoverDate = hoverIdx !== null && refPts[hoverIdx] ? fmtHover(refPts[hoverIdx].date) : null;

  const fmtValue = (v: number) => (format === 'currency' ? fmtCurrency(v) : fmtPct(v));
  const getDisplayValue = (pts: SeriesPoint[]) =>
    hoverIdx !== null && pts[hoverIdx] !== undefined
      ? pts[hoverIdx].value
      : pts[pts.length - 1]?.value ?? 0;

  const firstY = refPts.length ? toY(refPts[0].value) : null;
  const hoverX = hoverIdx !== null ? toX(hoverIdx, n) : null;

  return (
    <div className={`flex flex-col ${className}`}>
      {!hideHeader && isSymbolMode && hasData && (
        <div className="flex items-end gap-6 mb-1 min-h-[52px]">
          {lines.map((l, li) => {
            const v = getDisplayValue(l.data);
            return (
              <div key={li}>
                <div className="flex items-center gap-1.5 mb-0.5">
                  <div className="w-3 h-0.5 rounded-full" style={{ backgroundColor: l.color }} />
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">{l.label}</span>
                </div>
                <div
                  className="text-2xl font-bold tabular-nums leading-none transition-colors"
                  style={{ color: l.color }}
                >
                  {fmtValue(v)}
                </div>
              </div>
            );
          })}
          {headerRight}
        </div>
      )}

      {!hideRangeTabs && (
        <div className="flex items-center gap-0.5 mb-3">
          {ranges.map(r => (
            <button
              key={r.label}
              onClick={() => setDays(r.days, r.label)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                days === r.days
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      )}

      <div ref={containerRef} className="relative select-none" style={{ height }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
          </div>
        )}
        {!loading && !hasData && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-400">
            No price data available
          </div>
        )}
        {!loading && hasData && W > 0 && (
          <svg
            width={W} height={H}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{ cursor: 'crosshair', display: 'block' }}
          >
            <defs>
              {lines.map((l, li) => (
                <linearGradient key={li} id={`area-grad-${li}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={l.color} stopOpacity={0.18} />
                  <stop offset="100%" stopColor={l.color} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>

            {singleSeries && firstY !== null && (
              <line
                x1={PAD_L} y1={firstY} x2={W - PAD_R} y2={firstY}
                stroke="#d1d5db" strokeWidth={1} strokeDasharray="3,4"
              />
            )}

            {singleSeries && lines.map((l, li) => (
              l.data.length >= 2 && (
                <path key={`a-${li}`} d={makeAreaPath(l.data)} fill={`url(#area-grad-${li})`} />
              )
            ))}

            {lines.map((l, li) => (
              l.data.length >= 2 && (
                <path
                  key={`l-${li}`}
                  d={makeLinePath(l.data)}
                  fill="none"
                  stroke={l.color}
                  strokeWidth={2}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              )
            ))}

            {hoverIdx !== null && hoverX !== null && (
              <>
                <line
                  x1={hoverX} y1={PAD_T} x2={hoverX} y2={H - PAD_B}
                  stroke="#9ca3af" strokeWidth={1}
                />
                {lines.map((l, li) => {
                  const pt = l.data[hoverIdx];
                  if (!pt) return null;
                  return (
                    <g key={`h-${li}`}>
                      <circle cx={hoverX} cy={toY(pt.value)} r={4.5} fill={l.color} />
                      <circle cx={hoverX} cy={toY(pt.value)} r={2} fill="white" />
                    </g>
                  );
                })}
              </>
            )}
          </svg>
        )}

        {hoverIdx !== null && hoverX !== null && hoverDate && (
          <div
            className="absolute text-xs text-gray-500 font-semibold uppercase tracking-wide pointer-events-none whitespace-nowrap tabular-nums"
            style={{
              left: Math.min(Math.max(hoverX - 60, 4), (W || 300) - 124),
              top: 2,
            }}
          >
            {hoverDate}
          </div>
        )}
      </div>
    </div>
  );
}
