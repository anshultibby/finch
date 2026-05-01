'use client';

import React, { useState, useEffect } from 'react';
import ToolCall from './ToolCall';
import type { ToolCallStatus } from '@/lib/types';
import type { TimeEstimate } from '@/hooks/useChatStream';

interface ToolCallSummaryProps {
  toolCalls: ToolCallStatus[];
  isStreaming?: boolean;
  startTime?: number | null;
  timeEstimate?: TimeEstimate | null;
  onSelectTool?: (tool: ToolCallStatus) => void;
  onPeekAgent?: (agentId: string, chatId: string, name: string) => void;
}

// Tools that are always shown outside the collapsed summary
const ALWAYS_VISIBLE_TOOLS = new Set(['create_agent', 'place_trade']);

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
}

function formatEstimate(seconds: number): string {
  if (seconds <= 30) return '~30s';
  if (seconds <= 60) return '~1 min';
  if (seconds <= 90) return '~1-2 min';
  const min = Math.round(seconds / 60);
  return `~${min} min`;
}

/** Get the display name for the active tool */
function getActiveToolLabel(toolName: string): string {
  const map: Record<string, string> = {
    'bash': 'Running code',
    'execute_code': 'Running code',
    'web_search': 'Searching web',
    'news_search': 'Searching news',
    'scrape_url': 'Reading webpage',
    'write_chat_file': 'Writing file',
    'read_chat_file': 'Reading file',
    'replace_in_chat_file': 'Editing file',
    'get_portfolio': 'Fetching portfolio',
    'get_brokerage_status': 'Checking brokerage',
    'get_fmp_data': 'Fetching market data',
    'build_custom_etf': 'Building ETF',
    'present_swaps': 'Preparing results',
    'connect_brokerage': 'Connecting brokerage',
  };
  return map[toolName] || toolName.replace(/_/g, ' ');
}

export default function ToolCallSummary({
  toolCalls,
  isStreaming = false,
  startTime,
  timeEstimate,
  onSelectTool,
  onPeekAgent,
}: ToolCallSummaryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Sort tools by insertion order, then partition into special vs regular
  // and compute status counts in a single pass
  const sortedTools = [...toolCalls].sort(
    (a, b) => (a._insertionOrder ?? 0) - (b._insertionOrder ?? 0)
  );

  const specialTools: ToolCallStatus[] = [];
  const regularTools: ToolCallStatus[] = [];
  let completedCount = 0;
  let errorCount = 0;
  let activeToolName: string | null = null;

  for (const t of sortedTools) {
    if (ALWAYS_VISIBLE_TOOLS.has(t.tool_name)) {
      specialTools.push(t);
    } else {
      regularTools.push(t);
      if (t.status === 'completed') completedCount++;
      else if (t.status === 'error') errorCount++;
      else if (t.status === 'calling' || t.status === 'detected') activeToolName = t.tool_name;
    }
  }

  const totalCount = regularTools.length;

  // Elapsed time ticker — captures final value when streaming ends
  useEffect(() => {
    if (!startTime) {
      setElapsedSeconds(0);
      return;
    }
    if (!isStreaming) {
      // Capture final elapsed time once when streaming stops
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
      return;
    }
    const tick = () => setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [isStreaming, startTime]);

  // Auto-expand when only 1-2 regular tools and done
  const shouldAutoExpand = !isStreaming && regularTools.length <= 2 && regularTools.length > 0;

  // If there are no regular tools, just render special tools
  if (regularTools.length === 0 && specialTools.length === 0) return null;

  if (regularTools.length === 0) {
    return (
      <div className="flex flex-col gap-1">
        {specialTools.map(tool => (
          <ToolCall
            key={tool.tool_call_id}
            toolCall={tool}
            onShowOutput={() => onSelectTool?.(tool)}
            onPeekAgent={onPeekAgent}
          />
        ))}
      </div>
    );
  }

  // Compute remaining time estimate
  let estimateLabel = '';
  if (isStreaming && timeEstimate) {
    const estimatedTotal = timeEstimate.seconds;
    if (elapsedSeconds < 3) {
      estimateLabel = formatEstimate(estimatedTotal);
    } else if (totalCount > 0 && timeEstimate.tools > 0) {
      // Adjust estimate based on actual progress
      const toolProgress = completedCount / timeEstimate.tools;
      const remaining = Math.max(0, Math.round(estimatedTotal * (1 - toolProgress)));
      if (remaining <= 0 || elapsedSeconds > estimatedTotal * 1.5) {
        estimateLabel = 'Almost done...';
      } else {
        estimateLabel = `${formatEstimate(remaining)} remaining`;
      }
    } else {
      estimateLabel = formatEstimate(Math.max(0, estimatedTotal - elapsedSeconds));
    }
  }

  const expanded = isExpanded || shouldAutoExpand;

  return (
    <div className="flex flex-col gap-1">
      {/* Special tools always visible */}
      {specialTools.map(tool => (
        <ToolCall
          key={tool.tool_call_id}
          toolCall={tool}
          onShowOutput={() => onSelectTool?.(tool)}
          onPeekAgent={onPeekAgent}
        />
      ))}

      {/* Collapsed summary bar */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className={`flex items-center gap-2.5 py-2 px-3 rounded-lg cursor-pointer transition-all duration-150 select-none ${
          isStreaming
            ? 'bg-amber-50/70 border border-amber-200/60 hover:border-amber-300'
            : 'bg-gray-50/70 border border-gray-200/60 hover:border-gray-300'
        }`}
      >
        {/* Status icon */}
        <span className="flex-shrink-0">
          {isStreaming ? (
            <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse block" />
          ) : (
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </span>

        {/* Status text */}
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span className={`text-sm font-medium flex-shrink-0 ${
            isStreaming ? 'text-amber-700' : 'text-gray-600'
          }`}>
            {isStreaming
              ? `Working... ${completedCount}/${totalCount > 0 ? totalCount : '?'} steps`
              : `Completed ${totalCount} step${totalCount !== 1 ? 's' : ''}`
            }
          </span>

          {/* Active tool name or estimate description */}
          {isStreaming && activeToolName && (
            <span className="text-xs text-amber-600/80 truncate hidden sm:inline">
              {getActiveToolLabel(activeToolName)}
            </span>
          )}
          {isStreaming && !activeToolName && timeEstimate?.description && (
            <span className="text-xs text-amber-600/70 truncate hidden sm:inline">
              {timeEstimate.description}
            </span>
          )}
        </div>

        {/* Right side: time + chevron */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Time estimate or elapsed */}
          {isStreaming && estimateLabel && (
            <span className="text-xs text-amber-600/70">{estimateLabel}</span>
          )}
          {isStreaming && elapsedSeconds > 0 && (
            <span className="text-xs text-amber-500 tabular-nums">{formatDuration(elapsedSeconds)}</span>
          )}
          {!isStreaming && startTime && elapsedSeconds > 0 && (
            <span className="text-xs text-gray-400 tabular-nums">
              {formatDuration(elapsedSeconds)}
            </span>
          )}

          {/* Expand chevron */}
          <svg
            className={`w-4 h-4 transition-transform duration-200 ${
              isStreaming ? 'text-amber-400' : 'text-gray-400'
            } ${expanded ? 'rotate-90' : ''}`}
            fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
          >
            <path d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>

      {/* Time estimate description below the bar (first few seconds only) */}
      {isStreaming && timeEstimate?.description && elapsedSeconds < 10 && totalCount === 0 && (
        <p className="text-xs text-amber-600/60 px-3 -mt-0.5">
          {timeEstimate.description}
        </p>
      )}

      {/* Expanded tool list */}
      {expanded && (
        <div className="flex flex-col gap-1 pl-1 animate-in fade-in duration-200">
          {regularTools.map(tool => (
            <ToolCall
              key={tool.tool_call_id}
              toolCall={tool}
              onShowOutput={() => onSelectTool?.(tool)}
              onPeekAgent={onPeekAgent}
            />
          ))}
        </div>
      )}
    </div>
  );
}
