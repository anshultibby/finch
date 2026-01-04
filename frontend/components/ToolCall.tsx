import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ToolCallStatus } from '@/lib/api';

interface ToolCallProps {
  toolCall: ToolCallStatus;
  onShowOutput?: () => void;
  onNestedToolClick?: (tool: ToolCallStatus) => void;
}

const getToolIcon = (toolName: string) => {
  switch (toolName) {
    case 'execute_code':
    case 'run_python':
      return (
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    case 'web_search':
    case 'search':
      return (
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
      );
    case 'write_chat_file':
    case 'create_file':
    case 'write_file':
    case 'edit_file':
    case 'replace_in_chat_file':
    case 'read_chat_file':
      return (
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <polyline points="14,2 14,8 20,8" />
        </svg>
      );
    case 'delegate_execution':
      return (
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 00-3-3.87" />
          <path d="M16 3.13a4 4 0 010 7.75" />
        </svg>
      );
    case 'finish_execution':
      return (
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
          <polyline points="22,4 12,14.01 9,11.01" />
        </svg>
      );
    default:
      return (
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      );
  }
};

const isFileOperation = (toolName: string) => {
  return ['write_chat_file', 'create_file', 'write_file', 'edit_file', 'replace_in_chat_file', 'read_chat_file'].includes(toolName);
};

const isSearchOperation = (toolName: string) => {
  return ['web_search', 'news_search'].includes(toolName);
};

// Extract search query from arguments
const extractSearchQuery = (toolCall: ToolCallStatus): string | null => {
  if (toolCall.arguments?.query) {
    return toolCall.arguments.query;
  }
  return null;
};

// Extract filename from arguments or statusMessage
const extractFilename = (toolCall: ToolCallStatus): string | null => {
  // First try to get filename directly from arguments (most reliable)
  if (toolCall.arguments) {
    // Direct filename argument
    if (toolCall.arguments.filename) {
      const filename = toolCall.arguments.filename;
      // Get just the filename without path
      return filename.split('/').pop() || filename;
    }
    // For replace_in_chat_file, filename is inside params
    if (toolCall.arguments.params?.filename) {
      const filename = toolCall.arguments.params.filename;
      return filename.split('/').pop() || filename;
    }
  }
  
  // Fallback: try to extract from statusMessage
  const statusMessage = toolCall.statusMessage;
  if (!statusMessage) return null;
  
  const patterns = [
    /(?:Writing|Creating|Editing|Reading|Updating)\s+`?([^\s`]+\.\w+)`?/i,
    /(?:file|to)\s+`?([^\s`]+\.\w+)`?/i,
    /`([^\s`]+\.\w{1,5})`/,  // Match filename in backticks
    /([^\s\/]+\.\w{1,5})$/,  // Match filename at end
  ];
  
  for (const pattern of patterns) {
    const match = statusMessage.match(pattern);
    if (match) {
      const filename = match[1].split('/').pop() || match[1];
      return filename;
    }
  }
  
  return null;
};

const getStatusStyles = (status: string, isError: boolean) => {
  if (isError || status === 'error') {
    return {
      container: 'bg-red-50 border border-red-200 hover:border-red-300 hover:bg-red-100',
      icon: 'text-red-500',
      text: 'text-red-700',
      muted: 'text-red-500',
      file: 'bg-red-100 text-red-700'
    };
  }
  if (status === 'calling') {
    return {
      container: 'bg-amber-50 border border-amber-200 hover:border-amber-300 hover:bg-amber-100',
      icon: 'text-amber-500',
      text: 'text-amber-700',
      muted: 'text-amber-600',
      file: 'bg-amber-100 text-amber-700'
    };
  }
  return {
    container: 'bg-gray-50 border border-gray-200 hover:border-gray-300 hover:bg-gray-100',
    icon: 'text-gray-500',
    text: 'text-gray-700',
    muted: 'text-gray-500',
    file: 'bg-gray-100 text-gray-600'
  };
};

// Get a shorter display name for the tool
const getToolDisplayName = (toolName: string): string => {
  const nameMap: Record<string, string> = {
    'write_chat_file': 'Write File',
    'read_chat_file': 'Read File',
    'replace_in_chat_file': 'Edit File',
    'execute_code': 'Execute Code',
    'run_python': 'Run Python',
    'web_search': 'Search',
    'news_search': 'News Search',
    'get_fmp_data': 'Get FMP Data',
    'get_reddit_trending_stocks': 'Get Reddit Trending',
    'get_reddit_ticker_sentiment': 'Get Reddit Sentiment',
    'delegate_execution': 'Executor',
    'finish_execution': 'Done',
  };
  
  return nameMap[toolName] || toolName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

// Nested tool call component (compact row for inside delegation card)
function NestedToolCall({ tool, onClick }: { tool: ToolCallStatus; onClick?: () => void }) {
  const isError = tool.status === 'error' || !!tool.error;
  const isRunning = tool.status === 'calling';
  const toolName = getToolDisplayName(tool.tool_name);
  const isFile = isFileOperation(tool.tool_name);
  const isCode = tool.tool_name === 'execute_code' || tool.tool_name === 'run_python';
  const isSearch = isSearchOperation(tool.tool_name);
  const filename = isFile ? extractFilename(tool) : null;
  const searchQuery = isSearch ? extractSearchQuery(tool) : null;
  
  // Only show clickable style for tools that have viewable output
  const hasViewableOutput = isFile || isCode || isSearch;
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hasViewableOutput && onClick) {
      onClick();
    }
  };
  
  return (
    <div 
      onClick={handleClick}
      className={`flex items-center gap-2 py-1.5 px-3 text-xs border-l-2 transition-colors ${
        isError 
          ? 'border-l-red-300 bg-red-50/50' 
          : isRunning 
            ? 'border-l-blue-400 bg-blue-50/30' 
            : 'border-l-emerald-300 bg-white'
      } ${hasViewableOutput ? 'hover:bg-slate-100 cursor-pointer' : 'cursor-default'}`}
    >
      {/* Icon */}
      <span className={`flex-shrink-0 ${isError ? 'text-red-500' : isRunning ? 'text-blue-500' : 'text-slate-400'}`}>
        {getToolIcon(tool.tool_name)}
      </span>
      
      {/* Tool name */}
      <span className={`font-medium ${isError ? 'text-red-600' : isRunning ? 'text-blue-600' : 'text-slate-600'}`}>
        {toolName}
      </span>
      
      {/* Context: filename, query, or description */}
      {filename && (
        <code className="font-mono text-slate-500 bg-slate-100 px-1 rounded text-[11px]">{filename}</code>
      )}
      {searchQuery && (
        <span className="text-slate-500 truncate flex-1 min-w-0 italic">"{searchQuery}"</span>
      )}
      {!filename && !searchQuery && tool.statusMessage && tool.statusMessage !== tool.tool_name && (
        <span className="text-slate-400 truncate flex-1 min-w-0">{tool.statusMessage}</span>
      )}
      
      {/* Status indicator */}
      <span className="ml-auto flex-shrink-0">
        {isError ? (
          <span className="text-red-400 text-[10px]">failed</span>
        ) : isRunning ? (
          <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse block" />
        ) : hasViewableOutput ? (
          <svg className="w-3 h-3 text-slate-300" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M9 5l7 7-7 7" />
          </svg>
        ) : (
          <svg className="w-3 h-3 text-emerald-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M5 13l4 4L19 7" />
          </svg>
        )}
      </span>
    </div>
  );
}

export default function ToolCall({ toolCall, onShowOutput, onNestedToolClick }: ToolCallProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const description = toolCall.statusMessage || '';
  const isError = toolCall.status === 'error' || !!toolCall.error;
  const styles = getStatusStyles(toolCall.status, isError);
  
  const toolName = getToolDisplayName(toolCall.tool_name);
  const isFile = isFileOperation(toolCall.tool_name);
  const isSearch = isSearchOperation(toolCall.tool_name);
  const isDelegation = toolCall.tool_name === 'delegate_execution';
  const filename = isFile ? extractFilename(toolCall) : null;
  const searchQuery = isSearch ? extractSearchQuery(toolCall) : null;
  const nestedTools = toolCall.nestedTools || [];
  
  // Truncate search query for display
  const displayQuery = searchQuery && searchQuery.length > 80 
    ? searchQuery.substring(0, 80) + '...' 
    : searchQuery;

  // For delegation, render a card that groups all sub-agent activity
  if (isDelegation) {
    const completedCount = nestedTools.filter(t => t.status === 'completed').length;
    const totalCount = nestedTools.length;
    const runningCount = nestedTools.filter(t => t.status === 'calling').length;
    const isRunning = toolCall.status === 'calling';
    const isComplete = toolCall.status === 'completed';
    
    // Get the direction from arguments - this is the key info to show
    const direction = toolCall.arguments?.direction || toolCall.statusMessage || 'Working...';
    
    return (
      <div className={`rounded-lg overflow-hidden transition-all duration-300 border ${
        isError 
          ? 'bg-red-50/80 border-red-200' 
          : isRunning
            ? 'bg-slate-50/80 border-slate-200 shadow-sm'
            : 'bg-emerald-50/50 border-emerald-200'
      }`}>
        {/* Header - clickable to expand/collapse */}
        <div 
          onClick={() => setIsExpanded(!isExpanded)}
          className={`px-3 py-2.5 flex items-center gap-2 cursor-pointer transition-colors ${
            isError 
              ? 'hover:bg-red-100/50' 
              : isRunning 
                ? 'hover:bg-slate-100/50' 
                : 'hover:bg-emerald-100/50'
          }`}
        >
          {/* Status icon */}
          {isRunning ? (
            <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
            </div>
          ) : isError ? (
            <div className="w-5 h-5 flex items-center justify-center flex-shrink-0 text-red-500">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          ) : (
            <div className="w-5 h-5 flex items-center justify-center flex-shrink-0 text-emerald-500">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M5 13l4 4L19 7" />
              </svg>
            </div>
          )}
          
          {/* Direction text (truncated in header) */}
          <span className={`text-sm font-medium flex-1 min-w-0 truncate ${
            isError ? 'text-red-700' : isRunning ? 'text-slate-700' : 'text-emerald-700'
          }`}>
            {direction.split('\n')[0].substring(0, 60)}{direction.length > 60 ? '...' : ''}
          </span>
          
          {/* Progress indicator */}
          {totalCount > 0 && (
            <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 ${
              isError 
                ? 'bg-red-100 text-red-600' 
                : isRunning 
                  ? 'bg-blue-100 text-blue-600' 
                  : 'bg-emerald-100 text-emerald-600'
            }`}>
              {isRunning ? `${runningCount} running` : `${completedCount}/${totalCount}`}
            </span>
          )}
          
          {/* Expand chevron */}
          <svg 
            className={`w-4 h-4 flex-shrink-0 text-slate-400 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            viewBox="0 0 24 24"
          >
            <path d="M9 5l7 7-7 7" />
          </svg>
        </div>
        
        {/* Expanded content */}
        {isExpanded && (
          <>
            {/* Full direction text (if multi-line) */}
            {direction.includes('\n') && (
              <div className="px-3 pb-2 border-t border-slate-200/60">
                <div className={`text-sm leading-relaxed prose prose-sm max-w-none pt-2 ${
                  isError ? 'text-red-700' : 'text-slate-600'
                } [&_p]:m-0 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {direction}
                  </ReactMarkdown>
                </div>
              </div>
            )}
            
            {/* Thinking text - ephemeral streaming text from sub-agent */}
            {isRunning && toolCall.thinkingText && (
              <div className="px-3 py-2 border-t border-slate-200/60 bg-slate-50/50">
                <p className="text-xs text-slate-400 italic line-clamp-2">
                  {toolCall.thinkingText.length > 200 
                    ? '...' + toolCall.thinkingText.slice(-200) 
                    : toolCall.thinkingText}
                </p>
              </div>
            )}
            
            {/* Nested tools list */}
            {nestedTools.length > 0 && (
              <div className="border-t border-slate-200/60 divide-y divide-slate-100">
                {nestedTools.map((tool) => (
                  <NestedToolCall 
                    key={tool.tool_call_id} 
                    tool={tool}
                    onClick={() => onNestedToolClick?.(tool)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  // Standard tool call rendering
  return (
    <div 
      onClick={onShowOutput}
      className={`inline-flex items-center gap-2 py-1.5 px-3 rounded-lg cursor-pointer transition-all duration-150 whitespace-nowrap overflow-hidden ${styles.container}`}
    >
      {/* Icon - never shrink */}
      <span className={`flex-shrink-0 ${styles.icon}`}>
        {getToolIcon(toolCall.tool_name)}
      </span>
      
      {/* Tool name - never shrink */}
      <span className={`text-sm font-medium flex-shrink-0 ${styles.text}`}>
        {toolName}
      </span>

      {/* Filename pill for file operations - can shrink */}
      {filename && (
        <span className={`text-xs font-mono px-1.5 py-0.5 rounded truncate min-w-0 ${styles.file}`}>
          {filename}
        </span>
      )}

      {/* Search query pill for search operations */}
      {displayQuery && (
        <span className={`text-xs px-1.5 py-0.5 rounded truncate min-w-0 ${styles.file}`}>
          {displayQuery}
        </span>
      )}

      {/* Description - show for all tools when available and not just the tool name */}
      {description && description !== toolCall.tool_name && !filename && !displayQuery && (
        <span className={`text-sm ${styles.muted} truncate min-w-0`}>
          {description}
        </span>
      )}

      {/* Status indicator - never shrink */}
      <span className="flex-shrink-0 ml-auto">
        {isError ? (
          <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        ) : toolCall.status === 'calling' ? (
          <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse block" />
        ) : (
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M9 5l7 7-7 7" />
          </svg>
        )}
      </span>
    </div>
  );
}
