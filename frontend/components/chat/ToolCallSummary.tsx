'use client';

import React, { useState, useEffect } from 'react';
import ToolCall from './ToolCall';
import ActivityTicker from './ActivityTicker';
import SubAgentGroup, { isLimitSkipped } from './SubAgentGroup';
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
  const regularTools: ToolCallStatus[] = [];   // top-level (main-agent) tools, incl. delegate parents
  const tickerTools: ToolCallStatus[] = [];    // everything the live ticker narrates, in order
  const childrenByTask = new Map<string, ToolCallStatus[]>();  // sub-agent tools keyed by task_id
  let completedCount = 0;
  let errorCount = 0;

  for (const t of sortedTools) {
    // Sub-agent tools (emitted by `delegate`) are nested under their parent, not
    // counted as top-level steps. Group them by task_id for rendering below.
    if (t.sub_agent_id && t.task_id) {
      const arr = childrenByTask.get(t.task_id) ?? [];
      arr.push(t);
      childrenByTask.set(t.task_id, arr);
      tickerTools.push(t);
      continue;
    }
    if (ALWAYS_VISIBLE_TOOLS.has(t.tool_name)) {
      specialTools.push(t);
    } else {
      regularTools.push(t);
      tickerTools.push(t);
      if (t.status === 'completed') completedCount++;
      else if (t.status === 'error') errorCount++;
    }
  }

  const totalCount = regularTools.length;
  // Sub-agents that actually ran (delegates not rejected by the per-chat cap).
  const subAgentCount = regularTools.filter(t => t.tool_name === 'delegate' && !isLimitSkipped(t)).length;

  /** Render a top-level tool; a `delegate` becomes a rich sub-agent card with its tools + result. */
  const renderTool = (tool: ToolCallStatus) => {
    if (tool.tool_name === 'delegate') {
      const taskId = (tool.arguments?.task_id as string) || tool.task_id || '';
      return (
        <SubAgentGroup
          key={tool.tool_call_id}
          parent={tool}
          childTools={childrenByTask.get(taskId) ?? []}
          onSelectTool={onSelectTool}
          onPeekAgent={onPeekAgent}
        />
      );
    }
    return (
      <ToolCall
        key={tool.tool_call_id}
        toolCall={tool}
        onShowOutput={() => onSelectTool?.(tool)}
        onPeekAgent={onPeekAgent}
      />
    );
  };

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

  const shouldAutoExpand = false;

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

  // Simple time-based countdown from initial estimate
  let estimateLabel = '';
  if (isStreaming && timeEstimate) {
    const remaining = Math.max(0, timeEstimate.seconds - elapsedSeconds);
    if (remaining > 0) {
      estimateLabel = `${formatEstimate(remaining)} left`;
    }
  }

  const expanded = isExpanded || shouldAutoExpand;
  const elapsedLabel = elapsedSeconds > 0 ? formatDuration(elapsedSeconds) : undefined;

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

      {isStreaming && !expanded ? (
        /* Live ticker — finished actions evaporate, current one shimmers */
        <ActivityTicker
          tools={tickerTools}
          elapsedLabel={elapsedLabel}
          estimateLabel={estimateLabel || undefined}
          thinkingLabel={
            tickerTools.length === 0 && timeEstimate?.description
              ? timeEstimate.description
              : 'Thinking…'
          }
          onExpand={() => setIsExpanded(true)}
        />
      ) : (
        /* Summary bar — collapse control while expanded, receipt when done */
        <div
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2.5 py-2 px-3 rounded-xl cursor-pointer transition-colors duration-150 select-none bg-white border border-stone-200/80 hover:border-stone-300"
        >
          <span className="flex-shrink-0">
            {isStreaming ? (
              <span className="relative w-3 h-3 flex items-center justify-center">
                <span className="absolute inset-0 rounded-full bg-emerald-400 animate-halo" />
                <span className="relative w-[7px] h-[7px] rounded-full bg-emerald-500 block" />
              </span>
            ) : (
              <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
          </span>

          <span className="flex-1 min-w-0 text-sm font-medium text-stone-600 truncate">
            {isStreaming
              ? `Working — step ${Math.min(completedCount + 1, Math.max(totalCount, 1))} of ${totalCount > 0 ? totalCount : '…'}`
              : `Ran ${totalCount} step${totalCount !== 1 ? 's' : ''}`
            }
            {subAgentCount > 0 && (
              <span className="ml-1.5 font-normal text-indigo-500/70">
                · {subAgentCount} sub-agent{subAgentCount !== 1 ? 's' : ''}
              </span>
            )}
            {!isStreaming && errorCount > 0 && (
              <span className="ml-1.5 font-normal text-red-400">
                · {errorCount} failed
              </span>
            )}
          </span>

          <span className="flex items-center gap-2 flex-shrink-0">
            {elapsedLabel && startTime && (
              <span className="text-[11px] text-stone-400 tabular-nums">{elapsedLabel}</span>
            )}
            <svg
              className={`w-4 h-4 text-stone-300 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
              fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
            >
              <path d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      )}

      {/* Expanded tool list */}
      {expanded && (
        <div className="flex flex-col gap-1 pl-1 animate-fade-in">
          {regularTools.map(renderTool)}
        </div>
      )}
    </div>
  );
}
