'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';

interface FileViewerProps {
  content: string | null;
  filename: string | null;
  fileType: 'strategy' | 'chat' | 'user' | null;
}

export default function FileViewer({ content, filename, fileType }: FileViewerProps) {
  if (!content || !filename) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <div className="text-6xl mb-4">📁</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Select a file to view</h3>
          <p className="text-gray-600">Choose a strategy or file from the sidebar</p>
        </div>
      </div>
    );
  }

  const isMarkdown = filename.endsWith('.md') || fileType === 'strategy';
  const isJson = filename.endsWith('.json');
  const isCsv = filename.endsWith('.csv');
  const isCode = filename.endsWith('.py') || filename.endsWith('.js') || filename.endsWith('.ts');

  const renderContent = () => {
    // Markdown (strategies)
    if (isMarkdown) {
      return (
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                const language = match ? match[1] : '';
                
                return !inline && language ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={language}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      );
    }

    // JSON
    if (isJson) {
      try {
        const parsed = JSON.parse(content);
        return (
          <SyntaxHighlighter
            language="json"
            style={vscDarkPlus}
            customStyle={{ margin: 0, borderRadius: 0, height: '100%' }}
          >
            {JSON.stringify(parsed, null, 2)}
          </SyntaxHighlighter>
        );
      } catch (e) {
        return <pre className="whitespace-pre-wrap text-sm">{content}</pre>;
      }
    }

    // CSV
    if (isCsv) {
      const lines = content.split('\n').filter(line => line.trim());
      const headers = lines[0]?.split(',') || [];
      const rows = lines.slice(1).map(line => line.split(','));

      return (
        <div className="overflow-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {headers.map((header, i) => (
                  <th
                    key={i}
                    className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {header.trim()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j} className="px-4 py-2 text-sm text-gray-900">
                      {cell.trim()}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // Code
    if (isCode) {
      const language = filename.endsWith('.py') ? 'python' : 
                      filename.endsWith('.js') ? 'javascript' : 
                      filename.endsWith('.ts') ? 'typescript' : 'text';
      
      return (
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          customStyle={{ margin: 0, borderRadius: 0, height: '100%' }}
        >
          {content}
        </SyntaxHighlighter>
      );
    }

    // Plain text
    return (
      <pre className="whitespace-pre-wrap text-sm font-mono text-gray-800">
        {content}
      </pre>
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="px-6 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">
              {isMarkdown ? '📝' : isJson ? '📋' : isCsv ? '📊' : isCode ? '💻' : '📄'}
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{filename}</h3>
              <p className="text-xs text-gray-500 capitalize">{fileType} file</p>
            </div>
          </div>
          
          <button
            onClick={() => {
              navigator.clipboard.writeText(content);
              alert('Copied to clipboard!');
            }}
            className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            📋 Copy
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {renderContent()}
      </div>
    </div>
  );
}

