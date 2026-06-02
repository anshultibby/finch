'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  Clock, Repeat, X, CalendarClock, RefreshCw, CheckCircle2, AlertCircle,
  Pause, Play, Plus, Sparkles,
} from 'lucide-react';
import { jobsApi, type ScheduledJob, type JobListResponse, type Recurrence } from '@/lib/api';
import { useNavigation } from '@/contexts/NavigationContext';
import PageHeader from '@/components/ui/PageHeader';

const RUNS_PER_WEEK: Record<string, number> = { hourly: 168, daily: 7, weekdays: 5, weekly: 1 };
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
const fmtCr = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
const projectedWeekly = (j: ScheduledJob) =>
  j.recurrence && j.last_run_credits ? j.last_run_credits * (RUNS_PER_WEEK[j.recurrence] || 0) : 0;

export default function JobsPanel() {
  const { navigateTo } = useNavigation();
  const [data, setData] = useState<JobListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

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
  const anyActive = active.some(j => j.status === 'pending' || j.status === 'running');
  const allPaused = active.length > 0 && active.every(j => j.status === 'paused');
  const totalWeekly = active.reduce((s, j) => s + projectedWeekly(j), 0);
  const isEmpty = active.length === 0 && past.length === 0;

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
      <div className="max-w-5xl px-6 sm:px-10 py-8">
        {/* Header */}
        <PageHeader
          title="Automations"
          subtitle={data ? (
            <>
              {data.recurring_count}/{data.recurring_limit} recurring · {data.oneoff_count}/{data.oneoff_limit} one-off
              {totalWeekly > 0 && <span> · <span className="font-medium text-gray-600">~{fmtCr(totalWeekly)}</span> credits/week</span>}
            </>
          ) : undefined}
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

        {!error && active.length === 0 && past.length === 0 ? (
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
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 mb-8">
                {active.map(job => (
                  <JobCard key={job.id} job={job} busy={busy === job.id}
                    onPause={() => act(() => jobsApi.pause(job.id), job.id)}
                    onResume={() => act(() => jobsApi.resume(job.id), job.id)}
                    onCancel={() => act(() => jobsApi.cancel(job.id), job.id)} />
                ))}
              </div>
            )}
            {past.length > 0 && (
              <>
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">History</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                  {past.map(job => <JobCard key={job.id} job={job} busy={false} readOnly />)}
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
    </div>
  );
}

function JobCard({ job, busy, onPause, onResume, onCancel, readOnly }: {
  job: ScheduledJob; busy: boolean;
  onPause?: () => void; onResume?: () => void; onCancel?: () => void; readOnly?: boolean;
}) {
  const isRecurring = !!job.recurrence;
  const paused = job.status === 'paused';
  const done = job.status === 'done' || job.status === 'failed' || job.status === 'cancelled';
  const weekly = projectedWeekly(job);

  const timeLabel = paused ? 'Paused'
    : job.status === 'pending' ? `Next ${relativeTime(job.run_at)}`
    : exactTime(job.run_at);
  const costLabel = job.last_run_credits > 0
    ? `~${fmtCr(job.last_run_credits)}/run${weekly ? ` · ~${fmtCr(weekly)}/wk` : ''}`
    : (done ? '' : 'cost after 1st run');

  return (
    <div className={`group relative flex flex-col rounded-2xl border border-gray-200 bg-white p-4 min-h-[156px] transition-all ${
      paused ? 'opacity-60' : 'hover:border-gray-300 hover:shadow-md'
    }`}>
      {/* top */}
      <div className="flex items-center justify-between mb-3">
        <span className={`flex items-center justify-center w-9 h-9 rounded-xl ${
          paused ? 'bg-gray-100 text-gray-400' : isRecurring ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-500'
        }`}>
          {paused ? <Pause className="w-4 h-4" /> : isRecurring ? <Repeat className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
        </span>
        <div className="flex items-center gap-1.5">
          {isRecurring && <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">{RECURRENCE_LABEL[job.recurrence as string]}</span>}
          <StatusBadge status={job.status} />
        </div>
      </div>

      {/* body */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-gray-900 truncate">{job.name}</div>
        <div className="text-[13px] text-gray-500 line-clamp-2 mt-1 leading-snug">{job.message}</div>
      </div>

      {/* footer */}
      <div className="flex items-end justify-between mt-3 gap-2">
        <div className="min-w-0">
          <div className="text-[13px] font-medium text-gray-700 font-numeric truncate">{timeLabel}</div>
          {costLabel && <div className="text-[11px] text-gray-400 font-numeric truncate">{costLabel}</div>}
        </div>
        {!readOnly && (
          <div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
            <button onClick={paused ? onResume : onPause} disabled={busy} title={paused ? 'Resume' : 'Pause'}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-colors disabled:opacity-50">
              {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </button>
            <button onClick={onCancel} disabled={busy} title="Cancel"
              className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: ScheduledJob['status'] }) {
  const map: any = {
    done: { icon: CheckCircle2, cls: 'text-emerald-600', label: 'Done' },
    failed: { icon: AlertCircle, cls: 'text-red-500', label: 'Failed' },
    cancelled: { icon: X, cls: 'text-gray-400', label: 'Cancelled' },
  };
  const m = map[status];
  if (!m) return null;
  const Icon = m.icon;
  return <span className={`inline-flex items-center gap-0.5 text-[10px] font-medium ${m.cls}`}><Icon className="w-3 h-3" />{m.label}</span>;
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
