'use client';

import React, { useState } from 'react';
import FileTree from './FileTree';
import FileViewer from './FileViewer';

interface FilesPanelProps {
  chatId: string | null;
}

export default function FilesPanel({ chatId }: FilesPanelProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  if (!chatId) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center text-center px-8">
        <svg className="w-10 h-10 mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
        </svg>
        <p className="text-sm font-medium text-gray-600">No active chat</p>
        <p className="text-xs text-gray-400 mt-1">Start a chat to see sandbox files.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-white overflow-hidden border-r border-gray-100">
      <FileTree
        chatId={chatId}
        selectedFile={selectedFile ?? undefined}
        onFileSelect={setSelectedFile}
      />
      <div className="flex-1 overflow-hidden">
        <FileViewer filename={selectedFile} chatId={chatId} />
      </div>
    </div>
  );
}
