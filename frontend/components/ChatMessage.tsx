import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ToolCallStatus } from '@/lib/api';
import ToolCallGroup from './ToolCallGroup';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  toolCalls?: ToolCallStatus[];
  onFileClick?: (filename: string, chatId: string) => void;
  chatId?: string;
}

// Helper to check if a filename is an image
const isImageFile = (filename: string): boolean => {
  return /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(filename);
};

// Helper to get the API URL for a chat file
const getChatFileUrl = (chatId: string | undefined, filename: string): string => {
  if (!chatId) return '';
  // Use backend URL directly
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  return `${API_BASE_URL}/api/chat-files/${chatId}/download/${encodeURIComponent(filename)}`;
};

// Parse content and replace [file:...] references with appropriate components
const parseFileReferences = (content: string, chatId: string | undefined): React.ReactNode[] => {
  const parts: React.ReactNode[] = [];
  const filePattern = /\[file:([^\]]+)\]/g;
  let lastIndex = 0;
  let match;

  while ((match = filePattern.exec(content)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(content.substring(lastIndex, match.index));
    }

    const filename = match[1];
    const isImage = isImageFile(filename);

    if (isImage) {
      // Render image inline
      const imageUrl = getChatFileUrl(chatId, filename);
      parts.push(
        <div key={`file-${match.index}`} className="my-3 rounded-lg overflow-hidden border border-gray-200 bg-gray-50 max-w-full">
          <img 
            src={imageUrl} 
            alt={filename}
            className="max-w-full h-auto"
            loading="lazy"
            onError={(e) => {
              console.error('Failed to load image:', filename, 'from URL:', imageUrl);
              // Show error placeholder
              e.currentTarget.style.display = 'none';
              const parent = e.currentTarget.parentElement;
              if (parent) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'p-4 text-center text-red-600 text-sm';
                errorDiv.textContent = `⚠️ Failed to load image: ${filename}`;
                parent.insertBefore(errorDiv, e.currentTarget);
              }
            }}
          />
          <div className="px-3 py-2 bg-white border-t border-gray-200">
            <p className="text-xs text-gray-600 font-mono">{filename}</p>
          </div>
        </div>
      );
    } else {
      // Render as clickable link/button
      const fileUrl = getChatFileUrl(chatId, filename);
      parts.push(
        <a
          key={`file-${match.index}`}
          href={fileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 px-2 py-1 mx-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded text-sm border border-blue-200 transition-colors"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {filename}
        </a>
      );
    }

    lastIndex = filePattern.lastIndex;
  }

  // Add remaining text
  if (lastIndex < content.length) {
    parts.push(content.substring(lastIndex));
  }

  return parts.length > 0 ? parts : [content];
};

export default function ChatMessage({ role, content, toolCalls, chatId }: ChatMessageProps) {
  const isUser = role === 'user';

  // Parse file references for assistant messages (don't use g flag in test to avoid regex state issues)
  const hasFileReferences = !isUser && content && /\[file:[^\]]+\]/.test(content);
  const parsedContent = hasFileReferences ? parseFileReferences(content, chatId) : null;
  
  // Debug logging
  if (hasFileReferences && typeof window !== 'undefined') {
    console.log('🖼️ File references detected in message:', content.match(/\[file:[^\]]+\]/g));
    console.log('📝 Chat ID:', chatId);
  }

  // User message
  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[80%]">
          <div className="rounded-2xl px-4 py-3 bg-primary-600 text-white rounded-br-none shadow-sm">
            <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
          </div>
        </div>
      </div>
    );
  }

  // Assistant message - text only
  if (content && (!toolCalls || toolCalls.length === 0)) {
    return (
      <div className="flex justify-start mb-2">
        <div className="max-w-[80%] px-3">
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
        </div>
      </div>
    );
  }

  // Assistant message - tools only
  if (toolCalls && toolCalls.length > 0 && !content) {
    return (
      <div className="flex justify-start mb-1">
        <div className="max-w-[80%] px-3">
          <ToolCallGroup toolCalls={toolCalls} />
        </div>
      </div>
    );
  }

  // Assistant message - both text and tools (shouldn't happen with new flow)
  return (
    <div className="flex justify-start mb-2">
      <div className="max-w-[80%] px-3">
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
          <ToolCallGroup toolCalls={toolCalls} />
        )}
      </div>
    </div>
  );
}
