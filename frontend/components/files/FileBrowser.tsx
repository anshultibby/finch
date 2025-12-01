'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface FileItem {
  name: string;
  path: string;
  size: number;
  modified: string;
}

interface Strategy {
  name: string;
  filename: string;
  path: string;
  size: number;
  modified: string;
}

interface FileBrowserProps {
  chatId: string;
  onFileSelect: (content: string, filename: string, type: 'strategy' | 'chat' | 'user') => void;
}

export default function FileBrowser({ chatId, onFileSelect }: FileBrowserProps) {
  const { user } = useAuth();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [chatFiles, setChatFiles] = useState<FileItem[]>([]);
  const [userFiles, setUserFiles] = useState<FileItem[]>([]);
  const [selectedSection, setSelectedSection] = useState<'strategies' | 'chat' | 'user'>('strategies');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadFiles();
  }, [chatId, user?.id]);

  const loadFiles = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Load strategies
      const stratRes = await fetch(`/api/chat/${chatId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: 'list_code_strategies',
          user_id: user.id,
          mode: 'tool_only'
        })
      });
      
      if (stratRes.ok) {
        const data = await stratRes.json();
        // Parse tool result from response
        if (data.response && typeof data.response === 'string') {
          try {
            const parsed = JSON.parse(data.response);
            if (parsed.strategies) {
              setStrategies(parsed.strategies);
            }
          } catch (e) {
            console.error('Error parsing strategies:', e);
          }
        }
      }

      // Load chat files
      const chatRes = await fetch(`/api/chat/${chatId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: 'list_chat_files',
          user_id: user.id,
          mode: 'tool_only'
        })
      });
      
      if (chatRes.ok) {
        const data = await chatRes.json();
        if (data.response && typeof data.response === 'string') {
          try {
            const parsed = JSON.parse(data.response);
            if (parsed.files) {
              setChatFiles(parsed.files);
            }
          } catch (e) {
            console.error('Error parsing chat files:', e);
          }
        }
      }
    } catch (err) {
      console.error('Error loading files:', err);
      setError('Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (filename: string, type: 'strategy' | 'chat' | 'user') => {
    if (!user?.id) return;
    
    try {
      let toolName = '';
      let params: any = {};
      
      if (type === 'strategy') {
        toolName = 'get_code_strategy';
        params = { strategy_name: filename };
      } else if (type === 'chat') {
        toolName = 'read_chat_file';
        params = { filename };
      }
      
      const res = await fetch(`/api/chat/${chatId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: JSON.stringify({ tool: toolName, params }),
          user_id: user.id,
          mode: 'tool_only'
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.response && typeof data.response === 'string') {
          try {
            const parsed = JSON.parse(data.response);
            if (parsed.content) {
              onFileSelect(parsed.content, filename, type);
            }
          } catch (e) {
            console.error('Error parsing file content:', e);
          }
        }
      }
    } catch (err) {
      console.error('Error loading file:', err);
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

  return (
    <div className="h-full flex flex-col bg-white border-r border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900">📁 Files</h2>
          <button
            onClick={loadFiles}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            🔄
          </button>
        </div>

        {/* Section Tabs */}
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setSelectedSection('strategies')}
            className={`flex-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              selectedSection === 'strategies'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Strategies
          </button>
          <button
            onClick={() => setSelectedSection('chat')}
            className={`flex-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              selectedSection === 'chat'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Chat Files
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
            {error}
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Strategies */}
            {selectedSection === 'strategies' && (
              <div>
                {strategies.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-3xl mb-2">📝</div>
                    <p className="text-sm">No strategies yet</p>
                    <p className="text-xs mt-1">Create one in chat!</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {strategies.map((strategy) => (
                      <button
                        key={strategy.path}
                        onClick={() => loadFileContent(strategy.name, 'strategy')}
                        className="w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors group"
                      >
                        <div className="flex items-start gap-2">
                          <div className="text-xl">📊</div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-900 truncate group-hover:text-blue-600">
                              {strategy.name}
                            </div>
                            <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
                              <span>{formatFileSize(strategy.size)}</span>
                              <span>•</span>
                              <span>{formatDate(strategy.modified)}</span>
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Chat Files */}
            {selectedSection === 'chat' && (
              <div>
                {chatFiles.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-3xl mb-2">📄</div>
                    <p className="text-sm">No chat files yet</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {chatFiles.map((file) => (
                      <button
                        key={file.path}
                        onClick={() => loadFileContent(file.name, 'chat')}
                        className="w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors group"
                      >
                        <div className="flex items-start gap-2">
                          <div className="text-xl">
                            {file.name.endsWith('.json') ? '📋' : 
                             file.name.endsWith('.csv') ? '📊' : 
                             file.name.endsWith('.md') ? '📝' : '📄'}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-900 truncate group-hover:text-blue-600">
                              {file.name}
                            </div>
                            <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
                              <span>{formatFileSize(file.size)}</span>
                              <span>•</span>
                              <span>{formatDate(file.modified)}</span>
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

