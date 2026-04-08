'use client';

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface FileViewerProps {
  filename: string | null;
  chatId: string | null;
}

function getFileExt(filename: string) {
  return filename.split('.').pop()?.toLowerCase() || '';
}

function encodePath(relativePath: string) {
  return relativePath.split('/').map(encodeURIComponent).join('/');
}

function FileTypeBadge({ ext }: { ext: string }) {
  type BadgeConfig = { label: string; bg: string; text: string };
  const map: Record<string, BadgeConfig> = {
    py:   { label: 'Python',     bg: 'bg-blue-50',   text: 'text-blue-600' },
    js:   { label: 'JavaScript', bg: 'bg-yellow-50', text: 'text-yellow-700' },
    ts:   { label: 'TypeScript', bg: 'bg-blue-50',   text: 'text-blue-700' },
    tsx:  { label: 'TSX',        bg: 'bg-cyan-50',   text: 'text-cyan-700' },
    jsx:  { label: 'JSX',        bg: 'bg-cyan-50',   text: 'text-cyan-700' },
    json: { label: 'JSON',       bg: 'bg-orange-50', text: 'text-orange-600' },
    md:   { label: 'Markdown',   bg: 'bg-indigo-50', text: 'text-indigo-600' },
    csv:  { label: 'CSV',        bg: 'bg-green-50',  text: 'text-green-700' },
    html: { label: 'HTML',       bg: 'bg-red-50',    text: 'text-red-600' },
    css:  { label: 'CSS',        bg: 'bg-sky-50',    text: 'text-sky-600' },
    sh:   { label: 'Shell',      bg: 'bg-gray-100',  text: 'text-gray-500' },
    bash: { label: 'Bash',       bg: 'bg-gray-100',  text: 'text-gray-500' },
    sql:  { label: 'SQL',        bg: 'bg-purple-50', text: 'text-purple-600' },
    png:  { label: 'PNG',        bg: 'bg-purple-50', text: 'text-purple-600' },
    jpg:  { label: 'JPG',        bg: 'bg-purple-50', text: 'text-purple-600' },
    jpeg: { label: 'JPEG',       bg: 'bg-purple-50', text: 'text-purple-600' },
    gif:  { label: 'GIF',        bg: 'bg-purple-50', text: 'text-purple-600' },
    webp: { label: 'WebP',       bg: 'bg-purple-50', text: 'text-purple-600' },
    svg:  { label: 'SVG',        bg: 'bg-purple-50', text: 'text-purple-600' },
    yaml: { label: 'YAML',       bg: 'bg-amber-50',  text: 'text-amber-700' },
    yml:  { label: 'YAML',       bg: 'bg-amber-50',  text: 'text-amber-700' },
    txt:  { label: 'Text',       bg: 'bg-gray-100',  text: 'text-gray-500' },
    log:  { label: 'Log',        bg: 'bg-gray-100',  text: 'text-gray-500' },
  };
  const c = map[ext];
  if (!c) return null;
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

export default function FileViewer({ filename, chatId }: FileViewerProps) {
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setFileContent(null);
    setError(null);
    if (!filename || !chatId) return;

    const fetchFile = async () => {
      setLoading(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${apiUrl}/api/chat-files/${chatId}/download/${encodePath(filename)}`;
        const res = await fetch(url);

        if (!res.ok) {
          setError(`HTTP ${res.status}`);
          return;
        }

        const ext = getFileExt(filename);
        if (/^(png|jpg|jpeg|gif|webp)$/.test(ext)) {
          const blob = await res.blob();
          const reader = new FileReader();
          reader.onloadend = () => {
            setFileContent(reader.result as string);
            setLoading(false);
          };
          reader.onerror = () => { setError('Image read failed'); setLoading(false); };
          reader.readAsDataURL(blob);
          return;
        }

        setFileContent(await res.text());
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Network error');
      } finally {
        setLoading(false);
      }
    };

    fetchFile();
  }, [filename, chatId]);

  if (!filename) {
    return (
      <div className="flex flex-col h-full items-center justify-center text-center px-8 bg-gray-50/50">
        <div className="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center mb-3">
          <svg className="w-6 h-6 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-400">Select a file</p>
        <p className="text-xs text-gray-300 mt-1">Choose a file from the tree to view its contents</p>
      </div>
    );
  }

  const ext = getFileExt(filename);
  const parts = filename.split('/');
  const basename = parts[parts.length - 1];
  const dirParts = parts.slice(0, -1);

  const handleCopy = () => {
    if (!fileContent) return;
    navigator.clipboard.writeText(fileContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleDownload = () => {
    if (!fileContent) return;
    const blob = new Blob([fileContent], { type: 'application/octet-stream' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = basename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-40 gap-2 text-gray-400">
          <div className="w-4 h-4 border-2 border-gray-200 border-t-gray-400 rounded-full animate-spin" />
          <span className="text-sm">Loading…</span>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center h-40 text-center px-6">
          <div className="w-8 h-8 rounded-xl bg-red-50 flex items-center justify-center mb-2">
            <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-600">Failed to load</p>
          <p className="text-xs text-gray-400 mt-0.5">{error}</p>
        </div>
      );
    }

    if (fileContent === null) return null;

    // Images
    if (/^(png|jpg|jpeg|gif|webp)$/.test(ext)) {
      return (
        <div className="flex items-center justify-center p-8 bg-[#f8f8f8] min-h-[200px] flex-1">
          <img
            src={fileContent}
            alt={basename}
            className="max-w-full h-auto rounded-lg shadow-sm ring-1 ring-black/5"
            style={{ maxHeight: '70vh' }}
          />
        </div>
      );
    }

    // SVG
    if (ext === 'svg') {
      return (
        <div className="flex items-center justify-center p-8 bg-[#f8f8f8] min-h-[200px] flex-1">
          <img
            src={`data:image/svg+xml;base64,${btoa(fileContent)}`}
            alt={basename}
            className="max-w-full h-auto"
            style={{ maxHeight: '70vh' }}
          />
        </div>
      );
    }

    // HTML — iframe
    if (ext === 'html') {
      const blob = new Blob([fileContent], { type: 'text/html' });
      const blobUrl = URL.createObjectURL(blob);
      return (
        <iframe
          src={blobUrl}
          className="w-full border-0 flex-1"
          style={{ height: '100%', minHeight: '400px' }}
          sandbox="allow-scripts allow-same-origin"
          title={basename}
          onLoad={() => setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)}
        />
      );
    }

    // Markdown
    if (ext === 'md') {
      return (
        <div className="p-6 overflow-y-auto flex-1">
          <div className="prose prose-sm prose-slate max-w-none
            prose-headings:font-semibold prose-headings:text-gray-900
            prose-p:text-[13px] prose-p:text-gray-600 prose-p:leading-relaxed
            prose-li:text-[13px] prose-li:text-gray-600
            prose-code:text-[12px] prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded
            prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:text-[12px]
          ">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{fileContent}</ReactMarkdown>
          </div>
        </div>
      );
    }

    // CSV — table
    if (ext === 'csv') {
      const lines = fileContent.split('\n').filter((l) => l.trim());
      const headers = lines[0]?.split(',').map((h) => h.trim()) ?? [];
      const rows = lines.slice(1).map((l) => l.split(',').map((c) => c.trim()));
      return (
        <div className="overflow-auto flex-1">
          <table className="min-w-full text-[12px]">
            <thead className="bg-gray-50 sticky top-0 z-10 border-b border-gray-200">
              <tr>
                <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-400 border-r border-gray-100 w-8 tabular-nums">#</th>
                {headers.map((h, i) => (
                  <th key={i} className="px-3 py-2 text-left text-[11px] font-semibold text-gray-600 border-r border-gray-100 last:border-r-0 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri} className={`border-b border-gray-50 ${ri % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'} hover:bg-blue-50/20 transition-colors`}>
                  <td className="px-3 py-1.5 text-gray-300 border-r border-gray-50 tabular-nums text-[11px]">{ri + 1}</td>
                  {headers.map((_, ci) => (
                    <td key={ci} className="px-3 py-1.5 text-gray-700 border-r border-gray-50 last:border-r-0 whitespace-nowrap">{row[ci] ?? ''}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // JSON
    if (ext === 'json') {
      let formatted = fileContent;
      try { formatted = JSON.stringify(JSON.parse(fileContent), null, 2); } catch {}
      return (
        <div className="overflow-auto flex-1 bg-[#1e1e1e]">
          <pre className="p-5 text-[12px] text-gray-200 font-mono leading-relaxed"><code>{formatted}</code></pre>
        </div>
      );
    }

    // Code / dark files
    const isDark = ['py', 'js', 'ts', 'tsx', 'jsx', 'sh', 'bash', 'sql', 'css', 'yaml', 'yml'].includes(ext);
    return (
      <div className={`overflow-auto flex-1 ${isDark ? 'bg-[#1e1e1e]' : 'bg-white'}`}>
        <pre className={`p-5 text-[12px] font-mono leading-relaxed whitespace-pre ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
          <code>{fileContent}</code>
        </pre>
      </div>
    );
  };

  const isText = !(/^(png|jpg|jpeg|gif|webp|svg)$/.test(ext));

  return (
    <div className="flex flex-col h-full overflow-hidden bg-white">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-100 bg-white flex-shrink-0 min-w-0">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1 flex-1 min-w-0 overflow-hidden">
          {dirParts.map((part, i) => (
            <React.Fragment key={i}>
              <span className="text-[11px] text-gray-300 truncate max-w-[80px]">{part}</span>
              <svg className="w-2.5 h-2.5 text-gray-200 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z" />
              </svg>
            </React.Fragment>
          ))}
          <span className="text-[12px] font-medium text-gray-700 truncate">{basename}</span>
        </div>

        {/* File type badge */}
        <FileTypeBadge ext={ext} />

        {/* Actions */}
        {fileContent && !error && !loading && (
          <div className="flex items-center gap-1 flex-shrink-0">
            {isText && (
              <button
                onClick={handleCopy}
                className={`flex items-center gap-1 px-2 py-1 text-[11px] rounded-md transition-colors ${
                  copied
                    ? 'text-emerald-600 bg-emerald-50'
                    : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                }`}
              >
                {copied ? (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                  </svg>
                ) : (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
                  </svg>
                )}
                {copied ? 'Copied' : 'Copy'}
              </button>
            )}
            <button
              onClick={handleDownload}
              className="flex items-center gap-1 px-2 py-1 text-[11px] text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              Download
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto flex flex-col">
        {renderContent()}
      </div>
    </div>
  );
}
