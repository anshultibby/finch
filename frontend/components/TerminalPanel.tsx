import React, { useEffect, useRef, useState } from 'react';

interface TerminalPanelProps {
  title: string;
  output: string;
  isStreaming: boolean;
  isError?: boolean;
  command?: string;
  onClose: () => void;
}

// Parse terminal output to add syntax highlighting (light theme)
const formatTerminalLine = (line: string, isError: boolean) => {
  // Color prompt patterns (user@host:path$)
  const promptMatch = line.match(/^(\w+@[\w-]+:[~\/\w.-]+)\s*\$\s*(.*)$/);
  if (promptMatch) {
    return (
      <>
        <span className="text-emerald-600">{promptMatch[1]}</span>
        <span className="text-gray-400"> $ </span>
        <span className="text-amber-700">{promptMatch[2]}</span>
      </>
    );
  }

  // Color command indicator (> command)
  const cmdMatch = line.match(/^(>\s*)(.+)$/);
  if (cmdMatch) {
    return (
      <>
        <span className="text-emerald-600">{cmdMatch[1]}</span>
        <span className="text-gray-900 font-medium">{cmdMatch[2]}</span>
      </>
    );
  }

  // Success indicators
  if (line.includes('[✓]') || line.includes('✓') || line.toLowerCase().includes('success')) {
    return <span className="text-emerald-600">{line}</span>;
  }

  // Error/warning patterns
  if (isError || line.toLowerCase().includes('error') || line.toLowerCase().includes('failed') || line.toLowerCase().includes('exception')) {
    return <span className="text-red-600">{line}</span>;
  }
  if (line.toLowerCase().includes('warning')) {
    return <span className="text-amber-600">{line}</span>;
  }

  // File paths and URLs
  if (line.match(/^[\s]*[\/~][\w\/.-]+/) || line.includes('http')) {
    return <span className="text-blue-600">{line}</span>;
  }

  // Table headers or emphasized text
  if (line.match(/^\s*[\w\s]+\s+\d+\s+columns?/i)) {
    return <span className="text-cyan-600">{line}</span>;
  }

  return <span className="text-gray-700">{line}</span>;
};

export default function TerminalPanel({ title, output, isStreaming, isError = false, command, onClose }: TerminalPanelProps) {
  const outputRef = useRef<HTMLPreElement>(null);
  const [isAutoScroll, setIsAutoScroll] = useState(true);

  useEffect(() => {
    if (isAutoScroll && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output, isAutoScroll]);

  const handleScroll = () => {
    if (outputRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = outputRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
      setIsAutoScroll(isNearBottom);
    }
  };

  const jumpToLive = () => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
      setIsAutoScroll(true);
    }
  };

  const lines = output ? output.split('\n') : [];
  const hasContent = output && output.trim().length > 0;
  const detectError = isError || output?.toLowerCase().includes('error') || output?.toLowerCase().includes('traceback');

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-3">
          {/* Window controls */}
          <div className="flex items-center gap-1.5">
            <button 
              onClick={onClose}
              className="w-3 h-3 rounded-full bg-[#ff5f57] hover:bg-[#ff3b30] transition-colors group relative"
              title="Close"
            >
              <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 text-[8px] text-black font-bold">×</span>
            </button>
            <div className="w-3 h-3 rounded-full bg-[#febc2e] hover:bg-[#f5a623] transition-colors cursor-default" />
            <div className="w-3 h-3 rounded-full bg-[#28c840] hover:bg-[#1db954] transition-colors cursor-default" />
          </div>
          
          {/* Title */}
          <div className="flex items-center gap-2 ml-3">
            <div className="w-5 h-5 rounded bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="text-sm text-gray-800 font-semibold">Finch Computer</span>
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-3">
          {/* Status indicator */}
          {isStreaming ? (
            <span className="flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full font-medium">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              Running
            </span>
          ) : detectError ? (
            <span className="flex items-center gap-1.5 text-xs text-red-600 bg-red-50 border border-red-200 px-2.5 py-1 rounded-full font-medium">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Error
            </span>
          ) : hasContent ? (
            <span className="flex items-center gap-1.5 text-xs text-gray-500 bg-gray-100 border border-gray-200 px-2.5 py-1 rounded-full font-medium">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M5 13l4 4L19 7" />
              </svg>
              Done
            </span>
          ) : null}
        </div>
      </div>

      {/* Command/title bar */}
      <div className="px-4 py-2 bg-gray-50/50 border-b border-gray-100 flex items-center gap-2">
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span className="text-xs text-gray-500 font-medium">Executing:</span>
        <span className="text-xs text-gray-700 font-mono truncate flex-1">{command || title}</span>
      </div>
      
      {/* Terminal content */}
      <div className="flex-1 overflow-hidden relative bg-white">
        <pre 
          ref={outputRef}
          onScroll={handleScroll}
          className="h-full p-4 text-[13px] font-mono overflow-y-auto whitespace-pre-wrap break-words leading-[1.6] scrollbar-thin"
          style={{ fontFamily: "'JetBrains Mono', 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace" }}
        >
          {hasContent ? (
            lines.map((line, i) => (
              <div key={i} className="min-h-[1.6em]">
                {formatTerminalLine(line, detectError)}
              </div>
            ))
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
              {isStreaming ? (
                <>
                  <div className="relative">
                    <div className="w-10 h-10 rounded-full border-2 border-gray-200 border-t-emerald-500 animate-spin" />
                  </div>
                  <span className="text-sm">Waiting for output...</span>
                </>
              ) : (
                <>
                  <svg className="w-10 h-10 text-gray-300" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
                    <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <span className="text-sm">No output</span>
                </>
              )}
            </div>
          )}
        </pre>

        {/* Gradient fade at bottom when scrollable */}
        {hasContent && (
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent pointer-events-none" />
        )}
      </div>
      
      {/* Footer */}
      <div className="px-4 py-2.5 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Progress bar / Timeline */}
          <div className="flex items-center gap-2">
            <div className="w-24 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-300 ${
                  isStreaming ? 'bg-emerald-500 animate-pulse' : detectError ? 'bg-red-500' : 'bg-blue-500'
                }`}
                style={{ width: isStreaming ? '60%' : '100%' }}
              />
            </div>
            {isStreaming && (
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Jump to live button */}
          {!isAutoScroll && isStreaming && (
            <button
              onClick={jumpToLive}
              className="flex items-center gap-1.5 text-xs text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3 py-1.5 rounded-full font-medium transition-all"
            >
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
              Jump to live
            </button>
          )}

          {/* Live indicator */}
          {isStreaming && (
            <span className="flex items-center gap-1.5 text-xs text-gray-500">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              live
            </span>
          )}

          {/* Line count */}
          <span className="text-xs text-gray-400 tabular-nums">
            {lines.length} {lines.length === 1 ? 'line' : 'lines'}
          </span>
        </div>
      </div>
    </div>
  );
}
