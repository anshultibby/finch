'use client';

import React, { useState, useRef, useEffect } from 'react';
import { SparkleIcon } from './ActivityTicker';

// ═══════════════════════════════════════════════════════════════════════════
// ReasoningCard — a distinct, first-class card in the chat transcript for the
// agent's reasoning ("thoughts"). One component, two modes:
//   • live=true   → streams the thinking in real time (pulsing header, elapsed
//                   timer, char count, auto-scrolls to the newest tokens).
//   • live=false  → the persisted trace in history: a visible preview in-flow
//                   that expands to the full, scrollable trace.
// Either way it's expandable so the whole trace is readable in-place.
// ═══════════════════════════════════════════════════════════════════════════

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
}

interface ReasoningCardProps {
  text: string;
  /** Streaming now → pulse + "Thinking" + elapsed + auto-scroll to the tail. */
  live?: boolean;
  /** When the turn started, for the live elapsed timer. */
  startTime?: number | null;
}

export default function ReasoningCard({ text, live = false, startTime }: ReasoningCardProps) {
  // Live starts expanded so you actually watch it stream; history starts as a
  // compact preview the reader opts into.
  const [expanded, setExpanded] = useState(live);
  const [elapsed, setElapsed] = useState(0);
  const bodyRef = useRef<HTMLDivElement>(null);

  // While live, follow the newest reasoning — unless the user scrolled up to read.
  useEffect(() => {
    if (!live) return;
    const el = bodyRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    if (nearBottom) el.scrollTop = el.scrollHeight;
  }, [text, expanded, live]);

  useEffect(() => {
    if (!live || !startTime) return;
    const tick = () => setElapsed(Math.floor((Date.now() - startTime) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [live, startTime]);

  const clean = text.replace(/\n{3,}/g, '\n\n').trim();
  if (!clean) return null;

  // Live: a generous window showing the streaming tail. History: a short preview.
  const collapsedMax = live ? 'max-h-60' : 'max-h-28';
  const bodyMax = expanded ? 'max-h-[70vh]' : collapsedMax;

  return (
    <div className="mb-2 rounded-xl border border-stone-200/80 bg-stone-50 overflow-hidden">
      {/* Header — click to expand/collapse */}
      <button
        type="button"
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-stone-100/70 transition-colors"
        aria-expanded={expanded}
        aria-label={expanded ? 'Collapse reasoning' : 'Expand reasoning'}
      >
        <span className="relative w-3.5 h-3.5 flex items-center justify-center flex-shrink-0">
          {live && <span className="absolute inset-0 rounded-full bg-emerald-400/60 animate-halo" />}
          <SparkleIcon className={`relative w-3.5 h-3.5 ${live ? 'text-emerald-500' : 'text-emerald-500/80'}`} />
        </span>
        <span className={`text-[13px] font-medium ${live ? 'activity-shimmer-text' : 'text-stone-600'}`}>
          {live ? 'Thinking' : 'Reasoning'}
        </span>
        <span className="flex items-center gap-2 ml-auto flex-shrink-0 pl-2 text-[11px] text-stone-400 tabular-nums">
          <span>{clean.length.toLocaleString()} chars</span>
          {live && startTime && elapsed > 0 && <span>{formatElapsed(elapsed)}</span>}
        </span>
        <svg
          className={`w-3.5 h-3.5 text-stone-300 transition-transform duration-200 flex-shrink-0 ${expanded ? 'rotate-90' : ''}`}
          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
        >
          <path d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* Body — full trace, scrollable. Bottom fade signals "more" when collapsed. */}
      <div ref={bodyRef} className={`relative px-3 pb-3 overflow-y-auto chat-scrollbar ${bodyMax}`}>
        <p className="text-xs italic leading-5 text-stone-500 whitespace-pre-line">{clean}</p>
        {!expanded && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-stone-50 to-transparent" />
        )}
      </div>

      {!expanded && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="w-full py-1.5 text-[11px] text-stone-400 hover:text-stone-600 hover:bg-stone-100/70 transition-colors border-t border-stone-100"
        >
          Show full reasoning
        </button>
      )}
    </div>
  );
}
