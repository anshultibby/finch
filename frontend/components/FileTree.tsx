'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';

export interface FileItem {
  filename: string; // relative path, e.g. "results/chart.png"
  file_type: string;
  size_bytes: number;
}

interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: TreeNode[];
  file?: FileItem;
}

interface FileTreeProps {
  chatId: string;
  selectedFile?: string;
  onFileSelect: (filename: string) => void;
  onFilesLoaded?: (files: FileItem[]) => void;
  cachedFiles?: FileItem[];
}

function buildTree(files: FileItem[]): TreeNode[] {
  const dirMap = new Map<string, TreeNode>();
  const root: TreeNode[] = [];

  const sorted = [...files].sort((a, b) => a.filename.localeCompare(b.filename));

  for (const file of sorted) {
    const parts = file.filename.split('/');

    for (let i = 0; i < parts.length - 1; i++) {
      const dirPath = parts.slice(0, i + 1).join('/');
      if (!dirMap.has(dirPath)) {
        const dir: TreeNode = { name: parts[i], path: dirPath, isDir: true, children: [] };
        dirMap.set(dirPath, dir);
        if (i === 0) {
          root.push(dir);
        } else {
          const parentPath = parts.slice(0, i).join('/');
          dirMap.get(parentPath)!.children.push(dir);
        }
      }
    }

    const fileNode: TreeNode = {
      name: parts[parts.length - 1],
      path: file.filename,
      isDir: false,
      children: [],
      file,
    };

    if (parts.length === 1) {
      root.push(fileNode);
    } else {
      const parentPath = parts.slice(0, -1).join('/');
      dirMap.get(parentPath)!.children.push(fileNode);
    }
  }

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.isDir && !b.isDir) return -1;
      if (!a.isDir && b.isDir) return 1;
      return a.name.localeCompare(b.name);
    });
    for (const node of nodes) {
      if (node.isDir) sortNodes(node.children);
    }
  };
  sortNodes(root);

  return root;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}M`;
}

function FileIcon({ name }: { name: string }) {
  const ext = name.split('.').pop()?.toLowerCase() || '';

  const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'];
  if (imageExts.includes(ext)) {
    return (
      <div className="w-[18px] h-[18px] rounded-[3px] bg-purple-100 flex items-center justify-center flex-shrink-0">
        <svg className="w-2.5 h-2.5 text-purple-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21,15 16,10 5,21" />
        </svg>
      </div>
    );
  }

  type IconConfig = { label: string; bg: string; text: string };
  const map: Record<string, IconConfig> = {
    py:   { label: 'py',  bg: 'bg-blue-100',   text: 'text-blue-600' },
    js:   { label: 'js',  bg: 'bg-yellow-100', text: 'text-yellow-700' },
    ts:   { label: 'ts',  bg: 'bg-blue-100',   text: 'text-blue-700' },
    tsx:  { label: 'tsx', bg: 'bg-cyan-100',   text: 'text-cyan-700' },
    jsx:  { label: 'jsx', bg: 'bg-cyan-100',   text: 'text-cyan-700' },
    json: { label: '{}',  bg: 'bg-orange-100', text: 'text-orange-600' },
    md:   { label: 'md',  bg: 'bg-indigo-100', text: 'text-indigo-600' },
    csv:  { label: 'csv', bg: 'bg-green-100',  text: 'text-green-700' },
    html: { label: 'htm', bg: 'bg-red-100',    text: 'text-red-600' },
    css:  { label: 'css', bg: 'bg-sky-100',    text: 'text-sky-600' },
    sh:   { label: 'sh',  bg: 'bg-gray-100',   text: 'text-gray-500' },
    bash: { label: 'sh',  bg: 'bg-gray-100',   text: 'text-gray-500' },
    sql:  { label: 'sql', bg: 'bg-purple-100', text: 'text-purple-600' },
    yaml: { label: 'yml', bg: 'bg-amber-100',  text: 'text-amber-700' },
    yml:  { label: 'yml', bg: 'bg-amber-100',  text: 'text-amber-700' },
    txt:  { label: 'txt', bg: 'bg-gray-100',   text: 'text-gray-500' },
    log:  { label: 'log', bg: 'bg-gray-100',   text: 'text-gray-500' },
  };

  const c = map[ext] ?? { label: ext.slice(0, 3) || '?', bg: 'bg-gray-100', text: 'text-gray-400' };
  return (
    <div className={`w-[18px] h-[18px] rounded-[3px] flex items-center justify-center flex-shrink-0 ${c.bg}`}>
      <span className={`text-[7.5px] font-bold leading-none tracking-tight ${c.text}`}>{c.label}</span>
    </div>
  );
}

function TreeNodeView({
  node, depth, selectedFile, onSelect, expandedDirs, onToggleDir,
}: {
  node: TreeNode;
  depth: number;
  selectedFile?: string;
  onSelect: (path: string) => void;
  expandedDirs: Set<string>;
  onToggleDir: (path: string) => void;
}) {
  const indent = depth * 14;
  const isExpanded = expandedDirs.has(node.path);

  if (node.isDir) {
    return (
      <div>
        <button
          onClick={() => onToggleDir(node.path)}
          className="w-full flex items-center gap-1.5 py-[3px] text-left hover:bg-gray-50 transition-colors group rounded-sm mx-1"
          style={{ paddingLeft: `${6 + indent}px`, paddingRight: '6px' }}
        >
          <svg
            className={`w-3 h-3 text-gray-300 flex-shrink-0 transition-transform duration-150 ${isExpanded ? 'rotate-90' : ''}`}
            viewBox="0 0 24 24" fill="currentColor"
          >
            <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z" />
          </svg>
          <svg
            className="w-[15px] h-[15px] flex-shrink-0"
            viewBox="0 0 24 24"
            fill={isExpanded ? '#fbbf24' : '#fcd34d'}
          >
            <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
          </svg>
          <span className="text-[12px] text-gray-700 truncate font-medium">{node.name}</span>
          <span className="ml-auto text-[10px] text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
            {node.children.length}
          </span>
        </button>
        {isExpanded && (
          <div>
            {node.children.map((child) => (
              <TreeNodeView
                key={child.path}
                node={child}
                depth={depth + 1}
                selectedFile={selectedFile}
                onSelect={onSelect}
                expandedDirs={expandedDirs}
                onToggleDir={onToggleDir}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  const isSelected = selectedFile === node.path;
  return (
    <button
      onClick={() => onSelect(node.path)}
      title={node.file ? `${node.path} · ${formatBytes(node.file.size_bytes)}` : node.path}
      className={`w-full flex items-center gap-1.5 py-[3px] text-left transition-colors rounded-sm mx-1 group ${
        isSelected
          ? 'bg-blue-50'
          : 'hover:bg-gray-50'
      }`}
      style={{ paddingLeft: `${6 + indent}px`, paddingRight: '6px' }}
    >
      <FileIcon name={node.name} />
      <span className={`text-[12px] truncate flex-1 ${isSelected ? 'text-blue-800 font-medium' : 'text-gray-700'}`}>
        {node.name}
      </span>
      {node.file && (
        <span className="text-[10px] text-gray-300 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          {formatBytes(node.file.size_bytes)}
        </span>
      )}
    </button>
  );
}

export default function FileTree({ chatId, selectedFile, onFileSelect, onFilesLoaded }: FileTreeProps) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const onFilesLoadedRef = useRef(onFilesLoaded);
  onFilesLoadedRef.current = onFilesLoaded;

  const fetchFiles = useCallback(async (silent = false) => {
    if (!chatId) return;
    if (!silent) setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/chat-files/${chatId}`);
      if (res.ok) {
        const data: FileItem[] = await res.json();
        setFiles(data);
        onFilesLoadedRef.current?.(data);

        setExpandedDirs((prev) => {
          if (prev.size > 0) return prev;
          const topDirs = new Set<string>();
          for (const f of data) {
            const parts = f.filename.split('/');
            if (parts.length > 1) topDirs.add(parts[0]);
          }
          return topDirs;
        });
      }
    } catch {
      // silent fail on poll
    } finally {
      if (!silent) setLoading(false);
    }
  }, [chatId]);

  useEffect(() => {
    setFiles([]);
    setLoading(true);
    fetchFiles(false);
  }, [fetchFiles]);

  useEffect(() => {
    const id = setInterval(() => fetchFiles(true), 3000);
    return () => clearInterval(id);
  }, [fetchFiles]);

  const toggleDir = (path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const tree = buildTree(files);

  return (
    <div className="w-52 bg-white border-r border-gray-100 flex flex-col overflow-hidden flex-shrink-0">
      {/* Header */}
      <div className="px-3 py-2.5 flex items-center justify-between border-b border-gray-100 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-gray-500 tracking-wide">Files</span>
          {files.length > 0 && (
            <span className="text-[10px] text-gray-300 tabular-nums">{files.length}</span>
          )}
        </div>
        <button
          onClick={() => fetchFiles(false)}
          className="p-1 rounded hover:bg-gray-100 text-gray-300 hover:text-gray-500 transition-colors"
          title="Refresh"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M2.985 19.644l3.181-3.183" />
          </svg>
        </button>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1.5 space-y-px">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <div className="w-4 h-4 border-2 border-gray-100 border-t-gray-400 rounded-full animate-spin" />
          </div>
        ) : tree.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <svg className="w-6 h-6 text-gray-200 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
            </svg>
            <p className="text-[11px] text-gray-300">No files yet</p>
          </div>
        ) : (
          tree.map((node) => (
            <TreeNodeView
              key={node.path}
              node={node}
              depth={0}
              selectedFile={selectedFile}
              onSelect={onFileSelect}
              expandedDirs={expandedDirs}
              onToggleDir={toggleDir}
            />
          ))
        )}
      </div>
    </div>
  );
}
