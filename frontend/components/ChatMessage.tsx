import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export default function ChatMessage({ role, content, timestamp }: ChatMessageProps) {
  const isUser = role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        {isUser ? (
          /* User messages: keep bubble style */
          <div className="rounded-2xl px-4 py-3 bg-primary-600 text-white rounded-br-none shadow-sm">
            <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
          </div>
        ) : (
          /* AI messages: clean, readable markdown with subtle styling */
          <div className="px-3 py-2">
            <div className="prose prose-sm prose-slate max-w-none
              prose-headings:font-semibold prose-headings:text-gray-900
              prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
              prose-p:text-[15px] prose-p:text-gray-900 prose-p:leading-relaxed prose-p:my-2
              prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
              prose-strong:text-gray-900 prose-strong:font-semibold
              prose-code:text-sm prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-gray-800 prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:rounded-lg prose-pre:p-4 prose-pre:my-3
              prose-ul:my-2 prose-ol:my-2 prose-li:my-1 prose-li:text-[15px] prose-li:text-gray-900
              prose-table:text-sm prose-table:my-3
              prose-th:bg-gray-100 prose-th:font-semibold prose-th:p-2
              prose-td:p-2 prose-td:border prose-td:border-gray-200
              prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-gray-700
              prose-img:rounded-lg prose-img:shadow-md">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {content}
              </ReactMarkdown>
            </div>
          </div>
        )}
        {timestamp && (
          <p className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
            {new Date(timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}

