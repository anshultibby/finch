'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { storeApi } from '@/lib/api';
import type { StoreFile, Dream } from '@/lib/types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fileIcon(filename: string): string {
  if (filename.endsWith('.py')) return '{}';
  if (filename.endsWith('.md')) return '#';
  return '~';
}

function fileLabel(filename: string): string {
  const name = filename.replace('store/', '');
  const base = name.split('/').pop() || name;
  return base.replace('.md', '').replace('.py', '');
}

function groupFiles(files: StoreFile[]): { root: StoreFile[]; journal: StoreFile[]; modules: StoreFile[]; other: StoreFile[] } {
  const root: StoreFile[] = [];
  const journal: StoreFile[] = [];
  const modules: StoreFile[] = [];
  const other: StoreFile[] = [];

  for (const f of files) {
    const name = f.filename;
    if (name.includes('/journal/')) journal.push(f);
    else if (name.includes('/modules/')) modules.push(f);
    else if (name.match(/^store\/[^/]+$/)) root.push(f);
    else other.push(f);
  }

  root.sort((a, b) => {
    const order = ['preferences', 'user_model', 'self_model', 'next_session', 'anticipations', 'insights', 'learnings', 'strategy'];
    const ai = order.findIndex(o => a.filename.includes(o));
    const bi = order.findIndex(o => b.filename.includes(o));
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
  journal.sort((a, b) => b.filename.localeCompare(a.filename));
  modules.sort((a, b) => a.filename.localeCompare(b.filename));

  return { root, journal, modules, other };
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function processWikiLinks(text: string): string {
  return text.replace(/\[\[([^\]]+)\]\]/g, (_, page) => {
    const slug = page.trim();
    return `[${slug}](wiki://${slug})`;
  });
}

function WikiMarkdown({ content, onNavigate }: { content: string; onNavigate?: (filename: string) => void }) {
  const processed = processWikiLinks(content);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ href, children }) => {
          if (href?.startsWith('wiki://') && onNavigate) {
            const slug = href.replace('wiki://', '');
            const hasExt = /\.\w+$/.test(slug);
            const filename = hasExt ? `store/${slug}` : `store/${slug}.md`;
            return (
              <button
                onClick={() => onNavigate(filename)}
                className="text-blue-600 hover:text-blue-800 underline decoration-blue-300 hover:decoration-blue-500 transition-colors cursor-pointer"
              >
                {children}
              </button>
            );
          }
          return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
        },
      }}
    >
      {processed}
    </ReactMarkdown>
  );
}

// ---------------------------------------------------------------------------
// File Tree sidebar
// ---------------------------------------------------------------------------

function FileTree({
  files,
  selected,
  onSelect,
}: {
  files: StoreFile[];
  selected: string | null;
  onSelect: (filename: string) => void;
}) {
  const { root, journal, modules, other } = groupFiles(files);
  const [journalOpen, setJournalOpen] = useState(false);
  const [modulesOpen, setModulesOpen] = useState(false);

  const FileItem = ({ file }: { file: StoreFile }) => (
    <button
      onClick={() => onSelect(file.filename)}
      className={`w-full text-left px-3 py-1.5 text-sm flex items-center gap-2 rounded-md transition-colors ${
        selected === file.filename
          ? 'bg-gray-100 text-gray-900 font-medium'
          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
      }`}
    >
      <span className="text-gray-400 font-mono text-xs w-4 text-center shrink-0">{fileIcon(file.filename)}</span>
      <span className="truncate">{fileLabel(file.filename)}</span>
      {file.updated_at && (
        <span className="ml-auto text-[10px] text-gray-400 shrink-0">{timeAgo(file.updated_at)}</span>
      )}
    </button>
  );

  const FolderGroup = ({
    label,
    open,
    onToggle,
    items,
    icon,
  }: {
    label: string;
    open: boolean;
    onToggle: () => void;
    items: StoreFile[];
    icon: string;
  }) => (
    <div>
      <button
        onClick={onToggle}
        className="w-full text-left px-3 py-1.5 text-sm flex items-center gap-2 text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span className="text-[10px] w-4 text-center">{open ? '▼' : '▶'}</span>
        <span className="text-gray-400 font-mono text-xs">{icon}</span>
        <span>{label}</span>
        <span className="ml-auto text-[10px] text-gray-400">{items.length}</span>
      </button>
      {open && (
        <div className="ml-4">
          {items.map(f => <FileItem key={f.filename} file={f} />)}
        </div>
      )}
    </div>
  );

  return (
    <div className="flex flex-col gap-0.5">
      <div className="px-3 py-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
        Memory Store
      </div>
      {root.map(f => <FileItem key={f.filename} file={f} />)}
      {journal.length > 0 && (
        <FolderGroup label="journal" open={journalOpen} onToggle={() => setJournalOpen(o => !o)} items={journal} icon="/" />
      )}
      {modules.length > 0 && (
        <FolderGroup label="modules" open={modulesOpen} onToggle={() => setModulesOpen(o => !o)} items={modules} icon="/" />
      )}
      {other.map(f => <FileItem key={f.filename} file={f} />)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dream Log
// ---------------------------------------------------------------------------

function formatDuration(start?: string | null, end?: string | null): string {
  if (!start || !end) return '';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = secs % 60;
  return `${mins}m ${remSecs}s`;
}

function statusBadge(status: string) {
  const styles: Record<string, string> = {
    completed: 'bg-emerald-100 text-emerald-700',
    running: 'bg-blue-100 text-blue-700',
    failed: 'bg-red-100 text-red-700',
    pending: 'bg-gray-100 text-gray-600',
  };
  return (
    <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${styles[status] || styles.pending}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

interface TranscriptEntry {
  role: 'user' | 'assistant' | 'tool';
  content?: string;
  tool_name?: string;
  input?: Record<string, string>;
  output?: string;
}

function TranscriptViewer({ entries }: { entries: TranscriptEntry[] }) {
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());

  const toggleTool = (idx: number) => {
    setExpandedTools(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  };

  return (
    <div className="space-y-3 py-2">
      {entries.map((entry, idx) => {
        if (entry.role === 'user') {
          return (
            <div key={idx} className="flex gap-2.5">
              <div className="w-5 h-5 rounded bg-gray-100 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-[10px] text-gray-500 font-medium">U</span>
              </div>
              <div className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap flex-1">{entry.content}</div>
            </div>
          );
        }

        if (entry.role === 'tool') {
          const isOpen = expandedTools.has(idx);
          return (
            <div key={idx} className="ml-7">
              <button
                onClick={() => toggleTool(idx)}
                className="flex items-center gap-2 py-1 px-2 -mx-2 rounded hover:bg-gray-50 transition-colors group w-full text-left"
              >
                <svg className={`w-3 h-3 text-gray-300 group-hover:text-gray-500 transition-transform ${isOpen ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <span className="text-[11px] font-mono font-medium text-amber-700">{entry.tool_name}</span>
                {!isOpen && entry.output && (
                  <span className="text-[10px] text-gray-400 truncate ml-1 flex-1">{entry.output.slice(0, 60)}...</span>
                )}
              </button>
              {isOpen && (
                <div className="mt-1.5 ml-5 border-l-2 border-amber-100 pl-3 space-y-2 pb-1">
                  {entry.input && Object.keys(entry.input).length > 0 && (
                    <div>
                      <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Input</span>
                      <pre className="text-[11px] text-gray-600 bg-gray-50 rounded p-2 mt-1 whitespace-pre-wrap max-h-40 overflow-auto">
                        {Object.entries(entry.input).map(([k, v]) => `${k}: ${v}`).join('\n')}
                      </pre>
                    </div>
                  )}
                  {entry.output && (
                    <div>
                      <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Output</span>
                      <pre className="text-[11px] text-gray-600 bg-gray-50 rounded p-2 mt-1 whitespace-pre-wrap max-h-40 overflow-auto">{entry.output}</pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        }

        return (
          <div key={idx} className="flex gap-2.5">
            <div className="w-5 h-5 rounded bg-gray-800 flex items-center justify-center shrink-0 mt-0.5">
              <span className="text-[10px] text-white font-medium">A</span>
            </div>
            <div className="text-xs text-gray-700 leading-relaxed flex-1">
              <div className="prose prose-xs prose-gray max-w-none [&_p]:text-[13px] [&_li]:text-[13px]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.content || ''}</ReactMarkdown>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function DreamLog({
  dreams, selectedDreamId, onSelectDream,
}: {
  dreams: Dream[];
  onTrigger: () => void;
  triggering: boolean;
  selectedDreamId: string | null;
  onSelectDream: (dream: Dream) => void;
}) {
  if (dreams.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <div className="text-3xl mb-3">~</div>
        <p className="text-sm">No dreams yet</p>
        <p className="text-xs mt-1">Dreams run automatically after conversations</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5 py-1">
      {dreams.map(dream => {
        const isSelected = selectedDreamId === dream.id;
        const duration = formatDuration(dream.started_at, dream.completed_at);
        const dateStr = new Date(dream.created_at).toLocaleDateString('en-US', {
          month: 'short', day: 'numeric',
        });

        return (
          <button
            key={dream.id}
            onClick={() => onSelectDream(dream)}
            className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
              isSelected ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className={`text-sm font-mono truncate ${isSelected ? 'font-medium' : ''}`}>
                drm_{dream.id.slice(0, 8)}
              </span>
              <div className="flex items-center gap-1.5 shrink-0">
                {dream.status === 'running' && (
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                )}
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-gray-400 mt-0.5">
              <span>{dateStr}</span>
              {duration && <><span>·</span><span>{duration}</span></>}
              {dream.trigger === 'manual' && <><span>·</span><span>manual</span></>}
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Content viewer
// ---------------------------------------------------------------------------

function ContentViewer({
  file,
  content,
  loading,
  onEdit,
  onNavigate,
}: {
  file: StoreFile | null;
  content: string | null;
  loading: boolean;
  onEdit: (content: string) => Promise<void>;
  onNavigate: (filename: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setEditing(false);
  }, [file?.filename]);

  if (!file) {
    return (
      <div className="flex items-center justify-center h-full text-gray-300">
        <p className="text-sm">Select a file to view</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
      </div>
    );
  }

  const isPython = file.filename.endsWith('.py');
  const isMarkdown = file.filename.endsWith('.md');

  const handleSave = async () => {
    setSaving(true);
    try {
      await onEdit(editContent);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-mono text-xs text-gray-400">{fileIcon(file.filename)}</span>
          <span className="text-sm font-medium text-gray-800 truncate">{file.filename.replace('store/', '')}</span>
          {file.updated_at && (
            <span className="text-[10px] text-gray-400 shrink-0">updated {timeAgo(file.updated_at)}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!editing ? (
            <button
              onClick={() => { setEditContent(content || ''); setEditing(true); }}
              className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100 transition-colors"
            >
              Edit
            </button>
          ) : (
            <>
              <button
                onClick={() => setEditing(false)}
                className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-xs text-white bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {editing ? (
          <textarea
            value={editContent}
            onChange={e => setEditContent(e.target.value)}
            className="w-full h-full p-5 text-sm font-mono text-gray-800 bg-white resize-none focus:outline-none"
            spellCheck={false}
          />
        ) : isPython ? (
          <pre className="p-5 text-sm font-mono text-gray-800 whitespace-pre-wrap">{content || ''}</pre>
        ) : isMarkdown ? (
          <div className="p-5 prose prose-sm prose-gray max-w-none">
            <WikiMarkdown content={content || ''} onNavigate={onNavigate} />
          </div>
        ) : (
          <pre className="p-5 text-sm font-mono text-gray-800 whitespace-pre-wrap">{content || ''}</pre>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dream Progress (live SSE stream for running dreams)
// ---------------------------------------------------------------------------

const PHASE_LABELS: Record<string, string> = {
  starting: 'Starting up',
  read: 'Reading store & chats',
  organize: 'Extracting & organizing',
  'look-ahead': 'Looking ahead',
};

const PHASE_ORDER = ['read', 'organize', 'look-ahead'];

function DreamProgressView({ dream, onDreamComplete }: { dream: Dream; onDreamComplete: () => void }) {
  const [phase, setPhase] = useState<string>('starting');
  const [thinking, setThinking] = useState<string>('');
  const [toolCount, setToolCount] = useState(0);
  const [lastTool, setLastTool] = useState<string | null>(null);
  const [fileWrites, setFileWrites] = useState<{ path: string; is_new?: boolean }[]>([]);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState<{ summary: string; self_score: number | null; files_changed: number } | null>(null);
  const onCompleteRef = useRef(onDreamComplete);
  onCompleteRef.current = onDreamComplete;

  useEffect(() => {
    const stream = storeApi.streamDreamProgress(dream.id, {
      onPhase: (p) => setPhase(p),
      onThinking: (content) => setThinking(content),
      onTool: (name, count) => { setToolCount(count); setLastTool(name); },
      onFileWrite: (data) => setFileWrites(prev => [...prev, { path: data.path, is_new: data.is_new }]),
      onCompleted: (data) => {
        setCompleted(true);
        setResult({ summary: data.summary, self_score: data.self_score, files_changed: data.files_changed });
        setTimeout(() => onCompleteRef.current(), 1500);
      },
      onFailed: () => {
        setCompleted(true);
        setTimeout(() => onCompleteRef.current(), 1500);
      },
    });
    return () => stream.close();
  }, [dream.id]);

  const phaseIdx = PHASE_ORDER.indexOf(phase);
  const progress = phase === 'starting' ? 0 : phaseIdx >= 0 ? Math.round(((phaseIdx + 0.5) / PHASE_ORDER.length) * 100) : 0;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-800 font-mono">drm_{dream.id.slice(0, 8)}</span>
          {!completed ? (
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              Dreaming
            </span>
          ) : result ? (
            <span className="text-[11px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
              Complete
            </span>
          ) : (
            <span className="text-[11px] font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
              Failed
            </span>
          )}
        </div>
        <div className="text-[11px] text-gray-400">{toolCount} tool call{toolCount !== 1 ? 's' : ''}</div>
      </div>

      <div className="flex-1 overflow-auto px-5 py-4">
        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">{PHASE_LABELS[phase] || phase}</span>
            <span className="text-xs text-gray-400">{completed ? '100' : progress}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${completed ? 'bg-emerald-500' : 'bg-blue-500'}`}
              style={{ width: `${completed ? 100 : progress}%` }}
            />
          </div>
        </div>

        {/* Phase checklist */}
        <div className="mb-6 space-y-1.5">
          {PHASE_ORDER.map((p, i) => {
            const isDone = phaseIdx > i || completed;
            const isCurrent = p === phase && !completed;
            return (
              <div key={p} className="flex items-center gap-2 text-xs">
                {isDone ? (
                  <svg className="w-3.5 h-3.5 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="m4.5 12.75 6 6 9-13.5" />
                  </svg>
                ) : isCurrent ? (
                  <span className="w-3.5 h-3.5 flex items-center justify-center shrink-0">
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                  </span>
                ) : (
                  <span className="w-3.5 h-3.5 flex items-center justify-center shrink-0">
                    <span className="w-2 h-2 rounded-full bg-gray-200" />
                  </span>
                )}
                <span className={isDone ? 'text-gray-500' : isCurrent ? 'text-gray-900 font-medium' : 'text-gray-300'}>
                  {PHASE_LABELS[p]}
                </span>
              </div>
            );
          })}
        </div>

        {/* Current activity */}
        {!completed && (
          <div className="mb-6">
            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Activity</p>
            {lastTool && (
              <div className="flex items-center gap-2 text-xs text-gray-600 mb-1.5">
                <span className="w-1 h-1 rounded-full bg-amber-400 shrink-0" />
                <span className="font-mono text-amber-700">{lastTool}</span>
              </div>
            )}
            {thinking && (
              <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">{thinking}</p>
            )}
          </div>
        )}

        {/* Files written */}
        {fileWrites.length > 0 && (
          <div className="mb-6">
            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Files updated ({fileWrites.length})
            </p>
            <div className="space-y-0.5">
              {fileWrites.map((f, i) => (
                <div key={i} className="flex items-center gap-2 text-xs font-mono text-gray-600 py-0.5">
                  <span className="text-emerald-500">+</span>
                  <span className="truncate">{f.path.replace(/^\/home\/user\//, '').replace(/^store\//, '')}</span>
                  {f.is_new && <span className="text-[10px] px-1 py-0.5 rounded bg-amber-50 text-amber-700">new</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Completion result */}
        {completed && result && (
          <div className="border border-gray-100 rounded-lg p-4">
            <span className="text-sm font-medium text-gray-800">Dream complete</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dream Content Viewer (right pane)
// ---------------------------------------------------------------------------

const IS_DEV = process.env.NODE_ENV === 'development';

function DreamTranscriptSection({ dreamId }: { dreamId: string }) {
  const [open, setOpen] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!IS_DEV || !open || transcript !== null) return;
    let cancelled = false;
    setLoading(true);
    storeApi.getDreamTranscript(dreamId).then(data => {
      if (!cancelled) { setTranscript(data.transcript || []); setLoading(false); }
    }).catch(() => {
      if (!cancelled) { setTranscript([]); setLoading(false); }
    });
    return () => { cancelled = true; };
  }, [open, dreamId, transcript]);

  if (!IS_DEV) return null;

  return (
    <div className="border-t border-gray-100">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-5 py-3 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-50/50 transition-colors"
      >
        <svg className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-medium">Transcript (dev)</span>
        {loading && <div className="w-3 h-3 border border-gray-300 border-t-gray-500 rounded-full animate-spin ml-1" />}
      </button>
      {open && (
        <div className="px-5 pb-5">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
            </div>
          ) : transcript && transcript.length > 0 ? (
            <TranscriptViewer entries={transcript} />
          ) : (
            <p className="text-xs text-gray-400 py-4">No transcript recorded</p>
          )}
        </div>
      )}
    </div>
  );
}

function DreamContentViewer({ dream, onNavigate }: { dream: Dream; onNavigate: (filename: string) => void }) {
  const duration = formatDuration(dream.started_at, dream.completed_at);
  const dateStr = new Date(dream.created_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
  const timeStr = new Date(dream.created_at).toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit',
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2 min-w-0">
          {statusBadge(dream.status)}
        </div>
        <div className="flex items-center gap-3 text-[11px] text-gray-400">
          {duration && <span>{duration}</span>}
          <span>{dateStr}, {timeStr}</span>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {/* Summary — the main content */}
        {dream.summary && (
          <div className="px-5 py-4">
            <div className="prose prose-sm prose-gray max-w-none [&_h1]:text-base [&_h1]:font-semibold [&_h1]:mt-5 [&_h1]:mb-2 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mt-4 [&_h2]:mb-1.5 [&_h3]:text-xs [&_h3]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1 [&_p]:text-[13px] [&_li]:text-[13px] [&_table]:text-xs">
              <WikiMarkdown content={dream.summary} onNavigate={onNavigate} />
            </div>
          </div>
        )}

        {/* Transcript — collapsed by default, lazy-loaded on expand */}
        <DreamTranscriptSection dreamId={dream.id} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

export default function MemoryStorePanel() {
  const { user } = useAuth();
  const [files, setFiles] = useState<StoreFile[]>([]);
  const [dreams, setDreams] = useState<Dream[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedDream, setSelectedDream] = useState<Dream | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [tab, setTab] = useState<'store' | 'dreams'>('store');
  const [triggering, setTriggering] = useState(false);

  const loadFiles = useCallback(async () => {
    if (!user) return;
    const result = await storeApi.listStoreFiles();
    setFiles(result);
  }, [user]);

  const loadDreams = useCallback(async () => {
    if (!user) return;
    const result = await storeApi.listDreams();
    setDreams(result);
  }, [user]);

  useEffect(() => {
    loadFiles();
    loadDreams();
  }, [loadFiles, loadDreams]);

  const handleSelectFile = useCallback(async (filename: string) => {
    if (!user) return;
    setSelectedFile(filename);
    setSelectedDream(null);
    setContentLoading(true);
    try {
      const result = await storeApi.readStoreFile(filename);
      setFileContent(result?.content || '');
    } catch {
      setFileContent(null);
    } finally {
      setContentLoading(false);
    }
  }, [user]);

  const handleSelectDream = useCallback((dream: Dream) => {
    setSelectedDream(dream);
    setSelectedFile(null);
  }, []);

  const handleEdit = useCallback(async (content: string) => {
    if (!user || !selectedFile) return;
    await storeApi.updateStoreFile(selectedFile, content);
    setFileContent(content);
    loadFiles();
  }, [user, selectedFile, loadFiles]);

  const [triggerError, setTriggerError] = useState<string | null>(null);

  const handleTriggerDream = useCallback(async () => {
    if (!user || triggering) return;
    setTriggering(true);
    setTriggerError(null);
    try {
      const data = await storeApi.triggerDream();
      if (data.dream_id) {
        const newDream: Dream = {
          id: data.dream_id,
          status: 'running',
          trigger: 'manual',
          created_at: new Date().toISOString(),
          started_at: new Date().toISOString(),
        };
        setDreams(prev => [newDream, ...prev]);
        setSelectedDream(newDream);
        setSelectedFile(null);
        setTab('dreams');
      }
    } catch (e: any) {
      const msg = e?.message || '';
      if (msg.includes('already running') || msg.includes('cooldown')) {
        setTriggerError('A dream is already running');
      } else {
        setTriggerError('Failed to trigger dream');
      }
      setTimeout(() => setTriggerError(null), 4000);
    } finally {
      setTriggering(false);
    }
  }, [user, triggering]);

  const handleDreamComplete = useCallback(() => {
    loadDreams();
    loadFiles();
    if (selectedDream) {
      storeApi.listDreams(1).then(dreams => {
        const updated = dreams.find((d: Dream) => d.id === selectedDream.id);
        if (updated) setSelectedDream(updated);
      }).catch(() => {});
    }
  }, [loadDreams, loadFiles, selectedDream]);

  const selectedFileObj = files.find(f => f.filename === selectedFile) || null;

  return (
    <div className="flex h-full">
      {/* Left sidebar */}
      <div className="w-64 border-r border-gray-100 flex flex-col shrink-0">
        {/* Tabs — matches dashboard TopNavBar pattern */}
        <div className="shrink-0 border-b border-gray-100 px-3">
          <div className="flex items-center gap-4 h-11">
            {([{ key: 'store' as const, label: 'Store' }, { key: 'dreams' as const, label: 'Dreams' }]).map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`relative h-full flex items-center text-sm font-medium transition-colors ${
                  tab === t.key ? 'text-gray-900' : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                {t.label}
                {t.key === 'dreams' && dreams.some(d => d.status === 'running') && (
                  <span className="ml-1.5 inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                )}
                {tab === t.key && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-gray-900 rounded-full" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto py-1">
          {tab === 'store' ? (
            <FileTree files={files} selected={selectedFile} onSelect={handleSelectFile} />
          ) : (
            <div className="px-2">
              <div className="px-1 pt-2 pb-1">
                <button
                  onClick={handleTriggerDream}
                  disabled={triggering}
                  className="w-full text-xs text-gray-600 hover:text-gray-800 border border-gray-200 hover:border-gray-300 rounded-md py-1.5 transition-colors disabled:opacity-50"
                >
                  {triggering ? 'Triggering...' : 'Trigger Dream'}
                </button>
                {triggerError && (
                  <p className="text-[11px] text-red-500 mt-1 px-0.5">{triggerError}</p>
                )}
              </div>
              <DreamLog
                dreams={dreams}
                onTrigger={handleTriggerDream}
                triggering={triggering}
                selectedDreamId={selectedDream?.id || null}
                onSelectDream={handleSelectDream}
              />
            </div>
          )}
        </div>
      </div>

      {/* Right content */}
      <div className="flex-1 min-w-0">
        {selectedDream && (selectedDream.status === 'running' || selectedDream.status === 'pending') ? (
          <DreamProgressView dream={selectedDream} onDreamComplete={handleDreamComplete} />
        ) : selectedDream ? (
          <DreamContentViewer dream={selectedDream} onNavigate={handleSelectFile} />
        ) : (
          <ContentViewer
            file={selectedFileObj}
            content={fileContent}
            loading={contentLoading}
            onEdit={handleEdit}
            onNavigate={handleSelectFile}
          />
        )}
      </div>
    </div>
  );
}
