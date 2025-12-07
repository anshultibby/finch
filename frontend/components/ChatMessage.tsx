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

export default function ChatMessage({ role, content, toolCalls }: ChatMessageProps) {
  const isUser = role === 'user';

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
          <div className="prose prose-sm prose-slate max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
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
          <div className="prose prose-sm prose-slate max-w-none mb-2">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        )}
        {toolCalls && toolCalls.length > 0 && (
          <ToolCallGroup toolCalls={toolCalls} />
        )}
      </div>
    </div>
  );
}
