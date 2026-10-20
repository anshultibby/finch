'use client';

/**
 * WatchRadar — the user's stocks as blips on a radar Finch is sweeping.
 *
 * Distance from centre = size of today's move (capped), colour = direction,
 * a bigger blip = a holding, a ring = the user has written a thesis. The sweep
 * is the page's one continuous motion: each blip brightens as it passes, which
 * is the literal picture of "Finch is watching". Respects reduced motion.
 */
import { useMemo, useState } from 'react';

export interface RadarBlip {
  symbol: string;
  changePct: number | null;
  held?: boolean;
  thesis?: boolean;
  alert?: boolean; // e.g. a story change / weakened thesis on this name
}

const SWEEP_SECONDS = 7;
const MAX_MOVE = 6; // % move that reaches the outer ring

export default function WatchRadar({ blips, size = 300, onSelect }: {
  blips: RadarBlip[];
  size?: number;
  onSelect?: (symbol: string) => void;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const c = size / 2;
  const R = c - 14;

  const placed = useMemo(() => {
    const n = Math.max(blips.length, 1);
    // Biggest movers get labels; everything else reveals on hover.
    const labelled = new Set(
      [...blips].sort((a, b) => Math.abs(b.changePct ?? 0) - Math.abs(a.changePct ?? 0)).slice(0, 6).map(b => b.symbol),
    );
    return blips.map((b, i) => {
      const angle = (i / n) * 360 - 90 + 17; // start near 12 o'clock, offset so labels don't stack
      const mag = Math.min(Math.abs(b.changePct ?? 0) / MAX_MOVE, 1);
      const r = 26 + mag * (R - 34);
      const rad = (angle * Math.PI) / 180;
      return {
        ...b,
        x: c + r * Math.cos(rad),
        y: c + r * Math.sin(rad),
        // When the sweep (starting at 12 o'clock, clockwise) reaches this blip.
        delay: (((angle + 90) % 360 + 360) % 360) / 360 * SWEEP_SECONDS,
        labelled: labelled.has(b.symbol),
      };
    });
  }, [blips, c, R]);

  const color = (b: RadarBlip) =>
    b.alert ? '#fbbf24' : b.changePct == null ? '#a7f3d0' : b.changePct >= 0 ? '#34d399' : '#fb7185';

  return (
    <div className="relative select-none" style={{ width: size, height: size }}>
      <style>{`
        @keyframes finch-sweep { to { transform: rotate(360deg); } }
        @keyframes finch-blip { 0% { opacity: 1; transform: scale(1.9); } 18% { opacity: .95; transform: scale(1); } 100% { opacity: .55; transform: scale(1); } }
        .finch-sweep { transform-origin: ${c}px ${c}px; animation: finch-sweep ${SWEEP_SECONDS}s linear infinite; }
        .finch-blip { transform-box: fill-box; transform-origin: center; animation: finch-blip ${SWEEP_SECONDS}s ease-out infinite; opacity: .55; }
        @media (prefers-reduced-motion: reduce) {
          .finch-sweep { animation: none; opacity: .35; }
          .finch-blip { animation: none; opacity: .9; }
        }
      `}</style>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img"
        aria-label={`Finch is watching ${blips.length} stock${blips.length === 1 ? '' : 's'}`}>
        <defs>
          <radialGradient id="finch-radar-bg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#0f5a45" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#04241c" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="finch-sweep-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#34d399" stopOpacity="0" />
            <stop offset="100%" stopColor="#34d399" stopOpacity="0.28" />
          </linearGradient>
        </defs>

        <circle cx={c} cy={c} r={R} fill="url(#finch-radar-bg)" />
        {[0.33, 0.66, 1].map(f => (
          <circle key={f} cx={c} cy={c} r={R * f} fill="none" stroke="#a7f3d0" strokeOpacity={f === 1 ? 0.22 : 0.1} />
        ))}
        <line x1={c - R} y1={c} x2={c + R} y2={c} stroke="#a7f3d0" strokeOpacity="0.07" />
        <line x1={c} y1={c - R} x2={c} y2={c + R} stroke="#a7f3d0" strokeOpacity="0.07" />
        <text x={c + R * 0.66 + 4} y={c - 4} fill="#a7f3d0" fillOpacity="0.35" fontSize="9">±4%</text>

        {/* The sweep: a soft wedge trailing a bright edge, rotating clockwise from 12 o'clock. */}
        <g className="finch-sweep">
          <path d={`M ${c} ${c} L ${c} ${c - R} A ${R} ${R} 0 0 0 ${c - R * Math.sin(Math.PI / 5)} ${c - R * Math.cos(Math.PI / 5)} Z`}
            fill="url(#finch-sweep-grad)" />
          <line x1={c} y1={c} x2={c} y2={c - R} stroke="#6ee7b7" strokeOpacity="0.6" strokeWidth="1.2" />
        </g>

        {placed.map(b => (
          <g key={b.symbol} style={{ cursor: onSelect ? 'pointer' : 'default' }}
            onMouseEnter={() => setHover(b.symbol)} onMouseLeave={() => setHover(null)}
            onClick={() => onSelect?.(b.symbol)}>
            <title>{`${b.symbol}${b.changePct != null ? ` ${b.changePct >= 0 ? '+' : ''}${b.changePct.toFixed(2)}%` : ''}${b.held ? ' · held' : ''}${b.thesis ? ' · has a thesis' : ''}`}</title>
            {b.thesis && <circle cx={b.x} cy={b.y} r={b.held ? 9 : 7.5} fill="none" stroke={color(b)} strokeOpacity="0.5" />}
            <circle className="finch-blip" cx={b.x} cy={b.y} r={b.held ? 4.6 : 3.4} fill={color(b)}
              style={{ animationDelay: `${b.delay}s`, filter: `drop-shadow(0 0 6px ${color(b)})` }} />
            {(b.labelled || hover === b.symbol) && (
              <text x={b.x + 9} y={b.y + 3.5} fontSize="10.5" fontWeight={600}
                fill="#ecfdf5" fillOpacity={hover === b.symbol ? 1 : 0.78}>
                {b.symbol}
                {hover === b.symbol && b.changePct != null && (
                  <tspan fill={color(b)} fontWeight={700}>{` ${b.changePct >= 0 ? '+' : ''}${b.changePct.toFixed(1)}%`}</tspan>
                )}
              </text>
            )}
          </g>
        ))}

        <circle cx={c} cy={c} r="3" fill="#6ee7b7" />
      </svg>
    </div>
  );
}
