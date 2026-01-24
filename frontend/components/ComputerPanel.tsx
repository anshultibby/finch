import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import FileTree, { FileItem } from './FileTree';
import type { SearchResults, SearchResult } from '@/lib/types';

type PanelMode = 'terminal' | 'file' | 'search';

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
  chatId?: string; // For loading file tree
  onFileSelect?: (filename: string) => void; // Callback when user selects a different file
  cachedFiles?: FileItem[]; // Cached file list for instant display
  onFilesLoaded?: (files: FileItem[]) => void; // Callback when files are loaded
  // Search mode props
  searchResults?: SearchResults;
  // Edit/diff props
  isEditOperation?: boolean; // True for replace_in_chat_file
  oldStr?: string; // Original text for diff
  newStr?: string; // New text for diff
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

// Generate a simple diff view from old_str and new_str
const generateDiffView = (oldStr: string, newStr: string): React.ReactNode[] => {
  const oldLines = oldStr.split('\n');
  const newLines = newStr.split('\n');
  const result: React.ReactNode[] = [];
  
  // Show removed lines (red)
  oldLines.forEach((line, i) => {
    result.push(
      <div key={`old-${i}`} className="min-h-[1.6em] bg-red-50 border-l-2 border-red-400 pl-2 -ml-2">
        <span className="text-red-600 font-medium select-none mr-2">−</span>
        <span className="text-red-700">{line || ' '}</span>
      </div>
    );
  });
  
  // Show added lines (green)
  newLines.forEach((line, i) => {
    result.push(
      <div key={`new-${i}`} className="min-h-[1.6em] bg-green-50 border-l-2 border-green-400 pl-2 -ml-2">
        <span className="text-green-600 font-medium select-none mr-2">+</span>
        <span className="text-green-700">{line || ' '}</span>
      </div>
    );
  });
  
  return result;
};

// Check if file is an image
const isImageFile = (filename?: string): boolean => {
  if (!filename) return false;
  return /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(filename);
};

// Get image MIME type from filename
const getImageMimeType = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || 'png';
  if (ext === 'svg') return 'image/svg+xml';
  if (ext === 'jpg') return 'image/jpeg';
  return `image/${ext}`;
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

// Extract domain from URL for favicon
const getDomain = (url: string): string => {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname;
  } catch {
    return '';
  }
};

// Get favicon URL for a domain
const getFaviconUrl = (url: string): string => {
  const domain = getDomain(url);
  if (!domain) return '';
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
};

// Search result item component
const SearchResultItem = ({ result, index }: { result: SearchResult; index: number }) => {
  const domain = getDomain(result.link);
  const faviconUrl = getFaviconUrl(result.link);
  
  return (
    <a 
      href={result.link}
      target="_blank"
      rel="noopener noreferrer"
      className="block px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors group"
    >
      <div className="flex items-start gap-3">
        {/* Favicon */}
        <div className="flex-shrink-0 w-6 h-6 mt-0.5 rounded-md bg-gray-100 flex items-center justify-center overflow-hidden">
          {faviconUrl ? (
            <img 
              src={faviconUrl} 
              alt="" 
              className="w-4 h-4"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          ) : (
            <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10"/>
              <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
            </svg>
          )}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className="text-sm font-medium text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-2">
            {result.title}
          </h3>
          
          {/* Snippet */}
          <p className="text-xs text-gray-500 mt-1 line-clamp-2">
            {result.snippet}
          </p>
          
          {/* Meta info */}
          <div className="flex items-center gap-2 mt-1.5 text-xs text-gray-400">
            <span className="truncate max-w-[200px]">{domain}</span>
            {result.date && (
              <>
                <span>•</span>
                <span>{result.date}</span>
              </>
            )}
            {result.source && (
              <>
                <span>•</span>
                <span className="text-gray-500">{result.source}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </a>
  );
};

export default function ComputerPanel({ 
  mode,
  command,
  output = '',
  isError = false,
  filename,
  fileContent = '',
  fileType,
  chatId,
  onFileSelect,
  cachedFiles,
  onFilesLoaded,
  searchResults,
  isEditOperation = false,
  oldStr,
  newStr,
  isStreaming, 
  onClose 
}: ComputerPanelProps) {
  const contentRef = useRef<HTMLPreElement>(null);
  const searchContentRef = useRef<HTMLDivElement>(null);
  const [isAutoScroll, setIsAutoScroll] = useState(true);

  const content = mode === 'terminal' ? output : fileContent;
  const lines = content ? content.split('\n') : [];
  const hasContent = mode === 'search' 
    ? (searchResults?.results && searchResults.results.length > 0)
    : (content && content.trim().length > 0);
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
    if (mode === 'search') {
      return (
        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
      );
    }
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
    if (mode === 'search' && searchResults?.query) {
      return searchResults.query;
    }
    if (mode === 'file' && filename) {
      return filename;
    }
    return command || 'Terminal';
  };

  const getSubtitle = () => {
    if (mode === 'search') {
      return isStreaming ? 'Searching...' : 'Search';
    }
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
          {mode === 'search' ? 'Searching' : mode === 'file' ? 'Writing' : 'Running'}
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
        {mode === 'search' ? 'Done' : mode === 'file' ? 'Saved' : 'Done'}
      </span>
    );
  };

  const getIconBgColor = () => {
    if (mode === 'search') {
      return 'bg-gradient-to-br from-violet-500 to-purple-600';
    }
    if (mode === 'file') {
      return 'bg-gradient-to-br from-blue-500 to-indigo-600';
    }
    return 'bg-gradient-to-br from-emerald-500 to-teal-600';
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
    // Search mode
    if (mode === 'search') {
      if (!searchResults?.results || searchResults.results.length === 0) {
        return (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
            {isStreaming ? (
              <>
                <div className="relative">
                  <div className="w-10 h-10 rounded-full border-2 border-gray-200 border-t-violet-500 animate-spin" />
                </div>
                <span className="text-sm">Searching the web...</span>
              </>
            ) : (
              <>
                <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
                <span className="text-sm">No results found</span>
              </>
            )}
          </div>
        );
      }

      return (
        <div ref={searchContentRef} className="h-full overflow-y-auto">
          {/* Answer box if available */}
          {searchResults.answerBox && (
            <div className="mx-4 mt-4 mb-2 p-4 bg-violet-50 border border-violet-200 rounded-lg">
              {searchResults.answerBox.title && (
                <h4 className="text-sm font-semibold text-violet-900 mb-1">
                  {searchResults.answerBox.title}
                </h4>
              )}
              {searchResults.answerBox.answer && (
                <p className="text-sm text-violet-800">
                  {searchResults.answerBox.answer}
                </p>
              )}
              {searchResults.answerBox.snippet && !searchResults.answerBox.answer && (
                <p className="text-sm text-violet-700">
                  {searchResults.answerBox.snippet}
                </p>
              )}
            </div>
          )}
          
          {/* Knowledge graph if available */}
          {searchResults.knowledgeGraph && (
            <div className="mx-4 mt-4 mb-2 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-3">
                {searchResults.knowledgeGraph.imageUrl && (
                  <img 
                    src={searchResults.knowledgeGraph.imageUrl}
                    alt=""
                    className="w-16 h-16 rounded-lg object-cover"
                  />
                )}
                <div>
                  {searchResults.knowledgeGraph.title && (
                    <h4 className="text-sm font-semibold text-blue-900">
                      {searchResults.knowledgeGraph.title}
                    </h4>
                  )}
                  {searchResults.knowledgeGraph.type && (
                    <p className="text-xs text-blue-600 mt-0.5">
                      {searchResults.knowledgeGraph.type}
                    </p>
                  )}
                  {searchResults.knowledgeGraph.description && (
                    <p className="text-sm text-blue-800 mt-1 line-clamp-3">
                      {searchResults.knowledgeGraph.description}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {/* Results list */}
          <div className="divide-y divide-gray-100">
            {searchResults.results.map((result, index) => (
              <SearchResultItem key={index} result={result} index={index} />
            ))}
          </div>
        </div>
      );
    }

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

    // File mode - check if it's an image
    // Also verify fileType is not 'text' (which indicates an error message, not actual image data)
    if (mode === 'file' && isImageFile(filename) && fileType !== 'text') {
      const mimeType = getImageMimeType(filename || '');
      const isSvg = filename?.toLowerCase().endsWith('.svg');
      // SVG content is text, other images are base64
      const imageSrc = isSvg
        ? `data:${mimeType};base64,${btoa(content)}`
        : `data:${mimeType};base64,${content}`;
      
      return (
        <div className="flex items-center justify-center h-full p-4">
          <img 
            src={imageSrc} 
            alt={filename || 'Image'}
            className="max-w-full max-h-full object-contain rounded-lg shadow-md border border-gray-200"
          />
        </div>
      );
    }

    // Edit operation - show diff view with old_str and new_str
    if (mode === 'file' && isEditOperation && oldStr && newStr) {
      return <code>{generateDiffView(oldStr, newStr)}</code>;
    }

    // File mode with syntax highlighting
    if (highlightedCode) {
      return <code>{highlightedCode}</code>;
    }

    // File mode - plain display for non-code files
    return <code className="text-gray-700">{content}</code>;
  };

  const getFooterInfo = () => {
    if (mode === 'search') {
      const count = searchResults?.results?.length || 0;
      return `${count} ${count === 1 ? 'result' : 'results'}`;
    }
    return `${lines.length} ${lines.length === 1 ? 'line' : 'lines'}`;
  };

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 sm:py-3 bg-gray-50 border-b border-gray-200 safe-area-top">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          {/* Window controls - desktop only */}
          <div className="hidden md:flex items-center gap-1.5 flex-shrink-0">
            <button 
              onClick={onClose}
              className="w-3 h-3 rounded-full bg-[#ff5f57] hover:bg-[#ff3b30] active:bg-[#ff1f17] transition-colors group relative touch-manipulation"
              title="Close"
            >
              <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 text-[8px] text-black font-bold">×</span>
            </button>
            <div className="w-3 h-3 rounded-full bg-[#febc2e] hover:bg-[#f5a623] transition-colors cursor-default" />
            <div className="w-3 h-3 rounded-full bg-[#28c840] hover:bg-[#1db954] transition-colors cursor-default" />
          </div>
          
          {/* Title */}
          <div className="flex items-center gap-1.5 sm:gap-2 md:ml-3 min-w-0">
            <div className={`w-4 h-4 sm:w-5 sm:h-5 rounded flex items-center justify-center flex-shrink-0 ${getIconBgColor()}`}>
              {getIcon()}
            </div>
            <span className="text-xs sm:text-sm text-gray-800 font-semibold truncate">Finch Computer</span>
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          {getStatusBadge()}
          {/* Mobile close button */}
          <button 
            onClick={onClose}
            className="md:hidden p-2 text-gray-500 hover:text-gray-700 active:text-gray-900 hover:bg-gray-100 active:bg-gray-200 rounded-lg transition-colors touch-manipulation"
            title="Close"
            style={{ minHeight: '36px', minWidth: '36px' }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Info bar - only show for terminal and search modes (file mode has its own tab) */}
      {mode !== 'file' && (
        <div className="px-3 sm:px-4 py-2 bg-gray-50/50 border-b border-gray-100 flex items-center gap-2 min-w-0">
          {mode === 'search' ? (
            <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          ) : (
            <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          )}
          <span className="text-[10px] sm:text-xs text-gray-500 font-medium flex-shrink-0">{getSubtitle()}</span>
          <span className="text-[10px] sm:text-xs text-gray-700 font-mono truncate flex-1 min-w-0">{getTitle()}</span>
        </div>
      )}
      
      {/* Content */}
      <div className="flex-1 overflow-hidden relative bg-white flex">
        {/* File tree sidebar - only show in file mode with chatId */}
        {mode === 'file' && chatId && (
          <FileTree
            chatId={chatId}
            selectedFile={filename}
            onFileSelect={(selectedFilename) => {
              if (onFileSelect && selectedFilename !== filename) {
                onFileSelect(selectedFilename);
              }
            }}
            cachedFiles={cachedFiles}
            onFilesLoaded={onFilesLoaded}
          />
        )}
        
        {/* Main content area */}
        <div className="flex-1 overflow-hidden relative flex flex-col">
          {/* File tab header - only for file mode */}
          {mode === 'file' && filename && (
            <div className="flex-shrink-0 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center">
                <div className="px-3 py-1.5 bg-white border-r border-gray-200 flex items-center gap-2">
                  <svg className="w-3.5 h-3.5 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <polyline points="14,2 14,8 20,8" />
                  </svg>
                  <span className="text-xs font-medium text-gray-700">{filename}</span>
                </div>
              </div>
            </div>
          )}
          
        {/* Content */}
        <div className="flex-1 overflow-hidden relative">
          {mode === 'search' ? (
            renderContent()
          ) : mode === 'file' && isImageFile(filename) && fileType !== 'text' ? (
            // Images need direct rendering without <pre> wrapper for proper sizing
            <div className="h-full overflow-auto">
              {renderContent()}
            </div>
          ) : (
            <pre 
              ref={contentRef}
              onScroll={handleScroll}
              className="h-full text-[13px] font-mono overflow-y-auto whitespace-pre-wrap break-words leading-[1.6] scrollbar-thin"
              style={{ fontFamily: "'JetBrains Mono', 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace" }}
            >
              <div className="p-4">
                {renderContent()}
              </div>
            </pre>
          )}

            {/* Gradient fade at bottom when scrollable */}
            {hasContent && mode !== 'search' && (
              <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent pointer-events-none" />
            )}
          </div>
        </div>
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

        {/* Count */}
        <span className="text-xs text-gray-400 tabular-nums">
          {getFooterInfo()}
        </span>
      </div>
    </div>
  );
}
