'use client';

import React, { useState } from 'react';
import type { Resource } from '@/lib/types';

interface ResourcesSidebarProps {
  resources: Resource[];
  isOpen: boolean;
  onClose: () => void;
  onSelectResource: (resource: Resource) => void;
}

export default function ResourcesSidebar({
  resources,
  isOpen,
  onClose,
  onSelectResource,
}: ResourcesSidebarProps) {
  const [selectedType, setSelectedType] = useState<string>('all');

  // Get unique resource types
  const resourceTypes: string[] = ['all', ...Array.from(new Set(resources.map((r) => r.resource_type)))];

  // Filter resources by type
  const filteredResources =
    selectedType === 'all'
      ? resources
      : resources.filter((r) => r.resource_type === selectedType);

  const getResourceIcon = (type: string) => {
    switch (type) {
      case 'plot':
        return '📈';
      case 'portfolio':
        return '📊';
      case 'reddit_trends':
      case 'reddit_sentiment':
      case 'reddit_comparison':
        return '📱';
      case 'senate_trades':
      case 'house_trades':
        return '🏛️';
      case 'insider_trades':
      case 'ticker_insider_activity':
      case 'portfolio_insider_activity':
        return '💼';
      case 'file':
        return '📝';
      default:
        return '📄';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed top-0 right-0 h-full w-96 bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        } flex flex-col border-l border-blue-200`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-indigo-600">
          <div>
            <h2 className="text-2xl font-bold text-white">📦 Resources</h2>
            <p className="text-sm text-blue-100 mt-1">{resources.length} items saved</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:text-blue-100 transition-colors p-2 rounded-lg hover:bg-white/10"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Filter */}
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-b from-gray-50 to-white">
          <label className="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
            Filter by Type
          </label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white"
          >
            {resourceTypes.map((type) => (
              <option key={type} value={type}>
                {type === 'all' ? '📋 All Resources' : `${getResourceIcon(type)} ${type.replace(/_/g, ' ').toUpperCase()}`}
              </option>
            ))}
          </select>
        </div>

        {/* Resources List */}
        <div className="flex-1 overflow-y-auto bg-gray-50">
          {filteredResources.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <div className="text-7xl mb-6 animate-bounce">📦</div>
              <p className="text-lg font-semibold text-gray-700">No resources yet</p>
              <p className="text-sm text-gray-500 mt-2 max-w-xs">
                Function call results will be saved here for easy access
              </p>
            </div>
          ) : (
            <div className="p-3 space-y-2">
              {filteredResources.map((resource) => (
                <button
                  key={resource.id}
                  onClick={() => onSelectResource(resource)}
                  className="w-full bg-white hover:bg-blue-50 border border-gray-200 hover:border-blue-300 rounded-xl p-4 transition-all text-left shadow-sm hover:shadow-md group"
                >
                  <div className="flex items-start gap-3">
                    <div className="text-3xl flex-shrink-0 group-hover:scale-110 transition-transform">
                      {getResourceIcon(resource.resource_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-bold text-gray-900 truncate group-hover:text-blue-700">
                        {resource.title}
                      </h3>
                      <p className="text-xs text-gray-600 mt-1 font-medium">
                        {resource.tool_name.replace(/_/g, ' ')}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {formatDate(resource.created_at)}
                      </p>
                    </div>
                    <svg
                      className="w-5 h-5 text-gray-400 group-hover:text-blue-600 flex-shrink-0 group-hover:translate-x-1 transition-all"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

