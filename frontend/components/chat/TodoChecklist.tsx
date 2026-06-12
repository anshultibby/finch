'use client';

import React from 'react';
import type { TodoItem } from '@/lib/types';

/**
 * Live task-phase checklist shown while the agent works on a long task.
 * Fed by `todo_update` SSE events (the update_todos tool) — each event
 * replaces the whole list. Ephemeral: rendered only during streaming.
 */
export default function TodoChecklist({ items }: { items: TodoItem[] }) {
  const done = items.filter(i => i.status === 'completed').length;

  return (
    <div className="ml-5 mt-1 mb-1 animate-activity-in">
      <div className="inline-flex flex-col gap-1 rounded-xl border border-stone-100 bg-stone-50/60 px-3 py-2 min-w-[200px] max-w-full">
        <span className="text-[10px] font-medium uppercase tracking-wide text-stone-400">
          Tasks · {done}/{items.length}
        </span>
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-2 min-w-0">
            <span className="w-3.5 h-3.5 mt-[3px] flex items-center justify-center flex-shrink-0">
              {item.status === 'completed' ? (
                <svg className="w-3 h-3 text-emerald-500" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              ) : item.status === 'in_progress' ? (
                <span className="relative w-3 h-3 flex items-center justify-center">
                  <span className="absolute inset-0 rounded-full bg-emerald-400 animate-halo" />
                  <span className="relative w-[6px] h-[6px] rounded-full bg-emerald-500 block" />
                </span>
              ) : (
                <span className="w-[10px] h-[10px] rounded-full border-[1.5px] border-stone-300 block" />
              )}
            </span>
            <span
              className={`text-xs leading-5 min-w-0 ${
                item.status === 'completed'
                  ? 'text-stone-400 line-through decoration-stone-300'
                  : item.status === 'in_progress'
                    ? 'text-stone-700 font-medium'
                    : 'text-stone-400'
              }`}
            >
              {item.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
