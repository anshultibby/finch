'use client';

import React, { useState, useMemo } from 'react';
import type { Message, ToolCallStatus } from '@/lib/types';

interface ChatDebugPanelProps {
  messages: Message[];
  streamingText: string;
  streamingTools: ToolCallStatus[];
  isLoading: boolean;
  chatId: string | null;
}

interface MessageStats {
  totalMessages: number;
  byRole: { user: number; assistant: number; tool: number };
  totalChars: number;
  estimatedTokens: number;
  toolCallsCount: number;
}

interface TimelineItem {
  id: string;
  type: 'user' | 'assistant' | 'tool' | 'streaming';
  content: string;
  toolName?: string;
  status?: string;
  timestamp?: string;
  arguments?: Record<string, unknown>;
  error?: string;
  result?: string;  // Tool result content
}

// Check if debug mode is enabled via env variable
export const isDebugMode = () => {
  if (typeof window === 'undefined') return false;
  return process.env.NEXT_PUBLIC_DEBUG_MODE === 'true';
};

export default function ChatDebugPanel({
  messages,
  streamingText,
  streamingTools,
  isLoading,
  chatId,
}: ChatDebugPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState<'timeline' | 'stats' | 'raw'>('timeline');
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const toggleItem = (id: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Calculate statistics
  const stats = useMemo<MessageStats>(() => {
    const byRole = { user: 0, assistant: 0, tool: 0 };
    let totalChars = 0;
    let toolCallsCount = 0;

    messages.forEach((msg) => {
      if (msg.role in byRole) {
        byRole[msg.role as keyof typeof byRole]++;
      }
      totalChars += msg.content?.length || 0;
      if (msg.toolCalls) {
        toolCallsCount += msg.toolCalls.length;
      }
    });

    totalChars += streamingText.length;
    toolCallsCount += streamingTools.length;

    return {
      totalMessages: messages.length,
      byRole,
      totalChars,
      estimatedTokens: Math.ceil(totalChars / 4),
      toolCallsCount,
    };
  }, [messages, streamingText, streamingTools]);

  // Build timeline view
  const timeline = useMemo(() => {
    const items: TimelineItem[] = [];
    let idx = 0;

    messages.forEach((msg, msgIdx) => {
      if (msg.role === 'user') {
        items.push({
          id: `msg-${msgIdx}`,
          type: 'user',
          content: msg.content,
          timestamp: msg.timestamp,
        });
      } else if (msg.role === 'assistant') {
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          msg.toolCalls.forEach((tc, tcIdx) => {
            // Build the result string from various possible outputs
            let result: string | undefined;
            if (tc.result_summary) {
              result = tc.result_summary;
            } else if (tc.code_output) {
              const parts: string[] = [];
              if (tc.code_output.stdout) parts.push(tc.code_output.stdout);
              if (tc.code_output.stderr) parts.push(`[stderr] ${tc.code_output.stderr}`);
              if (parts.length > 0) result = parts.join('\n');
            } else if (tc.file_content) {
              result = `File: ${tc.file_content.filename} (${tc.file_content.content.length} chars)`;
            } else if (tc.search_results) {
              result = `Search: "${tc.search_results.query}" - ${tc.search_results.results.length} results`;
            } else if (tc.scraped_content) {
              result = `Scraped: ${tc.scraped_content.url} (${tc.scraped_content.content.length} chars)`;
            }

            items.push({
              id: `tool-${msgIdx}-${tcIdx}`,
              type: 'tool',
              content: tc.statusMessage || tc.tool_name,
              toolName: tc.tool_name,
              status: tc.status,
              arguments: tc.arguments,
              error: tc.error,
              result,
            });
          });
        }
        if (msg.content) {
          items.push({
            id: `asst-${msgIdx}`,
            type: 'assistant',
            content: msg.content,
            timestamp: msg.timestamp,
          });
        }
      }
      idx++;
    });

    // Add streaming state
    streamingTools.forEach((tc, i) => {
      // Build the result string for streaming tools too
      let result: string | undefined;
      if (tc.result_summary) {
        result = tc.result_summary;
      } else if (tc.code_output) {
        const parts: string[] = [];
        if (tc.code_output.stdout) parts.push(tc.code_output.stdout);
        if (tc.code_output.stderr) parts.push(`[stderr] ${tc.code_output.stderr}`);
        if (parts.length > 0) result = parts.join('\n');
      } else if (tc.file_content) {
        result = `File: ${tc.file_content.filename} (${tc.file_content.content.length} chars)`;
      }

      items.push({
        id: `streaming-tool-${i}`,
        type: 'tool',
        content: tc.statusMessage || tc.tool_name,
        toolName: tc.tool_name,
        status: tc.status + ' (streaming)',
        arguments: tc.arguments,
        error: tc.error,
        result,
      });
    });

    if (streamingText) {
      items.push({
        id: 'streaming-text',
        type: 'streaming',
        content: streamingText,
      });
    }

    return items;
  }, [messages, streamingTools, streamingText]);

  if (!isDebugMode()) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 font-mono text-xs">
      {/* Toggle button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute -top-8 right-0 px-2 py-1 bg-gray-800 text-gray-300 rounded-t text-xs hover:bg-gray-700"
      >
        {isExpanded ? '▼ Debug' : '▲ Debug'}
      </button>

      {isExpanded && (
        <div className="w-96 max-h-[600px] bg-gray-900 text-gray-100 rounded-lg shadow-2xl overflow-hidden border border-gray-700 flex flex-col">
          {/* Header */}
          <div className="px-3 py-2 bg-gray-800 border-b border-gray-700 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isLoading ? 'bg-yellow-400 animate-pulse' : 'bg-green-400'}`} />
              <span className="text-gray-300">
                {chatId ? `Chat: ${chatId.slice(0, 8)}...` : 'New Chat'}
              </span>
            </div>
            <div className="flex gap-1">
              {(['timeline', 'stats', 'raw'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-2 py-0.5 rounded text-xs ${
                    activeTab === tab
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="overflow-y-auto flex-1 p-2">
            {activeTab === 'timeline' && (
              <div className="space-y-1">
                {timeline.length === 0 ? (
                  <div className="text-gray-500 text-center py-4">No messages yet</div>
                ) : (
                  timeline.map((item) => {
                    const isItemExpanded = expandedItems.has(item.id);
                    const preview = item.content.slice(0, 200) + (item.content.length > 200 ? '...' : '');
                    
                    return (
                      <div
                        key={item.id}
                        className={`rounded text-xs ${
                          item.type === 'user'
                            ? 'bg-purple-900/50 border-l-2 border-purple-500'
                            : item.type === 'assistant'
                            ? 'bg-green-900/50 border-l-2 border-green-500'
                            : item.type === 'tool'
                            ? 'bg-blue-900/50 border-l-2 border-blue-500'
                            : 'bg-yellow-900/50 border-l-2 border-yellow-500'
                        }`}
                      >
                        {/* Header - always visible, clickable */}
                        <div
                          onClick={() => toggleItem(item.id)}
                          className="p-1.5 cursor-pointer hover:bg-white/5 flex items-start gap-2"
                        >
                          <span className="text-gray-500 select-none shrink-0">
                            {isItemExpanded ? '▼' : '▶'}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                              <span className="font-semibold uppercase text-[10px] text-gray-400">
                                {item.type === 'streaming' ? 'streaming' : item.type}
                              </span>
                              {item.toolName && (
                                <span className="text-blue-300">{item.toolName}</span>
                              )}
                              {item.status && (
                                <span
                                  className={`text-[10px] px-1 rounded ${
                                    item.status.includes('completed')
                                      ? 'bg-green-700'
                                      : item.status.includes('error')
                                      ? 'bg-red-700'
                                      : 'bg-yellow-700'
                                  }`}
                                >
                                  {item.status}
                                </span>
                              )}
                              {item.result && (
                                <span className="text-green-400 text-[10px]">
                                  ✓ has result
                                </span>
                              )}
                              <span className="text-gray-600 text-[10px]">
                                {item.content.length} chars
                              </span>
                            </div>
                            {!isItemExpanded && (
                              <div className="text-gray-400 truncate">{preview}</div>
                            )}
                          </div>
                        </div>

                        {/* Expanded content */}
                        {isItemExpanded && (
                          <div className="px-3 pb-2 pt-0 border-t border-white/10 mt-1">
                            {item.arguments && (
                              <div className="mb-2">
                                <div className="text-gray-500 text-[10px] mb-1">ARGUMENTS</div>
                                <pre className="bg-gray-800/50 p-1.5 rounded text-[10px] overflow-x-auto text-gray-300 whitespace-pre-wrap">
                                  {JSON.stringify(item.arguments, null, 2)}
                                </pre>
                              </div>
                            )}
                            {item.error && (
                              <div className="mb-2">
                                <div className="text-red-400 text-[10px] mb-1">ERROR</div>
                                <pre className="bg-red-900/30 p-1.5 rounded text-[10px] overflow-x-auto text-red-300 whitespace-pre-wrap">
                                  {item.error}
                                </pre>
                              </div>
                            )}
                            {item.result && (
                              <div className="mb-2">
                                <div className="text-green-400 text-[10px] mb-1">RESULT</div>
                                <pre className="bg-green-900/30 p-1.5 rounded text-[10px] overflow-x-auto text-green-300 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                  {item.result}
                                </pre>
                              </div>
                            )}
                            <div>
                              <div className="text-gray-500 text-[10px] mb-1">CONTENT</div>
                              <pre className="bg-gray-800/50 p-1.5 rounded text-[10px] overflow-x-auto text-gray-300 whitespace-pre-wrap max-h-48 overflow-y-auto">
                                {item.content}
                              </pre>
                            </div>
                            {item.timestamp && (
                              <div className="text-gray-600 text-[10px] mt-1">
                                {new Date(item.timestamp).toLocaleString()}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {activeTab === 'stats' && (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-gray-800 p-2 rounded">
                    <div className="text-gray-500 text-[10px]">MESSAGES</div>
                    <div className="text-lg font-bold">{stats.totalMessages}</div>
                  </div>
                  <div className="bg-gray-800 p-2 rounded">
                    <div className="text-gray-500 text-[10px]">TOOL CALLS</div>
                    <div className="text-lg font-bold">{stats.toolCallsCount}</div>
                  </div>
                  <div className="bg-gray-800 p-2 rounded">
                    <div className="text-gray-500 text-[10px]">EST. TOKENS</div>
                    <div className="text-lg font-bold">{stats.estimatedTokens.toLocaleString()}</div>
                  </div>
                  <div className="bg-gray-800 p-2 rounded">
                    <div className="text-gray-500 text-[10px]">CHARACTERS</div>
                    <div className="text-lg font-bold">{stats.totalChars.toLocaleString()}</div>
                  </div>
                </div>

                <div className="bg-gray-800 p-2 rounded">
                  <div className="text-gray-500 text-[10px] mb-1">BY ROLE</div>
                  <div className="flex gap-4">
                    <div>
                      <span className="text-purple-400">User:</span> {stats.byRole.user}
                    </div>
                    <div>
                      <span className="text-green-400">Assistant:</span> {stats.byRole.assistant}
                    </div>
                    <div>
                      <span className="text-blue-400">Tool:</span> {stats.byRole.tool}
                    </div>
                  </div>
                </div>

                <div className="bg-gray-800 p-2 rounded">
                  <div className="text-gray-500 text-[10px] mb-1">STATE</div>
                  <div className="flex flex-wrap gap-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${isLoading ? 'bg-yellow-700' : 'bg-gray-700'}`}>
                      {isLoading ? 'Loading' : 'Idle'}
                    </span>
                    {streamingText && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-700">
                        Streaming Text ({streamingText.length} chars)
                      </span>
                    )}
                    {streamingTools.length > 0 && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-700">
                        {streamingTools.length} Tool(s) Active
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'raw' && (
              <div className="space-y-1">
                <pre className="text-[10px] bg-gray-800 p-2 rounded overflow-x-auto whitespace-pre-wrap break-all max-h-[500px] overflow-y-auto">
                  {JSON.stringify(
                    {
                      chatId,
                      isLoading,
                      messagesCount: messages.length,
                      streamingTextLength: streamingText.length,
                      streamingToolsCount: streamingTools.length,
                      // Show full tool call data to debug
                      toolCalls: messages.flatMap((msg, i) => 
                        (msg.toolCalls || []).map((tc, j) => ({
                          msgIndex: i,
                          tool_name: tc.tool_name,
                          status: tc.status,
                          has_result_summary: !!tc.result_summary,
                          has_code_output: !!tc.code_output,
                          has_file_content: !!tc.file_content,
                          has_search_results: !!tc.search_results,
                          has_error: !!tc.error,
                          result_summary: tc.result_summary,
                          code_output: tc.code_output,
                          error: tc.error,
                        }))
                      ),
                      streamingTools: streamingTools.map(tc => ({
                        tool_name: tc.tool_name,
                        status: tc.status,
                        has_result_summary: !!tc.result_summary,
                        has_code_output: !!tc.code_output,
                        result_summary: tc.result_summary,
                        code_output: tc.code_output,
                      })),
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
