'use client';

import React, { useState, useEffect, useCallback } from 'react';

interface FileItem {
  filename: string;
  file_type: string;
  size_bytes: number;
}

interface ChartsPanelProps {
  chatId: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ChartsPanel({ chatId }: ChartsPanelProps) {
  const [charts, setCharts] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!chatId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/chat-files/${chatId}`);
      if (!res.ok) return;
      const files: FileItem[] = await res.json();
      const htmlFiles = files.filter(f => f.filename.endsWith('.html'));
      setCharts(htmlFiles);
      if (htmlFiles.length > 0 && !selected) setSelected(htmlFiles[0].filename);
    } catch {}
    finally { setLoading(false); }
  }, [chatId]);

  useEffect(() => { load(); }, [load]);

  if (!chatId) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center text-center px-8">
        <div className="text-4xl mb-3">📊</div>
        <p className="text-sm font-medium text-gray-700">No active chat</p>
        <p className="text-xs text-gray-400 mt-1">Charts created by the assistant will appear here.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full bg-white items-center justify-center">
        <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (charts.length === 0) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center text-center px-8">
        <div className="text-4xl mb-3">📊</div>
        <p className="text-sm font-medium text-gray-700">No charts yet</p>
        <p className="text-xs text-gray-400 mt-1 max-w-xs">Ask the assistant to create a chart — e.g. "Show me a TradingView chart for AAPL".</p>
      </div>
    );
  }

  const chartUrl = selected
    ? `${API_BASE}/api/chat-files/${chatId}/download/${encodeURIComponent(selected)}`
    : null;

  return (
    <div className="flex h-full bg-white">
      {/* Chart list */}
      {charts.length > 1 && (
        <div className="w-52 border-r border-gray-200 flex flex-col flex-shrink-0 bg-gray-50">
          <div className="px-3 py-2.5 border-b border-gray-200">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Charts</p>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {charts.map(c => (
              <button
                key={c.filename}
                onClick={() => setSelected(c.filename)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  selected === c.filename
                    ? 'bg-white shadow-sm border border-gray-200 text-gray-900 font-medium'
                    : 'text-gray-600 hover:bg-white hover:text-gray-900'
                }`}
              >
                <span className="truncate block">📊 {c.filename.replace('.html', '')}</span>
              </button>
            ))}
          </div>
          <div className="p-2 border-t border-gray-200">
            <button
              onClick={load}
              className="w-full text-xs text-gray-400 hover:text-gray-600 py-1 transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
      )}

      {/* Chart viewer */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {charts.length === 1 && (
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 flex-shrink-0">
            <p className="text-sm font-medium text-gray-700">📊 {selected?.replace('.html', '')}</p>
            <button onClick={load} className="text-xs text-gray-400 hover:text-gray-600 transition-colors">Refresh</button>
          </div>
        )}
        {chartUrl && (
          <iframe
            key={chartUrl}
            src={chartUrl}
            className="flex-1 w-full border-0"
            sandbox="allow-scripts allow-same-origin"
            title={selected ?? 'chart'}
          />
        )}
      </div>
    </div>
  );
}
