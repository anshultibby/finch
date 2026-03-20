'use client';

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface FileViewerProps {
  filename: string | null;
  chatId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function FileViewer({ filename, chatId, isOpen, onClose }: FileViewerProps) {
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setFileContent(null);
      setLoading(false);
      setError(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !filename || !chatId) return;

    const fetchFile = async () => {
      setLoading(true);
      setError(null);
      setFileContent(null);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${apiUrl}/api/chat-files/${chatId}/download/${encodeURIComponent(filename)}`;
        const response = await fetch(url);

        if (!response.ok) {
          setError(`Failed to load file (HTTP ${response.status})`);
          return;
        }

        const isImage = /\.(png|jpg|jpeg|gif|webp)$/i.test(filename);
        if (isImage) {
          const blob = await response.blob();
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = (reader.result as string).split(',')[1] || reader.result as string;
            setFileContent(base64);
            setLoading(false);
          };
          reader.onerror = () => {
            setError('Failed to process image file');
            setLoading(false);
          };
          reader.readAsDataURL(blob);
          return;
        }

        setFileContent(await response.text());
      } catch (err) {
        setError(`Network error: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setLoading(false);
      }
    };

    fetchFile();
  }, [isOpen, filename, chatId]);

  if (!isOpen || !filename) return null;

  const ext = filename.split('.').pop()?.toLowerCase() || '';

  const renderContent = () => {
    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-12 px-6 text-red-500 text-center">
          <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="font-medium mb-2">Failed to load file</p>
          <p className="text-sm text-gray-600">{error}</p>
        </div>
      );
    }

    if (loading || fileContent === null) {
      return (
        <div className="flex items-center justify-center py-12 text-gray-500 gap-3">
          <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading file...
        </div>
      );
    }

    // HTML
    if (ext === 'html') {
      const blob = new Blob([fileContent], { type: 'text/html' });
      const blobUrl = URL.createObjectURL(blob);
      return (
        <div className="bg-gray-900">
          <iframe
            src={blobUrl}
            className="w-full border-0"
            style={{ height: '650px' }}
            sandbox="allow-scripts allow-same-origin"
            title={filename}
            onLoad={() => setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)}
          />
        </div>
      );
    }

    // Images
    if (/^(png|jpg|jpeg|gif|webp|svg)$/.test(ext)) {
      const mimeType = ext === 'svg' ? 'image/svg+xml' : `image/${ext}`;
      const src = ext === 'svg'
        ? `data:${mimeType};base64,${btoa(fileContent)}`
        : `data:${mimeType};base64,${fileContent}`;
      return (
        <div className="p-6 bg-gray-50 flex items-center justify-center">
          <img src={src} alt={filename} className="max-w-full h-auto rounded-lg shadow-md" style={{ maxHeight: '70vh' }} />
        </div>
      );
    }

    // CSV
    if (ext === 'csv') {
      try {
        const lines = fileContent.split('\n').filter(l => l.trim());
        const headers = lines[0]?.split(',').map(h => h.trim()) || [];
        const rows = lines.slice(1).map(l => l.split(',').map(c => c.trim()));
        return (
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  {headers.map((h, i) => (
                    <th key={i} className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-r border-gray-200 last:border-r-0 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {rows.map((row, i) => (
                  <tr key={i} className="hover:bg-blue-50">
                    {row.map((cell, j) => (
                      <td key={j} className="px-4 py-3 text-sm text-gray-900 border-r border-gray-100 last:border-r-0 whitespace-nowrap">{cell || '-'}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      } catch {
        // fall through to text
      }
    }

    // JSON
    if (ext === 'json') {
      try {
        const formatted = JSON.stringify(JSON.parse(fileContent), null, 2);
        return (
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto bg-gray-900">
            <pre className="text-gray-100 p-6 text-sm leading-relaxed"><code>{formatted}</code></pre>
          </div>
        );
      } catch {
        // fall through to text
      }
    }

    // Markdown
    if (ext === 'md') {
      return (
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto p-6">
          <div className="prose prose-sm prose-slate max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{fileContent}</ReactMarkdown>
          </div>
        </div>
      );
    }

    // Python / code / default text
    const isDark = ['py', 'js', 'ts', 'tsx', 'jsx', 'sh', 'bash', 'sql', 'css'].includes(ext);
    return (
      <div className={`overflow-x-auto max-h-[600px] overflow-y-auto ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        <pre className={`p-6 text-sm leading-relaxed font-mono ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
          <code>{fileContent}</code>
        </pre>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 z-[60] flex items-center justify-center p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-indigo-600">
          <h2 className="text-lg font-bold text-white truncate">{filename}</h2>
          <button onClick={onClose} className="text-white hover:text-blue-100 p-2 rounded-lg hover:bg-white/10">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          {renderContent()}
        </div>

        {/* Footer */}
        {fileContent && !error && (
          <div className="px-6 py-3 border-t border-gray-200 bg-white flex items-center gap-3">
            <button
              onClick={() => {
                const blob = new Blob([fileContent], { type: 'application/octet-stream' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
              }}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download
            </button>
            <button
              onClick={() => navigator.clipboard.writeText(fileContent)}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy
            </button>
            <div className="flex-1" />
            <button onClick={onClose} className="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
