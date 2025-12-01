'use client';

import React, { useState, useEffect } from 'react';
import { X, FileText, Image, Code, Link as LinkIcon, Folder } from 'lucide-react';
import { resourcesApi, Resource } from '@/lib/api';

interface ChatFilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  chatId: string;
}

type FileCategory = 'all' | 'documents' | 'images' | 'code' | 'links';

export default function ChatFilesModal({ isOpen, onClose, chatId }: ChatFilesModalProps) {
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<FileCategory>('all');

  useEffect(() => {
    if (isOpen && chatId) {
      loadFiles();
    }
  }, [isOpen, chatId]);

  const loadFiles = async () => {
    setLoading(true);
    try {
      const files = await resourcesApi.getChatResources(chatId);
      setResources(files);
    } catch (error) {
      console.error('Error loading files:', error);
    } finally {
      setLoading(false);
    }
  };

  const getFileIcon = (type: string) => {
    if (type.includes('chart') || type.includes('plot')) return Image;
    if (type.includes('code') || type.includes('strategy')) return Code;
    if (type.includes('link') || type.includes('url')) return LinkIcon;
    return FileText;
  };

  const categorizeResource = (resource: Resource): FileCategory => {
    const type = resource.resource_type.toLowerCase();
    if (type.includes('chart') || type.includes('plot')) return 'images';
    if (type.includes('code') || type.includes('strategy')) return 'code';
    if (type.includes('link') || type.includes('url')) return 'links';
    return 'documents';
  };

  const filteredResources = selectedCategory === 'all' 
    ? resources 
    : resources.filter(r => categorizeResource(r) === selectedCategory);

  const getCategoryCount = (category: FileCategory) => {
    if (category === 'all') return resources.length;
    return resources.filter(r => categorizeResource(r) === category).length;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">All files in this chat</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Category tabs */}
        <div className="flex gap-2 px-6 py-3 border-b border-gray-200 overflow-x-auto">
          <CategoryButton
            active={selectedCategory === 'all'}
            onClick={() => setSelectedCategory('all')}
            count={getCategoryCount('all')}
          >
            All
          </CategoryButton>
          <CategoryButton
            active={selectedCategory === 'documents'}
            onClick={() => setSelectedCategory('documents')}
            count={getCategoryCount('documents')}
          >
            Documents
          </CategoryButton>
          <CategoryButton
            active={selectedCategory === 'images'}
            onClick={() => setSelectedCategory('images')}
            count={getCategoryCount('images')}
          >
            Images
          </CategoryButton>
          <CategoryButton
            active={selectedCategory === 'code'}
            onClick={() => setSelectedCategory('code')}
            count={getCategoryCount('code')}
          >
            Code files
          </CategoryButton>
          <CategoryButton
            active={selectedCategory === 'links'}
            onClick={() => setSelectedCategory('links')}
            count={getCategoryCount('links')}
          >
            Links
          </CategoryButton>
        </div>

        {/* Files list */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading files...</div>
          ) : filteredResources.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Folder className="w-12 h-12 mx-auto mb-2 text-gray-400" />
              <p>No files yet in this chat</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredResources.map((resource) => {
                const Icon = getFileIcon(resource.resource_type);
                const date = new Date(resource.created_at);
                const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                
                return (
                  <div
                    key={resource.id}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {resource.title}
                      </p>
                      <p className="text-xs text-gray-500">{timeStr}</p>
                    </div>
                    <button className="text-gray-400 hover:text-gray-600">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CategoryButton({ 
  active, 
  onClick, 
  count, 
  children 
}: { 
  active: boolean; 
  onClick: () => void; 
  count: number;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
        active
          ? 'bg-white text-gray-900 shadow-sm'
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
      }`}
    >
      {children}
      {count > 0 && <span className="ml-1.5 text-xs opacity-60">({count})</span>}
    </button>
  );
}

