import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ToolCall from './ToolCall';
import { isImageFile, isCsvFile, isHtmlFile, getApiBaseUrl } from '@/lib/utils';
import type { ToolCallStatus, Resource } from '@/lib/types';

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
  chatId?: string;
  onSelectTool?: (tool: ToolCallStatus) => void;
  resources?: Resource[];
  onFileClick?: (resource: Resource) => void;
  actions?: MessageAction[];
  isLastAssistantMessage?: boolean;
}

const getChatFileUrl = (chatId: string | undefined, filename: string): string => {
  if (!chatId) return '';
  return `${getApiBaseUrl()}/api/chat-files/${chatId}/download/${encodeURIComponent(filename)}`;
};

// Inline CSV Preview Component
function CsvPreview({ 
  filename, 
  chatId, 
  onOpen,
  resources
}: { 
  filename: string; 
  chatId: string | undefined;
  onOpen?: () => void;
  resources?: Resource[];
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

// Helper to find resource by filename
const findResourceByFilename = (resources: Resource[] | undefined, filename: string): Resource | null => {
  if (!resources) return null;
  return resources.find(r => 
    r.resource_type === 'file' && r.data?.filename === filename
  ) || null;
};

// Create a pseudo-resource for files not in resources list
const createPseudoResource = (filename: string, chatId: string): Resource => ({
  id: `pseudo-${filename}`,
  chat_id: chatId,
  user_id: '',
  tool_name: 'file_reference',
  resource_type: 'file',
  title: filename,
  data: {
    filename,
    file_type: filename.split('.').pop() || 'text'
  },
  created_at: new Date().toISOString()
});

const parseFileReferences = (
  content: string, 
  chatId: string | undefined,
  resources?: Resource[],
  onFileClick?: (resource: Resource) => void
): React.ReactNode[] => {
  const parts: React.ReactNode[] = [];
  const filePattern = /\[file:([^\]]+)\]/g;
  let lastIndex = 0;
  let match;

  while ((match = filePattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.substring(lastIndex, match.index));
    }

    const filename = match[1];
    const fileUrl = getChatFileUrl(chatId, filename);

    if (isImageFile(filename)) {
      parts.push(
        <div key={`file-${match.index}`} className="my-3 rounded-lg overflow-hidden border border-gray-200 bg-gray-50 max-w-full">
          <img src={fileUrl} alt={filename} className="max-w-full h-auto" loading="lazy" />
          <div className="px-3 py-2 bg-white border-t border-gray-200">
            <p className="text-xs text-gray-600 font-mono">{filename}</p>
          </div>
        </div>
      );
    } else if (isCsvFile(filename)) {
      // Render inline CSV preview
      const handleOpen = () => {
        if (!onFileClick || !chatId) return;
        const resource = findResourceByFilename(resources, filename) || createPseudoResource(filename, chatId);
        onFileClick(resource);
      };
      
      parts.push(
        <CsvPreview
          key={`csv-${match.index}`}
          filename={filename}
          chatId={chatId}
          onOpen={handleOpen}
          resources={resources}
        />
      );
    } else if (isHtmlFile(filename)) {
      // Render inline HTML preview (TradingView charts, etc.)
      const handleOpen = () => {
        if (!onFileClick || !chatId) return;
        const resource = findResourceByFilename(resources, filename) || createPseudoResource(filename, chatId);
        onFileClick(resource);
      };
      
      parts.push(
        <HtmlPreview
          key={`html-${match.index}`}
          filename={filename}
          chatId={chatId}
          onOpen={handleOpen}
        />
      );
    } else {
      // Other files - show clickable badge that opens in viewer
      const handleClick = () => {
        if (!onFileClick || !chatId) return;
        const resource = findResourceByFilename(resources, filename) || createPseudoResource(filename, chatId);
        onFileClick(resource);
      };
      
      parts.push(
        <button
          key={`file-${match.index}`}
          onClick={handleClick}
          className="inline-flex items-center gap-1 px-2 py-1 mx-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded text-sm border border-blue-200 transition-colors cursor-pointer"
        >
          📄 {filename}
        </button>
      );
    }

    lastIndex = filePattern.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(content.substring(lastIndex));
  }

  return parts.length > 0 ? parts : [content];
};

function ToolCallList({ toolCalls, onSelectTool }: { toolCalls: ToolCallStatus[], onSelectTool?: (tool: ToolCallStatus) => void }) {
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
        />
      ))}
    </div>
  );
}

function MessageActions({ actions }: { actions: MessageAction[] }) {
  return (
    <div className="flex items-center gap-1.5 mt-2 -ml-1">
      {actions.map((action, idx) => (
        <button
          key={idx}
          onClick={action.onClick}
          disabled={action.disabled || action.loading}
          className="flex items-center gap-1.5 px-2.5 py-2 text-gray-400 hover:text-gray-600 active:text-gray-800 hover:bg-gray-100 active:bg-gray-200 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
          title={action.label}
          style={{ minHeight: '40px', minWidth: '40px' }}
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

export default function ChatMessage({ role, content, toolCalls, chatId, onSelectTool, resources, onFileClick, actions, isLastAssistantMessage }: ChatMessageProps) {
  const isUser = role === 'user';
  const hasFileReferences = !isUser && content && /\[file:[^\]]+\]/.test(content);
  const parsedContent = hasFileReferences ? parseFileReferences(content, chatId, resources, onFileClick) : null;

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-2xl">
          <div className="rounded-2xl px-4 py-3 bg-primary-600 text-white rounded-br-none shadow-sm">
            <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
          </div>
        </div>
      </div>
    );
  }

  if (content && (!toolCalls || toolCalls.length === 0)) {
    return (
      <div className="flex justify-start mb-2">
        <div className="w-full px-3">
          {hasFileReferences ? (
            <div className="prose prose-sm prose-slate max-w-none">
              {parsedContent?.map((part, idx) => 
                typeof part === 'string' ? (
                  <ReactMarkdown key={idx} remarkPlugins={[remarkGfm]}>
                    {part}
                  </ReactMarkdown>
                ) : part
              )}
            </div>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </div>
          )}
          {actions && actions.length > 0 && isLastAssistantMessage && (
            <MessageActions actions={actions} />
          )}
        </div>
      </div>
    );
  }

  if (toolCalls && toolCalls.length > 0 && !content) {
    return (
      <div className="flex justify-start mb-2">
        <div className="w-full px-3">
          <ToolCallList toolCalls={toolCalls} onSelectTool={onSelectTool} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-2">
      <div className="w-full px-3">
        {content && (
          hasFileReferences ? (
            <div className="prose prose-sm prose-slate max-w-none mb-2">
              {parsedContent?.map((part, idx) => 
                typeof part === 'string' ? (
                  <ReactMarkdown key={idx} remarkPlugins={[remarkGfm]}>
                    {part}
                  </ReactMarkdown>
                ) : part
              )}
            </div>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none mb-2">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </div>
          )
        )}
        {toolCalls && toolCalls.length > 0 && (
          <ToolCallList toolCalls={toolCalls} onSelectTool={onSelectTool} />
        )}
        {actions && actions.length > 0 && isLastAssistantMessage && (
          <MessageActions actions={actions} />
        )}
      </div>
    </div>
  );
}
