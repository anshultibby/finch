import React, { useEffect, useRef, useState, useMemo } from 'react';

type PanelMode = 'terminal' | 'file';

interface ComputerPanelProps {
  mode: PanelMode;
  // Terminal mode props
  command?: string;
  output?: string;
  isError?: boolean;
  // File mode props  
  filename?: string;
  fileContent?: string;
  fileType?: string;
  // Common props
  isStreaming: boolean;
  onClose: () => void;
}

// Syntax highlighting for code files
const highlightCode = (code: string, language: string): React.ReactNode[] => {
  const lines = code.split('\n');
  
  return lines.map((line, lineIndex) => {
    const tokens: React.ReactNode[] = [];
    let remaining = line;
    let keyIndex = 0;
    
    // Process the line character by character with regex patterns
    while (remaining.length > 0) {
      let matched = false;
      
      // Comments (Python # and // style)
      const commentMatch = remaining.match(/^(#.*|\/\/.*)$/);
      if (commentMatch) {
        tokens.push(<span key={keyIndex++} className="text-gray-400 italic">{commentMatch[0]}</span>);
        remaining = '';
        matched = true;
      }
      
      // Multi-line string start (""" or ''') - simplified for single line
      if (!matched) {
        const tripleQuoteMatch = remaining.match(/^("""|''')/);
        if (tripleQuoteMatch) {
          // Just highlight triple quotes as string start
          tokens.push(<span key={keyIndex++} className="text-amber-600">{remaining}</span>);
          remaining = '';
          matched = true;
        }
      }
      
      // Strings (double or single quoted)
      if (!matched) {
        const stringMatch = remaining.match(/^("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/);
        if (stringMatch) {
          tokens.push(<span key={keyIndex++} className="text-amber-600">{stringMatch[0]}</span>);
          remaining = remaining.slice(stringMatch[0].length);
          matched = true;
        }
      }
      
      // f-strings
      if (!matched) {
        const fstringMatch = remaining.match(/^(f"(?:[^"\\]|\\.)*"|f'(?:[^'\\]|\\.)*')/);
        if (fstringMatch) {
          tokens.push(<span key={keyIndex++} className="text-amber-600">{fstringMatch[0]}</span>);
          remaining = remaining.slice(fstringMatch[0].length);
          matched = true;
        }
      }
      
      // Python keywords
      if (!matched) {
        const keywordMatch = remaining.match(/^(def|class|import|from|as|if|elif|else|for|while|try|except|finally|with|return|yield|raise|pass|break|continue|and|or|not|in|is|None|True|False|self|async|await|lambda)\b/);
        if (keywordMatch) {
          tokens.push(<span key={keyIndex++} className="text-purple-600 font-medium">{keywordMatch[0]}</span>);
          remaining = remaining.slice(keywordMatch[0].length);
          matched = true;
        }
      }
      
      // JavaScript/TypeScript keywords
      if (!matched && (language === 'javascript' || language === 'typescript')) {
        const jsKeywordMatch = remaining.match(/^(const|let|var|function|return|if|else|for|while|switch|case|break|continue|try|catch|finally|throw|new|this|class|extends|import|export|default|async|await|null|undefined|true|false)\b/);
        if (jsKeywordMatch) {
          tokens.push(<span key={keyIndex++} className="text-purple-600 font-medium">{jsKeywordMatch[0]}</span>);
          remaining = remaining.slice(jsKeywordMatch[0].length);
          matched = true;
        }
      }
      
      // Built-in functions
      if (!matched) {
        const builtinMatch = remaining.match(/^(print|len|range|str|int|float|list|dict|set|tuple|open|type|isinstance|hasattr|getattr|setattr|enumerate|zip|map|filter|sorted|reversed|sum|min|max|abs|round|input)\b/);
        if (builtinMatch) {
          tokens.push(<span key={keyIndex++} className="text-cyan-600">{builtinMatch[0]}</span>);
          remaining = remaining.slice(builtinMatch[0].length);
          matched = true;
        }
      }
      
      // Numbers
      if (!matched) {
        const numberMatch = remaining.match(/^(\d+\.?\d*|\.\d+)/);
        if (numberMatch) {
          tokens.push(<span key={keyIndex++} className="text-blue-600">{numberMatch[0]}</span>);
          remaining = remaining.slice(numberMatch[0].length);
          matched = true;
        }
      }
      
      // Function/method calls
      if (!matched) {
        const funcMatch = remaining.match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()/);
        if (funcMatch) {
          tokens.push(<span key={keyIndex++} className="text-blue-700">{funcMatch[1]}</span>);
          remaining = remaining.slice(funcMatch[1].length);
          matched = true;
        }
      }
      
      // Decorators
      if (!matched) {
        const decoratorMatch = remaining.match(/^(@[a-zA-Z_][a-zA-Z0-9_]*)/);
        if (decoratorMatch) {
          tokens.push(<span key={keyIndex++} className="text-yellow-600">{decoratorMatch[0]}</span>);
          remaining = remaining.slice(decoratorMatch[0].length);
          matched = true;
        }
      }
      
      // Operators
      if (!matched) {
        const operatorMatch = remaining.match(/^(=>|->|==|!=|<=|>=|&&|\|\||[+\-*/%=<>!&|^~])/);
        if (operatorMatch) {
          tokens.push(<span key={keyIndex++} className="text-rose-600">{operatorMatch[0]}</span>);
          remaining = remaining.slice(operatorMatch[0].length);
          matched = true;
        }
      }
      
      // Default: take one character
      if (!matched) {
        tokens.push(<span key={keyIndex++} className="text-gray-700">{remaining[0]}</span>);
        remaining = remaining.slice(1);
      }
    }
    
    return (
      <div key={lineIndex} className="min-h-[1.6em]">
        {tokens.length > 0 ? tokens : ' '}
      </div>
    );
  });
};

// Get language from filename or fileType
const getLanguage = (filename?: string, fileType?: string): string => {
  if (fileType === 'python' || filename?.endsWith('.py')) return 'python';
  if (fileType === 'javascript' || filename?.endsWith('.js')) return 'javascript';
  if (fileType === 'typescript' || filename?.endsWith('.ts') || filename?.endsWith('.tsx')) return 'typescript';
  if (fileType === 'json' || filename?.endsWith('.json')) return 'json';
  if (fileType === 'markdown' || filename?.endsWith('.md')) return 'markdown';
  if (fileType === 'csv' || filename?.endsWith('.csv')) return 'csv';
  return 'text';
};

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

  return <span className="text-gray-700">{line}</span>;
};

export default function ComputerPanel({ 
  mode,
  command,
  output = '',
  isError = false,
  filename,
  fileContent = '',
  fileType,
  isStreaming, 
  onClose 
}: ComputerPanelProps) {
  const contentRef = useRef<HTMLPreElement>(null);
  const [isAutoScroll, setIsAutoScroll] = useState(true);

  const content = mode === 'terminal' ? output : fileContent;
  const lines = content ? content.split('\n') : [];
  const hasContent = content && content.trim().length > 0;
  const detectError = mode === 'terminal' && (isError || output?.toLowerCase().includes('error') || output?.toLowerCase().includes('traceback'));

  useEffect(() => {
    if (isAutoScroll && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [content, isAutoScroll]);

  const handleScroll = () => {
    if (contentRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = contentRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
      setIsAutoScroll(isNearBottom);
    }
  };

  // Get icon and title based on mode
  const getIcon = () => {
    if (mode === 'file') {
      return (
        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <polyline points="14,2 14,8 20,8" />
        </svg>
      );
    }
    return (
      <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    );
  };

  const getTitle = () => {
    if (mode === 'file' && filename) {
      return filename;
    }
    return command || 'Terminal';
  };

  const getSubtitle = () => {
    if (mode === 'file') {
      return isStreaming ? 'Writing file...' : 'File';
    }
    return isStreaming ? 'Running...' : 'Executed';
  };

  const getStatusBadge = () => {
    if (isStreaming) {
      return (
        <span className="flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full font-medium">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          {mode === 'file' ? 'Writing' : 'Running'}
        </span>
      );
    }
    if (detectError) {
      return (
        <span className="flex items-center gap-1.5 text-xs text-red-600 bg-red-50 border border-red-200 px-2.5 py-1 rounded-full font-medium">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Error
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 text-xs text-gray-500 bg-gray-100 border border-gray-200 px-2.5 py-1 rounded-full font-medium">
        <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M5 13l4 4L19 7" />
        </svg>
        {mode === 'file' ? 'Saved' : 'Done'}
      </span>
    );
  };

  // Memoize syntax highlighting for performance
  const language = useMemo(() => getLanguage(filename, fileType), [filename, fileType]);
  const highlightedCode = useMemo(() => {
    if (mode === 'file' && hasContent && (language === 'python' || language === 'javascript' || language === 'typescript')) {
      return highlightCode(content, language);
    }
    return null;
  }, [mode, content, language, hasContent]);

  const renderContent = () => {
    if (!hasContent) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
          {isStreaming ? (
            <>
              <div className="relative">
                <div className="w-10 h-10 rounded-full border-2 border-gray-200 border-t-emerald-500 animate-spin" />
              </div>
              <span className="text-sm">{mode === 'file' ? 'Writing file...' : 'Waiting for output...'}</span>
            </>
          ) : (
            <>
              {getIcon()}
              <span className="text-sm">{mode === 'file' ? 'Empty file' : 'No output'}</span>
            </>
          )}
        </div>
      );
    }

    if (mode === 'terminal') {
      return lines.map((line, i) => (
        <div key={i} className="min-h-[1.6em]">
          {formatTerminalLine(line, detectError)}
        </div>
      ));
    }

    // File mode with syntax highlighting
    if (highlightedCode) {
      return <code>{highlightedCode}</code>;
    }

    // File mode - plain display for non-code files
    return <code className="text-gray-700">{content}</code>;
  };

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
            <div className={`w-5 h-5 rounded flex items-center justify-center ${
              mode === 'file' 
                ? 'bg-gradient-to-br from-blue-500 to-indigo-600' 
                : 'bg-gradient-to-br from-emerald-500 to-teal-600'
            }`}>
              {getIcon()}
            </div>
            <span className="text-sm text-gray-800 font-semibold">Finch Computer</span>
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-3">
          {getStatusBadge()}
        </div>
      </div>

      {/* Info bar */}
      <div className="px-4 py-2 bg-gray-50/50 border-b border-gray-100 flex items-center gap-2">
        {mode === 'file' ? (
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14,2 14,8 20,8" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
            <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        )}
        <span className="text-xs text-gray-500 font-medium">{getSubtitle()}</span>
        <span className="text-xs text-gray-700 font-mono truncate flex-1">{getTitle()}</span>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-hidden relative bg-white">
        <pre 
          ref={contentRef}
          onScroll={handleScroll}
          className="h-full p-4 text-[13px] font-mono overflow-y-auto whitespace-pre-wrap break-words leading-[1.6] scrollbar-thin"
          style={{ fontFamily: "'JetBrains Mono', 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace" }}
        >
          {renderContent()}
        </pre>

        {/* Gradient fade at bottom when scrollable */}
        {hasContent && (
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent pointer-events-none" />
        )}
      </div>
      
      {/* Footer */}
      <div className="px-4 py-2.5 bg-gray-50 border-t border-gray-200 flex items-center justify-end">
        {/* Live indicator */}
        {isStreaming && (
          <span className="flex items-center gap-1.5 text-xs text-gray-500 mr-3">
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
  );
}

