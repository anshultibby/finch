'use client';

import React, { useState } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

/**
 * Inline error banner for data sections that failed to load. Companion to
 * EmptyState: empty = "nothing here yet", this = "we couldn't find out".
 * Sections should never silently render blank on a failed fetch.
 */
export default function DataError({
  message,
  onRetry,
  className = '',
}: {
  message: string;
  onRetry?: () => void | Promise<unknown>;
  className?: string;
}) {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    if (!onRetry || retrying) return;
    setRetrying(true);
    try {
      await onRetry();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className={`flex items-center justify-between gap-3 rounded-xl border border-amber-200/70 bg-amber-50/60 px-4 py-3 ${className}`}>
      <div className="flex items-center gap-2.5 min-w-0">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" strokeWidth={2} />
        <span className="text-sm text-gray-700 truncate">{message}</span>
      </div>
      {onRetry && (
        <button
          onClick={handleRetry}
          disabled={retrying}
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-gray-900 hover:text-gray-600 disabled:opacity-50 transition-colors shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${retrying ? 'animate-spin' : ''}`} strokeWidth={2} />
          Retry
        </button>
      )}
    </div>
  );
}
