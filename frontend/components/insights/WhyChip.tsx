'use client';

/**
 * WhyChip — tap-to-explain for any price move.
 *
 * Renders a small "Why?" chip next to a price change. On click it fetches
 * Finch's read of the move — routine, news with the story intact, or a
 * narrative change; macro, sector or company — with the measured numbers behind
 * the call and source links.
 */
import { useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { insightsApi, MoveExplanation, VERDICT_META, DRIVER_LABEL, type MoveContext } from '@/lib/api';

interface WhyChipProps {
  symbol: string;
  /** Sign of today's move, used only to tint the chip. */
  changePct?: number | null;
  className?: string;
}

export default function WhyChip({ symbol, changePct, className = '' }: WhyChipProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<MoveExplanation | null>(null);
  const [error, setError] = useState(false);

  const positive = (changePct ?? 0) >= 0;

  const toggle = async () => {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (data || loading) return;
    setLoading(true);
    setError(false);
    try {
      const result = await insightsApi.whyIsItMoving(symbol);
      setData(result);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        onClick={toggle}
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium transition-colors border ${
          open
            ? 'bg-gray-900 text-white border-gray-900'
            : positive
            ? 'bg-emerald-50 text-emerald-700 border-emerald-100 hover:bg-emerald-100'
            : 'bg-red-50 text-red-600 border-red-100 hover:bg-red-100'
        }`}
        title={`Why is ${symbol} moving?`}
      >
        <Sparkles className="w-3 h-3" />
        Why?
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-2 z-30 w-96 max-w-[85vw] finch-surface rounded-xl bg-white p-3.5 shadow-lg border border-gray-100 text-left">
          <div className="flex items-start justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
              <Sparkles className="w-3 h-3 text-emerald-500" />
              Why it&apos;s moving
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-gray-300 hover:text-gray-500 -mt-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {loading && (
            <div className="space-y-2 py-1">
              <div className="h-3 rounded bg-gray-100 animate-pulse w-full" />
              <div className="h-3 rounded bg-gray-100 animate-pulse w-4/5" />
            </div>
          )}

          {error && !loading && (
            <p className="text-[13px] text-gray-500 py-1">
              Couldn&apos;t generate an explanation right now.
            </p>
          )}

          {data && !loading && (
            <>
              {data.verdict && (
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="rounded-md px-1.5 py-0.5 text-[11px] font-bold"
                    style={{ color: VERDICT_META[data.verdict].fg, background: VERDICT_META[data.verdict].bg }}>
                    {VERDICT_META[data.verdict].label}
                  </span>
                  {data.driver && <span className="text-[11px] font-medium text-gray-400">{DRIVER_LABEL[data.driver]}</span>}
                </div>
              )}
              {data.headline && <p className="text-[14px] font-semibold text-gray-900 leading-snug mb-1">{data.headline}</p>}
              <p className="text-[13px] leading-relaxed text-gray-800">{data.explanation}</p>
              {data.context && <MeasuredStrip ctx={data.context} />}
              {data.watch && (
                <p className="text-[12.5px] leading-snug text-gray-600 mt-2"><span className="font-semibold text-gray-900">Watch: </span>{data.watch}</p>
              )}
              {data.sources.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-gray-100 space-y-1">
                  {data.sources.slice(0, 2).map((s, i) => (
                    <a
                      key={i}
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-[11px] text-gray-400 hover:text-emerald-600 truncate"
                    >
                      {s.site ? `${s.site} · ` : ''}
                      {s.title}
                    </a>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/** The numbers behind the verdict: how unusual, and how much is market/sector. */
function MeasuredStrip({ ctx }: { ctx: MoveContext }) {
  const pct = (n: number | null) => (n == null ? null : `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`);
  const items = [
    ctx.move_multiple != null ? `${ctx.move_multiple}× its typical move` : null,
    pct(ctx.spy_change_pct) ? `Market ${pct(ctx.spy_change_pct)}` : null,
    pct(ctx.sector_change_pct) ? `${ctx.sector_etf || 'Sector'} ${pct(ctx.sector_change_pct)}` : null,
    ctx.volume_ratio != null ? `Volume ${ctx.volume_ratio}×` : null,
    ctx.earnings,
  ].filter(Boolean) as string[];
  if (!items.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {items.map(t => <span key={t} className="rounded-md bg-stone-100 px-1.5 py-0.5 text-[11px] font-medium text-stone-600">{t}</span>)}
    </div>
  );
}
