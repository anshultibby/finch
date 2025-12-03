'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface FileItem {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

interface FileBrowserProps {
  chatId: string;
  onFileSelect: (content: string, filename: string, type: 'strategy' | 'chat' | 'user') => void;
}

export default function FileBrowser({ chatId, onFileSelect }: FileBrowserProps) {
  const { user } = useAuth();
  const [chatFiles, setChatFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId, user?.id]);

  const loadFiles = async () => {
    if (!user?.id || !chatId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Load chat files from the backend
      const chatRes = await fetch(`${apiUrl}/api/chat-files/${chatId}`);
      
      if (chatRes.ok) {
        const files = await chatRes.json();
        console.log('📁 Loaded chat files:', files);
        setChatFiles(files);
      } else {
        const errorText = await chatRes.text();
        console.error('Failed to load chat files:', errorText);
        setError('Failed to load files');
      }
    } catch (err) {
      console.error('Error loading files:', err);
      setError('Failed to load files. Is the backend server running?');
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (filename: string, type: 'strategy' | 'chat' | 'user') => {
    if (!user?.id) return;
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      if (type === 'chat') {
        const res = await fetch(`${apiUrl}/api/chat-files/${chatId}/download/${filename}`);
        
        if (res.ok) {
          const content = await res.text();
          console.log('✅ Loaded file content:', filename);
          onFileSelect(content, filename, type);
        } else {
          console.error('Failed to load file content:', await res.text());
          setError('Failed to load file content');
        }
      }
    } catch (err) {
      console.error('Error loading file:', err);
      setError('Failed to load file. Is the backend server running?');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return isoString;
    }
  };

  const getFileIcon = (filename: string) => {
    if (filename.endsWith('.json')) return '📋';
    if (filename.endsWith('.csv')) return '📊';
    if (filename.endsWith('.md')) return '📝';
    if (filename.endsWith('.py')) return '🐍';
    if (filename.endsWith('.js') || filename.endsWith('.ts')) return '💻';
    return '📄';
  };

  return (
    <div className="h-full flex flex-col bg-white border-r border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">📁 Chat Files</h2>
          <button
            onClick={loadFiles}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            🔄
          </button>
        </div>
      </div>

      {/* File List */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading && (
          <div className="text-center py-8 text-gray-500">
            <div className="animate-spin text-2xl mb-2">⏳</div>
            Loading files...
          </div>
        )}

        {error && (
          <div className="text-center py-8 text-red-600">
            <div className="text-2xl mb-2">⚠️</div>
            <p className="text-sm">{error}</p>
            <button
              onClick={loadFiles}
              className="mt-3 px-3 py-1.5 text-sm bg-red-100 hover:bg-red-200 rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {!loading && !error && (
          <div>
            {chatFiles.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <div className="text-3xl mb-2">📄</div>
                <p className="text-sm">No files yet</p>
                <p className="text-xs mt-1 text-gray-400">Files created in chat will appear here</p>
              </div>
            ) : (
              <div className="space-y-1">
                {chatFiles.map((file) => (
                  <button
                    key={file.id}
                    onClick={() => loadFileContent(file.filename, 'chat')}
                    className="w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors group"
                  >
                    <div className="flex items-start gap-2">
                      <div className="text-xl">
                        {getFileIcon(file.filename)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 truncate group-hover:text-blue-600">
                          {file.filename}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
                          <span className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px] font-medium">
                            {file.file_type}
                          </span>
                          <span>•</span>
                          <span>{formatFileSize(file.size_bytes)}</span>
                          <span>•</span>
                          <span>{formatDate(file.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

