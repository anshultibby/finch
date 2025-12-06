import React, { useState } from 'react';
import { ToolCallStatus } from '@/lib/api';

interface ToolCallGroupProps {
  toolCalls: ToolCallStatus[];
  timestamp?: string;
}

export default function ToolCallGroup({ toolCalls, timestamp }: ToolCallGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  return (
    <div className="my-3 border border-gray-200 rounded-lg bg-gray-50 overflow-hidden">
      {/* Header - Collapsible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-sm font-medium text-gray-700">
            {toolCalls.length} tool{toolCalls.length > 1 ? 's' : ''} executed
          </span>
        </div>
        {timestamp && (
          <span className="text-xs text-gray-500">
            {new Date(timestamp).toLocaleTimeString()}
          </span>
        )}
      </button>

      {/* Tool List - Collapsible */}
      {isExpanded && (
        <div className="px-4 py-2 space-y-2 border-t border-gray-200">
          {toolCalls.map((toolCall) => {
            const isCompleted = toolCall.status === 'completed';
            const isError = toolCall.status === 'error';
            const isInProgress = toolCall.status === 'calling';

            return (
              <div
                key={toolCall.tool_call_id}
                className="flex items-start gap-2 text-sm"
              >
                {/* Bullet - Hollow for in-progress, Filled for completed */}
                <div className="mt-0.5 flex-shrink-0">
                  {isInProgress && (
                    <div className="w-4 h-4 rounded-full border-2 border-blue-500 animate-pulse" />
                  )}
                  {isCompleted && (
                    <div className="w-4 h-4 rounded-full bg-green-500" />
                  )}
                  {isError && (
                    <div className="w-4 h-4 rounded-full bg-red-500" />
                  )}
                </div>

                {/* Tool Description */}
                <div className="flex-1 min-w-0">
                  <div className={`${isCompleted ? 'text-gray-600' : 'text-gray-900'}`}>
                    {toolCall.statusMessage || toolCall.tool_name}
                  </div>
                  
                  {/* Show result summary if completed */}
                  {isCompleted && toolCall.result_summary && (
                    <div className="text-xs text-gray-500 mt-0.5">
                      {toolCall.result_summary}
                    </div>
                  )}
                  
                  {/* Show error if failed */}
                  {isError && toolCall.error && (
                    <div className="text-xs text-red-600 mt-0.5">
                      Error: {toolCall.error}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

