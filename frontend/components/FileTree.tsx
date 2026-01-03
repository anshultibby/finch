'use client';

import React, { useState, useEffect } from 'react';

interface FileItem {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

interface FileTreeProps {
  chatId: string;
  selectedFile?: string;
  onFileSelect: (filename: string) => void;
}

// Get icon for file type
const getFileIcon = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  
  switch (ext) {
    case 'py':
      return (
        <svg className="w-4 h-4 text-yellow-500" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm-.5 4.5c.276 0 .5.224.5.5v2c0 .276-.224.5-.5.5s-.5-.224-.5-.5V5c0-.276.224-.5.5-.5zm-3 1c.276 0 .5.224.5.5v5.5h3V9c0-.276.224-.5.5-.5s.5.224.5.5v3c0 .276-.224.5-.5.5h-4c-.276 0-.5-.224-.5-.5V6c0-.276.224-.5.5-.5zm7 7c.276 0 .5.224.5.5v5.5c0 .276-.224.5-.5.5h-4c-.276 0-.5-.224-.5-.5v-3c0-.276.224-.5.5-.5s.5.224.5.5v2.5h3V13c0-.276.224-.5.5-.5zm-.5 5.5c-.276 0-.5-.224-.5-.5v-2c0-.276.224-.5.5-.5s.5.224.5.5v2c0 .276-.224.5-.5.5z"/>
        </svg>
      );
    case 'js':
    case 'ts':
    case 'tsx':
    case 'jsx':
      return (
        <svg className="w-4 h-4 text-yellow-400" viewBox="0 0 24 24" fill="currentColor">
          <path d="M0 0h24v24H0V0zm22.034 18.276c-.175-1.095-.888-2.015-3.003-2.873-.736-.345-1.554-.585-1.797-1.14-.091-.33-.105-.51-.046-.705.15-.646.915-.84 1.515-.66.39.12.75.42.976.9 1.034-.676 1.034-.676 1.755-1.125-.27-.42-.404-.601-.586-.78-.63-.705-1.469-1.065-2.834-1.034l-.705.089c-.676.165-1.32.525-1.71 1.005-1.14 1.291-.811 3.541.569 4.471 1.365 1.02 3.361 1.244 3.616 2.205.24 1.17-.87 1.545-1.966 1.41-.811-.18-1.26-.586-1.755-1.336l-1.83 1.051c.21.48.45.689.81 1.109 1.74 1.756 6.09 1.666 6.871-1.004.029-.09.24-.705.074-1.65l.046.067zm-8.983-7.245h-2.248c0 1.938-.009 3.864-.009 5.805 0 1.232.063 2.363-.138 2.711-.33.689-1.18.601-1.566.48-.396-.196-.597-.466-.83-.855-.063-.105-.11-.196-.127-.196l-1.825 1.125c.305.63.75 1.172 1.324 1.517.855.51 2.004.675 3.207.405.783-.226 1.458-.691 1.811-1.411.51-.93.402-2.07.397-3.346.012-2.054 0-4.109 0-6.179l.004-.056z"/>
        </svg>
      );
    case 'json':
      return (
        <svg className="w-4 h-4 text-orange-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 6h2a2 2 0 012 2v2a2 2 0 01-2 2H4m0-6v6m16-6h-2a2 2 0 00-2 2v2a2 2 0 002 2h2m0-6v6"/>
          <circle cx="12" cy="12" r="1"/>
        </svg>
      );
    case 'csv':
      return (
        <svg className="w-4 h-4 text-green-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14,2 14,8 20,8"/>
          <line x1="8" y1="13" x2="16" y2="13"/>
          <line x1="8" y1="17" x2="16" y2="17"/>
          <line x1="10" y1="9" x2="10" y2="21"/>
        </svg>
      );
    case 'md':
      return (
        <svg className="w-4 h-4 text-blue-400" viewBox="0 0 24 24" fill="currentColor">
          <path d="M22.27 19.385H1.73A1.73 1.73 0 010 17.655V6.345a1.73 1.73 0 011.73-1.73h20.54A1.73 1.73 0 0124 6.345v11.31a1.73 1.73 0 01-1.73 1.73zM5.769 15.923v-4.5l2.308 2.885 2.307-2.885v4.5h2.308V8.077h-2.308l-2.307 2.885-2.308-2.885H3.461v7.846h2.308zM21.232 12h-2.309V8.077h-2.307V12h-2.308l3.461 4.039 3.463-4.039z"/>
        </svg>
      );
    case 'html':
      return (
        <svg className="w-4 h-4 text-orange-500" viewBox="0 0 24 24" fill="currentColor">
          <path d="M1.5 0h21l-1.91 21.563L11.977 24l-8.564-2.438L1.5 0zm7.031 9.75l-.232-2.718 10.059.003.23-2.622L5.412 4.41l.698 8.01h9.126l-.326 3.426-2.91.804-2.955-.81-.188-2.11H6.248l.33 4.171L12 19.351l5.379-1.443.744-8.157H8.531z"/>
        </svg>
      );
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'webp':
    case 'svg':
      return (
        <svg className="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21,15 16,10 5,21"/>
        </svg>
      );
    default:
      return (
        <svg className="w-4 h-4 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14,2 14,8 20,8"/>
        </svg>
      );
  }
};

// Format file size
const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function FileTree({ chatId, selectedFile, onFileSelect }: FileTreeProps) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    const loadFiles = async () => {
      if (!chatId) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/chat-files/${chatId}`);
        
        if (response.ok) {
          const data = await response.json();
          setFiles(data);
        } else {
          setError('Failed to load files');
        }
      } catch (err) {
        console.error('Error loading files:', err);
        setError('Failed to load files');
      } finally {
        setLoading(false);
      }
    };
    
    loadFiles();
  }, [chatId]);

  if (loading) {
    return (
      <div className="w-48 bg-gray-50 border-r border-gray-200 flex flex-col">
        <div className="px-2 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
          <span>Explorer</span>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="w-4 h-4 border-2 border-gray-200 border-t-blue-500 rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error || files.length === 0) {
    return (
      <div className="w-48 bg-gray-50 border-r border-gray-200 flex flex-col">
        <div className="px-2 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
          <span>Explorer</span>
        </div>
        <div className="px-3 py-4 text-xs text-gray-400 text-center">
          {error || 'No files yet'}
        </div>
      </div>
    );
  }

  return (
    <div className="w-48 bg-gray-50 border-r border-gray-200 flex flex-col overflow-hidden">
      {/* Header - compact */}
      <div className="px-2 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center justify-between">
        <span>Explorer</span>
        <span className="text-[10px] text-gray-400 font-normal normal-case">{files.length} files</span>
      </div>
      
      {/* Folder section */}
      <div className="flex-1 overflow-y-auto">
        {/* Folder header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
        >
          <svg 
            className={`w-3 h-3 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} 
            viewBox="0 0 24 24" 
            fill="currentColor"
          >
            <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
          </svg>
          <svg className="w-4 h-4 text-amber-500" viewBox="0 0 24 24" fill="currentColor">
            <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
          </svg>
          <span className="truncate">chat-files</span>
        </button>
        
        {/* Files list */}
        {isExpanded && (
          <div className="pl-4">
            {files.map((file) => (
              <button
                key={file.id}
                onClick={() => onFileSelect(file.filename)}
                className={`w-full flex items-center gap-2 px-2 py-0.5 text-left transition-colors group ${
                  selectedFile === file.filename
                    ? 'bg-blue-100 text-blue-900 border-l-2 border-blue-500'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                {getFileIcon(file.filename)}
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] truncate">{file.filename}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
      
      {/* Footer with selected file info - removed, filename now shows at top of content */}
    </div>
  );
}

