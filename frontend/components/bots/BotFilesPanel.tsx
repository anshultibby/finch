'use client';

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { botsApi } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface SandboxFile {
  name: string;
  type: 'file' | 'directory';
  size: number | null;
  path: string;
}

interface BotFilesPanelProps {
  userId: string;
  botId: string;
  onBack: () => void;
}

function formatSize(bytes: number | null): string {
  if (bytes == null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(name: string, type: string) {
  if (type === 'directory') {
    return (
      <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
      </svg>
    );
  }
  const lower = name.toLowerCase();
  if (lower.endsWith('.md')) {
    return (
      <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    );
  }
  if (lower.endsWith('.py')) {
    return (
      <svg className="w-4 h-4 text-yellow-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
      </svg>
    );
  }
  if (lower.endsWith('.csv')) {
    return (
      <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M10.875 12h-7.5c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125" />
      </svg>
    );
  }
  if (/\.(png|jpg|jpeg|gif|webp|bmp|svg|ico)$/i.test(lower)) {
    return (
      <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
      </svg>
    );
  }
  return (
    <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

const LANGUAGE_MAP: Record<string, string> = {
  py: 'python',
  js: 'javascript',
  ts: 'typescript',
  tsx: 'tsx',
  jsx: 'jsx',
  json: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'toml',
  sh: 'bash',
  bash: 'bash',
  zsh: 'bash',
  sql: 'sql',
  html: 'html',
  css: 'css',
  xml: 'xml',
  rs: 'rust',
  go: 'go',
  rb: 'ruby',
  java: 'java',
  c: 'c',
  cpp: 'cpp',
  h: 'c',
  hpp: 'cpp',
  env: 'bash',
  dockerfile: 'docker',
  tf: 'hcl',
};

function getLanguage(filename: string): string | null {
  const lower = filename.toLowerCase();
  const ext = lower.includes('.') ? lower.split('.').pop()! : lower;
  return LANGUAGE_MAP[ext] || null;
}

function isMarkdown(name: string) {
  return name.toLowerCase().endsWith('.md');
}

function isImage(name: string) {
  return /\.(png|jpg|jpeg|gif|webp|bmp|svg|ico)$/i.test(name);
}

function isCsv(name: string) {
  return name.toLowerCase().endsWith('.csv');
}

function isHiddenOrSensitive(name: string): boolean {
  return name.startsWith('.');
}

function parseCsv(content: string): { headers: string[]; rows: string[][] } {
  const lines = content.split('\n').filter((l) => l.trim());
  if (lines.length === 0) return { headers: [], rows: [] };

  // Simple CSV parse — handles quoted fields with commas
  const parseLine = (line: string): string[] => {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += ch;
      }
    }
    result.push(current.trim());
    return result;
  };

  const headers = parseLine(lines[0]);
  const rows = lines.slice(1).map(parseLine);
  return { headers, rows };
}

export default function BotFilesPanel({ userId, botId, onBack }: BotFilesPanelProps) {
  const [files, setFiles] = useState<SandboxFile[]>([]);
  const [currentPath, setCurrentPath] = useState('');
  const [pathHistory, setPathHistory] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // File viewer state
  const [viewingFile, setViewingFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileMeta, setFileMeta] = useState<{ binary?: boolean; mime?: string; encoding?: string } | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const triggerDownload = useCallback(async (url: string, filename: string) => {
    setDownloading(true);
    try {
      const res = await fetch(url, { headers: { 'X-User-ID': userId } });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(a.href);
      a.remove();
    } catch (e) {
      console.error('Download error:', e);
    } finally {
      setDownloading(false);
    }
  }, [userId]);

  const downloadFile = useCallback((path: string) => {
    const filename = path.split('/').pop() || 'file';
    const url = botsApi.downloadSandboxFileUrl(userId, botId, path);
    triggerDownload(url, filename);
  }, [userId, botId, triggerDownload]);

  const downloadAll = useCallback(() => {
    const url = botsApi.downloadAllSandboxFilesUrl(userId, botId, currentPath);
    const zipName = currentPath
      ? `bot-${botId.slice(0, 8)}-${currentPath.replace(/\//g, '-')}.zip`
      : `bot-${botId.slice(0, 8)}-files.zip`;
    triggerDownload(url, zipName);
  }, [userId, botId, currentPath, triggerDownload]);

  const fetchFiles = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await botsApi.listSandboxFiles(userId, botId, path);
      setFiles(data.files || []);
      if (data.error) setError(data.error);
    } catch (e) {
      setError('Failed to load files');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, [userId, botId]);

  useEffect(() => {
    fetchFiles(currentPath);
  }, [currentPath, fetchFiles]);

  const navigateTo = (path: string) => {
    setPathHistory((prev) => [...prev, currentPath]);
    setCurrentPath(path);
    setViewingFile(null);
    setFileContent(null);
    setFileMeta(null);
  };

  const navigateBack = () => {
    if (viewingFile) {
      setViewingFile(null);
      setFileContent(null);
      setFileMeta(null);
      return;
    }
    const prev = pathHistory[pathHistory.length - 1];
    if (prev !== undefined) {
      setPathHistory((h) => h.slice(0, -1));
      setCurrentPath(prev);
    }
  };

  const openFile = async (file: SandboxFile) => {
    if (file.type === 'directory') {
      navigateTo(file.path);
      return;
    }
    setFileLoading(true);
    setViewingFile(file.path);
    setFileMeta(null);
    try {
      const data = await botsApi.readSandboxFile(userId, botId, file.path);
      if (data) {
        setFileContent(data.content);
        setFileMeta({ binary: data.binary, mime: data.mime, encoding: data.encoding });
      } else {
        setFileContent('[Failed to read file]');
      }
    } catch {
      setFileContent('[Failed to read file]');
    } finally {
      setFileLoading(false);
    }
  };

  const breadcrumbs = currentPath ? currentPath.split('/') : [];
  const currentFileName = viewingFile ? viewingFile.split('/').pop() || '' : '';

  // Render file content based on type
  const renderFileContent = () => {
    if (fileLoading) {
      return (
        <div className="flex items-center justify-center h-32">
          <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-400 rounded-full animate-spin" />
        </div>
      );
    }
    if (fileContent == null) return null;

    // Image files (base64 from backend)
    if (isImage(currentFileName) && fileMeta?.encoding === 'base64' && fileMeta?.mime) {
      return (
        <div className="p-6 flex items-center justify-center">
          <img
            src={`data:${fileMeta.mime};base64,${fileContent}`}
            alt={currentFileName}
            className="max-w-full max-h-[70vh] rounded-lg border border-gray-100 shadow-sm"
          />
        </div>
      );
    }

    // Binary file fallback
    if (fileMeta?.binary && fileMeta?.encoding !== 'base64') {
      return (
        <div className="flex flex-col items-center justify-center h-48 text-gray-400">
          <svg className="w-8 h-8 mb-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
          <p className="text-sm font-medium">Binary file</p>
          <p className="text-xs mt-1">Cannot display this file type</p>
        </div>
      );
    }

    // Markdown
    if (isMarkdown(currentFileName)) {
      return (
        <div className="px-6 py-5 max-w-2xl">
          <div className="prose prose-sm prose-gray max-w-none
            prose-headings:font-semibold prose-headings:text-gray-900
            prose-h1:text-lg prose-h1:border-b prose-h1:border-gray-100 prose-h1:pb-2 prose-h1:mb-4
            prose-h2:text-[15px] prose-h2:mt-6 prose-h2:mb-2
            prose-h3:text-[13px] prose-h3:mt-4 prose-h3:mb-1.5
            prose-p:text-[13px] prose-p:text-gray-600 prose-p:leading-relaxed
            prose-li:text-[13px] prose-li:text-gray-600
            prose-strong:text-gray-800
            prose-code:text-[12px] prose-code:bg-gray-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:border prose-code:border-gray-100
            prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-100 prose-pre:rounded-xl prose-pre:text-[12px]
          ">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{fileContent}</ReactMarkdown>
          </div>
        </div>
      );
    }

    // CSV — table view
    if (isCsv(currentFileName)) {
      return <CsvTableView content={fileContent} />;
    }

    // Code files with syntax highlighting
    const lang = getLanguage(currentFileName);
    if (lang) {
      return (
        <div className="p-4">
          <SyntaxHighlighter
            language={lang}
            style={oneLight}
            showLineNumbers
            lineNumberStyle={{ color: '#c0c0c0', fontSize: '11px', minWidth: '2.5em', paddingRight: '1em' }}
            customStyle={{
              margin: 0,
              borderRadius: '12px',
              border: '1px solid #f0f0f0',
              fontSize: '12px',
              lineHeight: '1.6',
              background: '#fafafa',
            }}
            wrapLongLines
          >
            {fileContent}
          </SyntaxHighlighter>
        </div>
      );
    }

    // Plain text fallback
    return (
      <div className="p-4">
        <pre className="text-[12px] text-gray-700 font-mono leading-relaxed bg-gray-50 border border-gray-100 rounded-xl p-4 overflow-x-auto whitespace-pre-wrap break-words">
          {fileContent}
        </pre>
      </div>
    );
  };

  // Render file viewer
  if (viewingFile) {
    return (
      <div className="flex flex-col h-full bg-white">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 shrink-0">
          <button
            onClick={navigateBack}
            className="p-1 -ml-1 text-gray-400 hover:text-gray-600 transition-colors rounded-lg hover:bg-gray-50"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>
          <div className="flex items-center gap-2 min-w-0">
            {getFileIcon(currentFileName, 'file')}
            <span className="text-sm font-medium text-gray-900 truncate">{currentFileName}</span>
          </div>
          <span className="text-[11px] text-gray-400 truncate ml-auto mr-2">{viewingFile}</span>
          {!isHiddenOrSensitive(currentFileName) && (
            <button
              onClick={() => viewingFile && downloadFile(viewingFile)}
              disabled={downloading}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors rounded-lg hover:bg-gray-50 disabled:opacity-50 shrink-0"
              title="Download file"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {renderFileContent()}
        </div>
      </div>
    );
  }

  // Render file navigator
  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 shrink-0">
        <button
          onClick={currentPath ? navigateBack : onBack}
          className="p-1 -ml-1 text-gray-400 hover:text-gray-600 transition-colors rounded-lg hover:bg-gray-50"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
        </svg>
        <div className="flex items-center gap-1 min-w-0 text-sm">
          <button
            onClick={() => { setCurrentPath(''); setPathHistory([]); }}
            className="text-gray-500 hover:text-gray-700 font-medium shrink-0"
          >
            /
          </button>
          {breadcrumbs.map((part, i) => (
            <React.Fragment key={i}>
              <span className="text-gray-300">/</span>
              <button
                onClick={() => {
                  const newPath = breadcrumbs.slice(0, i + 1).join('/');
                  setCurrentPath(newPath);
                  setPathHistory((h) => h.slice(0, i));
                }}
                className={`truncate ${i === breadcrumbs.length - 1 ? 'text-gray-900 font-medium' : 'text-gray-500 hover:text-gray-700'}`}
              >
                {part}
              </button>
            </React.Fragment>
          ))}
        </div>
        <button
          onClick={() => fetchFiles(currentPath)}
          className="ml-auto p-1 text-gray-400 hover:text-gray-600 transition-colors rounded-lg hover:bg-gray-50"
          title="Refresh"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M2.985 19.644l3.181-3.183" />
          </svg>
        </button>
      </div>

      {/* File list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-400 rounded-full animate-spin" />
          </div>
        ) : error && files.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <svg className="w-8 h-8 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
            </svg>
            <p className="text-sm font-medium text-gray-500">Sandbox not available</p>
            <p className="text-xs text-gray-400 mt-1">Start a chat to initialize the sandbox environment.</p>
          </div>
        ) : files.length === 0 ? (
          <div className="p-6 text-center text-sm text-gray-400">
            Empty directory
          </div>
        ) : (
          <div className="py-1">
            {files.map((file) => (
              <button
                key={file.path}
                onClick={() => openFile(file)}
                className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-50 transition-colors group"
              >
                {getFileIcon(file.name, file.type)}
                <span className="text-[13px] text-gray-700 truncate flex-1 group-hover:text-gray-900">
                  {file.name}
                </span>
                {file.type === 'file' && file.size != null && (
                  <span className="text-[11px] text-gray-400 tabular-nums shrink-0">
                    {formatSize(file.size)}
                  </span>
                )}
                {file.type === 'directory' && (
                  <svg className="w-3.5 h-3.5 text-gray-300 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** CSV table viewer with sticky header and alternating rows */
function CsvTableView({ content }: { content: string }) {
  const { headers, rows } = useMemo(() => parseCsv(content), [content]);

  if (headers.length === 0) {
    return (
      <div className="p-6 text-center text-sm text-gray-400">
        Empty CSV file
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
          <table className="w-full text-[12px]">
            <thead className="sticky top-0 z-10">
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-3 py-2.5 text-left font-semibold text-gray-500 text-[11px] uppercase tracking-wider border-r border-gray-100 bg-gray-50 w-10">
                  #
                </th>
                {headers.map((h, i) => (
                  <th
                    key={i}
                    className="px-3 py-2.5 text-left font-semibold text-gray-700 whitespace-nowrap border-r border-gray-100 last:border-r-0 bg-gray-50"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr
                  key={ri}
                  className={`border-b border-gray-50 last:border-b-0 ${ri % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-blue-50/40 transition-colors`}
                >
                  <td className="px-3 py-2 text-gray-400 text-[11px] tabular-nums border-r border-gray-100">
                    {ri + 1}
                  </td>
                  {headers.map((_, ci) => (
                    <td
                      key={ci}
                      className="px-3 py-2 text-gray-700 whitespace-nowrap border-r border-gray-100 last:border-r-0"
                    >
                      {row[ci] ?? ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-3 py-2 bg-gray-50 border-t border-gray-200 text-[11px] text-gray-400">
          {rows.length} row{rows.length !== 1 ? 's' : ''} x {headers.length} column{headers.length !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  );
}
