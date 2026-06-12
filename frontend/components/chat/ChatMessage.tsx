import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ToolCallSummary from './ToolCallSummary';
import { isImageFile, isCsvFile, isHtmlFile, getApiBaseUrl } from '@/lib/utils';
import { getAuthHeader } from '@/lib/api';
import type { ToolCallStatus } from '@/lib/types';
import type { TimeEstimate, ThoughtEntry } from '@/hooks/useChatStream';

export interface MessageAction {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  toolCalls?: ToolCallStatus[];
  thoughts?: ThoughtEntry[];
  chatId?: string;
  userId?: string;
  onSelectTool?: (tool: ToolCallStatus) => void;
  onFileClick?: (filename: string) => void;
  onVisualizationClick?: (filename: string) => void;
  onSendMessage?: (msg: string) => void;
  onPeekAgent?: (agentId: string, chatId: string, name: string) => void;
  onEditMessage?: (newContent: string) => void;
  onFeedback?: (type: 'like' | 'dislike', comment: string) => void;
  actions?: MessageAction[];
  isLastAssistantMessage?: boolean;
  isStreaming?: boolean;
  startTime?: number | null;
  timeEstimate?: TimeEstimate | null;
}

const getChatFileUrl = (chatId: string | undefined, filename: string): string => {
  if (!chatId) return '';
  if (filename.startsWith('/')) {
    return `${getApiBaseUrl()}/api/chat-files/${chatId}/sandbox-file?path=${encodeURIComponent(filename)}`;
  }
  return `${getApiBaseUrl()}/api/chat-files/${chatId}/download/${encodeURIComponent(filename)}`;
};

// SandboxImage — image with shimmer skeleton, fade-in, and error/retry
function SandboxImage({
  src,
  alt,
  onClick,
}: {
  src: string;
  alt: string;
  onClick?: () => void;
}) {
  const [status, setStatus] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [retryCount, setRetryCount] = useState(0);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const basename = alt || src.split('/').pop() || src;

  // Fetch image with auth header, convert to blob URL so <img> can render it
  // (browsers can't attach Authorization headers to plain <img src>).
  useEffect(() => {
    let cancelled = false;
    let createdUrl: string | null = null;
    setStatus('loading');
    setBlobUrl(null);

    (async () => {
      try {
        const authHeader = await getAuthHeader();
        const res = await fetch(src, { headers: authHeader });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        if (cancelled) return;
        createdUrl = URL.createObjectURL(blob);
        setBlobUrl(createdUrl);
      } catch {
        if (!cancelled) setStatus('error');
      }
    })();

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [src, retryCount]);

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-gray-100 bg-white shadow-sm max-w-full group/img relative">
      {/* Shimmer shown while loading */}
      {status === 'loading' && (
        <div className="animate-shimmer" style={{ height: 240 }} />
      )}

      {/* Error state */}
      {status === 'error' && (
        <div className="flex flex-col items-center justify-center gap-2 py-10 px-4 bg-gray-50">
          <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-xs text-gray-400 font-mono">{basename}</p>
          <button
            onClick={() => { setRetryCount(c => c + 1); setStatus('loading'); }}
            className="text-xs text-blue-500 hover:text-blue-700 underline underline-offset-2"
          >
            Retry
          </button>
        </div>
      )}

      {/* Actual image — hidden while loading/error, visible once loaded */}
      <img
        src={blobUrl || ''}
        alt={basename}
        className="max-w-full h-auto cursor-pointer transition-opacity duration-300 block"
        style={{
          maxHeight: 520,
          display: status === 'error' ? 'none' : 'block',
          opacity: status === 'loaded' ? 1 : 0,
        }}
        onLoad={() => setStatus('loaded')}
        onError={() => setStatus('error')}
        onClick={onClick}
      />

      {/* Hover overlay with expand icon */}
      {status === 'loaded' && (
        <div className="absolute bottom-0 right-0 p-2 opacity-0 group-hover/img:opacity-100 transition-opacity">
          <div className="bg-black/50 backdrop-blur-sm rounded-md p-1.5 cursor-pointer" onClick={onClick}>
            <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}

const CITE_BADGE_RE = /^\d+$/;

function extractCitations(md: string): Map<number, string> {
  const refs = new Map<number, string>();
  const linked = /\[\^(\d+)\]\((https?:\/\/[^)]+)\)/g;
  let m;
  while ((m = linked.exec(md)) !== null) {
    refs.set(parseInt(m[1]), m[2]);
  }
  const defs = /^\[\^(\d+)\]:\s*(https?:\/\/\S+)/gm;
  while ((m = defs.exec(md)) !== null) {
    if (!refs.has(parseInt(m[1]))) refs.set(parseInt(m[1]), m[2]);
  }
  return refs;
}

function preprocessCitations(md: string): string {
  // [^N](url) → a clickable badge link.
  let result = md.replace(/\[\^(\d+)\]\((https?:\/\/[^)]+)\)/g, (_m, n, url) =>
    `[${n}](${url})`
  );
  // Bare [^N] (no url) → a superscript badge that scrolls to the matching source,
  // instead of a digit glued onto the preceding word.
  result = result.replace(/\[\^(\d+)\](?![:(])/g, (_m, n) => `[${n}](#cite-${n})`);
  result = result.replace(/^\[\^\d+\]:.*$/gm, '');
  return result;
}

function citationDomain(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    return host;
  } catch { return url; }
}

function CitationReferences({ citations }: { citations: Map<number, string> }) {
  if (citations.size === 0) return null;
  const sorted = Array.from(citations.entries()).sort((a, b) => a[0] - b[0]);
  return (
    <div className="mt-3 pt-2 border-t border-gray-200">
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {sorted.map(([num, url]) => (
          <a
            key={num}
            id={`cite-${num}`}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 transition-colors group/ref scroll-mt-24"
          >
            <span className="inline-flex items-center justify-center w-4 h-4 text-[10px] font-semibold bg-blue-100 text-blue-700 rounded-full shrink-0">{num}</span>
            <span className="group-hover/ref:underline truncate max-w-[200px]">{citationDomain(url)}</span>
          </a>
        ))}
      </div>
    </div>
  );
}

// Custom ReactMarkdown components that route sandbox image paths through the API
const makeMarkdownComponents = (chatId: string | undefined, onFileClick?: (filename: string) => void) => ({
  img: ({ src, alt, ...props }: React.ImgHTMLAttributes<HTMLImageElement>) => {
    if (src && chatId && (src.startsWith('/home/user/') || src.startsWith('/tmp/'))) {
      const proxiedSrc = `${getApiBaseUrl()}/api/chat-files/${chatId}/sandbox-file?path=${encodeURIComponent(src)}`;
      const basename = src.split('/').pop() || src;
      return (
        <SandboxImage
          src={proxiedSrc}
          alt={alt || basename}
          onClick={() => onFileClick?.(basename)}
        />
      );
    }
    return <img src={src} alt={alt} {...props} />;
  },
  a: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => {
    const text = typeof children === 'string' ? children
      : Array.isArray(children) ? children.map(c => typeof c === 'string' ? c : '').join('') : '';
    if (CITE_BADGE_RE.test(text.trim())) {
      const badgeClass = "no-underline inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 text-[11px] font-bold bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors cursor-pointer ml-0.5 -top-1.5 relative";
      // In-page citation (bare [^N]) → scroll to the source row, don't open a tab.
      if (href?.startsWith('#cite-')) {
        return (
          <a
            href={href}
            title="Jump to source"
            className={badgeClass}
            onClick={(e) => {
              e.preventDefault();
              document.getElementById(href.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }}
            {...props}
          >
            {text.trim()}
          </a>
        );
      }
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          title={href}
          className={badgeClass}
          {...props}
        >
          {text.trim()}
        </a>
      );
    }
    if (href?.startsWith('http')) {
      return <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline" {...props}>{children}</a>;
    }
    return <a href={href} {...props}>{children}</a>;
  },
  // Wide comparison tables are common in financial output — let them scroll
  // horizontally on narrow screens instead of breaking the layout.
  table: ({ children, ...props }: React.TableHTMLAttributes<HTMLTableElement>) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full text-sm m-0" {...props}>{children}</table>
    </div>
  ),
});

// Inline CSV Preview Component
function CsvPreview({
  filename,
  chatId,
  onOpen
}: {
  filename: string;
  chatId: string | undefined;
  onOpen?: () => void;
}) {
  const [csvData, setCsvData] = useState<{ headers: string[]; rows: string[][]; totalRows: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCsv = async () => {
      if (!chatId) return;
      
      try {
        setLoading(true);
        const url = getChatFileUrl(chatId, filename);
        const authHeader = await getAuthHeader();
        const response = await fetch(url, { headers: authHeader });
        
        if (!response.ok) {
          throw new Error(`Failed to load CSV: ${response.status}`);
        }
        
        const content = await response.text();
        const lines = content.split('\n').filter(line => line.trim());
        const headers = lines[0]?.split(',').map(h => h.trim()) || [];
        const allRows = lines.slice(1).map(line => line.split(',').map(cell => cell.trim()));
        
        // Show first 5 rows as preview
        const previewRows = allRows.slice(0, 5);
        
        setCsvData({
          headers,
          rows: previewRows,
          totalRows: allRows.length
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load CSV');
      } finally {
        setLoading(false);
      }
    };
    
    fetchCsv();
  }, [chatId, filename]);

  if (loading) {
    return (
      <div className="my-3 p-4 bg-gray-50 rounded-lg border border-gray-200 animate-pulse">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 bg-gray-300 rounded"></div>
          <div className="h-4 bg-gray-300 rounded w-32"></div>
        </div>
      </div>
    );
  }

  if (error || !csvData) {
    return (
      <button
        onClick={onOpen}
        className="inline-flex items-center gap-2 px-3 py-2 my-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm border border-blue-200 transition-colors cursor-pointer"
      >
        📊 {filename}
      </button>
    );
  }

  return (
    <div 
      onClick={onOpen}
      className="my-3 rounded-lg overflow-hidden border border-gray-200 bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
    >
      {/* Header */}
      <div className="px-4 py-2.5 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
          </svg>
          <span className="font-medium text-gray-900 text-sm">{filename}</span>
        </div>
        <span className="text-xs text-gray-500 group-hover:text-blue-600 transition-colors">
          Click to expand →
        </span>
      </div>
      
      {/* Table Preview */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-xs">
          <thead className="bg-gray-50">
            <tr>
              {csvData.headers.map((header, i) => (
                <th
                  key={i}
                  className="px-3 py-2 text-left font-semibold text-gray-700 uppercase tracking-wider whitespace-nowrap"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {csvData.rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {row.map((cell, j) => (
                  <td key={j} className="px-3 py-2 text-gray-900 whitespace-nowrap">
                    {cell || '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Footer showing more rows available */}
      {csvData.totalRows > 5 && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-center">
          <span className="text-xs text-gray-500">
            Showing 5 of {csvData.totalRows} rows • Click to view all
          </span>
        </div>
      )}
    </div>
  );
}

// Inline HTML Preview Component (for TradingView charts, etc.)
function HtmlPreview({ 
  filename, 
  chatId, 
  onOpen
}: { 
  filename: string; 
  chatId: string | undefined;
  onOpen?: () => void;
}) {
  const [htmlContent, setHtmlContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    let currentBlobUrl: string | null = null;
    
    const fetchHtml = async () => {
      if (!chatId) {
        console.log('HtmlPreview: No chatId provided');
        setLoading(false);
        setError('No chat ID');
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        const url = getChatFileUrl(chatId, filename);
        console.log('HtmlPreview: Fetching HTML from:', url);
        const authHeader = await getAuthHeader();
        const response = await fetch(url, { headers: authHeader });
        
        if (!response.ok) {
          throw new Error(`Failed to load HTML: ${response.status}`);
        }
        
        const content = await response.text();
        console.log('HtmlPreview: Loaded HTML content, length:', content.length);
        setHtmlContent(content);
        
        // Create blob URL for iframe
        const blob = new Blob([content], { type: 'text/html' });
        currentBlobUrl = URL.createObjectURL(blob);
        setBlobUrl(currentBlobUrl);
        setLoading(false);
      } catch (err) {
        console.error('HtmlPreview: Error loading HTML:', err);
        setError(err instanceof Error ? err.message : 'Failed to load HTML');
        setLoading(false);
      }
    };
    
    fetchHtml();
    
    // Cleanup blob URL on unmount
    return () => {
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
  }, [chatId, filename]);

  if (loading) {
    return (
      <div className="my-3 p-4 bg-gray-900 rounded-lg border border-gray-700 animate-pulse">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 bg-gray-600 rounded"></div>
          <div className="h-4 bg-gray-600 rounded w-48"></div>
        </div>
        <div className="mt-3 h-64 bg-gray-800 rounded"></div>
      </div>
    );
  }

  if (error) {
    console.log('HtmlPreview: Showing error state for', filename, '- error:', error);
    return (
      <button
        onClick={onOpen}
        className="inline-flex items-center gap-2 px-3 py-2 my-2 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg text-sm border border-red-200 transition-colors cursor-pointer"
      >
        ⚠️ {filename} (click to view)
      </button>
    );
  }

  if (!blobUrl) {
    console.log('HtmlPreview: No blob URL yet for', filename);
    return (
      <button
        onClick={onOpen}
        className="inline-flex items-center gap-2 px-3 py-2 my-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-sm border border-indigo-200 transition-colors cursor-pointer"
      >
        📊 {filename}
      </button>
    );
  }

  return (
    <div className="my-3 rounded-lg overflow-hidden border border-gray-700 bg-gray-900 shadow-lg">
      {/* Header */}
      <div className="px-4 py-2.5 bg-gradient-to-r from-indigo-900/50 to-purple-900/50 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <span className="font-medium text-gray-200 text-sm">{filename}</span>
        </div>
        <button
          onClick={onOpen}
          className="text-xs text-gray-400 hover:text-indigo-400 transition-colors"
        >
          Open fullscreen →
        </button>
      </div>
      
      {/* Embedded iframe */}
      <div className="bg-gray-900">
        <iframe
          src={blobUrl}
          className="w-full border-0"
          style={{ height: '500px', minHeight: '400px' }}
          sandbox="allow-scripts allow-same-origin"
          title={filename}
        />
      </div>
    </div>
  );
}

const getSandboxFileUrl = (chatId: string | undefined, sandboxPath: string): string => {
  if (!chatId) return '';
  return `${getApiBaseUrl()}/api/chat-files/${chatId}/sandbox-file?path=${encodeURIComponent(sandboxPath)}`;
};

// ═══════════════════════════════════════════════════════════════════════════
// Inline UI Block Renderers (markdown tags)
// ═══════════════════════════════════════════════════════════════════════════

function InlineButtons({ body, onSend }: { body: string; onSend?: (msg: string) => void }) {
  const [clickedValue, setClickedValue] = React.useState<string | null>(null);
  const parts = body.split('|');
  const title = parts[0] || '';
  const options = parts.slice(1).map(opt => {
    const [label, ...rest] = opt.split('~');
    const value = rest.join('~') || label;
    return { label: label.trim(), value: value.trim() };
  });

  return (
    <div className="flex flex-col gap-1.5 my-2 not-prose">
      {title && <p className="text-sm font-medium text-gray-700">{title}</p>}
      <div className="flex flex-wrap gap-2">
        {options.map((opt, i) => {
          const isClicked = clickedValue === opt.value;
          const isDisabled = clickedValue !== null;
          return (
            <button
              key={i}
              disabled={isDisabled}
              onClick={() => { setClickedValue(opt.value); onSend?.(opt.value); }}
              className={`px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${
                isClicked
                  ? 'bg-primary-600 text-white border-primary-600'
                  : isDisabled
                  ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-default'
                  : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100 hover:border-gray-300'
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function InlineInfoCard({ body }: { body: string }) {
  const parts = body.split('|');
  const title = parts[0] || '';
  const subtitle = parts[1] || '';
  let badge = '';
  let style: 'default' | 'success' | 'warning' | 'accent' = 'default';
  const fields: { label: string; value: string }[] = [];

  for (let i = 2; i < parts.length; i++) {
    const p = parts[i];
    if (p.startsWith('badge:')) badge = p.slice(6).trim();
    else if (p.startsWith('style:')) style = p.slice(6).trim() as typeof style;
    else if (p.includes('=')) {
      const [label, ...v] = p.split('=');
      fields.push({ label: label.trim(), value: v.join('=').trim() });
    }
  }

  const styleMap = {
    default: 'border-gray-200 bg-gray-50/50',
    success: 'border-emerald-200 bg-emerald-50/50',
    warning: 'border-amber-200 bg-amber-50/50',
    accent: 'border-violet-200 bg-violet-50/50',
  };
  const badgeMap = {
    default: 'bg-gray-100 text-gray-600',
    success: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-700',
    accent: 'bg-violet-100 text-violet-700',
  };

  return (
    <div className={`border rounded-lg px-3 py-2.5 my-2 not-prose ${styleMap[style]}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-gray-800">{title}</p>
          {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
        </div>
        {badge && (
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap ${badgeMap[style]}`}>
            {badge}
          </span>
        )}
      </div>
      {fields.length > 0 && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2">
          {fields.map((f, i) => (
            <div key={i} className="flex justify-between text-xs">
              <span className="text-gray-500">{f.label}</span>
              <span className="text-gray-800 font-medium">{f.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function InlineProgress({ body }: { body: string }) {
  const parts = body.split('|');
  const steps = (parts[0] || '').split(',').map(s => s.trim()).filter(Boolean);
  let current = 0;
  for (let i = 1; i < parts.length; i++) {
    if (parts[i].startsWith('current=')) current = parseInt(parts[i].slice(8)) || 0;
  }

  return (
    <div className="flex flex-col gap-1.5 my-2 px-1 not-prose">
      <div className="flex items-center gap-0">
        {steps.map((step, si) => {
          const done = si < current;
          const active = si === current;
          return (
            <React.Fragment key={si}>
              {si > 0 && (
                <div className={`flex-1 h-px ${done ? 'bg-emerald-400' : 'bg-gray-200'}`} />
              )}
              <div className="flex flex-col items-center gap-0.5" style={{ minWidth: 24 }}>
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-semibold ${
                  done ? 'bg-emerald-500 text-white' :
                  active ? 'bg-primary-600 text-white ring-2 ring-primary-200' :
                  'bg-gray-200 text-gray-400'
                }`}>
                  {done ? '✓' : si + 1}
                </div>
                <span className={`text-[10px] leading-tight text-center max-w-[60px] ${
                  active ? 'text-primary-700 font-medium' : done ? 'text-emerald-600' : 'text-gray-400'
                }`}>{step}</span>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

function InlineStatus({ body }: { body: string }) {
  const parts = body.split('|');
  const style = (parts[0] || 'info').trim() as 'success' | 'warning' | 'error' | 'info';
  const message = parts.slice(1).join('|').trim();
  const cfg = {
    success: { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', icon: '✓' },
    warning: { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-700', icon: '⚠' },
    error: { bg: 'bg-red-50 border-red-200', text: 'text-red-700', icon: '✕' },
    info: { bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700', icon: 'ℹ' },
  }[style] || { bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700', icon: 'ℹ' };

  return (
    <div className={`flex items-start gap-2 px-3 py-2 rounded-lg border my-2 not-prose ${cfg.bg}`}>
      <span className={`text-sm ${cfg.text}`}>{cfg.icon}</span>
      <p className={`text-sm ${cfg.text}`}>{message}</p>
    </div>
  );
}

const CURLY_TAG_RE = /\{\{(file|visualization|image|buttons|info_card|progress|status):([^}]+)\}\}/g;
const HAS_CURLY_TAGS_RE = /\{\{(file|visualization|image|buttons|info_card|progress|status):/;

const parseFileReferences = (
  content: string,
  chatId: string | undefined,
  onFileClick?: (filename: string) => void,
  onVisualizationClick?: (filename: string) => void,
  onSendMessage?: (msg: string) => void,
): React.ReactNode[] => {
  const parts: React.ReactNode[] = [];
  // Match {{type:body}} tags (primary) and legacy [type:body] tags (backward compat for old messages)
  const markerPattern = /\{\{(file|visualization|image|buttons|info_card|progress|status):([^}]+)\}\}|\[(file|visualization|image):\s*([^\]]+)\]/g;
  let lastIndex = 0;
  let match;

  while ((match = markerPattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.substring(lastIndex, match.index));
    }

    const markerType = match[1] || match[3];
    const filename = (match[2] || match[4] || '').trim();

    if (markerType === 'image') {
      // [image:filename.png] — render inline from sandbox
      const sandboxPath = filename.startsWith('/') ? filename : `/home/user/${filename}`;
      const imgUrl = getSandboxFileUrl(chatId, sandboxPath);
      const basename = filename.split('/').pop() || filename;
      parts.push(
        <SandboxImage
          key={`img-${match.index}`}
          src={imgUrl}
          alt={basename}
          onClick={() => onFileClick?.(basename)}
        />
      );
    } else if (markerType === 'visualization') {
      // Render as a clickable chip that navigates to the Charts panel
      const displayName = filename.replace(/\.(html|js)$/i, '').replace(/[_-]/g, ' ');
      parts.push(
        <button
          key={`viz-${match.index}`}
          onClick={() => onVisualizationClick?.(filename)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 my-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-sm font-medium border border-indigo-200 transition-colors cursor-pointer group"
        >
          <svg className="w-4 h-4 text-indigo-500 group-hover:text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
          {displayName}
          <svg className="w-3 h-3 text-indigo-400 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      );
    } else if (markerType === 'buttons') {
      parts.push(<InlineButtons key={`btn-${match.index}`} body={filename} onSend={onSendMessage} />);
    } else if (markerType === 'info_card') {
      parts.push(<InlineInfoCard key={`card-${match.index}`} body={filename} />);
    } else if (markerType === 'progress') {
      parts.push(<InlineProgress key={`prog-${match.index}`} body={filename} />);
    } else if (markerType === 'status') {
      parts.push(<InlineStatus key={`stat-${match.index}`} body={filename} />);
    } else {
      // Existing [file:...] handling
      const fileUrl = getChatFileUrl(chatId, filename);

      if (isImageFile(filename)) {
        parts.push(
          <SandboxImage
            key={`file-${match.index}`}
            src={fileUrl}
            alt={filename}
            onClick={() => onFileClick?.(filename)}
          />
        );
      } else if (isCsvFile(filename)) {
        parts.push(
          <CsvPreview
            key={`csv-${match.index}`}
            filename={filename}
            chatId={chatId}
            onOpen={() => onFileClick?.(filename)}
          />
        );
      } else if (isHtmlFile(filename)) {
        parts.push(
          <HtmlPreview
            key={`html-${match.index}`}
            filename={filename}
            chatId={chatId}
            onOpen={() => onFileClick?.(filename)}
          />
        );
      } else {
        parts.push(
          <button
            key={`file-${match.index}`}
            onClick={() => onFileClick?.(filename)}
            className="inline-flex items-center gap-1 px-2 py-1 mx-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded text-sm border border-blue-200 transition-colors cursor-pointer"
          >
            {filename}
          </button>
        );
      }
    }

    lastIndex = markerPattern.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(content.substring(lastIndex));
  }

  return parts.length > 0 ? parts : [content];
};

function FeedbackModal({ type, onSubmit, onClose }: {
  type: 'like' | 'dislike';
  onSubmit: (comment: string) => void;
  onClose: () => void;
}) {
  const [comment, setComment] = React.useState('');
  const inputRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => { inputRef.current?.focus(); }, []);

  const handleSubmit = () => { onSubmit(comment.trim()); onClose(); };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.4)' }} onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl p-5 w-full max-w-sm" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-2 mb-3">
          {type === 'like' ? (
            <svg className="w-5 h-5 text-emerald-500" fill="currentColor" stroke="currentColor" strokeWidth={0.5} viewBox="0 0 24 24"><path d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" /></svg>
          ) : (
            <svg className="w-5 h-5 text-red-500" fill="currentColor" stroke="currentColor" strokeWidth={0.5} viewBox="0 0 24 24"><path d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v2a3.5 3.5 0 003.5 3.5h.174a.535.535 0 00.524-.448l.497-2.986A1.5 1.5 0 0116.18 14.5H18a2.5 2.5 0 002.5-2.5v0a2.5 2.5 0 00-.69-1.726l-3.549-3.643A2 2 0 0014.846 6H10m0 8H7.5" /></svg>
          )}
          <span className="font-semibold text-gray-900 text-sm">
            {type === 'like' ? 'What did you like?' : 'What could be better?'}
          </span>
        </div>
        <textarea
          ref={inputRef}
          value={comment}
          onChange={e => setComment(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
            if (e.key === 'Escape') onClose();
          }}
          placeholder={type === 'like' ? 'Tell us what was helpful (optional)...' : 'Tell us what went wrong (optional)...'}
          className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm mb-3 focus:outline-none focus:border-gray-400 resize-none"
          rows={3}
        />
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 py-2 text-sm text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">Cancel</button>
          <button onClick={handleSubmit} className="flex-1 py-2 text-sm text-white bg-gray-900 rounded-xl hover:bg-gray-800 transition-colors">Submit</button>
        </div>
      </div>
    </div>
  );
}

function MessageActions({ actions, alwaysVisible, onFeedback, feedbackGiven, setFeedbackModal }: {
  actions: MessageAction[];
  alwaysVisible?: boolean;
  onFeedback?: (type: 'like' | 'dislike', comment: string) => void;
  feedbackGiven?: 'like' | 'dislike' | null;
  setFeedbackModal?: (type: 'like' | 'dislike' | null) => void;
}) {
  return (
    <div className={`flex items-center gap-0.5 mt-3 -ml-1 ${alwaysVisible ? 'opacity-100' : 'opacity-0 group-hover/msg:opacity-100'} transition-opacity`}>
      {actions.map((action, idx) => (
        <button
          key={idx}
          onClick={action.onClick}
          disabled={action.disabled || action.loading}
          className="flex items-center justify-center w-8 h-8 text-gray-400 hover:text-gray-600 active:text-gray-800 hover:bg-gray-100 active:bg-gray-200 rounded-md transition-all disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
          title={action.label}
        >
          {action.loading ? (
            <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin" />
          ) : (
            action.icon
          )}
        </button>
      ))}
      {onFeedback && setFeedbackModal && (
        <>
          <button
            onClick={() => setFeedbackModal('like')}
            className={`flex items-center justify-center w-8 h-8 rounded-md transition-all touch-manipulation ${feedbackGiven === 'like' ? 'text-emerald-500' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
            title="Good response"
          >
            <svg className="w-4 h-4" fill={feedbackGiven === 'like' ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" /></svg>
          </button>
          <button
            onClick={() => setFeedbackModal('dislike')}
            className={`flex items-center justify-center w-8 h-8 rounded-md transition-all touch-manipulation ${feedbackGiven === 'dislike' ? 'text-red-500' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
            title="Bad response"
          >
            <svg className="w-4 h-4" fill={feedbackGiven === 'dislike' ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v2a3.5 3.5 0 003.5 3.5h.174a.535.535 0 00.524-.448l.497-2.986A1.5 1.5 0 0116.18 14.5H18a2.5 2.5 0 002.5-2.5v0a2.5 2.5 0 00-.69-1.726l-3.549-3.643A2 2 0 0014.846 6H10m0 8H7.5" /></svg>
          </button>
        </>
      )}
    </div>
  );
}

export default function ChatMessage({ role, content: rawContent, toolCalls, thoughts, chatId, userId, onSelectTool, onFileClick, onVisualizationClick, onSendMessage, onPeekAgent, onEditMessage, onFeedback, actions, isLastAssistantMessage, isStreaming, startTime, timeEstimate }: ChatMessageProps) {
  const isUser = role === 'user';
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [feedbackModal, setFeedbackModal] = useState<'like' | 'dislike' | null>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<'like' | 'dislike' | null>(null);
  const [userCopied, setUserCopied] = useState(false);
  const editRef = React.useRef<HTMLTextAreaElement>(null);
  const contentCleaned = !isUser && rawContent ? rawContent.replace(/\n{3,}/g, '\n\n').trim() : rawContent;
  const content = !isUser && contentCleaned ? preprocessCitations(contentCleaned) : contentCleaned;
  const citations = React.useMemo(() => !isUser && contentCleaned ? extractCitations(contentCleaned) : new Map<number, string>(), [isUser, contentCleaned]);
  const hasSpecialTags = !isUser && content && (
    HAS_CURLY_TAGS_RE.test(content) ||
    /\[(file|visualization|image):\s*[^\]]+\]/.test(content)
  );
  const parsedContent = hasSpecialTags ? parseFileReferences(content, chatId, onFileClick, onVisualizationClick, onSendMessage) : null;
  const mdComponents = React.useMemo(() => makeMarkdownComponents(chatId, onFileClick), [chatId, onFileClick]);

  useEffect(() => {
    if (isEditing && editRef.current) {
      editRef.current.focus();
      editRef.current.setSelectionRange(editRef.current.value.length, editRef.current.value.length);
    }
  }, [isEditing]);

  if (isUser) {
    if (isEditing) {
      return (
        <div className="flex justify-end mb-3">
          <div className="max-w-3xl w-full">
            <textarea
              ref={editRef}
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (editText.trim() && editText.trim() !== rawContent) {
                    onEditMessage?.(editText.trim());
                  }
                  setIsEditing(false);
                }
                if (e.key === 'Escape') {
                  setIsEditing(false);
                }
              }}
              className="w-full rounded-2xl px-4 py-3 bg-primary-600 text-white rounded-br-sm shadow-sm text-sm leading-relaxed resize-none outline-none focus:ring-2 focus:ring-primary-400"
              rows={Math.max(2, editText.split('\n').length)}
            />
            <div className="flex justify-end gap-2 mt-1.5">
              <button
                onClick={() => setIsEditing(false)}
                className="px-3 py-1 text-xs text-gray-500 hover:text-gray-700 rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (editText.trim() && editText.trim() !== rawContent) {
                    onEditMessage?.(editText.trim());
                  }
                  setIsEditing(false);
                }}
                className="px-3 py-1 text-xs text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="flex flex-col items-end mb-3 group/user">
        <div className="max-w-3xl">
          <div className="rounded-2xl px-4 py-3 bg-primary-600 text-white rounded-br-sm shadow-sm">
            <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{content}</p>
          </div>
        </div>
        <div className="flex items-center gap-0.5 mt-1 mr-1 opacity-0 group-hover/user:opacity-100 transition-opacity">
          <button
            onClick={() => { navigator.clipboard.writeText(rawContent); setUserCopied(true); setTimeout(() => setUserCopied(false), 1500); }}
            className="flex items-center justify-center w-7 h-7 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-all"
            title="Copy"
          >
            {userCopied ? (
              <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
            )}
          </button>
          {onEditMessage && (
            <button
              onClick={() => { setEditText(rawContent); setIsEditing(true); }}
              className="flex items-center justify-center w-7 h-7 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-all"
              title="Edit"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
              </svg>
            </button>
          )}
        </div>
      </div>
    );
  }

  if (content && (!toolCalls || toolCalls.length === 0)) {
    return (
      <>
        <div className="flex justify-start mb-2 group/msg">
          <div className="w-full px-3">
            {hasSpecialTags ? (
              <div className="prose prose-sm prose-slate max-w-none">
                {parsedContent?.map((part, idx) =>
                  typeof part === 'string' ? (
                    <ReactMarkdown key={idx} remarkPlugins={[remarkGfm]} components={mdComponents}>
                      {preprocessCitations(part)}
                    </ReactMarkdown>
                  ) : part
                )}
              </div>
            ) : (
              <div className="prose prose-sm prose-slate max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                  {content}
                </ReactMarkdown>
              </div>
            )}
            <CitationReferences citations={citations} />
            {actions && actions.length > 0 && (
              <MessageActions actions={actions} alwaysVisible={isLastAssistantMessage} onFeedback={onFeedback} feedbackGiven={feedbackGiven} setFeedbackModal={setFeedbackModal} />
            )}
          </div>
        </div>
        {feedbackModal && (
          <FeedbackModal type={feedbackModal} onSubmit={(comment) => { setFeedbackGiven(feedbackModal); onFeedback?.(feedbackModal, comment); }} onClose={() => setFeedbackModal(null)} />
        )}
      </>
    );
  }

  if (toolCalls && toolCalls.length > 0 && !content) {
    return (
      <div className="flex justify-start mb-2">
        <div className="w-full px-3">
          <ToolCallSummary toolCalls={toolCalls} thoughts={thoughts} onSelectTool={onSelectTool} onPeekAgent={onPeekAgent} isStreaming={isStreaming} startTime={startTime} timeEstimate={timeEstimate} />
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex justify-start mb-2 group/msg">
        <div className="w-full px-3">
          {content && (
            hasSpecialTags ? (
              <div className="prose prose-sm prose-slate max-w-none mb-2">
                {parsedContent?.map((part, idx) =>
                  typeof part === 'string' ? (
                    <ReactMarkdown key={idx} remarkPlugins={[remarkGfm]} components={mdComponents}>
                      {preprocessCitations(part)}
                    </ReactMarkdown>
                  ) : part
                )}
              </div>
            ) : (
              <div className="prose prose-sm prose-slate max-w-none mb-2">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                  {content}
                </ReactMarkdown>
              </div>
            )
          )}
          <CitationReferences citations={citations} />
          {toolCalls && toolCalls.length > 0 && (
            <ToolCallSummary toolCalls={toolCalls} thoughts={thoughts} onSelectTool={onSelectTool} onPeekAgent={onPeekAgent} isStreaming={isStreaming} startTime={startTime} timeEstimate={timeEstimate} />
          )}
          {actions && actions.length > 0 && (
            <MessageActions actions={actions} alwaysVisible={isLastAssistantMessage} onFeedback={onFeedback} feedbackGiven={feedbackGiven} setFeedbackModal={setFeedbackModal} />
          )}
        </div>
      </div>
      {feedbackModal && (
        <FeedbackModal type={feedbackModal} onSubmit={(comment) => { setFeedbackGiven(feedbackModal); onFeedback?.(feedbackModal, comment); }} onClose={() => setFeedbackModal(null)} />
      )}
    </>
  );
}
