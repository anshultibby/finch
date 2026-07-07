'use client';

/**
 * "While you were gone" — the agent accounting for itself, first thing.
 *
 * An append-only ledger of what Finch did since the user last looked:
 * checks run, moves flagged, trades proposed (with dollar stakes), plus
 * anything still waiting on them (approvals) and the next scheduled check —
 * so day 2 opens with proof of work, not generic market data.
 *
 * For users with no brokerage and no activity it renders a ghost of the
 * ledger they'd have — concrete preview beats promise.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigation } from '@/contexts/NavigationContext';
import { activityApi, type ActivityRecap, type AgentEvent } from '@/lib/api';
import ApprovalCard from './ApprovalCard';

const TYPE_META: Record<string, { dot: string; label: string }> = {
  job_run: { dot: 'bg-emerald-500', label: 'check' },
  alert: { dot: 'bg-amber-500', label: 'alert' },
  trade_proposed: { dot: 'bg-emerald-600 ring-2 ring-emerald-200', label: 'proposal' },
  trade_decided: { dot: 'bg-gray-400', label: 'decision' },
  brief: { dot: 'bg-sky-500', label: 'brief' },
  insight: { dot: 'bg-violet-500', label: 'insight' },
};

function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 90) return 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function timeUntil(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return 'any moment';
  const m = Math.round(ms / 60000);
  if (m < 60) return `in ${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `in ${h}h ${m % 60}m`;
  const d = new Date(iso);
  return d.toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' });
}

function EventRow({ event, onOpen }: { event: AgentEvent; onOpen: (e: AgentEvent) => void }) {
  const meta = TYPE_META[event.event_type] || { dot: 'bg-gray-300', label: '' };
  const clickable = Boolean(event.data?.chat_id || event.data?.symbol);
  return (
    <button
      onClick={() => clickable && onOpen(event)}
      disabled={!clickable}
      className={`w-full text-left flex gap-3 py-2 group ${clickable ? 'cursor-pointer' : 'cursor-default'}`}
    >
      <div className="flex flex-col items-center pt-1.5">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${meta.dot}`} />
        <span className="w-px flex-1 bg-gray-100 group-last:hidden" />
      </div>
      <div className="flex-1 min-w-0 pb-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className={`text-[13px] font-semibold text-gray-800 truncate ${clickable ? 'group-hover:text-emerald-700' : ''}`}>
            {event.title}
          </span>
          <span className="text-[11px] text-gray-400 tabular-nums flex-shrink-0">
            {event.value_cents ? (
              <span className="font-bold text-gray-600 mr-2">${(event.value_cents / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
            ) : null}
            {timeAgo(event.created_at)}
          </span>
        </div>
        {event.body && (
          <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">{event.body}</p>
        )}
      </div>
    </button>
  );
}

/** Ghost ledger for pre-connect users: what this surface looks like alive. */
function GhostLedger({ onConnect }: { onConnect: () => void }) {
  const sample = [
    { dot: 'bg-emerald-500', title: 'Scanned your holdings — 2 needed attention', value: '' },
    { dot: 'bg-amber-500', title: 'NVDA ▼ 4.2% — flagged before open', value: '$312' },
    { dot: 'bg-emerald-600 ring-2 ring-emerald-200', title: 'Proposed: BUY $500 of VOO (limit)', value: '$500' },
  ];
  return (
    <div className="flex-shrink-0 rounded-2xl border border-gray-200 bg-white shadow-sm p-4 mb-6 relative overflow-hidden">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 rounded-full bg-gray-300" />
        <span className="text-[11px] font-bold tracking-[0.14em] text-gray-400 uppercase">Your agent&apos;s ledger</span>
      </div>
      <div className="select-none pointer-events-none" aria-hidden>
        {sample.map((r, i) => (
          <div key={i} className="flex gap-3 py-2 opacity-60">
            <div className="flex flex-col items-center pt-1.5">
              <span className={`w-2 h-2 rounded-full ${r.dot}`} />
              {i < sample.length - 1 && <span className="w-px flex-1 bg-gray-100" />}
            </div>
            <div className="flex-1 flex items-baseline justify-between gap-3">
              <span className="text-[13px] font-semibold text-gray-700 blur-[3px]">{r.title}</span>
              {r.value && <span className="text-[11px] font-bold text-gray-500 blur-[3px] tabular-nums">{r.value}</span>}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-gray-500">
          This is what Finch keeps for you: every check, alert, and proposed trade — with the dollars at stake.
        </p>
        <button
          onClick={onConnect}
          className="flex-shrink-0 px-4 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 transition-colors"
        >
          Connect brokerage
        </button>
      </div>
    </div>
  );
}

export default function WhileYouWereGone({
  hasBrokerage,
  onConnect,
}: {
  hasBrokerage: boolean;
  onConnect: () => void;
}) {
  const { loadChat, openStock } = useNavigation();
  const [recap, setRecap] = useState<ActivityRecap | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [decided, setDecided] = useState<Record<string, string>>({});

  useEffect(() => {
    let alive = true;
    activityApi.getRecap()
      .then((r) => { if (alive) setRecap(r); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const openEvent = useCallback((e: AgentEvent) => {
    const chatId = e.data?.chat_id as string | undefined;
    const symbol = e.data?.symbol as string | undefined;
    if (chatId) loadChat(chatId);
    else if (symbol) openStock(symbol);
  }, [loadChat, openStock]);

  const dismiss = useCallback(() => {
    setDismissed(true);
    activityApi.markSeen().catch(() => {});
  }, []);

  const onTradeDecided = useCallback((id: string, status: string) => {
    setDecided((d) => ({ ...d, [id]: status }));
  }, []);

  const pending = useMemo(
    () => (recap?.pending_trades || []).filter((t) => !decided[t.id]),
    [recap, decided],
  );
  const decidedEntries = useMemo(
    () => (recap?.pending_trades || []).filter((t) => decided[t.id]),
    [recap, decided],
  );

  if (!recap) return null;

  // Nothing yet and no brokerage: show the ghost of the ledger they'd have.
  if (!recap.has_content) {
    if (!hasBrokerage) return <GhostLedger onConnect={onConnect} />;
    // Connected but quiet: one honest line — watching, and when it checks next.
    if (recap.next_run?.run_at) {
      return (
        <div className="flex-shrink-0 flex items-center gap-2 mb-5 px-1">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <p className="text-xs text-gray-500">
            Finch is watching your accounts — next check ({recap.next_run.name}) {timeUntil(recap.next_run.run_at)}.
          </p>
        </div>
      );
    }
    return null;
  }

  const events = recap.events || [];
  const shown = expanded ? events : events.slice(0, 5);
  const showLedger = !dismissed;

  if (!showLedger && pending.length === 0 && decidedEntries.length === 0) return null;

  return (
    <div className="flex-shrink-0 rounded-2xl border border-gray-200 bg-white shadow-sm mb-6 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-3.5 pb-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-[11px] font-bold tracking-[0.14em] text-gray-500 uppercase">
            While you were gone
          </span>
        </div>
        {showLedger && (
          <button
            onClick={dismiss}
            className="text-[11px] font-semibold text-gray-400 hover:text-emerald-700 transition-colors"
          >
            Caught up ✓
          </button>
        )}
      </div>

      <div className="px-4 pb-4">
        {recap.headline && showLedger && (
          <p className="text-[15px] font-semibold text-gray-900 leading-snug mb-3">{recap.headline}</p>
        )}

        {/* Approvals first — they're the ask */}
        {pending.length > 0 && (
          <div className="flex flex-col gap-3 mb-3">
            {pending.map((t) => (
              <ApprovalCard key={t.id} trade={t} onDecided={onTradeDecided} />
            ))}
          </div>
        )}
        {decidedEntries.map((t) => (
          <div
            key={t.id}
            className={`rounded-xl px-3 py-2 mb-2 text-xs font-semibold ${
              decided[t.id] === 'approved'
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-gray-50 text-gray-500'
            }`}
          >
            {decided[t.id] === 'approved' ? '✓ Order sent to Robinhood — ' : 'Rejected — no order placed. '}
            {t.summary}
          </div>
        ))}

        {/* The ledger */}
        {showLedger && shown.length > 0 && (
          <div className="mt-1">
            {shown.map((e) => (
              <EventRow key={e.id} event={e} onOpen={openEvent} />
            ))}
            {events.length > 5 && (
              <button
                onClick={() => setExpanded((v) => !v)}
                className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 mt-1"
              >
                {expanded ? 'Show less' : `Show all ${events.length} entries`}
              </button>
            )}
          </div>
        )}

        {/* Forward-looking trust line */}
        {showLedger && recap.next_run?.run_at && (
          <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-dashed border-gray-100">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span className="text-[11px] text-gray-400">
              Next check: <span className="font-semibold text-gray-600">{recap.next_run.name}</span> {timeUntil(recap.next_run.run_at)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
