'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { Clock, Pause, Play, Plus, Trash2, ArrowUp, Loader2, ExternalLink, Download } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { watchlistApi, marketApi, jobsApi, accountApi, thesesApi, THESIS_STATUS_META, type ScheduledJob, type UserPreferences, type Thesis } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import TickerLogo from '@/components/ui/TickerLogo';
import WatchlistImportModal from '@/components/home/WatchlistImportModal';
import { CHECK_TEMPLATES, cadenceLabel, nextRunAt, shortWhen, fmtUsd, fmtPct, ui } from './shared';

// Everything Finch keeps an eye on, in one place: the stocks, the recurring
// checks (each a plain-English rule you can pause), and how often Finch is
// allowed to reach out. Mirrors frontend-mobile/app/watching.tsx.

type Stock = { symbol: string; name?: string; price?: number; change_pct?: number };

// Morning brief and the heartbeat (and its one-off tripwire runs) are
// controlled by the Check-ins toggles below.
const TOGGLED_SYSTEM_JOBS = new Set(['morning_brief', 'heartbeat', 'heartbeat_trigger']);

export default function WatchingPanel() {
  const { user } = useAuth();
  const { openStock, openChatWithPrompt, loadChat, navigateTo } = useNavigation();
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [owned, setOwned] = useState<string[]>([]);
  const [custom, setCustom] = useState('');
  const [adding, setAdding] = useState<string | null>(null);
  const [addSymbol, setAddSymbol] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStocks = useCallback(async () => {
    if (!user) return;
    const d = await watchlistApi.getWatchlist(user.id).catch(() => null);
    const raw: any[] = d?.symbols || d?.watchlist || [];
    if (raw.length && typeof raw[0] === 'object') {
      setStocks(raw.map(i => ({ symbol: i.symbol, name: i.name, price: i.price, change_pct: i.changesPercentage ?? i.change_pct })));
      return;
    }
    const syms = raw.map(String);
    if (!syms.length) { setStocks([]); return; }
    const quotes = await marketApi.getBatchQuotes(syms.slice(0, 40)).catch(() => []);
    const m = new Map((Array.isArray(quotes) ? quotes : []).map((q: any) => [q.symbol, q]));
    setStocks(syms.map(s => ({ symbol: s, name: (m.get(s) as any)?.name, price: (m.get(s) as any)?.price, change_pct: (m.get(s) as any)?.changesPercentage })));
  }, [user]);

  // Built-ins with their own toggle under Check-ins aren't repeated as checks.
  const loadJobs = useCallback(() => jobsApi.list()
    .then(d => setJobs((d.jobs || []).filter(j =>
      j.status !== 'cancelled' && j.status !== 'done' && !TOGGLED_SYSTEM_JOBS.has(j.system_key || ''))))
    .catch(() => {}), []);

  useEffect(() => {
    if (!user) return;
    loadStocks();
    loadJobs();
    accountApi.getPreferences(user.id).then(setPrefs).catch(() => {});
    thesesApi.list().then(d => { setTheses(d.theses || []); setOwned(d.owned || []); }).catch(() => {});
  }, [user, loadStocks, loadJobs]);

  if (!user) return null;

  const addTemplate = async (t: typeof CHECK_TEMPLATES[number]) => {
    setAdding(t.name);
    setError(null);
    try {
      await jobsApi.create({ name: t.name, message: t.message, recurrence: t.recurrence, run_at: nextRunAt(t.hour, t.recurrence === 'weekly') });
      await loadJobs();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Couldn't add that check — you may be at your plan's limit.");
    } finally {
      setAdding(null);
    }
  };

  const submitCustom = () => {
    const t = custom.trim();
    if (!t) return;
    setCustom('');
    openChatWithPrompt(
      `Set up a recurring check for me: "${t}". Restate it as a precise rule, pick a sensible schedule, confirm with me, then schedule it. Only notify me when the rule actually fires.`,
      'New check',
    );
  };

  const setPref = async (patch: Partial<UserPreferences>) => {
    if (!prefs) return;
    const prev = prefs;
    setPrefs({ ...prefs, ...patch });
    try { setPrefs(await accountApi.updatePreferences(user.id, patch)); } catch { setPrefs(prev); }
  };

  const addStock = async () => {
    const sym = addSymbol.trim().toUpperCase();
    if (!sym) return;
    setAddSymbol('');
    await watchlistApi.addSymbol(user.id, sym).catch(() => {});
    loadStocks();
  };

  const removeStock = async (sym: string) => {
    setStocks(s => s.filter(x => x.symbol !== sym));
    await watchlistApi.removeSymbol(user.id, sym).catch(() => loadStocks());
  };

  const active = jobs.filter(j => j.status !== 'paused').length;

  return (
    <div className="h-full overflow-y-auto bg-[#fafaf9]">
      <div className={ui.page}>
        <PageHeader title="Watching" subtitle={`${stocks.length} stocks · ${active} active check${active === 1 ? '' : 's'}`} />

        {/* Theses — the user's own story per stock; every alert is judged against these */}
        <div className={`${ui.section} mt-0`}>Your theses</div>
        {theses.length === 0 ? (
          <p className={`${ui.card} p-4 text-[13.5px] text-stone-500 mb-2`}>
            Write down why you own each stock and what would make you wrong. Finch judges every move, earnings report and dividend change against your words. Open any stock to add one.
          </p>
        ) : (
          <div className={`${ui.card} overflow-hidden mb-2`}>
            {theses.map(t => {
              const last = [...t.log].reverse().find(e => e.status);
              return (
                <button key={t.symbol} onClick={() => openStock(t.symbol)} className={ui.row}>
                  <TickerLogo symbol={t.symbol} size={26} />
                  <div className="flex-1 min-w-0">
                    <div className="text-[14.5px] font-bold text-gray-900">{t.symbol}</div>
                    <div className="text-[12.5px] text-stone-500 truncate">{t.why}</div>
                  </div>
                  {last?.status && (
                    <span className="rounded-md px-1.5 py-0.5 text-[10.5px] font-bold"
                      style={{ color: THESIS_STATUS_META[last.status].fg, background: THESIS_STATUS_META[last.status].bg }}>{last.status}</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
        {(() => {
          // Held names first (real money), then the watchlist.
          const has = (sym: string) => theses.some(t => t.symbol === sym.toUpperCase());
          const uncovered = Array.from(new Set([...owned, ...stocks.map(s => s.symbol.toUpperCase())])).filter(sym => !has(sym));
          if (!uncovered.length) return null;
          return (
            <div className="mb-2">
              <p className="text-[12.5px] text-stone-500 mb-1.5">No thesis yet — click to write one:</p>
              <div className="flex flex-wrap gap-1.5">
                {uncovered.slice(0, 12).map(sym => (
                  <button key={sym} onClick={() => openStock(sym)} className={`${ui.chip} ${ui.chipOff} font-bold`}>+ {sym}{owned.includes(sym) ? ' · held' : ''}</button>
                ))}
              </div>
            </div>
          );
        })()}

        {/* Checks */}
        <div className="flex items-end justify-between">
          <div className={ui.section}>Checks Finch runs for you</div>
          <button onClick={() => navigateTo({ type: 'jobs' })} className="mb-2.5 text-[12.5px] font-bold text-emerald-700 hover:underline">
            All automations
          </button>
        </div>
        {jobs.length > 0 && (
          <div className={`${ui.card} overflow-hidden mb-3`}>
            {jobs.map(j => {
              const isPaused = j.status === 'paused';
              return (
                <div key={j.id} className="flex items-center gap-3 px-4 py-3 border-t first:border-t-0 border-stone-100">
                  {isPaused ? <Pause className="w-4 h-4 text-stone-400" /> : <Clock className="w-4 h-4 text-emerald-600" />}
                  <div className="flex-1 min-w-0" title={j.message}>
                    <div className={`text-[14.5px] font-bold truncate ${isPaused ? 'text-stone-400' : 'text-gray-900'}`}>{j.name}</div>
                    <div className="text-[12.5px] text-stone-500 truncate">
                      {cadenceLabel(j.recurrence as string)}
                      {isPaused ? ' · paused' : j.run_at ? ` · next ${shortWhen(j.run_at)}` : ''}
                      {j.last_run_at ? ` · last ran ${new Date(j.last_run_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : ''}
                    </div>
                  </div>
                  {j.run_chat_id && (
                    <button onClick={() => loadChat(j.run_chat_id!)} title="See last run" className="p-1.5 text-stone-400 hover:text-stone-700"><ExternalLink className="w-4 h-4" /></button>
                  )}
                  <button onClick={() => (isPaused ? jobsApi.resume(j.id) : jobsApi.pause(j.id)).then(loadJobs).catch(() => {})}
                    title={isPaused ? 'Resume' : 'Pause'} className="p-1.5 text-stone-400 hover:text-stone-700">
                    {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                  </button>
                  {!j.system_key && (
                    <button onClick={() => window.confirm(`Delete "${j.name}"?`) && jobsApi.cancel(j.id).then(loadJobs).catch(() => {})}
                      title="Delete" className="p-1.5 text-stone-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="bg-white border border-emerald-100 rounded-2xl p-3">
          <div className="flex items-center gap-2 pl-2">
            <input value={custom} onChange={e => setCustom(e.target.value)} onKeyDown={e => e.key === 'Enter' && submitCustom()}
              placeholder="Tell Finch what to watch for…" className="flex-1 bg-transparent text-[15px] py-2 focus:outline-none" />
            <button onClick={submitCustom} disabled={!custom.trim()} aria-label="Set up check"
              className={`w-8 h-8 rounded-full flex items-center justify-center ${custom.trim() ? 'bg-emerald-600 text-white' : 'bg-stone-200 text-white'}`}>
              <ArrowUp className="w-4 h-4" strokeWidth={2.6} />
            </button>
          </div>
          {CHECK_TEMPLATES.filter(t => !jobs.some(j => j.name === t.name)).map(t => (
            <button key={t.name} onClick={() => addTemplate(t)} disabled={!!adding}
              className="w-full flex items-center gap-2 px-2 py-2 text-left text-[13.5px] font-medium text-stone-700 hover:text-gray-900">
              {adding === t.name ? <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" /> : <Plus className="w-3.5 h-3.5 text-emerald-600" />}
              {t.label}
            </button>
          ))}
        </div>
        {error && <div className="text-[12.5px] text-red-600 mt-2">{error}</div>}

        {/* Check-ins */}
        {prefs && (
          <>
            <div className={ui.section}>Check-ins</div>
            <div className={`${ui.card} overflow-hidden`}>
              <Toggle title="Morning brief" sub={`What changed overnight, before the open · ${prefs.morning_brief_time}`}
                on={prefs.morning_brief_enabled} onChange={v => setPref({ morning_brief_enabled: v, morning_brief_timezone: localTimeZone() })} />
              <Toggle title="Daily portfolio watch" sub="Finch reviews your book and the news, and pings you only if it matters"
                on={prefs.heartbeat_enabled} onChange={v => setPref({ heartbeat_enabled: v })} />
            </div>
          </>
        )}

        {/* Stocks */}
        <div className="flex items-end justify-between">
          <div className={ui.section}>Stocks</div>
          <button onClick={() => setShowImport(true)} className="mb-2.5 flex items-center gap-1.5 text-[12.5px] font-bold text-emerald-700">
            <Download className="w-3.5 h-3.5" /> Import
          </button>
        </div>
        <div className={`${ui.card} overflow-hidden`}>
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-stone-100">
            <input value={addSymbol} onChange={e => setAddSymbol(e.target.value)} onKeyDown={e => e.key === 'Enter' && addStock()}
              placeholder="Add a ticker…" className="flex-1 bg-transparent text-[14px] py-1 uppercase placeholder:normal-case focus:outline-none" />
            <button onClick={addStock} disabled={!addSymbol.trim()} className="text-[13px] font-bold text-emerald-700 disabled:text-stone-300">Add</button>
          </div>
          {stocks.length === 0 ? (
            <p className="px-4 py-4 text-[13.5px] text-stone-500">No stocks yet. Add a few, or import from a screenshot or Robinhood, and Finch starts watching them.</p>
          ) : stocks.map(s => (
            <div key={s.symbol} className="group flex items-center gap-3 px-4 py-2.5 border-t first:border-t-0 border-stone-100 hover:bg-stone-50">
              <button onClick={() => openStock(s.symbol)} className="flex-1 min-w-0 flex items-center gap-3 text-left">
                <TickerLogo symbol={s.symbol} size={28} />
                <div className="min-w-0">
                  <div className="text-[14.5px] font-bold text-gray-900">{s.symbol}</div>
                  {s.name && <div className="text-[12px] text-stone-500 truncate">{s.name}</div>}
                </div>
              </button>
              <div className="text-right">
                <div className="text-[14px] font-medium tabular-nums text-gray-900">{fmtUsd(s.price)}</div>
                {s.change_pct != null && <div className={`text-[12px] tabular-nums ${s.change_pct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>{fmtPct(s.change_pct)}</div>}
              </div>
              <button onClick={() => removeStock(s.symbol)} title="Remove" className="p-1 text-stone-300 opacity-0 group-hover:opacity-100 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      </div>
      {showImport && (
        <WatchlistImportModal userId={user.id} listId={null} listName="Watchlist" onClose={() => setShowImport(false)} onImported={() => { setShowImport(false); loadStocks(); }} />
      )}
    </div>
  );
}

function Toggle({ title, sub, on, onChange }: { title: string; sub: string; on: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 border-t first:border-t-0 border-stone-100">
      <div className="flex-1">
        <div className="text-[14.5px] font-bold text-gray-900">{title}</div>
        <div className="text-[12.5px] text-stone-500">{sub}</div>
      </div>
      <button role="switch" aria-checked={on} onClick={() => onChange(!on)}
        className={`relative w-10 h-6 rounded-full transition-colors ${on ? 'bg-emerald-500' : 'bg-stone-300'}`}>
        <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${on ? 'left-[18px]' : 'left-0.5'}`} />
      </button>
    </div>
  );
}

// The brief time is stored as local HH:MM + an IANA zone; without the zone the
// backend falls back to UTC and "08:00" fires at 1am Pacific.
function localTimeZone(): string {
  try { return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'; } catch { return 'UTC'; }
}
