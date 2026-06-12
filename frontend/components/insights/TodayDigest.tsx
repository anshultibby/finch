'use client';

/**
 * TodayDigest — the generated "Today" story for the user's portfolio.
 *
 * Shows the day's P&L, an AI narrative of what drove it (grounded in
 * headlines), and tappable mover chips that expand into per-stock
 * "why it's moving" explanations.
 */
import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { insightsApi, PortfolioDigest, MoveExplanation } from '@/lib/api';

interface TodayDigestProps {
  userId: string;
  onSelectSymbol?: (symbol: string) => void;
  className?: string;
}

export default function TodayDigest({ userId, onSelectSymbol, className = '' }: TodayDigestProps) {
  const [digest, setDigest] = useState<PortfolioDigest | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [explanations, setExplanations] = useState<Record<string, MoveExplanation | 'loading' | 'error'>>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    insightsApi
      .getPortfolioDigest(userId)
      .then(d => { if (!cancelled) setDigest(d); })
      .catch(() => { if (!cancelled) setDigest(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [userId]);

  const toggleMover = async (symbol: string) => {
    if (expanded === symbol) {
      setExpanded(null);
      return;
    }
    setExpanded(symbol);
    if (explanations[symbol] && explanations[symbol] !== 'error') return;
    setExplanations(prev => ({ ...prev, [symbol]: 'loading' }));
    try {
      const result = await insightsApi.whyIsItMoving(symbol);
      setExplanations(prev => ({ ...prev, [symbol]: result }));
    } catch {
      setExplanations(prev => ({ ...prev, [symbol]: 'error' }));
    }
  };

  if (loading) {
    return (
      <div className={`finch-surface rounded-2xl bg-white p-5 ${className}`}>
        <div className="flex items-center gap-1.5 mb-3">
          <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-gray-400">Today</span>
        </div>
        <div className="space-y-2">
          <div className="h-3.5 rounded bg-gray-100 animate-pulse w-full" />
          <div className="h-3.5 rounded bg-gray-100 animate-pulse w-3/4" />
        </div>
      </div>
    );
  }

  if (!digest || !digest.success || digest.mode === 'empty' || !digest.narrative) {
    return null;
  }

  const isPortfolio = digest.mode === 'portfolio';
  const dayChange = digest.day_change ?? 0;
  const dayUp = dayChange >= 0;
  const expandedExplanation = expanded ? explanations[expanded] : undefined;

  return (
    <div className={`finch-surface rounded-2xl bg-white p-5 ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-gray-400">
            {isPortfolio ? 'Today' : 'Your watchlist today'}
          </span>
        </div>
        {isPortfolio && (
          <span className={`text-sm font-bold font-numeric ${dayUp ? 'text-emerald-600' : 'text-red-500'}`}>
            {dayUp ? '+' : '-'}${Math.abs(dayChange).toLocaleString(undefined, { maximumFractionDigits: 0 })}
            {' '}({dayUp ? '+' : ''}{(digest.day_change_pct ?? 0).toFixed(2)}%)
          </span>
        )}
      </div>

      <p className="text-[13.5px] leading-relaxed text-gray-700">{digest.narrative}</p>

      {(digest.movers?.length ?? 0) > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3.5">
          {digest.movers!.map(m => {
            const up = m.change_pct >= 0;
            const active = expanded === m.symbol;
            return (
              <button
                key={m.symbol}
                onClick={() => toggleMover(m.symbol)}
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
                  active
                    ? 'bg-gray-900 text-white border-gray-900'
                    : 'bg-white border-gray-150 text-gray-700 hover:border-gray-300'
                }`}
                style={!active ? { borderColor: 'rgba(0,0,0,0.08)' } : undefined}
              >
                <span className="font-semibold">{m.symbol}</span>
                <span className={`font-numeric ${active ? (up ? 'text-emerald-300' : 'text-red-300') : up ? 'text-emerald-600' : 'text-red-500'}`}>
                  {up ? '+' : ''}{m.change_pct.toFixed(1)}%
                </span>
              </button>
            );
          })}
        </div>
      )}

      {expanded && (
        <div className="mt-3 rounded-xl bg-gray-50 border border-gray-100 p-3">
          {expandedExplanation === 'loading' && (
            <div className="space-y-2">
              <div className="h-3 rounded bg-gray-200/70 animate-pulse w-full" />
              <div className="h-3 rounded bg-gray-200/70 animate-pulse w-2/3" />
            </div>
          )}
          {expandedExplanation === 'error' && (
            <p className="text-xs text-gray-500">Couldn&apos;t generate an explanation right now.</p>
          )}
          {expandedExplanation && expandedExplanation !== 'loading' && expandedExplanation !== 'error' && (
            <>
              <p className="text-[13px] leading-relaxed text-gray-700">{expandedExplanation.explanation}</p>
              <div className="flex items-center justify-between mt-2">
                {expandedExplanation.sources[0] ? (
                  <a
                    href={expandedExplanation.sources[0].url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-gray-400 hover:text-emerald-600 truncate max-w-[70%]"
                  >
                    {expandedExplanation.sources[0].site ? `${expandedExplanation.sources[0].site} · ` : ''}
                    {expandedExplanation.sources[0].title}
                  </a>
                ) : <span />}
                {onSelectSymbol && (
                  <button
                    onClick={() => onSelectSymbol(expanded)}
                    className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 shrink-0"
                  >
                    View {expanded} →
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
