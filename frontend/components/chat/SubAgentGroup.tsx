'use client';

import React, { useState } from 'react';
import ToolCall from './ToolCall';
import type { ToolCallStatus } from '@/lib/types';

interface SubAgentGroupProps {
  parent: ToolCallStatus;            // the `delegate` tool call
  childTools: ToolCallStatus[];      // the sub-agent's own tool calls, in order
  onSelectTool?: (tool: ToolCallStatus) => void;
  onPeekAgent?: (agentId: string, chatId: string, name: string) => void;
}

/** A capped delegate returns this error; render it as a calm "skipped", not a failure. */
export function isLimitSkipped(t: ToolCallStatus): boolean {
  if (t.tool_name !== 'delegate') return false;
  const isErr = t.status === 'error' || !!t.error;
  return isErr && /limit/i.test((t.error || '') + (t.result_summary || ''));
}

// The delegate result reads: "Task 'x' complete. Output written to ... Summary:\n\n<summary>".
// Pull just the human-facing summary.
function extractSummary(raw?: string): string | null {
  if (!raw) return null;
  const idx = raw.indexOf('Summary:');
  const text = (idx >= 0 ? raw.slice(idx + 'Summary:'.length) : raw).trim();
  return text || null;
}

export default function SubAgentGroup({ parent, childTools, onSelectTool, onPeekAgent }: SubAgentGroupProps) {
  const task = (parent.arguments?.task_id as string) || parent.task_id || 'sub-agent';
  const running = parent.status === 'detected' || parent.status === 'calling';
  const isError = parent.status === 'error' || !!parent.error;
  const summary = extractSummary(parent.result_summary);
  const [open, setOpen] = useState(true);

  // Capped delegate → muted chip, no body. Reads as intentional, not an error.
  if (isLimitSkipped(parent)) {
    return (
      <div className="inline-flex items-center gap-2 py-1.5 px-3 rounded-lg bg-gray-50 border border-gray-200/70">
        <svg className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="9" /><path d="M5.6 5.6l12.8 12.8" />
        </svg>
        <span className="text-sm font-medium text-gray-500">Sub-agent</span>
        <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{task}</span>
        <span className="text-xs text-gray-400">skipped — 2 sub-agent limit</span>
      </div>
    );
  }

  const statusLabel = running
    ? 'working…'
    : isError
      ? 'failed'
      // Child tool calls only exist live (they run inside the delegate, not on the
      // saved message), so show the count only when we actually have them.
      : childTools.length > 0
        ? `${childTools.length} tool${childTools.length !== 1 ? 's' : ''} · done`
        : 'done';

  return (
    <div className={`rounded-lg border transition-colors ${running ? 'border-indigo-200 bg-indigo-50/40' : 'border-gray-200 bg-white'}`}>
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2.5 py-2 px-3 text-left select-none"
      >
        <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${isError ? 'bg-red-100' : 'bg-indigo-100'}`}>
          {running ? (
            <span className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse block" />
          ) : (
            <svg className={`w-3.5 h-3.5 ${isError ? 'text-red-500' : 'text-indigo-600'}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          )}
        </div>
        <span className="text-sm font-semibold text-gray-800 flex-shrink-0">Sub-agent</span>
        <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-indigo-100/70 text-indigo-700 truncate min-w-0">{task}</span>
        <span className={`text-xs flex-shrink-0 ${running ? 'text-indigo-500' : isError ? 'text-red-500' : 'text-gray-400'}`}>{statusLabel}</span>
        <svg
          className={`w-4 h-4 ml-auto flex-shrink-0 text-gray-400 transition-transform duration-200 ${open ? 'rotate-90' : ''}`}
          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
        >
          <path d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* Body: nested tools + final result */}
      {open && (
        <div className="px-3 pb-3 flex flex-col gap-1 animate-fade-in">
          <div className="ml-2 pl-3 border-l-2 border-indigo-200/70 flex flex-col gap-1">
            {childTools.map(child => (
              <ToolCall
                key={child.tool_call_id}
                toolCall={child}
                onShowOutput={() => onSelectTool?.(child)}
                onPeekAgent={onPeekAgent}
              />
            ))}
            {childTools.length === 0 && running && (
              <span className="text-xs text-indigo-400/80 animate-pulse py-1">Starting…</span>
            )}
          </div>

          {summary && !running && (
            <div className="mt-1 rounded-md bg-indigo-50/60 border border-indigo-100 p-2.5">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-indigo-500/80 mb-1">Result</div>
              <p className="text-xs text-gray-600 whitespace-pre-wrap max-h-40 overflow-y-auto">{summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
