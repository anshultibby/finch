'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Clock, Repeat, X, CalendarClock, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { jobsApi, type ScheduledJob, type JobListResponse } from '@/lib/api';
import { useNavigation } from '@/contexts/NavigationContext';
import EmptyState from '@/components/ui/EmptyState';

const RECURRENCE_LABEL: Record<string, string> = {
  hourly: 'Hourly', daily: 'Daily', weekly: 'Weekly', weekdays: 'Weekdays',
};

function relativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  const diff = t - Date.now();
  const abs = Math.abs(diff);
  const mins = Math.round(abs / 60000);
  const hrs = Math.round(abs / 3600000);
  const days = Math.round(abs / 86400000);
  let rel: string;
  if (mins < 1) rel = 'now';
  else if (mins < 60) rel = `${mins}m`;
  else if (hrs < 24) rel = `${hrs}h`;
  else rel = `${days}d`;
  return diff >= 0 ? `in ${rel}` : `${rel} ago`;
}

function exactTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

export default function JobsPanel() {
  const { navigateTo } = useNavigation();
  const [data, setData] = useState<JobListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      setData(await jobsApi.list());
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Could not load jobs');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const cancel = async (id: string) => {
    setCancelling(id);
    try { await jobsApi.cancel(id); await load(); }
    catch { /* ignore */ }
    finally { setCancelling(null); }
  };

  const active = (data?.jobs || []).filter(j => j.status === 'pending' || j.status === 'running');
  const past = (data?.jobs || []).filter(j => j.status === 'done' || j.status === 'failed');

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center gap-3">
        <RefreshCw className="w-6 h-6 text-emerald-500 animate-spin" />
        <p className="text-sm text-gray-400">Loading scheduled jobs…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white overflow-y-auto">
      <div className="max-w-3xl w-full mx-auto px-4 sm:px-6 py-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600">
              <CalendarClock className="w-5 h-5" strokeWidth={2} />
            </span>
            <div>
              <h1 className="text-lg font-bold text-gray-900 leading-tight">Scheduled</h1>
              {data && (
                <p className="text-xs text-gray-400">
                  {data.recurring_count}/{data.recurring_limit} recurring · {data.oneoff_count}/{data.oneoff_limit} one-off
                </p>
              )}
            </div>
          </div>
          <button onClick={load} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {error && (
          <div className="mb-3 text-sm text-red-500 bg-red-50 border border-red-100 rounded-xl px-3.5 py-2.5">{error}</div>
        )}

        {!error && active.length === 0 && past.length === 0 ? (
          <EmptyState
            icon={CalendarClock}
            title="Nothing scheduled"
            description="Ask Finch to remind you, send a digest, or watch a price — e.g. “every weekday at 9am, summarize my watchlist” or “alert me if NVDA drops below $200.”"
            action={{ label: 'Start a chat', onClick: () => navigateTo({ type: 'chat' }) }}
            className="py-20"
          />
        ) : (
          <>
            {active.length > 0 && (
              <div className="space-y-2 mb-6">
                {active.map(job => (
                  <JobRow key={job.id} job={job} cancelling={cancelling === job.id} onCancel={() => cancel(job.id)} />
                ))}
              </div>
            )}
            {past.length > 0 && (
              <>
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">History</div>
                <div className="space-y-2 opacity-70">
                  {past.slice(0, 10).map(job => (
                    <JobRow key={job.id} job={job} cancelling={false} onCancel={() => {}} readOnly />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function JobRow({ job, cancelling, onCancel, readOnly }: { job: ScheduledJob; cancelling: boolean; onCancel: () => void; readOnly?: boolean }) {
  const isRecurring = !!job.recurrence;
  return (
    <div className="group flex items-start gap-3 rounded-xl border border-gray-200 px-4 py-3 hover:border-gray-300 transition-colors">
      <span className={`flex-shrink-0 mt-0.5 flex items-center justify-center w-8 h-8 rounded-lg ${
        isRecurring ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-500'
      }`}>
        {isRecurring ? <Repeat className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900 truncate">{job.name}</span>
          {isRecurring && (
            <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600 bg-emerald-50 rounded px-1.5 py-0.5">
              {RECURRENCE_LABEL[job.recurrence as string] || job.recurrence}
            </span>
          )}
          <StatusBadge status={job.status} />
        </div>
        <div className="text-xs text-gray-500 truncate mt-0.5">{job.message}</div>
        <div className="flex items-center gap-2 text-[11px] text-gray-400 mt-1 font-numeric">
          <span title={exactTime(job.run_at)}>
            {job.status === 'pending' ? `Next ${relativeTime(job.run_at)}` : exactTime(job.run_at)}
          </span>
          {job.run_count > 0 && <span>· ran {job.run_count}×</span>}
        </div>
      </div>

      {!readOnly && (
        <button
          onClick={onCancel}
          disabled={cancelling}
          title="Cancel"
          className="flex-shrink-0 p-1.5 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: ScheduledJob['status'] }) {
  if (status === 'pending' || status === 'running') return null;
  const map = {
    done: { icon: CheckCircle2, cls: 'text-emerald-600', label: 'Done' },
    failed: { icon: AlertCircle, cls: 'text-red-500', label: 'Failed' },
    cancelled: { icon: X, cls: 'text-gray-400', label: 'Cancelled' },
  } as const;
  const m = (map as any)[status];
  if (!m) return null;
  const Icon = m.icon;
  return <span className={`inline-flex items-center gap-0.5 text-[10px] font-medium ${m.cls}`}><Icon className="w-3 h-3" />{m.label}</span>;
}
