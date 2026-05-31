'use client';

import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  /** Primary call-to-action. */
  action?: { label: string; onClick: () => void };
  /** Optional secondary hint shown under the action. */
  hint?: string;
  className?: string;
}

/**
 * Shared empty-state. One consistent, inviting pattern across the app —
 * an accented icon, a clear title, a short line of guidance, and (ideally)
 * a single action so the screen is never a dead end.
 */
export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  hint,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center text-center px-6 py-16 ${className}`}>
      <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-500 mb-4">
        <Icon className="w-7 h-7" strokeWidth={1.75} />
      </div>
      <h3 className="text-base font-semibold text-gray-900 mb-1.5">{title}</h3>
      {description && (
        <p className="text-sm text-gray-500 max-w-xs leading-relaxed">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-5 inline-flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-emerald-700 hover:shadow-md active:scale-[0.98]"
        >
          {action.label}
        </button>
      )}
      {hint && <p className="mt-3 text-xs text-gray-400">{hint}</p>}
    </div>
  );
}
