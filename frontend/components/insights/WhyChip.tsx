'use client';

/**
 * WhyChip — tap-to-explain for any price move.
 *
 * Renders a small "Why?" chip next to a price change. On click it fetches the
 * AI move explanation (grounded in today's headlines, cached server-side) and
 * reveals it in an inline card with source links.
 */
import { useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { insightsApi, MoveExplanation } from '@/lib/api';

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
        <div className="absolute left-0 top-full mt-2 z-30 w-80 max-w-[85vw] finch-surface rounded-xl bg-white p-3.5 shadow-lg border border-gray-100 text-left">
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
              <p className="text-[13px] leading-relaxed text-gray-800">{data.explanation}</p>
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
