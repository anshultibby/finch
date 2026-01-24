import React from 'react';
import type { ToolCallStatus } from '@/lib/types';

interface ToolCallProps {
  toolCall: ToolCallStatus;
  onShowOutput?: () => void;
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
    case 'scrape_url':
      return (
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10"/>
          <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
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

const isScrapeOperation = (toolName: string) => {
  return toolName === 'scrape_url';
};

// Extract search query from arguments
const extractSearchQuery = (toolCall: ToolCallStatus): string | null => {
  if (toolCall.arguments?.query) {
    return toolCall.arguments.query;
  }
  return null;
};

// Extract URL from scrape_url arguments
const extractUrl = (toolCall: ToolCallStatus): string | null => {
  if (toolCall.arguments?.url) {
    return toolCall.arguments.url;
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
    'scrape_url': 'Scrape URL',
    'get_fmp_data': 'Get FMP Data',
    'get_reddit_trending_stocks': 'Get Reddit Trending',
    'get_reddit_ticker_sentiment': 'Get Reddit Sentiment',
    'delegate_execution': 'Task Executor',
    'finish_execution': 'Done',
  };
  
  return nameMap[toolName] || toolName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

export default function ToolCall({ toolCall, onShowOutput }: ToolCallProps) {
  const description = toolCall.statusMessage || '';
  const isError = toolCall.status === 'error' || !!toolCall.error;
  const styles = getStatusStyles(toolCall.status, isError);
  
  const toolName = getToolDisplayName(toolCall.tool_name);
  const isFile = isFileOperation(toolCall.tool_name);
  const isSearch = isSearchOperation(toolCall.tool_name);
  const isScrape = isScrapeOperation(toolCall.tool_name);
  const filename = isFile ? extractFilename(toolCall) : null;
  const searchQuery = isSearch ? extractSearchQuery(toolCall) : null;
  const url = isScrape ? extractUrl(toolCall) : null;
  
  // Truncate search query for display
  const displayQuery = searchQuery && searchQuery.length > 80 
    ? searchQuery.substring(0, 80) + '...' 
    : searchQuery;
  
  // Truncate URL for display
  const displayUrl = url && url.length > 50 
    ? url.substring(0, 50) + '...' 
    : url;
  return (
    <div 
      onClick={onShowOutput}
      className={`inline-flex items-center gap-2 py-2 px-3 rounded-lg cursor-pointer transition-all duration-150 whitespace-nowrap overflow-hidden touch-manipulation ${styles.container}`}
      style={{ minHeight: '44px' }}
    >
      {/* Icon - never shrink */}
      <span className={`flex-shrink-0 ${styles.icon}`}>
        {getToolIcon(toolCall.tool_name)}
      </span>
      
      {/* Tool name - never shrink */}
      <span className={`text-sm sm:text-sm font-medium flex-shrink-0 ${styles.text}`}>
        {toolName}
      </span>

      {/* Filename pill for file operations - can shrink, hide on very small screens */}
      {filename && (
        <span className={`hidden xs:inline-block text-xs font-mono px-1.5 py-0.5 rounded truncate min-w-0 ${styles.file}`}>
          {filename}
        </span>
      )}

      {/* Search query pill for search operations - hide on very small screens */}
      {displayQuery && (
        <span className={`hidden xs:inline-block text-xs px-1.5 py-0.5 rounded truncate min-w-0 ${styles.file}`}>
          {displayQuery}
        </span>
      )}

      {/* URL pill for scrape operations - hide on very small screens */}
      {displayUrl && (
        <span className={`hidden xs:inline-block text-xs font-mono px-1.5 py-0.5 rounded truncate min-w-0 ${styles.file}`}>
          {displayUrl}
        </span>
      )}

      {/* Description - show for all tools when available and not just the tool name */}
      {description && description !== toolCall.tool_name && !filename && !displayQuery && !displayUrl && (
        <span className={`hidden sm:inline text-sm ${styles.muted} truncate min-w-0`}>
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
