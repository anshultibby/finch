'use client';

import React, { useState } from 'react';
import FileTree from './FileTree';
import FileViewer from './FileViewer';
import type { FileItem } from './FileTree';

interface FilesPanelProps {
  chatId: string | null;
}

export default function FilesPanel({ chatId }: FilesPanelProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [cachedFiles, setCachedFiles] = useState<FileItem[]>([]);

  if (!chatId) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center text-center px-8">
        <div className="text-4xl mb-3">📁</div>
        <p className="text-sm font-medium text-gray-700">No active chat</p>
        <p className="text-xs text-gray-400 mt-1">Start a chat to see sandbox files.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-white">
      <FileTree
        chatId={chatId}
        selectedFile={selectedFile ?? undefined}
        onFileSelect={setSelectedFile}
        cachedFiles={cachedFiles}
        onFilesLoaded={setCachedFiles}
      />
      <div className="flex-1 overflow-hidden">
        <FileViewer
          filename={selectedFile}
          chatId={chatId}
          isOpen={!!selectedFile}
          onClose={() => setSelectedFile(null)}
        />
        {!selectedFile && (
          <div className="flex flex-col h-full items-center justify-center text-center px-8">
            <div className="text-4xl mb-3 text-gray-200">📄</div>
            <p className="text-sm font-medium text-gray-500">Select a file to view</p>
          </div>
        )}
      </div>
    </div>
  );
}
