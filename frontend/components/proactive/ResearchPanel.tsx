'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Search, X, ArrowUpRight, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { marketApi, watchlistApi } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import TickerLogo from '@/components/ui/TickerLogo';
import { ui } from './shared';

// Financials: find a company, land on its statements. Filed numbers come from
// the statements (with SEC links on the stock page); anything interpretive is
// handed to Finch in chat. Mirrors frontend-mobile/app/research.tsx.

const DEEP_DIVES = [
  { label: 'Read the latest 10-K for me', prompt: (s: string) => `Read ${s}'s latest 10-K and give me: what changed vs. last year, the 3 biggest risks they disclosed, and anything buried in the footnotes. Quote the filing.` },
  { label: 'Is it cheap or expensive?', prompt: (s: string) => `Is ${s} cheap or expensive right now? Compare its valuation multiples to its own 5-year history and its closest peers, then take a stance.` },
  { label: 'Bull vs. bear case', prompt: (s: string) => `Give me the strongest bull case and the strongest bear case for ${s}, each backed by numbers from the financials. Then tell me which side you'd take.` },
];

export default function ResearchPanel() {
  const { user } = useAuth();
  const { openStock, openChatWithPrompt } = useNavigation();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [mine, setMine] = useState<string[]>([]);
  const debounce = useRef<ReturnType<typeof setTimeout>>();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => {
    if (!user) return;
    watchlistApi.getWatchlist(user.id)
      .then(d => setMine((d?.symbols || d?.watchlist || []).map((i: any) => (typeof i === 'string' ? i : i.symbol)).filter(Boolean)))
      .catch(() => {});
  }, [user]);

  const onChange = (text: string) => {
    setQ(text);
    if (debounce.current) clearTimeout(debounce.current);
    if (!text.trim()) { setResults([]); return; }
    debounce.current = setTimeout(async () => {
      setSearching(true);
      try {
        const d = await marketApi.searchStocks(text.trim(), 10);
        setResults(Array.isArray(d) ? d : d?.results || []);
      } catch { setResults([]); }
      finally { setSearching(false); }
    }, 250);
  };

  const open = (symbol: string) => openStock(symbol, 'financials');
  const focus = mine[0] || 'AAPL';

  return (
    <div className="h-full overflow-y-auto bg-[#fafaf9]">
      <div className={ui.page}>
        <PageHeader title="Financials" subtitle="Statements, filings, earnings calls" />

        <div className="flex items-center gap-2 bg-white border border-stone-200 rounded-xl px-3.5 focus-within:border-stone-300">
          <Search className="w-4 h-4 text-stone-400" />
          <input ref={inputRef} data-testid="research-search" value={q} onChange={e => onChange(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && results[0] && open(results[0].symbol)}
            placeholder="Search a company or ticker" className="flex-1 bg-transparent text-[15.5px] py-3 focus:outline-none" />
          {searching ? <Loader2 className="w-4 h-4 animate-spin text-stone-400" /> : q && (
            <button onClick={() => onChange('')} aria-label="Clear"><X className="w-4 h-4 text-stone-400" /></button>
          )}
        </div>

        {q.trim() ? (
          <div className={`${ui.card} overflow-hidden mt-3`}>
            {!searching && results.length === 0 ? (
              <p className="p-4 text-center text-[14px] text-stone-500">No matches for &ldquo;{q}&rdquo;.</p>
            ) : results.map(r => (
              <button key={`${r.symbol}-${r.exchangeShortName}`} onClick={() => open(r.symbol)} className={ui.row}>
                <TickerLogo symbol={r.symbol} size={30} />
                <div className="flex-1 min-w-0">
                  <div className="text-[14.5px] font-bold text-gray-900">{r.symbol}</div>
                  <div className="text-[12.5px] text-stone-500 truncate">{r.name}{r.exchangeShortName ? ` · ${r.exchangeShortName}` : ''}</div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <>
            {mine.length > 0 && (
              <>
                <div className={ui.section}>Your stocks</div>
                <div className="flex flex-wrap gap-2">
                  {mine.slice(0, 20).map(s => (
                    <button key={s} onClick={() => open(s)} className={`${ui.chip} ${ui.chipOff} font-bold flex items-center gap-1.5`}>
                      <TickerLogo symbol={s} size={18} /> {s}
                    </button>
                  ))}
                </div>
              </>
            )}
            <div className={ui.section}>Have Finch dig in{mine.length > 0 ? ` · ${focus}` : ''}</div>
            <div className={`${ui.card} overflow-hidden`}>
              {DEEP_DIVES.map(d => (
                <button key={d.label} onClick={() => openChatWithPrompt(d.prompt(focus), `${focus}: ${d.label}`)} className={ui.row}>
                  <span className="flex-1 text-[14px] text-gray-900">{d.label}</span>
                  <ArrowUpRight className="w-4 h-4 text-stone-400" />
                </button>
              ))}
            </div>
            <p className="text-[11.5px] text-stone-400 mt-4 leading-relaxed">
              Statements are as filed (via Financial Modeling Prep, with SEC links on each stock). Finch&apos;s read of them is AI-generated — check the source before acting.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
