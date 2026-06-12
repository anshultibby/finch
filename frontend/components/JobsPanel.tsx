'use client';

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Clock, Repeat, X, CalendarClock, RefreshCw, CheckCircle2, AlertCircle,
  Pause, Play, Plus, Sparkles, ChevronRight,
} from 'lucide-react';
import { jobsApi, type ScheduledJob, type JobListResponse, type Recurrence } from '@/lib/api';
import PageHeader from '@/components/ui/PageHeader';

const RECURRENCE_LABEL: Record<string, string> = { hourly: 'Hourly', daily: 'Daily', weekly: 'Weekly', weekdays: 'Weekdays' };

function relativeTime(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  const abs = Math.abs(diff);
  const m = Math.round(abs / 60000), h = Math.round(abs / 3600000), d = Math.round(abs / 86400000);
  const rel = m < 1 ? 'now' : m < 60 ? `${m}m` : h < 24 ? `${h}h` : `${d}d`;
  return diff >= 0 ? `in ${rel}` : `${rel} ago`;
}
function exactTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

export default function JobsPanel() {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try { setData(await jobsApi.list()); }
    catch (e: any) { setError(e?.response?.data?.detail || e?.message || 'Could not load jobs'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (fn: () => Promise<any>, key: string) => {
    setBusy(key);
    try { await fn(); await load(); } catch { /* ignore */ } finally { setBusy(null); }
  };

  const jobs = data?.jobs || [];
  const active = jobs.filter(j => ['pending', 'running', 'paused'].includes(j.status));
  const past = jobs.filter(j => ['done', 'failed', 'cancelled'].includes(j.status));
  const allPaused = active.length > 0 && active.every(j => j.status === 'paused');
  const isEmpty = active.length === 0 && past.length === 0;

  // Keep the open modal in sync with reloaded data (e.g. after pause/resume).
  const selected = useMemo(
    () => (selectedId ? jobs.find(j => j.id === selectedId) || null : null),
    [selectedId, jobs],
  );

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center gap-3">
        <RefreshCw className="w-6 h-6 text-emerald-500 animate-spin" />
        <p className="text-sm text-gray-400">Loading automations…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white overflow-y-auto">
      <div className="max-w-5xl w-full px-6 sm:px-10 py-8">
        {/* Header */}
        <PageHeader
          title="Automations"
          subtitle={active.length > 0
            ? `${active.length} ${active.length === 1 ? 'task runs' : 'tasks run'} on a schedule — results land in chat and email`
            : 'Tasks Finch runs for you on a schedule'}
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

        {error && <div className="mb-4 text-sm text-red-500 bg-red-50 border border-red-100 rounded-2xl px-4 py-3">{error}</div>}

        {!error && isEmpty ? (
          <div className="text-center py-20">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-50 mb-5">
              <CalendarClock className="w-7 h-7 text-emerald-500" strokeWidth={1.75} />
            </div>
            <h2 className="text-lg font-bold text-gray-900 mb-2">No automations yet</h2>
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
                  {past.map(job => (
                    <HistoryRow key={job.id} job={job} onOpen={() => setSelectedId(job.id)} />
                  ))}
                </div>
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
        />
      )}
    </div>
  );
}

// ── Active card ──────────────────────────────────────────────────────────────

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
    <button
      onClick={onOpen}
      className={`group relative flex flex-col text-left rounded-2xl border border-gray-200 bg-white p-4 transition-all cursor-pointer ${
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
        <span
          role="button"
          onClick={(e) => { e.stopPropagation(); (paused ? onResume : onPause)(); }}
          title={paused ? 'Resume' : 'Pause'}
          className={`p-1.5 rounded-lg text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-all flex-shrink-0 ${
            busy ? 'opacity-50 pointer-events-none' : 'opacity-0 group-hover:opacity-100'
          }`}
        >
          {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
        </span>
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
    </button>
  );
}

// ── History row ──────────────────────────────────────────────────────────────

function HistoryRow({ job, onOpen }: { job: ScheduledJob; onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="group flex items-center gap-3 w-full text-left px-1 py-2.5 hover:bg-gray-50 transition-colors cursor-pointer"
    >
      <StatusIcon status={job.status} />
      <div className="flex-1 min-w-0">
        <span className="text-[13px] font-medium text-gray-700 truncate block">{job.name}</span>
      </div>
      <span className="text-[12px] text-gray-400 font-numeric flex-shrink-0">{exactTime(job.run_at)}</span>
      <ChevronRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-gray-500 transition-colors flex-shrink-0" />
    </button>
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

function JobDetailModal({ job, busy, onClose, onPause, onResume, onCancel }: {
  job: ScheduledJob; busy: boolean;
  onClose: () => void; onPause: () => void; onResume: () => void; onCancel: () => void;
}) {
  const isRecurring = !!job.recurrence;
  const isSystem = !!job.system_key;
  const paused = job.status === 'paused';
  const activeStates = ['pending', 'running', 'paused'];
  const isActive = activeStates.includes(job.status);

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
              <button onClick={onCancel} disabled={busy}
                className="rounded-full px-4 py-2 text-sm font-medium text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50">
                Delete
              </button>
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
