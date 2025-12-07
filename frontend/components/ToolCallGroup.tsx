import React, { useState } from 'react';
import { ToolCallStatus } from '@/lib/api';

interface ToolCallGroupProps {
  toolCalls: ToolCallStatus[];
}

// Map tool names to display info
const getToolDisplay = (toolName: string): { icon: React.ReactNode; verb: string } => {
  const iconClass = "w-3.5 h-3.5";
  
  switch (toolName) {
    case 'web_search':
    case 'search':
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>,
        verb: 'Searching'
      };
    case 'browse_url':
    case 'browser':
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>,
        verb: 'Browsing'
      };
    case 'write_chat_file':
    case 'create_file':
    case 'write_file':
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.375 2.625a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4Z"/></svg>,
        verb: 'Writing'
      };
    case 'edit_file':
    case 'update_file':
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.375 2.625a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4Z"/></svg>,
        verb: 'Editing'
      };
    case 'execute_code':
    case 'run_python':
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>,
        verb: 'Running'
      };
    case 'screen_stocks':
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>,
        verb: 'Screening'
      };
    case 'backtest_portfolio':
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
        verb: 'Backtesting'
      };
    case 'build_custom_etf':
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>,
        verb: 'Building ETF'
      };
    default:
      return {
        icon: <svg className={iconClass} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>,
        verb: 'Using'
      };
  }
};

export default function ToolCallGroup({ toolCalls }: ToolCallGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  
  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  const allComplete = toolCalls.every(t => t.status === 'completed' || t.status === 'error');
  const hasError = toolCalls.some(t => t.status === 'error');
  const runningCount = toolCalls.filter(t => t.status === 'calling').length;
  const isRunning = runningCount > 0;

  // Generate summary text
  const getSummary = () => {
    if (hasError) return 'Error occurred';
    if (allComplete) return `Completed ${toolCalls.length} action${toolCalls.length > 1 ? 's' : ''}`;
    if (isRunning) return `Running ${runningCount} action${runningCount > 1 ? 's' : ''}...`;
    return `${toolCalls.length} action${toolCalls.length > 1 ? 's' : ''}`;
  };

  return (
    <div 
      className={`border rounded-md my-1 transition-all ${
        isRunning 
          ? 'border-blue-200 bg-blue-50/50' 
          : hasError
          ? 'border-red-200 bg-red-50/30'
          : 'border-gray-200 bg-gray-50/50'
      }`}
      style={isRunning ? { animation: 'pulse 2s ease-in-out infinite' } : undefined}
    >
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-1.5 px-2.5 py-1.5 text-left hover:bg-gray-100/50 rounded-md transition-colors"
      >
        {/* Status indicator */}
        {allComplete ? (
          <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        ) : hasError ? (
          <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        
        <span className="flex-1 text-sm font-medium text-gray-700">{getSummary()}</span>
        
        {/* Chevron */}
        <svg 
          className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <div className="px-2.5 pb-1.5 space-y-0.5">
          {toolCalls.map((tool) => {
            const display = getToolDisplay(tool.tool_name);
            const description = tool.statusMessage || tool.tool_name;
            
            return (
              <div
                key={tool.tool_call_id}
                className="flex items-center gap-1.5 px-1.5 py-1 rounded bg-white/60 border border-gray-100 text-xs"
              >
                <span className="text-gray-400 flex-shrink-0">{display.icon}</span>
                <span className="font-medium text-gray-600 flex-shrink-0">{display.verb}</span>
                <span className="text-gray-500">{description}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
