'use client';

import React, { useState, useEffect, useRef } from 'react';

export interface PriceSeriesConfig {
  symbol: string;
  color: string;
  label?: string;
}

export interface RangeOption {
  label: string;
  days: number;
}

export const DEFAULT_RANGES: RangeOption[] = [
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: 'All', days: 3650 },
];

interface PricePt { date: string; pct: number }

const PAD_T = 8;
const PAD_B = 28; // x-axis labels
const PAD_L = 4;
const PAD_R = 52; // y-axis labels

/**
 * Reusable multi-line price chart with range selector and Robinhood-style hover.
 * Live values update above the chart as you scrub.
 * Fetches from /api/market-prices — no API key required.
 */
export default function PriceRangeChart({
  series,
  defaultDays = 365,
  ranges = DEFAULT_RANGES,
  height = 200,
  className = '',
}: {
  series: PriceSeriesConfig[];
  defaultDays?: number;
  ranges?: RangeOption[];
  height?: number;
  className?: string;
}) {
  const [days, setDays] = useState(defaultDays);
  const [data, setData] = useState<Record<string, PricePt[]> | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(600);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setW(entry.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const symbolsKey = series.map(s => s.symbol).join(',');
  useEffect(() => {
    setData(null);
    setLoading(true);
    setHoverIdx(null);
    fetch(`/api/market-prices?symbols=${symbolsKey}&days=${days}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbolsKey, days]);

  const H = height;
  const chartW = W - PAD_L - PAD_R;
  const chartH = H - PAD_T - PAD_B;

  const allSeriesPts = series.map(s => data?.[s.symbol] ?? []);
  const allPcts = allSeriesPts.flat().map(p => p.pct);
  const minY = allPcts.length ? Math.min(...allPcts) : -10;
  const maxY = allPcts.length ? Math.max(...allPcts) : 10;
  const rangeY = maxY - minY || 1;

  const refPts = allSeriesPts[0] ?? [];
  const n = refPts.length;

  const toX = (i: number) => PAD_L + (i / Math.max(n - 1, 1)) * chartW;
  const toY = (pct: number) => PAD_T + (1 - (pct - minY) / rangeY) * chartH;
  const makePath = (pts: PricePt[]) =>
    pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${toX(i).toFixed(1)},${toY(p.pct).toFixed(1)}`).join(' ');

  // 4 evenly-spaced x-axis labels
  const xLabels: { x: number; label: string }[] = [];
  if (n > 1) {
    [0, Math.floor(n / 3), Math.floor(2 * n / 3), n - 1].forEach(idx => {
      const d = new Date(refPts[idx].date + 'T00:00:00');
      xLabels.push({
        x: toX(idx),
        label: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      });
    });
  }

  const hoverX = hoverIdx !== null ? toX(hoverIdx) : null;
  const hoverDate = hoverIdx !== null && refPts[hoverIdx]
    ? new Date(refPts[hoverIdx].date + 'T00:00:00').toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
      })
    : null;

  const handleMouseMove = (e: React.MouseEvent<SVGElement>) => {
    if (!n) return;
    const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
    const x = e.clientX - rect.left - PAD_L;
    setHoverIdx(Math.max(0, Math.min(n - 1, Math.round((x / chartW) * (n - 1)))));
  };

  // Returns pct at hover point, or last point when idle
  const getPct = (pts: PricePt[]) =>
    hoverIdx !== null && pts[hoverIdx] !== undefined
      ? pts[hoverIdx].pct
      : pts[pts.length - 1]?.pct ?? 0;

  const hasData = allPcts.length > 0;
  const isHovering = hoverIdx !== null;

  return (
    <div className={`flex flex-col ${className}`}>

      {/* ── Live values header (Robinhood pattern) ── */}
      {hasData && (
        <div className="flex items-end gap-6 mb-1 min-h-[52px]">
          {series.map((s, si) => {
            const pts = allSeriesPts[si];
            const pct = getPct(pts);
            const isPos = pct >= 0;
            return (
              <div key={s.symbol}>
                <div className="flex items-center gap-1.5 mb-0.5">
                  <div className="w-3 h-0.5 rounded-full" style={{ backgroundColor: s.color }} />
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                    {s.label ?? s.symbol}
                  </span>
                </div>
                <div
                  className="text-2xl font-bold tabular-nums leading-none transition-colors"
                  style={{ color: s.color }}
                >
                  {isPos ? '+' : ''}{pct.toFixed(1)}%
                </div>
              </div>
            );
          })}

          {/* Date — appears when hovering, fades out otherwise */}
          <div className={`ml-auto pb-1 text-xs font-medium text-gray-400 transition-opacity ${isHovering ? 'opacity-100' : 'opacity-0'}`}>
            {hoverDate ?? ''}
          </div>
        </div>
      )}

      {/* ── Range tabs ── */}
      <div className="flex items-center gap-0.5 mb-3">
        {ranges.map(r => (
          <button
            key={r.label}
            onClick={() => setDays(r.days)}
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

      {/* ── Chart ── */}
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
            onMouseLeave={() => setHoverIdx(null)}
            style={{ cursor: 'crosshair', display: 'block' }}
          >
            {/* Zero baseline */}
            {(() => {
              const zy = toY(0);
              return zy >= PAD_T && zy <= H - PAD_B
                ? <line x1={PAD_L} y1={zy} x2={W - PAD_R} y2={zy}
                    stroke="#e5e7eb" strokeWidth={1} strokeDasharray="4,3" />
                : null;
            })()}

            {/* Series lines */}
            {series.map((s, si) => {
              const pts = allSeriesPts[si];
              if (pts.length < 2) return null;
              return (
                <path key={s.symbol} d={makePath(pts)} fill="none"
                  stroke={s.color} strokeWidth={2}
                  strokeLinejoin="round" strokeLinecap="round" />
              );
            })}

            {/* Hover crosshair */}
            {hoverIdx !== null && hoverX !== null && (
              <>
                <line x1={hoverX} y1={PAD_T} x2={hoverX} y2={H - PAD_B}
                  stroke="#9ca3af" strokeWidth={1} />
                {series.map((s, si) => {
                  const pt = allSeriesPts[si][hoverIdx];
                  if (!pt) return null;
                  return (
                    <circle key={s.symbol}
                      cx={hoverX} cy={toY(pt.pct)} r={4}
                      fill="white" stroke={s.color} strokeWidth={2.5} />
                  );
                })}
              </>
            )}

            {/* X-axis labels */}
            {xLabels.map((d, i) => (
              <text key={i} x={d.x} y={H - 8}
                textAnchor={i === 0 ? 'start' : i === xLabels.length - 1 ? 'end' : 'middle'}
                fontSize={10} fill="#9ca3af" fontFamily="system-ui, sans-serif">
                {d.label}
              </text>
            ))}

            {/* Y-axis labels — right */}
            <text x={W - PAD_R + 6} y={PAD_T + 10}
              fontSize={9} fill="#9ca3af" fontFamily="system-ui, sans-serif">
              {maxY >= 0 ? '+' : ''}{maxY.toFixed(1)}%
            </text>
            <text x={W - PAD_R + 6} y={H - PAD_B - 2}
              fontSize={9} fill="#9ca3af" fontFamily="system-ui, sans-serif">
              {minY >= 0 ? '+' : ''}{minY.toFixed(1)}%
            </text>
          </svg>
        )}
      </div>
    </div>
  );
}
