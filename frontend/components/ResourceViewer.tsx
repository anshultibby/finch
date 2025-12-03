'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Resource } from '@/lib/api';

// Dynamic import for Plotly (client-side only)
let Plot: any = null;
if (typeof window !== 'undefined') {
  import('react-plotly.js').then((module) => {
    Plot = module.default;
  });
}

interface ResourceViewerProps {
  resource: Resource | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function ResourceViewer({ resource, isOpen, onClose }: ResourceViewerProps) {
  const [viewMode, setViewMode] = useState<'table' | 'json'>('table');
  const [plotLoaded, setPlotLoaded] = useState(false);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  // Reset file state when closing or switching resources
  useEffect(() => {
    if (!isOpen) {
      setFileContent(null);
      setFileLoading(false);
      setFileError(null);
    }
  }, [isOpen]);
  
  // Debug logging when resource changes
  useEffect(() => {
    if (resource) {
      console.log('📄 ResourceViewer opened with resource:', {
        id: resource.id,
        type: resource.resource_type,
        title: resource.title,
        hasChatId: !!resource.chat_id,
        hasFilename: !!resource.data?.filename,
        chatId: resource.chat_id,
        filename: resource.data?.filename
      });
    }
  }, [resource]);

  // Check if this is a plot resource
  const isPlot = resource?.resource_type === 'plot' && resource?.data?.plotly_json;
  
  // Check if this is a file resource
  const isFile = resource?.resource_type === 'file';

  useEffect(() => {
    // Wait for Plotly to load
    if (isPlot && typeof window !== 'undefined') {
      const checkPlot = setInterval(() => {
        if (Plot) {
          setPlotLoaded(true);
          clearInterval(checkPlot);
        }
      }, 100);
      return () => clearInterval(checkPlot);
    }
  }, [isPlot]);

  useEffect(() => {
    // Fetch file content if this is a file resource
    if (isFile) {
      // Check for required fields
      if (!resource?.chat_id) {
        console.error('❌ File resource is missing chat_id:', resource);
        setFileError(`Resource is missing chat_id. This is likely a bug. Resource ID: ${resource?.id}`);
        setFileLoading(false);
        return;
      }
      
      if (!resource?.data?.filename) {
        console.error('❌ File resource is missing filename:', resource);
        setFileError(`Resource is missing filename. Resource ID: ${resource?.id}`);
        setFileLoading(false);
        return;
      }
      
      const fetchFileContent = async () => {
        setFileLoading(true);
        setFileError(null);
        setFileContent(null);
        try {
          const chatId = resource.chat_id;
          const filename = resource.data.filename;
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          const url = `${apiUrl}/api/chat-files/${chatId}/download/${filename}`;
          console.log('📥 Fetching file from:', url);
          console.log('📋 Resource data:', {
            id: resource.id,
            chatId,
            filename,
            fileType: resource.data.file_type,
            sizeBytes: resource.data.size_bytes
          });
          
          const response = await fetch(url);
          if (response.ok) {
            const content = await response.text();
            console.log('✅ File content loaded successfully:', content.length, 'characters');
            setFileContent(content);
          } else {
            const errorText = await response.text();
            console.error('❌ Failed to fetch file:', {
              status: response.status,
              statusText: response.statusText,
              error: errorText,
              url
            });
            setFileError(`Failed to load file (HTTP ${response.status}): ${errorText || response.statusText}`);
          }
        } catch (error) {
          console.error('❌ Error fetching file content:', error);
          setFileError(`Network error: ${error instanceof Error ? error.message : String(error)}. Is the backend server running?`);
        } finally {
          setFileLoading(false);
        }
      };
      fetchFileContent();
    }
  }, [isFile, resource]);

  if (!isOpen || !resource) return null;

  const formatJson = (data: any) => {
    return JSON.stringify(data, null, 2);
  };

  const renderPlot = () => {
    if (!isPlot || !plotLoaded || !Plot) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="text-gray-500">Loading chart...</div>
        </div>
      );
    }

    try {
      const plotlyData = JSON.parse(resource.data.plotly_json);
      return (
        <div className="w-full h-full flex items-center justify-center">
          <Plot
            data={plotlyData.data}
            layout={plotlyData.layout}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: ['lasso2d', 'select2d']
            }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      );
    } catch (error) {
      return (
        <div className="text-center py-8 text-red-500">
          Error rendering chart: {String(error)}
        </div>
      );
    }
  };

  const renderFile = () => {
    if (fileError) {
      return (
        <div className="flex flex-col items-center justify-center py-12 px-6">
          <div className="text-red-500 text-center max-w-2xl">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="font-semibold mb-3 text-lg">Failed to load file</p>
            <p className="text-sm text-gray-700 bg-gray-100 p-4 rounded-lg mb-4 font-mono text-left whitespace-pre-wrap break-words">{fileError}</p>
            <div className="text-xs text-gray-600 bg-yellow-50 p-3 rounded border border-yellow-200 text-left">
              <p className="font-semibold mb-2">Troubleshooting steps:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Make sure the backend server is running (check console)</li>
                <li>Check browser console (F12) for detailed error messages</li>
                <li>Verify NEXT_PUBLIC_API_URL is set correctly ({process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'})</li>
                <li>Try refreshing the page to reload resources</li>
              </ul>
            </div>
          </div>
        </div>
      );
    }

    if (fileLoading || !fileContent) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="text-gray-500 flex items-center gap-3">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Loading file...
          </div>
        </div>
      );
    }

    const fileType = resource?.data?.file_type || 'text';
    const getLanguageClass = () => {
      switch (fileType) {
        case 'python': return 'language-python';
        case 'json': return 'language-json';
        case 'markdown': return 'language-markdown';
        case 'csv': return 'language-csv';
        default: return 'language-text';
      }
    };

    return (
      <div className="bg-gray-900 rounded-xl shadow-lg overflow-hidden">
        <div className="px-4 py-2 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-gray-400">
              {resource?.data?.filename}
            </span>
            <span className="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300">
              {fileType}
            </span>
          </div>
          <span className="text-xs text-gray-500">
            {(resource?.data?.size_bytes || 0)} bytes
          </span>
        </div>
        <pre className={`text-gray-100 p-6 text-sm overflow-x-auto leading-relaxed ${getLanguageClass()}`}>
          <code>{fileContent}</code>
        </pre>
      </div>
    );
  };

  const renderAsTable = (data: any) => {
    // Check if data has an array we can display as a table
    let tableData: any[] = [];

    if (Array.isArray(data)) {
      tableData = data;
    } else if (data.data && Array.isArray(data.data)) {
      // New simplified format with data array
      tableData = data.data;
    } else if (data.mentions && Array.isArray(data.mentions)) {
      tableData = data.mentions;
    } else if (data.trades && Array.isArray(data.trades)) {
      tableData = data.trades;
    } else if (data.holdings && Array.isArray(data.holdings)) {
      tableData = data.holdings;
    } else if (data.positions && Array.isArray(data.positions)) {
      tableData = data.positions;
    }

    if (tableData.length === 0) {
      return (
        <div className="text-center py-8 text-gray-500">
          No table data available. Switch to JSON view.
        </div>
      );
    }

    // Get all unique keys from the array
    const allKeys = new Set<string>();
    tableData.forEach((item) => {
      Object.keys(item).forEach((key) => allKeys.add(key));
    });
    const keys = Array.from(allKeys);

    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
          <thead className="bg-gradient-to-r from-blue-50 to-indigo-50">
            <tr>
              {keys.map((key) => (
                <th
                  key={key}
                  className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200"
                >
                  {key.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {tableData.map((row, idx) => (
              <tr key={idx} className="hover:bg-gray-50 transition-colors">
                {keys.map((key) => (
                  <td
                    key={key}
                    className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap"
                  >
                    {typeof row[key] === 'object' && row[key] !== null
                      ? JSON.stringify(row[key])
                      : row[key]?.toString() || '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const canShowTable = () => {
    const data = resource.data;
    if (Array.isArray(data)) return data.length > 0;
    return !!(
      (data.data && Array.isArray(data.data)) ||
      (data.mentions && Array.isArray(data.mentions)) ||
      (data.trades && Array.isArray(data.trades)) ||
      (data.holdings && Array.isArray(data.holdings)) ||
      (data.positions && Array.isArray(data.positions))
    );
  };

  const exportAsCSV = () => {
    const data = resource.data;
    let tableData: any[] = [];

    if (Array.isArray(data)) {
      tableData = data;
    } else if (data.data) {
      tableData = data.data;
    } else if (data.mentions) {
      tableData = data.mentions;
    } else if (data.trades) {
      tableData = data.trades;
    } else if (data.holdings) {
      tableData = data.holdings;
    } else if (data.positions) {
      tableData = data.positions;
    }

    if (tableData.length === 0) return;

    const keys = Object.keys(tableData[0]);
    const csvHeader = keys.join(',');
    const csvRows = tableData.map((row) =>
      keys.map((key) => {
        const value = row[key];
        if (typeof value === 'string' && value.includes(',')) {
          return `"${value}"`;
        }
        return value;
      }).join(',')
    );

    const csv = [csvHeader, ...csvRows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${resource.title.replace(/\s+/g, '_')}.csv`;
    a.click();
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-60 z-[60] flex items-center justify-center p-4 backdrop-blur-sm"
        onClick={onClose}
      >
        {/* Modal */}
        <div
          className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-indigo-600">
            <div>
              <h2 className="text-2xl font-bold text-white">{resource.title}</h2>
              <p className="text-sm text-blue-100 mt-1">
                {resource.tool_name.replace(/_/g, ' ')} • {new Date(resource.created_at).toLocaleString()}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-blue-100 transition-colors p-2 rounded-lg hover:bg-white/10"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* View Mode Toggle */}
          {!isPlot && !isFile && canShowTable() && (
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setViewMode('table')}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                    viewMode === 'table'
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                  }`}
                >
                  📊 Table View
                </button>
                <button
                  onClick={() => setViewMode('json')}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                    viewMode === 'json'
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                  }`}
                >
                  {'{ }'} JSON View
                </button>
              </div>
              {(resource.metadata?.total_count || resource.data?.data?.length) && (
                <span className="text-sm text-gray-600 font-medium">
                  {resource.metadata?.total_count || resource.data?.data?.length} items total
                </span>
              )}
            </div>
          )}

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
            {isPlot ? (
              <div className="bg-white rounded-xl shadow-sm overflow-hidden h-full min-h-[600px]">
                {renderPlot()}
              </div>
            ) : isFile ? (
              renderFile()
            ) : viewMode === 'table' ? (
              <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                {renderAsTable(resource.data)}
              </div>
            ) : (
              <div className="bg-gray-900 rounded-xl shadow-lg overflow-hidden">
                <pre className="text-gray-100 p-6 text-sm overflow-x-auto leading-relaxed">
                  {formatJson(resource.data)}
                </pre>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 bg-white flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isFile && fileContent && (
                <>
                  <button
                    onClick={() => {
                      const blob = new Blob([fileContent], { type: 'text/plain' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = resource?.data?.filename || 'file.txt';
                      a.click();
                    }}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border-2 border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Download File
                  </button>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(fileContent);
                    }}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border-2 border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy Content
                  </button>
                </>
              )}
              {!isPlot && !isFile && canShowTable() && (
                <button
                  onClick={exportAsCSV}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border-2 border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Export CSV
                </button>
              )}
              {!isFile && (
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(formatJson(resource.data));
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border-2 border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy JSON
                </button>
              )}
            </div>
            <button
              onClick={onClose}
              className="px-6 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

