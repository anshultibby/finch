'use client';

import React, { useState } from 'react';
import FileBrowser from './FileBrowser';
import FileViewer from './FileViewer';

interface FilesViewProps {
  chatId: string;
}

export default function FilesView({ chatId }: FilesViewProps) {
  const [selectedFile, setSelectedFile] = useState<{
    content: string;
    filename: string;
    type: 'strategy' | 'chat' | 'user';
  } | null>(null);

  const handleFileSelect = (content: string, filename: string, type: 'strategy' | 'chat' | 'user') => {
    setSelectedFile({ content, filename, type });
  };

  return (
    <div className="flex h-full">
      {/* File Browser Sidebar */}
      <div className="w-80 flex-shrink-0">
        <FileBrowser 
          chatId={chatId} 
          onFileSelect={handleFileSelect}
        />
      </div>

      {/* File Viewer */}
      <div className="flex-1">
        <FileViewer
          content={selectedFile?.content || null}
          filename={selectedFile?.filename || null}
          fileType={selectedFile?.type || null}
        />
      </div>
    </div>
  );
}

