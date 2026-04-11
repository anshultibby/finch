import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ToolCall from './ToolCall';
import { isImageFile, isCsvFile, isHtmlFile, getApiBaseUrl } from '@/lib/utils';
import type { ToolCallStatus, SwapData } from '@/lib/types';

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
  swap_data?: SwapData[];
  chatId?: string;
  userId?: string;
  onSelectTool?: (tool: ToolCallStatus) => void;
  onFileClick?: (filename: string) => void;
  onVisualizationClick?: (filename: string) => void;
  onSendMessage?: (msg: string) => void;
  onPeekAgent?: (agentId: string, chatId: string, name: string) => void;
  actions?: MessageAction[];
  isLastAssistantMessage?: boolean;
}

const getChatFileUrl = (chatId: string | undefined, filename: string): string => {
  if (!chatId) return '';
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
  const basename = alt || src.split('/').pop() || src;
  const resolvedSrc = retryCount > 0 ? `${src}${src.includes('?') ? '&' : '?'}_r=${retryCount}` : src;

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-gray-100 bg-white shadow-sm max-w-full group/img">
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
        src={resolvedSrc}
        alt={basename}
        className="max-w-full h-auto cursor-pointer transition-opacity duration-300"
        style={{
          maxHeight: 520,
          display: status === 'error' ? 'none' : 'block',
          opacity: status === 'loaded' ? 1 : 0,
          minHeight: status === 'loading' ? 240 : undefined,
        }}
        onLoad={() => setStatus('loaded')}
        onError={() => setStatus('error')}
        onClick={onClick}
      />

      {/* Caption */}
      {status === 'loaded' && (
        <div className="px-3 py-2 border-t border-gray-100 flex items-center justify-between">
          <span className="text-[11px] text-gray-400 font-mono truncate">{basename}</span>
          <svg className="w-3.5 h-3.5 text-gray-300 group-hover/img:text-gray-500 transition-colors shrink-0 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </div>
      )}
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
        const response = await fetch(url);
        
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
        const response = await fetch(url);
        
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

const parseFileReferences = (
  content: string,
  chatId: string | undefined,
  onFileClick?: (filename: string) => void,
  onVisualizationClick?: (filename: string) => void
): React.ReactNode[] => {
  const parts: React.ReactNode[] = [];
  // Match [file:...], [visualization:...], and [image:...] markers
  const markerPattern = /\[(file|visualization|image):\s*([^\]]+)\]/g;
  let lastIndex = 0;
  let match;

  while ((match = markerPattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.substring(lastIndex, match.index));
    }

    const markerType = match[1];
    const filename = match[2].trim();

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
      const displayName = filename.replace(/\.html$/i, '').replace(/[_-]/g, ' ');
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

function ReminderModal({ swap, onClose, userId }: { swap: SwapData; onClose: () => void; userId: string }) {
  const [email, setEmail] = React.useState('');
  const [submitted, setSubmitted] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  const handleSubmit = async () => {
    if (!email.trim()) return;
    setLoading(true);
    try {
      const today = new Date().toISOString().split('T')[0];
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          email: email.trim(),
          symbol_sold: swap.sell_symbol,
          symbol_bought: swap.buy_symbol,
          loss_amount: Math.abs(swap.sell_loss),
          sale_date: today,
        }),
      });
      setSubmitted(true);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const remindDate = new Date();
  remindDate.setDate(remindDate.getDate() + 61);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.4)' }} onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
        {submitted ? (
          <div className="text-center py-4">
            <div className="text-2xl mb-3">✓</div>
            <div className="font-semibold text-gray-900 mb-1">Reminder set</div>
            <div className="text-sm text-gray-500">
              We'll email you on {remindDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })} when you can safely repurchase {swap.sell_symbol}.
            </div>
            <button onClick={onClose} className="mt-4 text-sm text-gray-400 hover:text-gray-600">Close</button>
          </div>
        ) : (
          <>
            <div className="font-semibold text-gray-900 mb-1">Set 61-day repurchase reminder</div>
            <div className="text-sm text-gray-500 mb-4">
              We'll email you on <strong>{remindDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</strong> when the wash sale window clears for <strong>{swap.sell_symbol}</strong>.
            </div>
            <input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm mb-3 focus:outline-none focus:border-gray-400"
              autoFocus
            />
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 py-2.5 text-sm text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">Cancel</button>
              <button
                onClick={handleSubmit}
                disabled={!email.trim() || loading}
                className="flex-1 py-2.5 text-sm text-white bg-gray-900 rounded-xl hover:bg-gray-800 disabled:opacity-40 transition-colors"
              >
                {loading ? 'Saving…' : 'Set reminder'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function WaitlistModal({ onClose }: { onClose: () => void }) {
  const [email, setEmail] = React.useState('');
  const [submitted, setSubmitted] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  const handleSubmit = async () => {
    if (!email.trim()) return;
    setLoading(true);
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/waitlist/alpaca`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });
      setSubmitted(true);
    } catch (e) {
      setSubmitted(true); // show success even on error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.4)' }} onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
        {submitted ? (
          <div className="text-center py-4">
            <div className="text-2xl mb-3">🎉</div>
            <div className="font-semibold text-gray-900 mb-1">You're on the list</div>
            <div className="text-sm text-gray-500">We'll let you know when Alpaca auto-execution launches.</div>
            <button onClick={onClose} className="mt-4 text-sm text-gray-400 hover:text-gray-600">Close</button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-1">
              <div className="font-semibold text-gray-900">Alpaca Auto-Execution</div>
              <span className="text-[10px] font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full uppercase tracking-wide">Beta</span>
            </div>
            <div className="text-sm text-gray-500 mb-4">
              We're building direct integration with Alpaca to execute these swaps automatically. Join the waitlist and we'll notify you when it's ready.
            </div>
            <input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm mb-3 focus:outline-none focus:border-gray-400"
              autoFocus
            />
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 py-2.5 text-sm text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">Cancel</button>
              <button
                onClick={handleSubmit}
                disabled={!email.trim() || loading}
                className="flex-1 py-2.5 text-sm text-white bg-gray-900 rounded-xl hover:bg-gray-800 disabled:opacity-40 transition-colors"
              >
                {loading ? 'Joining…' : 'Join waitlist'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function SwapCard({ swap, index, userId }: { swap: SwapData; index: number; userId: string }) {
  const [showReminder, setShowReminder] = React.useState(false);
  const [showWaitlist, setShowWaitlist] = React.useState(false);

  return (
    <>
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-4 hover:border-gray-300 transition-colors">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-gray-400 bg-gray-100 px-2 py-0.5 rounded">#{index + 1}</span>
            <div className="flex items-center gap-1.5">
              <span className="font-medium text-sm text-red-600">{swap.sell_symbol}</span>
              <span className="text-gray-400">→</span>
              <span className="font-medium text-sm text-emerald-600">{swap.buy_symbol}</span>
            </div>
          </div>
          <span className="text-xs text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded-full">
            Save ~${swap.estimated_savings.toLocaleString()}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
          <div className="bg-red-50/60 rounded-lg px-3 py-2">
            <div className="text-gray-500 mb-0.5">Sell</div>
            <div className="text-red-600 font-medium">{swap.sell_qty} shares · ${Math.abs(swap.sell_loss).toLocaleString()} loss</div>
            <div className="text-gray-400 mt-0.5">{swap.sell_loss_pct.toFixed(1)}%</div>
          </div>
          <div className="bg-emerald-50/60 rounded-lg px-3 py-2">
            <div className="text-gray-500 mb-0.5">Buy</div>
            <div className="text-emerald-700 font-medium">{swap.buy_symbol}</div>
            <div className="text-gray-400 mt-0.5 truncate">{swap.buy_reason}</div>
          </div>
        </div>
        <div className="text-[11px] text-gray-400 mb-2">Correlation: {(swap.correlation * 100).toFixed(0)}%</div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowReminder(true)}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 border border-gray-200 text-gray-600 text-xs font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            61-day reminder
          </button>
          <button
            onClick={() => setShowWaitlist(true)}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 transition-colors"
          >
            Execute via Alpaca
            <span className="text-[9px] bg-white/20 px-1.5 py-0.5 rounded font-semibold">BETA</span>
          </button>
        </div>
      </div>
      {showReminder && <ReminderModal swap={swap} onClose={() => setShowReminder(false)} userId={userId} />}
      {showWaitlist && <WaitlistModal onClose={() => setShowWaitlist(false)} />}
    </>
  );
}

function SwapCards({ swaps, userId }: { swaps: SwapData[]; userId: string }) {
  const totalSavings = swaps.reduce((sum, s) => sum + s.estimated_savings, 0);
  return (
    <div className="space-y-3 my-3">
      <div className="grid gap-3 sm:grid-cols-2">
        {swaps.map((swap, i) => (
          <SwapCard key={`${swap.sell_symbol}-${swap.buy_symbol}`} swap={swap} index={i} userId={userId} />
        ))}
      </div>
      {swaps.length > 1 && (
        <div className="px-1 text-sm text-gray-600 font-medium">
          Total estimated savings: <span className="text-emerald-600">${totalSavings.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}

function ToolCallList({ toolCalls, onSelectTool, onPeekAgent }: { toolCalls: ToolCallStatus[], onSelectTool?: (tool: ToolCallStatus) => void, onPeekAgent?: (agentId: string, chatId: string, name: string) => void }) {
  // Sort by insertion order to maintain stable rendering
  // Tools without _insertionOrder (e.g., from history) keep their array position
  const sortedTools = [...toolCalls].sort((a, b) => {
    const orderA = a._insertionOrder ?? Infinity;
    const orderB = b._insertionOrder ?? Infinity;
    return orderA - orderB;
  });
  
  return (
    <div className="flex flex-col gap-1">
      {sortedTools.map((tool) => (
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

function MessageActions({ actions, alwaysVisible }: { actions: MessageAction[]; alwaysVisible?: boolean }) {
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
    </div>
  );
}

export default function ChatMessage({ role, content, toolCalls, swap_data, chatId, userId, onSelectTool, onFileClick, onVisualizationClick, onSendMessage, onPeekAgent, actions, isLastAssistantMessage }: ChatMessageProps) {
  const isUser = role === 'user';
  const hasFileReferences = !isUser && content && /\[(file|visualization|image):\s*[^\]]+\]/.test(content);
  const parsedContent = hasFileReferences ? parseFileReferences(content, chatId, onFileClick, onVisualizationClick) : null;
  const mdComponents = React.useMemo(() => makeMarkdownComponents(chatId, onFileClick), [chatId, onFileClick]);

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-2xl">
          <div className="rounded-2xl px-4 py-3 bg-primary-600 text-white rounded-br-sm shadow-sm">
            <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{content}</p>
          </div>
        </div>
      </div>
    );
  }

  if (content && (!toolCalls || toolCalls.length === 0)) {
    return (
      <div className="flex justify-start mb-2 group/msg">
        <div className="w-full px-3">
          {hasFileReferences ? (
            <div className="prose prose-sm prose-slate max-w-none">
              {parsedContent?.map((part, idx) =>
                typeof part === 'string' ? (
                  <ReactMarkdown key={idx} remarkPlugins={[remarkGfm]} components={mdComponents}>
                    {part}
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
          {actions && actions.length > 0 && (
            <MessageActions actions={actions} alwaysVisible={isLastAssistantMessage} />
          )}
        </div>
      </div>
    );
  }

  if (toolCalls && toolCalls.length > 0 && !content) {
    return (
      <div className="flex justify-start mb-2">
        <div className="w-full px-3">
          <ToolCallList toolCalls={toolCalls} onSelectTool={onSelectTool} onPeekAgent={onPeekAgent} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-2 group/msg">
      <div className="w-full px-3">
        {content && (
          hasFileReferences ? (
            <div className="prose prose-sm prose-slate max-w-none mb-2">
              {parsedContent?.map((part, idx) =>
                typeof part === 'string' ? (
                  <ReactMarkdown key={idx} remarkPlugins={[remarkGfm]} components={mdComponents}>
                    {part}
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
        {swap_data && swap_data.length > 0 && (
          <SwapCards swaps={swap_data} userId={userId || ''} />
        )}
        {toolCalls && toolCalls.length > 0 && (
          <ToolCallList toolCalls={toolCalls} onSelectTool={onSelectTool} onPeekAgent={onPeekAgent} />
        )}
        {actions && actions.length > 0 && (
          <MessageActions actions={actions} alwaysVisible={isLastAssistantMessage} />
        )}
      </div>
    </div>
  );
}
