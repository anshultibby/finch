'use client';

import React, { useState, useEffect, useCallback } from 'react';

interface ChartEntry {
  filename: string;
  title: string;
  description?: string;
  group?: string;
}

interface ChartsManifest {
  charts: ChartEntry[];
}

interface FileItem {
  filename: string;
  file_type: string;
  size_bytes: number;
}

interface ChartsPanelProps {
  chatId: string | null;
  selectedChart?: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ChartsPanel({ chatId, selectedChart }: ChartsPanelProps) {
  const [manifest, setManifest] = useState<ChartsManifest | null>(null);
  const [fallbackCharts, setFallbackCharts] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // When selectedChart prop changes, select it and refresh
  useEffect(() => {
    if (selectedChart) {
      setSelected(selectedChart);
      load();
    }
  }, [selectedChart]);

  const load = useCallback(async () => {
    if (!chatId) return;
    setLoading(true);
    try {
      // Try to fetch the manifest first
      const manifestRes = await fetch(
        `${API_BASE}/api/chat-files/${chatId}/download/${encodeURIComponent('charts.json')}`
      );
      if (manifestRes.ok) {
        const data: ChartsManifest = await manifestRes.json();
        setManifest(data);
        setFallbackCharts([]);
        if (data.charts.length > 0 && !selected && !selectedChart) {
          setSelected(data.charts[0].filename);
        }
      } else {
        // No manifest — fall back to listing all .html files
        setManifest(null);
        const res = await fetch(`${API_BASE}/api/chat-files/${chatId}`);
        if (res.ok) {
          const files: FileItem[] = await res.json();
          const htmlFiles = files.filter(f => f.filename.endsWith('.html'));
          setFallbackCharts(htmlFiles);
          if (htmlFiles.length > 0 && !selected && !selectedChart) {
            setSelected(htmlFiles[0].filename);
          }
        }
      }
    } catch {
      setManifest(null);
    } finally {
      setLoading(false);
    }
  }, [chatId]);

  useEffect(() => { load(); }, [load]);

  const toggleGroup = (group: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  };

  // Build the chart list — either from manifest or fallback
  const chartEntries: ChartEntry[] = manifest
    ? manifest.charts
    : fallbackCharts.map(f => ({ filename: f.filename, title: f.filename.replace('.html', '') }));

  const hasCharts = chartEntries.length > 0;

  // Group charts
  const groups = new Map<string, ChartEntry[]>();
  for (const entry of chartEntries) {
    const group = entry.group || '';
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(entry);
  }
  const hasGroups = manifest !== null && groups.size > 1 || (groups.size === 1 && !groups.has(''));

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

  if (!hasCharts) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center text-center px-8">
        <div className="text-4xl mb-3">📊</div>
        <p className="text-sm font-medium text-gray-700">No charts yet</p>
        <p className="text-xs text-gray-400 mt-1 max-w-xs">Ask the assistant to create a chart — e.g. &ldquo;Show me a TradingView chart for AAPL&rdquo;.</p>
      </div>
    );
  }

  const chartUrl = selected
    ? `${API_BASE}/api/chat-files/${chatId}/download/${encodeURIComponent(selected)}`
    : null;

  const showSidebar = chartEntries.length > 1;

  return (
    <div className="flex h-full bg-white">
      {/* Sidebar */}
      {showSidebar && (
        <div className="w-56 border-r border-gray-200 flex flex-col flex-shrink-0 bg-gray-50">
          <div className="px-3 py-2.5 border-b border-gray-200">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Charts</p>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {hasGroups ? (
              // Grouped view
              Array.from(groups.entries()).map(([group, entries]) => {
                const groupKey = group || 'Other';
                const isCollapsed = collapsedGroups.has(groupKey);
                return (
                  <div key={groupKey} className="mb-1">
                    <button
                      onClick={() => toggleGroup(groupKey)}
                      className="w-full flex items-center gap-1.5 px-2 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-700 transition-colors"
                    >
                      <svg
                        className={`w-3 h-3 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      {groupKey}
                      <span className="ml-auto text-[10px] font-normal text-gray-400">{entries.length}</span>
                    </button>
                    {!isCollapsed && (
                      <div className="space-y-0.5 ml-1">
                        {entries.map(entry => (
                          <ChartButton
                            key={entry.filename}
                            entry={entry}
                            isSelected={selected === entry.filename}
                            onSelect={() => setSelected(entry.filename)}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              // Flat view
              <div className="space-y-0.5">
                {chartEntries.map(entry => (
                  <ChartButton
                    key={entry.filename}
                    entry={entry}
                    isSelected={selected === entry.filename}
                    onSelect={() => setSelected(entry.filename)}
                  />
                ))}
              </div>
            )}
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
        {!showSidebar && chartEntries.length === 1 && (
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 flex-shrink-0">
            <p className="text-sm font-medium text-gray-700">📊 {chartEntries[0].title}</p>
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

function ChartButton({ entry, isSelected, onSelect }: { entry: ChartEntry; isSelected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
        isSelected
          ? 'bg-white shadow-sm border border-gray-200 text-gray-900'
          : 'text-gray-600 hover:bg-white hover:text-gray-900'
      }`}
    >
      <span className={`block text-sm truncate ${isSelected ? 'font-medium' : ''}`}>
        {entry.title}
      </span>
      {entry.description && (
        <span className="block text-[11px] text-gray-400 truncate mt-0.5">
          {entry.description}
        </span>
      )}
    </button>
  );
}
