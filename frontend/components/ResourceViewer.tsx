'use client';

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Resource } from '@/lib/types';

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
          
          // Check if this is a binary image file
          const isImageFile = filename.match(/\.(png|jpg|jpeg|gif|webp)$/i);
          
          const response = await fetch(url);
          if (response.ok) {
            if (isImageFile) {
              // For binary images, fetch as blob and convert to base64
              const blob = await response.blob();
              const reader = new FileReader();
              reader.onloadend = () => {
                const base64 = reader.result as string;
                // Extract just the base64 data (remove data URL prefix)
                const base64Data = base64.split(',')[1] || base64;
                console.log('✅ Image content loaded successfully as base64:', base64Data.length, 'characters');
                setFileContent(base64Data);
                setFileLoading(false);
              };
              reader.onerror = () => {
                console.error('❌ Failed to read blob as base64');
                setFileError('Failed to process image file');
                setFileLoading(false);
              };
              reader.readAsDataURL(blob);
              return; // Don't set loading to false here, wait for reader callback
            } else {
              const content = await response.text();
              console.log('✅ File content loaded successfully:', content.length, 'characters');
              setFileContent(content);
            }
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
    const filename = resource?.data?.filename || '';
    
    // HTML files - render in iframe (for TradingView widgets, etc.)
    const isHtml = filename.match(/\.html$/i);
    if (isHtml) {
      // Create a blob URL from the HTML content for sandboxed iframe
      const blob = new Blob([fileContent], { type: 'text/html' });
      const blobUrl = URL.createObjectURL(blob);
      
      return (
        <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200">
          <div className="px-5 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 text-sm">{filename}</h4>
                  <p className="text-xs text-gray-600">Interactive Widget • HTML</p>
                </div>
              </div>
              <span className="text-xs text-gray-500 font-mono">
                {(resource?.data?.size_bytes || 0).toLocaleString()} bytes
              </span>
            </div>
          </div>
          <div className="bg-gray-900">
            <iframe
              src={blobUrl}
              className="w-full border-0"
              style={{ height: '650px', minHeight: '500px' }}
              sandbox="allow-scripts allow-same-origin"
              title={filename}
              onLoad={() => {
                // Clean up blob URL after iframe loads
                // Note: We delay cleanup to ensure iframe has loaded
                setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
              }}
            />
          </div>
        </div>
      );
    }

    // Image files - render as image
    const isImage = filename.match(/\.(png|jpg|jpeg|gif|webp|svg)$/i);
    if (isImage) {
      const imageExtension = filename.split('.').pop()?.toLowerCase() || 'png';
      const mimeType = imageExtension === 'svg' ? 'image/svg+xml' : `image/${imageExtension}`;
      // Binary images are fetched as base64, SVGs are fetched as text
      const isSvg = imageExtension === 'svg';
      const imageSrc = isSvg 
        ? `data:${mimeType};base64,${btoa(fileContent)}`
        : `data:${mimeType};base64,${fileContent}`;
      
      return (
        <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200">
          <div className="px-5 py-3 bg-gradient-to-r from-purple-50 to-pink-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 text-sm">{filename}</h4>
                  <p className="text-xs text-gray-600">Image • {imageExtension.toUpperCase()}</p>
                </div>
              </div>
              <span className="text-xs text-gray-500 font-mono">
                {(resource?.data?.size_bytes || 0).toLocaleString()} bytes
              </span>
            </div>
          </div>
          <div className="p-6 bg-gray-50 flex items-center justify-center">
            <div className="max-w-full">
              <img 
                src={imageSrc} 
                alt={filename}
                className="max-w-full h-auto rounded-lg shadow-md border border-gray-200"
                style={{ maxHeight: '70vh' }}
              />
            </div>
          </div>
        </div>
      );
    }
    
    // CSV files - render as a table
    if (fileType === 'csv' || filename.endsWith('.csv')) {
      try {
        const lines = fileContent.split('\n').filter(line => line.trim());
        const headers = lines[0]?.split(',').map(h => h.trim()) || [];
        const rows = lines.slice(1).map(line => {
          // Simple CSV parsing - doesn't handle quoted commas yet
          return line.split(',').map(cell => cell.trim());
        });

        return (
          <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200">
            <div className="px-5 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                    </svg>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 text-sm">{filename}</h4>
                    <p className="text-xs text-gray-600">{rows.length} rows × {headers.length} columns</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    {headers.map((header, i) => (
                      <th
                        key={i}
                        className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-r border-gray-200 last:border-r-0 whitespace-nowrap"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {rows.map((row, i) => (
                    <tr key={i} className="hover:bg-blue-50 transition-colors">
                      {row.map((cell, j) => (
                        <td
                          key={j}
                          className="px-4 py-3 text-sm text-gray-900 border-r border-gray-100 last:border-r-0 whitespace-nowrap"
                        >
                          {cell || '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      } catch (error) {
        console.error('Error parsing CSV:', error);
        // Fall through to raw text view
      }
    }
    
    // JSON files - render with syntax highlighting
    if (fileType === 'json' || filename.endsWith('.json')) {
      try {
        const parsed = JSON.parse(fileContent);
        const formatted = JSON.stringify(parsed, null, 2);
        
        return (
          <div className="bg-gray-900 rounded-xl shadow-lg overflow-hidden border border-gray-700">
            <div className="px-5 py-3 bg-gray-800 border-b border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-purple-900/50 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div>
                    <h4 className="font-semibold text-white text-sm">{filename}</h4>
                    <p className="text-xs text-gray-400">JSON Document</p>
                  </div>
                </div>
                <span className="text-xs text-gray-500 font-mono">
                  {(resource?.data?.size_bytes || 0).toLocaleString()} bytes
                </span>
              </div>
            </div>
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
              <pre className="text-gray-100 p-6 text-sm leading-relaxed">
                <code className="language-json">{formatted}</code>
              </pre>
            </div>
          </div>
        );
      } catch (error) {
        console.error('Error parsing JSON:', error);
        // Fall through to raw text view
      }
    }
    
    // Python files - render with syntax highlighting
    if (fileType === 'python' || filename.endsWith('.py')) {
      return (
        <div className="bg-gray-900 rounded-xl shadow-lg overflow-hidden border border-gray-700">
          <div className="px-5 py-3 bg-gray-800 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-900/50 rounded-lg flex items-center justify-center">
                  <span className="text-2xl">🐍</span>
                </div>
                <div>
                  <h4 className="font-semibold text-white text-sm">{filename}</h4>
                  <p className="text-xs text-gray-400">Python Script</p>
                </div>
              </div>
              <span className="text-xs text-gray-500 font-mono">
                {fileContent.split('\n').length} lines
              </span>
            </div>
          </div>
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <pre className="text-gray-100 p-6 text-sm leading-relaxed font-mono">
              <code className="language-python">{fileContent}</code>
            </pre>
          </div>
        </div>
      );
    }
    
    // Markdown files - render with formatting
    if (fileType === 'markdown' || filename.endsWith('.md')) {
      return (
        <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200">
          <div className="px-5 py-3 bg-gradient-to-r from-green-50 to-emerald-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 text-sm">{filename}</h4>
                  <p className="text-xs text-gray-600">Markdown Document</p>
                </div>
              </div>
            </div>
          </div>
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto p-6">
            <div className="prose prose-sm prose-slate max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {fileContent}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      );
    }

    // Default - plain text with prettier styling
    return (
      <div className="bg-gray-900 rounded-xl shadow-lg overflow-hidden border border-gray-700">
        <div className="px-5 py-3 bg-gray-800 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gray-700 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold text-white text-sm">{filename}</h4>
                <p className="text-xs text-gray-400 capitalize">{fileType || 'text'}</p>
              </div>
            </div>
            <span className="text-xs text-gray-500 font-mono">
              {(resource?.data?.size_bytes || 0).toLocaleString()} bytes
            </span>
          </div>
        </div>
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
          <pre className="text-gray-100 p-6 text-sm leading-relaxed font-mono">
            <code>{fileContent}</code>
          </pre>
        </div>
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
          <div className="flex-1 overflow-y-auto bg-gray-50">
            <div className="p-6">
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

