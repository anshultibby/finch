'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { Clock, Sparkles } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import { marketApi, watchlistApi, jobsApi, thesesApi, type ScheduledJob, type Thesis } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';
import { EARNINGS_SLOT, earningsPreviewPrompt, fmtUsd, shortWhen, ymd, ui } from './shared';

// Two kinds of time on one page: when the market will tell you something
// (earnings for what you own and watch), and when Finch will (its scheduled
// checks and briefs). Mirrors frontend-mobile/app/calendar.tsx.

type Scope = 'yours' | 'all';

function dayHeading(dateStr: string) {
  const d = new Date(`${dateStr}T12:00:00`);
  const today = new Date(); today.setHours(12, 0, 0, 0);
  const diff = Math.round((d.getTime() - today.getTime()) / 86_400_000);
  const label = d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
  return diff === 0 ? `Today · ${label}` : diff === 1 ? `Tomorrow · ${label}` : label;
}

export default function CalendarPanel() {
  const { user } = useAuth();
  const { openStock, openChatWithPrompt, navigateTo } = useNavigation();
  const [scope, setScope] = useState<Scope>('yours');
  const [earnings, setEarnings] = useState<any[]>([]);
  const [mine, setMine] = useState<Set<string>>(new Set());
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Earnings render as soon as they land; "yours" fills in as the watchlist
  // and the (slower) brokerage sync resolve.
  useEffect(() => {
    let alive = true;
    const addMine = (syms: string[]) => alive && setMine(prev => new Set(Array.from(prev).concat(syms.map(x => x.toUpperCase()))));
    if (user) {
      watchlistApi.getWatchlist(user.id)
        .then(d => addMine((d?.symbols || d?.watchlist || []).map((i: any) => String(typeof i === 'string' ? i : i.symbol))))
        .catch(() => {});
      // Holdings come from the backend's cached brokerage sync — no live SnapTrade call.
      thesesApi.list().then(d => { if (alive) { setTheses(d.theses || []); addMine(d.owned || []); } }).catch(() => {});
      jobsApi.list().then(d => alive && setJobs(d.jobs || [])).catch(() => {});
    }
    const from = new Date();
    const to = new Date(); to.setDate(to.getDate() + 14);
    marketApi.getEarnings(ymd(from), ymd(to))
      .then(d => { if (alive) { setEarnings(Array.isArray(d) ? d : d?.earnings || []); setError(false); } })
      .catch(() => alive && setError(true))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [user]);

  const visible = useMemo(
    () => (scope === 'yours' ? earnings.filter(e => mine.has(String(e.symbol).toUpperCase())) : earnings.slice(0, 120)),
    [scope, earnings, mine],
  );
  const byDay = useMemo(() => {
    const m = new Map<string, any[]>();
    visible.forEach(e => { if (!m.has(e.date)) m.set(e.date, []); m.get(e.date)!.push(e); });
    return Array.from(m.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [visible]);

  const schedule = useMemo(() => {
    const horizon = Date.now() + 7 * 86_400_000;
    return jobs
      .filter(j => (j.status === 'pending' || j.status === 'running') && j.run_at && new Date(j.run_at).getTime() <= horizon)
      .sort((a, b) => a.run_at.localeCompare(b.run_at))
      .slice(0, 6);
  }, [jobs]);

  return (
    <div className="h-full overflow-y-auto bg-[#fafaf9]">
      <div className={ui.page}>
        <PageHeader title="Calendar" subtitle="Next two weeks" />

        {schedule.length > 0 && (
          <>
            <div className={`${ui.section} mt-0`}>Finch&apos;s schedule</div>
            <div className={`${ui.card} overflow-hidden mb-2`}>
              {schedule.map(j => (
                <button key={j.id} onClick={() => navigateTo({ type: 'watching' })} className={ui.row}>
                  <Clock className="w-4 h-4 text-emerald-600" />
                  <span className="flex-1 text-[14px] font-medium text-gray-900 truncate">{j.name}</span>
                  <span className="text-[12.5px] text-stone-500">{shortWhen(j.run_at)}</span>
                </button>
              ))}
            </div>
          </>
        )}

        <div className="flex items-center justify-between mt-6 mb-3">
          <div className="text-[11.5px] font-bold text-stone-500 uppercase tracking-wider">Earnings</div>
          <div className="flex bg-stone-100 rounded-lg p-0.5">
            {(['yours', 'all'] as Scope[]).map(s => (
              <button key={s} onClick={() => setScope(s)}
                className={`px-4 py-1 rounded-md text-[13px] font-medium ${scope === s ? 'bg-white shadow-sm text-gray-900' : 'text-stone-500'}`}>
                {s === 'yours' ? 'Yours' : 'All'}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className={`${ui.card} p-4 space-y-3 animate-pulse`}>{[0, 1, 2, 3].map(i => <div key={i} className="h-9 bg-stone-100 rounded" />)}</div>
        ) : error && earnings.length === 0 ? (
          <div className={`${ui.card} p-5 text-[14px] text-stone-600`}>Couldn&apos;t load the earnings calendar.</div>
        ) : byDay.length === 0 ? (
          <div className={`${ui.card} p-5`}>
            <p className="text-[14px] text-stone-500">
              {scope === 'yours'
                ? mine.size === 0
                  ? 'Add stocks to Watching or connect a brokerage and their earnings show up here — with a preview from Finch the day before.'
                  : 'None of your stocks report in the next two weeks.'
                : 'No earnings scheduled.'}
            </p>
            {scope === 'yours' && earnings.length > 0 && (
              <button onClick={() => setScope('all')} className="mt-2.5 text-[13px] font-bold text-emerald-700">See all {earnings.length} reports</button>
            )}
          </div>
        ) : (
          byDay.map(([day, rows]) => (
            <div key={day} className="mb-4">
              <div className="text-[13.5px] font-bold text-gray-900 mb-1.5">{dayHeading(day)}</div>
              <div className={`${ui.card} overflow-hidden`}>
                {rows.map((e: any, i: number) => {
                  const yours = mine.has(String(e.symbol).toUpperCase());
                  return (
                    <div key={`${e.symbol}-${i}`} className="flex items-center gap-3 px-4 py-2.5 border-t first:border-t-0 border-stone-100 hover:bg-stone-50">
                      <button onClick={() => openStock(e.symbol, 'earnings')} className="flex-1 min-w-0 text-left">
                        <div className="flex items-center gap-2">
                          <span className="text-[14.5px] font-bold text-gray-900">{e.symbol}</span>
                          {yours && scope === 'all' && <span className="px-1.5 rounded bg-emerald-50 text-emerald-700 text-[10.5px] font-bold">Yours</span>}
                        </div>
                        <div className="text-[12.5px] text-stone-500">
                          {EARNINGS_SLOT[String(e.time || '').toLowerCase()] || 'Time TBD'}
                          {e.epsEstimated != null ? ` · EPS est. ${fmtUsd(e.epsEstimated)}` : ''}
                        </div>
                      </button>
                      {yours && (
                        <button onClick={() => openChatWithPrompt(earningsPreviewPrompt(e.symbol, theses.find(t => t.symbol === String(e.symbol).toUpperCase())), `${e.symbol} earnings preview`)}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-[12px] font-bold hover:bg-emerald-100">
                          <Sparkles className="w-3 h-3" /> Preview
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
