'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface JournalEntry {
  filename: string;
  content: string;
  updated_at?: string;
}

interface BotJournalViewerProps {
  entries: JournalEntry[];
  onBack: () => void;
}

function parseDate(filename: string, updatedAt?: string): Date {
  // filename is YYYY-MM-DD.md
  const match = filename.match(/^(\d{4}-\d{2}-\d{2})\.md$/);
  if (match) return new Date(match[1] + 'T12:00:00');
  if (updatedAt) return new Date(updatedAt);
  return new Date(0);
}

function formatDateHeading(filename: string): string {
  const match = filename.match(/^(\d{4}-\d{2}-\d{2})\.md$/);
  if (!match) return filename;
  const d = new Date(match[1] + 'T12:00:00');
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = d.toDateString() === yesterday.toDateString();

  const formatted = d.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  });

  if (isToday) return `Today — ${formatted}`;
  if (isYesterday) return `Yesterday — ${formatted}`;
  return formatted;
}

function formatTime(updatedAt?: string): string {
  if (!updatedAt) return '';
  const d = new Date(updatedAt);
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export default function BotJournalViewer({ entries, onBack }: BotJournalViewerProps) {
  // Sort entries by date, newest first
  const sorted = [...entries].sort((a, b) => {
    const da = parseDate(a.filename, a.updated_at);
    const db = parseDate(b.filename, b.updated_at);
    return db.getTime() - da.getTime();
  });

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100 shrink-0">
        <button
          onClick={onBack}
          className="p-1 -ml-1 text-gray-400 hover:text-gray-600 transition-colors rounded-lg hover:bg-gray-50"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
        </svg>
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Journal</h2>
          <p className="text-[11px] text-gray-400">Daily observations, notes & trade reasoning</p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <svg className="w-8 h-8 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
            </svg>
            <p className="text-sm font-medium text-gray-500">No journal entries yet</p>
            <p className="text-xs text-gray-400 mt-1 max-w-xs leading-relaxed">
              Your bot will log daily observations, trade reasoning, and market notes as it operates.
            </p>
          </div>
        ) : (
          <div className="px-6 py-5 max-w-2xl space-y-6">
            {sorted.map((entry) => (
              <div key={entry.filename}>
                {/* Date heading */}
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="text-[13px] font-semibold text-gray-900">
                    {formatDateHeading(entry.filename)}
                  </h3>
                  {entry.updated_at && (
                    <span className="text-[11px] text-gray-400">
                      Last updated {formatTime(entry.updated_at)}
                    </span>
                  )}
                </div>

                {/* Entry content */}
                <div className="pl-3 border-l-2 border-gray-100">
                  <div className="prose prose-sm prose-gray max-w-none
                    prose-headings:font-semibold prose-headings:text-gray-900
                    prose-h1:text-[15px] prose-h1:mb-2
                    prose-h2:text-[13px] prose-h2:mt-4 prose-h2:mb-1.5
                    prose-p:text-[13px] prose-p:text-gray-600 prose-p:leading-relaxed
                    prose-li:text-[13px] prose-li:text-gray-600 prose-li:my-0.5
                    prose-ul:my-1
                    prose-strong:text-gray-800
                    prose-code:text-[12px] prose-code:bg-gray-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:border prose-code:border-gray-100
                  ">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
