'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ClipboardList, CircleDot, PauseCircle, CheckCircle2, XCircle,
  CalendarClock, ChevronRight, MessagesSquare, RefreshCw,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { tasksApi, type AgentTask, type TaskStatus } from '@/lib/api';
import { useNavigation } from '@/contexts/NavigationContext';
import PageHeader from '@/components/ui/PageHeader';
import EmptyState from '@/components/ui/EmptyState';

// Open work first — the board is read top-down, so the order is the priority.
const GROUPS: { status: TaskStatus; label: string; icon: React.ReactNode; tone: string }[] = [
  { status: 'open',    label: 'Open',    icon: <CircleDot className="w-3.5 h-3.5" />,   tone: 'text-emerald-600 bg-emerald-50' },
  { status: 'blocked', label: 'Blocked', icon: <PauseCircle className="w-3.5 h-3.5" />, tone: 'text-amber-600 bg-amber-50' },
  { status: 'done',    label: 'Done',    icon: <CheckCircle2 className="w-3.5 h-3.5" />, tone: 'text-stone-500 bg-stone-100' },
  { status: 'dropped', label: 'Dropped', icon: <XCircle className="w-3.5 h-3.5" />,      tone: 'text-stone-400 bg-stone-100' },
];

/** "Due today" / "3 days overdue" — the only date framing that matters here. */
function reviewLabel(iso: string | null): { text: string; overdue: boolean } | null {
  if (!iso) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(`${iso}T00:00:00`);
  const days = Math.round((due.getTime() - today.getTime()) / 86_400_000);
  if (days < 0) return { text: `${Math.abs(days)}d overdue`, overdue: true };
  if (days === 0) return { text: 'Due today', overdue: true };
  if (days === 1) return { text: 'Due tomorrow', overdue: false };
  if (days <= 14) return { text: `Due in ${days}d`, overdue: false };
  return { text: `Due ${due.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`, overdue: false };
}

function TaskRow({ task, expanded, onToggle }: {
  task: AgentTask; expanded: boolean; onToggle: () => void;
}) {
  const { loadChat, openStock } = useNavigation();
  const [body, setBody] = useState<string | null>(null);
  const [loadingBody, setLoadingBody] = useState(false);
  const review = reviewLabel(task.review_on);

  // The body is the whole point of opening a row, but it's dead weight in the
  // list — fetch it on first expand only.
  useEffect(() => {
    if (!expanded || body !== null || loadingBody) return;
    setLoadingBody(true);
    tasksApi.get(task.slug)
      .then(full => setBody(full.body || ''))
      .catch(() => setBody(''))
      .finally(() => setLoadingBody(false));
  }, [expanded, body, loadingBody, task.slug]);

  return (
    <div className="border border-stone-200 rounded-xl overflow-hidden bg-white">
      <button
        onClick={onToggle}
        aria-expanded={expanded}
        className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-stone-50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 mt-0.5 flex-shrink-0 text-stone-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
        <div className="min-w-0 flex-1">
          <div className="text-[14px] font-medium text-gray-900 leading-snug">{task.title}</div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
            {task.symbols.map(sym => (
              <button
                key={sym}
                onClick={e => { e.stopPropagation(); openStock(sym); }}
                className="text-[11px] font-semibold tracking-wide text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded hover:bg-emerald-100"
              >
                {sym}
              </button>
            ))}
            {review && (
              <span className={`inline-flex items-center gap-1 text-[11.5px] ${review.overdue ? 'text-amber-600 font-medium' : 'text-stone-500'}`}>
                <CalendarClock className="w-3 h-3" />
                {review.text}
              </span>
            )}
            {task.opened_on && (
              <span className="text-[11.5px] text-stone-400">opened {task.opened_on}</span>
            )}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-stone-100">
          {loadingBody && <div className="text-[13px] text-stone-400 py-2">Loading…</div>}
          {body !== null && !loadingBody && (
            <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-headings:font-semibold prose-p:text-gray-600 prose-li:text-gray-600">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {/* The frontmatter block is machine state, not something to read. */}
                {body.replace(/^---[\s\S]*?---\n/, '')}
              </ReactMarkdown>
            </div>
          )}
          {task.chat_id && (
            <button
              onClick={() => loadChat(task.chat_id!)}
              className="mt-3 inline-flex items-center gap-1.5 text-[12.5px] text-emerald-700 hover:text-emerald-800 font-medium"
            >
              <MessagesSquare className="w-3.5 h-3.5" />
              Open the conversation this came from
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function TasksPanel() {
  const [tasks, setTasks] = useState<AgentTask[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showClosed, setShowClosed] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setTasks((await tasksApi.list()).tasks);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Could not load tasks');
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const grouped = useMemo(() => {
    const by = new Map<TaskStatus, AgentTask[]>();
    for (const t of tasks || []) {
      if (!by.has(t.status)) by.set(t.status, []);
      by.get(t.status)!.push(t);
    }
    return by;
  }, [tasks]);

  const openCount = (grouped.get('open') || []).length;
  const dueCount = (grouped.get('open') || []).filter(t => {
    const r = reviewLabel(t.review_on);
    return r?.overdue;
  }).length;

  const visibleGroups = GROUPS.filter(g =>
    (showClosed || (g.status !== 'done' && g.status !== 'dropped')) &&
    (grouped.get(g.status) || []).length > 0
  );

  return (
    <div className="max-w-3xl mx-auto px-5 py-7">
      <PageHeader
        title="Tasks"
        subtitle={
          tasks === null ? 'Loading…'
            : openCount === 0 ? 'Nothing open right now'
            : `${openCount} open${dueCount ? ` · ${dueCount} due for review` : ''}`
        }
        actions={
          <>
            <button
              onClick={() => setShowClosed(s => !s)}
              className="text-[13px] text-stone-500 hover:text-stone-800 px-2 py-1.5"
            >
              {showClosed ? 'Hide closed' : 'Show closed'}
            </button>
            <button
              onClick={load}
              aria-label="Refresh tasks"
              className="p-1.5 text-stone-400 hover:text-stone-700 rounded-lg hover:bg-stone-100"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </>
        }
      />

      {error && (
        <div className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mb-4">
          {error}
        </div>
      )}

      {tasks !== null && tasks.length === 0 && !error && (
        <EmptyState
          icon={ClipboardList}
          title="No tasks yet"
          description="When Finch takes on work that spans more than one sitting — tracking a thesis, watching for a catalyst — it files it here so you can see what it's working on and why."
        />
      )}

      <div className="space-y-6">
        {visibleGroups.map(group => (
          <section key={group.status}>
            <div className="flex items-center gap-2 mb-2.5">
              <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide px-2 py-1 rounded-md ${group.tone}`}>
                {group.icon}
                {group.label}
              </span>
              <span className="text-[12px] text-stone-400">
                {(grouped.get(group.status) || []).length}
              </span>
            </div>
            <div className="space-y-2">
              {(grouped.get(group.status) || []).map(task => (
                <TaskRow
                  key={task.id}
                  task={task}
                  expanded={expanded === task.id}
                  onToggle={() => setExpanded(expanded === task.id ? null : task.id)}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
