'use client';

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Clock, Repeat, X, CalendarClock, RefreshCw, CheckCircle2, AlertCircle,
  Pause, Play, Plus, Sparkles, ChevronRight, MessagesSquare,
} from 'lucide-react';
import { jobsApi, type ScheduledJob, type JobListResponse, type Recurrence, type RoutineUsage } from '@/lib/api';
import { useNavigation } from '@/contexts/NavigationContext';
import PageHeader from '@/components/ui/PageHeader';
import { relativeTime, exactTime } from '@/lib/utils/time';

const RECURRENCE_LABEL: Record<string, string> = { hourly: 'Hourly', daily: 'Daily', weekly: 'Weekly', weekdays: 'Weekdays' };


export default function JobsPanel() {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [historyLimit, setHistoryLimit] = useState(25);
  const [usage, setUsage] = useState<RoutineUsage | null>(null);
  const { loadChat } = useNavigation();

  const load = useCallback(async () => {
    setError(null);
    try {
      // Usage is best-effort — a routine list that renders without the caps
      // banner is fine; a failed caps lookup must not blank the whole screen.
      const [list, u] = await Promise.all([jobsApi.list(), jobsApi.usage().catch(() => null)]);
      setData(list);
      setUsage(u);
    }
    catch (e: any) { setError(e?.response?.data?.detail || e?.message || 'Could not load routines'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  // "Next run in 5m" is computed at render, so without a tick it stays "in 5m"
  // indefinitely. Re-render every 30s so the countdowns stay truthful.
  const [, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 30_000);
    return () => clearInterval(t);
  }, []);

  const act = async (fn: () => Promise<any>, key: string) => {
    setBusy(key);
    try { await fn(); await load(); } catch { /* ignore */ } finally { setBusy(null); }
  };

  const jobs = data?.jobs || [];
  const active = jobs.filter(j => ['pending', 'running', 'paused'].includes(j.status));
  const past = jobs
    .filter(j => ['done', 'failed', 'cancelled'].includes(j.status))
    .sort((a, b) => new Date(b.last_run_at || b.run_at).getTime() - new Date(a.last_run_at || a.run_at).getTime());
  const allPaused = active.length > 0 && active.every(j => j.status === 'paused');
  const isEmpty = active.length === 0 && past.length === 0;

  // Keep the open modal in sync with reloaded data (e.g. after pause/resume).
  const selected = useMemo(
    () => (selectedId ? jobs.find(j => j.id === selectedId) || null : null),
    [selectedId, jobs],
  );

  // Render the shell immediately with skeleton cards rather than replacing the
  // whole page with a spinner — the header and New button are usable while the
  // list is still in flight, and the layout doesn't jump when it lands.
  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white overflow-y-auto">
        <div className="max-w-5xl w-full px-6 sm:px-10 py-8">
          <PageHeader title="Routines" subtitle="Standing requests Finch carries out for you on a schedule" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" aria-busy="true" aria-label="Loading routines">
            {[0, 1, 2, 3].map(i => (
              <div key={i} className="rounded-2xl border border-gray-200 bg-white p-4 animate-pulse">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-xl bg-gray-100" />
                  <div className="h-2.5 w-24 rounded bg-gray-100" />
                </div>
                <div className="h-3.5 w-2/5 rounded bg-gray-100 mb-2" />
                <div className="h-3 w-full rounded bg-gray-50 mb-1.5" />
                <div className="h-3 w-4/5 rounded bg-gray-50" />
                <div className="h-3 w-28 rounded bg-gray-100 mt-4" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white overflow-y-auto">
      <div className="max-w-5xl w-full px-6 sm:px-10 py-8">
        {/* Header */}
        <PageHeader
          title="Routines"
          subtitle={active.length > 0
            ? `${active.length} ${active.length === 1 ? 'routine runs' : 'routines run'} on a schedule — results land in chat and email`
            : 'Standing requests Finch carries out for you on a schedule'}
          actions={!isEmpty && (
            <>
              {active.length > 0 && (
                <button
                  onClick={() => act(() => (allPaused ? jobsApi.resumeAll() : jobsApi.pauseAll()), 'all')}
                  disabled={busy === 'all'}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-[13px] font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors disabled:opacity-50"
                >
                  {allPaused ? <><Play className="w-3.5 h-3.5" /> Resume all</> : <><Pause className="w-3.5 h-3.5" /> Pause all</>}
                </button>
              )}
              <button
                onClick={() => setShowCreate(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-gray-900 px-3.5 py-1.5 text-[13px] font-semibold text-white hover:bg-gray-800 transition-colors"
              >
                <Plus className="w-4 h-4" /> New
              </button>
            </>
          )}
        />

        {usage && <UsageBanner usage={usage} atRoutineCap={active.filter(j => j.recurrence).length >= usage.max_active_routines} />}

        {error && (
          <div className="mb-4 flex items-center justify-between gap-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-2xl px-4 py-3">
            <span>{error}</span>
            <button
              onClick={() => { setLoading(true); load(); }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-2.5 py-1 text-[13px] font-medium text-red-600 hover:bg-red-50 transition-colors flex-shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </button>
          </div>
        )}

        {!error && isEmpty ? (
          <div className="text-center py-20">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-50 mb-5">
              <CalendarClock className="w-7 h-7 text-emerald-500" strokeWidth={1.75} />
            </div>
            <h2 className="text-lg font-bold text-gray-900 mb-2">No routines yet</h2>
            <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
              Have Finch check a price, send a digest, or run research on a schedule — once or repeating. Ask in chat, or set one up by hand.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-6 inline-flex items-center gap-1.5 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 transition-all hover:shadow-md"
            >
              <Plus className="w-4 h-4" /> New automation
            </button>
          </div>
        ) : (
          <>
            {active.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-10">
                {active.map(job => (
                  <JobCard key={job.id} job={job} busy={busy === job.id}
                    onOpen={() => setSelectedId(job.id)}
                    onPause={() => act(() => jobsApi.pause(job.id), job.id)}
                    onResume={() => act(() => jobsApi.resume(job.id), job.id)} />
                ))}
              </div>
            )}
            {past.length > 0 && (
              <>
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">History</div>
                <div className="divide-y divide-gray-100 border-y border-gray-100">
                  {/* Capped: a self-scheduling agent produces a few rows per
                      trading day, so this list grows without bound. */}
                  {past.slice(0, historyLimit).map(job => (
                    <HistoryRow key={job.id} job={job} onOpen={() => setSelectedId(job.id)}
                      onOpenChat={job.run_chat_id ? () => loadChat(job.run_chat_id!) : undefined} />
                  ))}
                </div>
                {past.length > historyLimit && (
                  <button
                    onClick={() => setHistoryLimit(n => n + 25)}
                    className="mt-3 text-[13px] font-medium text-gray-500 hover:text-gray-900 transition-colors"
                  >
                    Show older ({past.length - historyLimit} more)
                  </button>
                )}
              </>
            )}
          </>
        )}
      </div>

      {showCreate && (
        <CreateJobModal
          onClose={() => setShowCreate(false)}
          onCreated={async () => { setShowCreate(false); await load(); }}
        />
      )}

      {selected && (
        <JobDetailModal
          job={selected}
          busy={busy === selected.id}
          onClose={() => setSelectedId(null)}
          onPause={() => act(() => jobsApi.pause(selected.id), selected.id)}
          onResume={() => act(() => jobsApi.resume(selected.id), selected.id)}
          onCancel={async () => { await act(() => jobsApi.cancel(selected.id), selected.id); setSelectedId(null); }}
          onOpenChat={selected.run_chat_id
            ? () => { setSelectedId(null); loadChat(selected.run_chat_id!); }
            : undefined}
        />
      )}
    </div>
  );
}

// ── Active card ──────────────────────────────────────────────────────────────

// Caps + usage, always visible so a limit is never an invisible wall. Shows the
// upgrade path at the friction points (at the routine cap, or out of daily runs).
function UsageBanner({ usage, atRoutineCap }: { usage: RoutineUsage; atRoutineCap: boolean }) {
  const isFree = usage.plan === 'free';
  const runsCap = usage.runs_per_day;                        // null = unlimited
  const runsUsedUp = runsCap != null && usage.runs_today >= runsCap;
  const showUpgrade = isFree && (atRoutineCap || runsUsedUp);

  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-2.5">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
        <span className={atRoutineCap ? 'text-gray-900' : 'text-gray-600'}>
          <span className="font-semibold text-gray-900">{usage.active_routines}</span>
          {' of '}{usage.max_active_routines} routines
        </span>
        <span className="text-gray-300">·</span>
        <span className={runsUsedUp ? 'text-gray-900' : 'text-gray-600'}>
          <span className="font-semibold text-gray-900">{usage.runs_today}</span>
          {' of '}{runsCap == null ? '∞' : runsCap} runs today
        </span>
        {isFree && (
          <>
            <span className="text-gray-300">·</span>
            <span className="text-gray-500">checks hourly</span>
          </>
        )}
      </div>
      {showUpgrade ? (
        <a
          href="/settings"
          className="inline-flex items-center gap-1 rounded-lg bg-gray-900 px-3 py-1.5 text-[13px] font-semibold text-white hover:bg-gray-800 transition-colors flex-shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5" /> Upgrade to Pro
        </a>
      ) : isFree ? (
        <a href="/settings" className="text-[13px] font-medium text-gray-500 hover:text-gray-900 transition-colors flex-shrink-0">
          Pro: unlimited &amp; every 5 min →
        </a>
      ) : null}
    </div>
  );
}

function JobCard({ job, busy, onOpen, onPause, onResume }: {
  job: ScheduledJob; busy: boolean;
  onOpen: () => void; onPause: () => void; onResume: () => void;
}) {
  const isRecurring = !!job.recurrence;
  const isSystem = !!job.system_key;
  const paused = job.status === 'paused';
  const running = job.status === 'running';

  const scheduleLabel = isRecurring
    ? RECURRENCE_LABEL[job.recurrence as string]
    : `Once · ${exactTime(job.run_at)}`;
  const timeLabel = paused ? 'Paused'
    : running ? 'Running now'
    : `Next run ${relativeTime(job.run_at)}`;

  return (
    // A div, not a button: this card contains its own pause control, and a
    // button inside a button is invalid HTML that breaks keyboard focus.
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(); }
      }}
      className={`group relative flex flex-col text-left rounded-2xl border border-gray-200 bg-white p-4 transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
        paused ? 'opacity-60 hover:opacity-90' : 'hover:border-gray-300 hover:shadow-md'
      }`}
    >
      {/* top row: icon · schedule · pause toggle */}
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`flex items-center justify-center w-8 h-8 rounded-xl flex-shrink-0 ${
            paused ? 'bg-gray-100 text-gray-400' : isRecurring ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-500'
          }`}>
            {paused ? <Pause className="w-4 h-4" /> : isRecurring ? <Repeat className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 truncate">{scheduleLabel}</span>
          {isSystem && (
            <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600 flex-shrink-0" title="Built-in Finch automation">
              <Sparkles className="w-2.5 h-2.5" /> Finch
            </span>
          )}
        </div>
        {/* Always visible, not hover-revealed: opacity-0 until :hover made this
            control unreachable on touch, where there is no hover state. */}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); (paused ? onResume : onPause)(); }}
          disabled={busy}
          title={paused ? 'Resume' : 'Pause'}
          aria-label={`${paused ? 'Resume' : 'Pause'} ${job.name}`}
          className="p-1.5 rounded-lg text-gray-300 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 transition-colors flex-shrink-0 disabled:opacity-50"
        >
          {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
        </button>
      </div>

      {/* body */}
      <div className="text-sm font-semibold text-gray-900 truncate">{job.name}</div>
      <div className="text-[13px] text-gray-500 line-clamp-2 mt-1 leading-snug">{job.message}</div>

      {/* footer */}
      <div className="flex items-center justify-between mt-3">
        <span className={`inline-flex items-center gap-1.5 text-[12px] font-medium font-numeric ${
          running ? 'text-emerald-600' : 'text-gray-500'
        }`}>
          {running && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />}
          {timeLabel}
        </span>
        <span className="inline-flex items-center gap-0.5 text-[12px] text-gray-300 group-hover:text-gray-500 transition-colors">
          Details <ChevronRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </div>
  );
}

// ── History row ──────────────────────────────────────────────────────────────

function HistoryRow({ job, onOpen, onOpenChat }: {
  job: ScheduledJob; onOpen: () => void; onOpenChat?: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(); }
      }}
      className="group flex items-center gap-3 w-full text-left px-1 py-2.5 hover:bg-gray-50 transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 rounded-lg"
    >
      <StatusIcon status={job.status} />
      <div className="flex-1 min-w-0">
        <span className="text-[13px] font-medium text-gray-700 truncate block">{job.name}</span>
      </div>
      {onOpenChat && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onOpenChat(); }}
          title="View execution in chat"
          aria-label={`View execution of ${job.name}`}
          className="p-1.5 rounded-lg text-gray-300 hover:text-emerald-600 hover:bg-emerald-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 transition-colors flex-shrink-0"
        >
          <MessagesSquare className="w-4 h-4" />
        </button>
      )}
      <span className="text-[12px] text-gray-400 font-numeric flex-shrink-0">{exactTime(job.run_at)}</span>
      <ChevronRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-gray-500 transition-colors flex-shrink-0" />
    </div>
  );
}

function StatusIcon({ status }: { status: ScheduledJob['status'] }) {
  if (status === 'done') return <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />;
  if (status === 'failed') return <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />;
  return <X className="w-4 h-4 text-gray-300 flex-shrink-0" />;
}

const STATUS_LABEL: Record<ScheduledJob['status'], string> = {
  pending: 'Scheduled', running: 'Running', paused: 'Paused',
  done: 'Done', failed: 'Failed', cancelled: 'Cancelled',
};

// ── Detail modal ─────────────────────────────────────────────────────────────

function JobDetailModal({ job, busy, onClose, onPause, onResume, onCancel, onOpenChat }: {
  job: ScheduledJob; busy: boolean;
  onClose: () => void; onPause: () => void; onResume: () => void; onCancel: () => void;
  onOpenChat?: () => void;
}) {
  const isRecurring = !!job.recurrence;
  const isSystem = !!job.system_key;
  const paused = job.status === 'paused';
  const activeStates = ['pending', 'running', 'paused'];
  const isActive = activeStates.includes(job.status);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const meta: { label: string; value: string }[] = [
    {
      label: 'Schedule',
      value: isRecurring ? RECURRENCE_LABEL[job.recurrence as string] : 'Once',
    },
    {
      label: isActive ? 'Next run' : 'Last scheduled',
      value: paused ? '—' : `${exactTime(job.run_at)} (${relativeTime(job.run_at)})`,
    },
    ...(job.last_run_at ? [{ label: 'Last ran', value: relativeTime(job.last_run_at) }] : []),
    ...(job.run_count > 0 ? [{ label: 'Runs so far', value: String(job.run_count) }] : []),
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/30 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col max-h-[85vh]" onClick={e => e.stopPropagation()}>
        {/* header */}
        <div className="px-6 pt-6 pb-4 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <span className={`flex items-center justify-center w-10 h-10 rounded-xl flex-shrink-0 ${
              paused ? 'bg-gray-100 text-gray-400' : isRecurring ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-500'
            }`}>
              {paused ? <Pause className="w-5 h-5" /> : isRecurring ? <Repeat className="w-5 h-5" /> : <Clock className="w-5 h-5" />}
            </span>
            <div className="min-w-0">
              <h2 className="text-base font-bold text-gray-900 leading-snug">{job.name}</h2>
              <div className="flex items-center gap-1.5 mt-1">
                <span className={`text-[11px] font-semibold uppercase tracking-wide ${
                  job.status === 'failed' ? 'text-red-500' : job.status === 'running' ? 'text-emerald-600' : 'text-gray-400'
                }`}>{STATUS_LABEL[job.status]}</span>
                {isSystem && (
                  <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600">
                    <Sparkles className="w-2.5 h-2.5" /> Finch
                  </span>
                )}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors flex-shrink-0">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* body */}
        <div className="px-6 pb-2 overflow-y-auto">
          <div className="rounded-2xl bg-gray-50 border border-gray-100 px-4 py-3.5">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1.5">What it does</div>
            <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{job.message}</p>
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 mt-4">
            {meta.map(m => (
              <div key={m.label}>
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{m.label}</dt>
                <dd className="text-[13px] font-medium text-gray-800 font-numeric mt-0.5">{m.value}</dd>
              </div>
            ))}
          </dl>

          {onOpenChat && (
            <button
              onClick={onOpenChat}
              className="group flex items-center gap-3 w-full mt-4 rounded-2xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-emerald-300 hover:bg-emerald-50/40 transition-colors"
            >
              <span className="flex items-center justify-center w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex-shrink-0">
                <MessagesSquare className="w-4 h-4" />
              </span>
              <span className="flex-1 min-w-0">
                <span className="block text-[13px] font-semibold text-gray-900">View execution</span>
                <span className="block text-[12px] text-gray-500 truncate">
                  {job.run_count > 1
                    ? `Every step from all ${job.run_count} runs, in the run chat`
                    : 'Every step of the run — tool calls, output, result'}
                </span>
              </span>
              <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-emerald-500 transition-colors flex-shrink-0" />
            </button>
          )}

          {job.last_error && (
            <div className="mt-4 rounded-2xl bg-red-50 border border-red-100 px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-red-400 mb-1">Last error</div>
              <p className="text-[13px] text-red-600 leading-relaxed break-words">{job.last_error}</p>
            </div>
          )}
        </div>

        {/* footer */}
        <div className="px-6 py-4 flex items-center justify-between gap-2 border-t border-gray-100 mt-4">
          <div>
            {isActive && !isSystem && (
              // Two-step: deleting a recurring automation is not recoverable
              // from this screen, and it sat one stray click away.
              confirmDelete ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="text-[13px] text-gray-500">Delete?</span>
                  <button onClick={onCancel} disabled={busy}
                    className="rounded-full bg-red-500 px-3 py-1.5 text-[13px] font-semibold text-white hover:bg-red-600 transition-colors disabled:opacity-50">
                    Yes, delete
                  </button>
                  <button onClick={() => setConfirmDelete(false)} disabled={busy}
                    className="rounded-full px-3 py-1.5 text-[13px] font-medium text-gray-600 hover:bg-gray-100 transition-colors">
                    Keep
                  </button>
                </span>
              ) : (
                <button onClick={() => setConfirmDelete(true)} disabled={busy}
                  className="rounded-full px-4 py-2 text-sm font-medium text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50">
                  Delete
                </button>
              )
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="rounded-full px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors">Close</button>
            {isActive && (
              <button onClick={paused ? onResume : onPause} disabled={busy}
                className="inline-flex items-center gap-1.5 rounded-full bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800 transition-colors disabled:opacity-50">
                {paused ? <><Play className="w-3.5 h-3.5" /> Resume</> : <><Pause className="w-3.5 h-3.5" /> Pause</>}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Create modal ─────────────────────────────────────────────────────────────

const REPEAT_OPTIONS: { value: Recurrence; label: string }[] = [
  { value: null, label: 'Once' },
  { value: 'hourly', label: 'Hourly' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekdays', label: 'Weekdays' },
  { value: 'weekly', label: 'Weekly' },
];

// Starters — a blank textarea doesn't tell you what an automation can be. Each
// fills the whole form, so one click gets you to a working automation you can
// then edit. `hour` is local 24h; `null` recurrence means one-off.
const STARTERS: {
  label: string; emoji: string; message: string;
  recurrence: Recurrence; hour: number; name: string;
}[] = [
  {
    emoji: '☀️', label: 'Morning watchlist check', recurrence: 'weekdays', hour: 8,
    name: 'Morning watchlist check',
    message: "Check my watchlist and holdings for overnight moves, news since yesterday, and anything reporting earnings in the next few days. Give me a tight summary — only what actually matters, and say so if it's a quiet morning.",
  },
  {
    emoji: '🔔', label: 'Price alert', recurrence: 'hourly', hour: 9,
    name: 'NVDA price alert',
    message: "Check NVDA's current price. If it drops below $200, notify me with a one-line explanation of why it moved. If it hasn't, do nothing and reply with a single short line — don't notify me.",
  },
  {
    emoji: '📊', label: 'Weekly portfolio review', recurrence: 'weekly', hour: 17,
    name: 'Weekly portfolio review',
    message: 'Review my portfolio for the week: what moved and why, how my positions performed against SPY, any position that has grown into a concentration risk, and one thing worth considering next week.',
  },
  {
    emoji: '📰', label: 'Earnings watch', recurrence: 'daily', hour: 7,
    name: 'Earnings watch',
    message: 'Check which of my holdings or watchlist names report earnings today or tomorrow. For each, give me the consensus estimate, what the stock has done into the print, and what to watch for. Skip silently if none are reporting.',
  },
];

function whenAtHour(hour: number): string {
  // Next occurrence of `hour` local time, as a datetime-local string.
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  if (d.getTime() <= Date.now()) d.setDate(d.getDate() + 1);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function defaultWhen(): string {
  // local datetime-local string for "next hour, on the hour"
  const d = new Date(Date.now() + 60 * 60 * 1000);
  d.setMinutes(0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function CreateJobModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [message, setMessage] = useState('');
  const [when, setWhen] = useState(defaultWhen());
  const [recurrence, setRecurrence] = useState<Recurrence>(null);
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    if (!message.trim() || !when) return;
    setSaving(true); setErr(null);
    try {
      await jobsApi.create({
        message: message.trim(),
        run_at: new Date(when).toISOString(),
        recurrence: recurrence || undefined,
        name: name.trim() || undefined,
      });
      onCreated();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e?.message || 'Could not schedule');
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/30 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-gray-200 overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="px-6 pt-6 pb-2 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">New automation</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 pb-6 space-y-4">
          {/* starters */}
          <div>
            <label className="block text-[13px] font-semibold text-gray-700 mb-1.5">Start from an example</label>
            <div className="flex flex-wrap gap-1.5">
              {STARTERS.map(s => (
                <button
                  key={s.label}
                  onClick={() => {
                    setMessage(s.message);
                    setRecurrence(s.recurrence);
                    setWhen(whenAtHour(s.hour));
                    setName(s.name);
                  }}
                  className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-[13px] text-gray-600 hover:border-emerald-300 hover:text-gray-900 transition-colors"
                >
                  <span className="mr-1">{s.emoji}</span>{s.label}
                </button>
              ))}
            </div>
          </div>

          {/* message */}
          <div>
            <label className="block text-[13px] font-semibold text-gray-700 mb-1.5">What should Finch do?</label>
            <textarea
              value={message}
              onChange={e => setMessage(e.target.value)}
              rows={3}
              autoFocus
              placeholder="e.g. Check if NVDA is below $200 and notify me if it is."
              className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 resize-none"
            />
            <p className="text-[11px] text-gray-400 mt-1.5 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-emerald-500" /> Write it like a request — it runs fresh, with full tools.
            </p>
          </div>

          {/* repeat */}
          <div>
            <label className="block text-[13px] font-semibold text-gray-700 mb-1.5">Repeat</label>
            <div className="flex flex-wrap gap-1.5">
              {REPEAT_OPTIONS.map(opt => (
                <button key={opt.label} onClick={() => setRecurrence(opt.value)}
                  className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
                    recurrence === opt.value ? 'bg-gray-900 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* when + name */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[13px] font-semibold text-gray-700 mb-1.5">{recurrence ? 'First run' : 'When'}</label>
              <input type="datetime-local" value={when} onChange={e => setWhen(e.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:border-emerald-400" />
            </div>
            <div>
              <label className="block text-[13px] font-semibold text-gray-700 mb-1.5">Name <span className="text-gray-400 font-normal">(optional)</span></label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="Auto from message"
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-emerald-400" />
            </div>
          </div>

          {err && <div className="text-sm text-red-500">{err}</div>}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button onClick={onClose} className="rounded-full px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors">Cancel</button>
            <button onClick={submit} disabled={saving || !message.trim() || !when}
              className="rounded-full bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors disabled:opacity-50">
              {saving ? 'Scheduling…' : 'Schedule'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
