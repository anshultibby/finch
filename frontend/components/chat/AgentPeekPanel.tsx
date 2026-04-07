'use client';

import React, { useEffect, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatApi } from '@/lib/api';
import type { ToolCallStatus } from '@/lib/types';

interface AgentMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  tool_calls?: ToolCallStatus[];
}

interface AgentPeekPanelProps {
  agentId: string;
  chatId: string;
  agentName: string;
  onClose: () => void;
}

function CodeOutputBlock({ output }: { output: { stdout?: string; stderr?: string } }) {
  const text = [output.stdout, output.stderr].filter(Boolean).join('\n').trim();
  if (!text) return null;
  return (
    <pre className="mt-1.5 text-[11px] bg-gray-950 text-gray-300 rounded p-2.5 overflow-x-auto whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
      {text}
    </pre>
  );
}

function ToolCallChip({ tool }: { tool: ToolCallStatus }) {
  const [expanded, setExpanded] = useState(false);
  const hasOutput = tool.code_output && (tool.code_output.stdout || tool.code_output.stderr);

  const isError = tool.status === 'error';
  const chipClass = isError
    ? 'bg-red-50 border-red-200 text-red-700'
    : 'bg-gray-50 border-gray-200 text-gray-600';

  return (
    <div className={`rounded-lg border ${chipClass} text-xs overflow-hidden`}>
      <button
        onClick={() => hasOutput && setExpanded(e => !e)}
        className={`w-full flex items-center gap-2 px-2.5 py-1.5 text-left ${hasOutput ? 'cursor-pointer hover:bg-black/5' : 'cursor-default'}`}
      >
        <span className="font-mono font-medium truncate flex-1">
          {tool.statusMessage || tool.tool_name}
        </span>
        {isError && <span className="text-red-500 flex-shrink-0">✕</span>}
        {!isError && <span className="text-gray-400 flex-shrink-0">✓</span>}
        {hasOutput && (
          <svg
            className={`w-3 h-3 flex-shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>
      {expanded && hasOutput && (
        <div className="px-2.5 pb-2.5">
          <CodeOutputBlock output={tool.code_output!} />
        </div>
      )}
    </div>
  );
}

function AgentMessageBubble({ msg }: { msg: AgentMessage }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-indigo-600 text-white rounded-2xl rounded-br-sm px-3.5 py-2.5 text-sm">
          <p className="whitespace-pre-wrap break-words leading-relaxed">{msg.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[95%] w-full space-y-1.5">
        {msg.tool_calls && msg.tool_calls.length > 0 && (
          <div className="space-y-1">
            {msg.tool_calls.map(tc => (
              <ToolCallChip key={tc.tool_call_id} tool={tc} />
            ))}
          </div>
        )}
        {msg.content && (
          <div className="prose prose-sm prose-slate max-w-none text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AgentPeekPanel({ agentId, chatId, agentName, onClose }: AgentPeekPanelProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMessages = useCallback(async () => {
    try {
      const data = await chatApi.getChatHistoryForDisplay(chatId);
      setMessages(data.messages as AgentMessage[]);
      setError(null);
    } catch {
      setError('Could not load agent activity.');
    } finally {
      setLoading(false);
    }
  }, [chatId]);

  useEffect(() => {
    fetchMessages();
    // Poll every 5s to catch new activity while agent runs
    const interval = setInterval(fetchMessages, 5000);
    return () => clearInterval(interval);
  }, [fetchMessages]);

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-gray-100 flex-shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
            <svg className="w-3.5 h-3.5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">{agentName}</p>
            <p className="text-[11px] text-gray-400">Sub-agent activity</p>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <a
            href={`/bot/${agentId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2 py-1 text-xs text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-md transition-colors"
          >
            Open
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {loading && (
          <div className="flex items-center justify-center h-32">
            <div className="w-5 h-5 border-2 border-indigo-300 border-t-indigo-600 rounded-full animate-spin" />
          </div>
        )}
        {error && (
          <div className="text-sm text-red-500 text-center py-8">{error}</div>
        )}
        {!loading && !error && messages.length === 0 && (
          <div className="text-center py-12">
            <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-3">
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500">Task queued — open the agent to run it.</p>
            <a
              href={`/bot/${agentId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
            >
              Open agent chat
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        )}
        {!loading && messages.map((msg, i) => (
          <AgentMessageBubble key={i} msg={msg} />
        ))}
      </div>
    </div>
  );
}
