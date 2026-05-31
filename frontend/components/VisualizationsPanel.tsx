'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { ArrowLeft, Trash2, BarChart3, LayoutGrid, Clock, Tag, Share2, MessageSquare, Pencil, X, Check } from 'lucide-react';
import { Visualization } from '@/lib/types';
import { visualizationsApi } from '@/lib/api';
import api from '@/lib/api';
import { useNavigation } from '@/contexts/NavigationContext';
import EmptyState from '@/components/ui/EmptyState';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

const CATEGORY_COLORS: Record<string, string> = {
  portfolio: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  analysis: 'bg-blue-50 text-blue-700 border-blue-200',
  market: 'bg-amber-50 text-amber-700 border-amber-200',
  tracker: 'bg-violet-50 text-violet-700 border-violet-200',
  tax: 'bg-rose-50 text-rose-700 border-rose-200',
};

const CATEGORY_ACCENTS: Record<string, string> = {
  portfolio: 'from-emerald-400 to-emerald-600',
  analysis: 'from-blue-400 to-blue-600',
  market: 'from-amber-400 to-amber-500',
  tracker: 'from-violet-400 to-violet-600',
  tax: 'from-rose-400 to-rose-500',
};

function getCategoryColor(cat: string | null): string {
  if (!cat) return 'bg-gray-50 text-gray-600 border-gray-200';
  return CATEGORY_COLORS[cat.toLowerCase()] || 'bg-gray-50 text-gray-600 border-gray-200';
}

function getCategoryAccent(cat: string | null): string {
  if (!cat) return 'from-slate-300 to-slate-400';
  return CATEGORY_ACCENTS[cat.toLowerCase()] || 'from-slate-300 to-slate-400';
}

function displayName(viz: Visualization): string {
  if (viz.title) return viz.title;
  return viz.filename.replace(/\.html$/i, '').replace(/[_-]/g, ' ');
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

interface VisualizationsPanelProps {
  vizId?: string;
}

export default function VisualizationsPanel({ vizId }: VisualizationsPanelProps) {
  const { loadChat, openChatWithPrompt } = useNavigation();
  const [visualizations, setVisualizations] = useState<Visualization[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState('all');
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [htmlLoading, setHtmlLoading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // ── Fetch list ──
  const fetchVisualizations = useCallback(async () => {
    try {
      const data = await visualizationsApi.list();
      setVisualizations(data.visualizations || []);
    } catch (e) {
      console.error('Failed to fetch visualizations', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchVisualizations(); }, [fetchVisualizations]);

  // ── Resolve vizId prop to selectedId ──
  useEffect(() => {
    if (!vizId || visualizations.length === 0) return;
    const normalizedId = vizId.replace(/\.js$/i, '.html');
    const match = normalizedId.endsWith('.html')
      ? visualizations.find(v => v.filename === normalizedId)
      : visualizations.find(v => v.id === vizId);
    if (match) setSelectedId(match.id);
  }, [vizId, visualizations]);

  // ── Load HTML for detail view ──
  useEffect(() => {
    if (!selectedId) { setBlobUrl(null); return; }
    let revoke: string | null = null;
    setHtmlLoading(true);
    visualizationsApi.getRenderHtml(selectedId).then(html => {
      const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
      revoke = url;
      setBlobUrl(url);
    }).catch(e => {
      console.error('Failed to load visualization HTML', e);
      setBlobUrl(null);
    }).finally(() => setHtmlLoading(false));
    return () => { if (revoke) URL.revokeObjectURL(revoke); };
  }, [selectedId]);

  // ── PostMessage bridge (parent side) ──
  useEffect(() => {
    if (!selectedId) return;
    const handler = async (event: MessageEvent) => {
      if (event.data?.type !== 'finch-fetch') return;
      const { url, body, id } = event.data;
      if (typeof url !== 'string' || !url.startsWith('/api/')) {
        iframeRef.current?.contentWindow?.postMessage(
          { type: 'finch-response', id, error: 'Invalid URL' }, '*'
        );
        return;
      }
      try {
        const response = body ? await api.post(url, body) : await api.get(url);
        iframeRef.current?.contentWindow?.postMessage(
          { type: 'finch-response', id, data: response.data }, '*'
        );
      } catch (e: any) {
        iframeRef.current?.contentWindow?.postMessage(
          { type: 'finch-response', id, error: e?.message || 'Request failed' }, '*'
        );
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [selectedId]);

  // ── Derived state ──
  const selectedViz = selectedId ? visualizations.find(v => v.id === selectedId) : null;
  const categories = ['all', ...Array.from(new Set(visualizations.map(v => v.category).filter(Boolean) as string[]))];
  const filtered = activeFilter === 'all'
    ? visualizations
    : visualizations.filter(v => v.category?.toLowerCase() === activeFilter.toLowerCase());

  // ── Handlers ──
  const handleDelete = async () => {
    if (!selectedId) return;
    try {
      await visualizationsApi.delete(selectedId);
      setVisualizations(prev => prev.filter(v => v.id !== selectedId));
      setSelectedId(null);
      setConfirmDelete(false);
    } catch (e) {
      console.error('Failed to delete visualization', e);
    }
  };

  const handleRename = (id: string) => {
    const trimmed = renameValue.trim();
    if (!trimmed) { setRenamingId(null); return; }
    setVisualizations(prev => prev.map(v => v.id === id ? { ...v, title: trimmed } : v));
    setRenamingId(null);
    visualizationsApi.update(id, { title: trimmed }).catch(e => console.error('Failed to rename', e));
  };

  const handleGalleryDelete = async (id: string) => {
    try {
      await visualizationsApi.delete(id);
      setVisualizations(prev => prev.filter(v => v.id !== id));
    } catch (e) {
      console.error('Failed to delete', e);
    }
    setDeletingId(null);
  };

  const handleShare = async () => {
    if (!selectedId || !selectedViz) return;
    setShareLoading(true);
    try {
      let token = selectedViz.share_token;
      if (!selectedViz.is_public || !token) {
        const result = await visualizationsApi.toggleShare(selectedId);
        setVisualizations(prev => prev.map(v =>
          v.id === selectedId ? { ...v, is_public: result.is_public, share_token: result.share_token } : v
        ));
        token = result.share_token;
      }
      if (token) {
        window.open(`${window.location.origin}/share/viz/${token}`, '_blank');
      }
    } catch (e) {
      console.error('Failed to share', e);
    } finally {
      setShareLoading(false);
    }
  };


  // ── Detail view ──
  if (selectedViz) {
    return (
      <div className="flex flex-col h-full bg-white">
        {/* Top bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--finch-border)] bg-white">
          <button
            onClick={() => { setSelectedId(null); setConfirmDelete(false); }}
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-gray-900 truncate">
              {displayName(selectedViz)}
            </h2>
            {selectedViz.category && (
              <span className={`inline-block mt-0.5 text-[10px] font-medium px-1.5 py-0.5 rounded border ${getCategoryColor(selectedViz.category)}`}>
                {selectedViz.category}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {selectedViz.chat_id && (
              <button
                onClick={() => loadChat(selectedViz.chat_id!)}
                className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
                title="Open in Chat"
              >
                <MessageSquare className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={handleShare}
              disabled={shareLoading}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
              title="Share"
            >
              <Share2 className="w-4 h-4" />
            </button>
            {confirmDelete ? (
              <div className="flex items-center gap-1.5 ml-1">
                <button
                  onClick={handleDelete}
                  className="px-2.5 py-1 text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded-md transition-colors"
                >
                  Confirm
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-2.5 py-1 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(true)}
                className="p-1.5 rounded-lg hover:bg-red-50 transition-colors text-gray-400 hover:text-red-500"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Iframe */}
        <div className="flex-1 relative">
          {htmlLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <div className="w-4 h-4 border-2 border-emerald-300 border-t-transparent rounded-full animate-spin" />
                Loading visualization...
              </div>
            </div>
          )}
          {blobUrl && (
            <iframe
              ref={iframeRef}
              src={blobUrl}
              sandbox="allow-scripts"
              className="w-full h-full border-0"
              title={displayName(selectedViz)}
            />
          )}
        </div>
      </div>
    );
  }

  // ── Gallery view ──
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-5 pb-3">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="p-1.5 rounded-lg bg-emerald-50">
            <BarChart3 className="w-4 h-4 text-emerald-600" />
          </div>
          <h1 className="text-lg font-semibold text-gray-900 tracking-tight">Visualizations</h1>
          {visualizations.length > 0 && (
            <span className="text-xs text-gray-400 font-medium bg-gray-100 px-1.5 py-0.5 rounded-full">
              {visualizations.length}
            </span>
          )}
        </div>

        {/* Category filters */}
        {categories.length > 1 && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setActiveFilter(cat)}
                className={`
                  px-2.5 py-1 text-xs font-medium rounded-full border transition-all whitespace-nowrap
                  ${activeFilter === cat
                    ? 'bg-gray-900 text-white border-gray-900'
                    : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300 hover:text-gray-700'
                  }
                `}
              >
                {cat === 'all' ? 'All' : cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-5 pb-5">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 animate-pulse">
            {[1, 2, 3].map(i => (
              <div key={i} className="rounded-xl border border-gray-100 h-40">
                <div className="h-1.5 rounded-t-xl bg-gray-100" />
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-gray-100 rounded w-3/4" />
                  <div className="h-3 bg-gray-50 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <EmptyState
              icon={LayoutGrid}
              title="No visualizations yet"
              description="Ask Finch to build a chart, dashboard, or tracker and it'll show up here."
              action={{
                label: 'Create a visualization',
                onClick: () => openChatWithPrompt(
                  'Create a visualization: a chart comparing the YTD performance of AAPL, MSFT, NVDA, and GOOGL',
                  'New visualization',
                ),
              }}
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.map((viz, i) => (
              <div
                key={viz.id}
                className="group relative text-left finch-surface finch-surface-hover rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-emerald-400"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                {/* Hover actions */}
                <div className="absolute top-2.5 right-2 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                  <button
                    onClick={(e) => { e.stopPropagation(); setRenamingId(viz.id); setRenameValue(viz.title || displayName(viz)); }}
                    className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                    title="Rename"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeletingId(viz.id); }}
                    className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"
                    title="Delete"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>

                {/* Delete confirm overlay */}
                {deletingId === viz.id && (
                  <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/95 backdrop-blur-sm">
                    <div className="text-center">
                      <p className="text-xs text-gray-600 mb-2">Delete this visualization?</p>
                      <div className="flex items-center gap-1.5 justify-center">
                        <button
                          onClick={() => handleGalleryDelete(viz.id)}
                          className="px-2.5 py-1 text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded-md"
                        >
                          Delete
                        </button>
                        <button
                          onClick={() => setDeletingId(null)}
                          className="px-2.5 py-1 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                <button
                  onClick={() => setSelectedId(viz.id)}
                  className="w-full text-left focus:outline-none"
                >
                {/* Accent strip */}
                <div className={`h-1.5 bg-gradient-to-r ${getCategoryAccent(viz.category)}`} />

                <div className="p-4">
                  {/* Title — inline rename */}
                  {renamingId === viz.id ? (
                    <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={e => setRenameValue(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handleRename(viz.id); if (e.key === 'Escape') setRenamingId(null); }}
                        className="flex-1 text-sm font-semibold text-gray-900 bg-gray-50 border border-gray-200 rounded px-1.5 py-0.5 outline-none focus:border-emerald-400"
                      />
                      <button onClick={() => handleRename(viz.id)} className="p-0.5 text-emerald-600 hover:text-emerald-700">
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => setRenamingId(null)} className="p-0.5 text-gray-400 hover:text-gray-600">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <h3 className="text-sm font-semibold text-gray-900 truncate group-hover:text-emerald-700 transition-colors">
                      {displayName(viz)}
                    </h3>
                  )}

                  {/* Description */}
                  {viz.description && (
                    <p className="text-xs text-gray-400 mt-1 line-clamp-2">{viz.description}</p>
                  )}

                  {/* Meta row */}
                  <div className="flex items-center gap-2 mt-3">
                    {viz.category && (
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${getCategoryColor(viz.category)}`}>
                        {viz.category}
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-[10px] text-gray-400 ml-auto">
                      <Clock className="w-3 h-3" />
                      {relativeTime(viz.updated_at)}
                    </span>
                  </div>

                  {/* Tags */}
                  {viz.tags && viz.tags.length > 0 && (
                    <div className="flex items-center gap-1 mt-2 flex-wrap">
                      {viz.tags.slice(0, 3).map(tag => (
                        <span key={tag} className="inline-flex items-center gap-0.5 text-[10px] text-gray-400 bg-gray-50 rounded px-1.5 py-0.5">
                          <Tag className="w-2.5 h-2.5" />{tag}
                        </span>
                      ))}
                      {viz.tags.length > 3 && (
                        <span className="text-[10px] text-gray-300">+{viz.tags.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
