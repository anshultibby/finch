'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface BotDocViewerProps {
  title: string;
  icon: string;
  content: string;
  description: string;
  onBack: () => void;
}

export default function BotDocViewer({ title, icon, content, description, onBack }: BotDocViewerProps) {
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
        <span className="text-lg">{icon}</span>
        <div>
          <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
          <p className="text-[11px] text-gray-400">{description}</p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {content ? (
          <div className="px-6 py-5 max-w-2xl">
            <div className="prose prose-sm prose-gray max-w-none
              prose-headings:font-semibold prose-headings:text-gray-900
              prose-h1:text-lg prose-h1:border-b prose-h1:border-gray-100 prose-h1:pb-2 prose-h1:mb-4
              prose-h2:text-[15px] prose-h2:mt-6 prose-h2:mb-2
              prose-h3:text-[13px] prose-h3:mt-4 prose-h3:mb-1.5
              prose-p:text-[13px] prose-p:text-gray-600 prose-p:leading-relaxed
              prose-li:text-[13px] prose-li:text-gray-600
              prose-strong:text-gray-800
              prose-code:text-[12px] prose-code:bg-gray-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:border prose-code:border-gray-100
              prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-100 prose-pre:rounded-xl prose-pre:text-[12px]
              prose-table:text-[12px]
              prose-th:text-gray-500 prose-th:font-semibold prose-th:text-[11px] prose-th:uppercase prose-th:tracking-wide
              prose-td:text-gray-600
            ">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <span className="text-3xl mb-3">{icon}</span>
            <p className="text-sm font-medium text-gray-500">No {title.toLowerCase()} yet</p>
            <p className="text-xs text-gray-400 mt-1 max-w-xs leading-relaxed">
              {title === 'Strategy'
                ? 'Chat with your bot to define a trading thesis, backtest it, and build a strategy.'
                : 'Your bot will accumulate operational memory as it trades and learns from outcomes.'
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
