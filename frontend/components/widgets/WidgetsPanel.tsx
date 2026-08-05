'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { widgetsApi } from '@/lib/api';
import { useNavigation } from '@/contexts/NavigationContext';
import WidgetCanvas from './WidgetCanvas';
import type { Widget, WidgetSummary, WidgetData } from './types';

export default function WidgetsPanel({ widgetId }: { widgetId?: string }) {
  return widgetId ? <WidgetDetail widgetId={widgetId} /> : <WidgetList />;
}

// ── list ────────────────────────────────────────────────────────────────────
function WidgetList() {
  const { navigateTo } = useNavigation();
  const [widgets, setWidgets] = useState<WidgetSummary[] | null>(null);

  useEffect(() => {
    widgetsApi.list().then(setWidgets).catch(() => setWidgets([]));
  }, []);

  if (widgets === null) {
    return <div className="h-full overflow-y-auto p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 auto-rows-min">
      {[0, 1, 2].map((i) => <div key={i} className="h-28 rounded-xl bg-gray-100 animate-pulse" />)}
    </div>;
  }

  if (widgets.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center py-24 text-center px-6">
        <div className="text-4xl mb-3">📊</div>
        <div className="text-lg font-semibold text-gray-900">No widgets yet</div>
        <p className="text-sm text-gray-500 mt-1 max-w-sm">
          Ask the agent to build one — “make me a tracker for oil and the Strait of Hormuz”, or “a widget for my portfolio”.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {widgets.map((w, i) => (
          <button
            key={w.id}
            onClick={() => navigateTo({ type: 'widgets', widgetId: w.id })}
            className="text-left p-4 rounded-xl border border-gray-200 shadow-sm bg-white hover:border-emerald-200 hover-lift transition-colors"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <div className="flex items-start gap-3">
              <div className="text-2xl shrink-0">{w.emoji || '📊'}</div>
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-gray-900 truncate">{w.title}</div>
                {w.description && <div className="text-xs text-gray-500 line-clamp-2 mt-0.5">{w.description}</div>}
                <div className="flex items-center gap-2 mt-2">
                  {w.visibility === 'public' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">Public</span>
                  )}
                  {(w.tags || []).slice(0, 2).map((t) => (
                    <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-50 text-gray-500 border border-gray-200">{t}</span>
                  ))}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── detail (with view-driven polling) ────────────────────────────────────────
function WidgetDetail({ widgetId }: { widgetId: string }) {
  const { navigateTo, goBack } = useNavigation();
  const [widget, setWidget] = useState<Widget | null>(null);
  const [data, setData] = useState<WidgetData | undefined>();
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    widgetsApi.get(widgetId).then(setWidget).catch(() => setWidget(null));
  }, [widgetId]);

  const refresh = useCallback(() => {
    if (document.visibilityState !== 'visible') return;
    widgetsApi.getData(widgetId).then(setData).catch(() => {});
  }, [widgetId]);

  // Poll on the widget's interval, only while the tab is visible.
  useEffect(() => {
    if (!widget) return;
    refresh();
    const intervalMs = Math.max(60, widget.spec?.refresh?.interval_seconds || 60) * 1000;
    const start = () => {
      if (timerRef.current) return;
      timerRef.current = setInterval(refresh, intervalMs);
    };
    const stop = () => {
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    };
    const onVis = () => { if (document.visibilityState === 'visible') { refresh(); start(); } else stop(); };
    start();
    document.addEventListener('visibilitychange', onVis);
    return () => { stop(); document.removeEventListener('visibilitychange', onVis); };
  }, [widget, refresh]);

  const doPublish = async () => {
    if (!widget) return;
    setBusy(true);
    try {
      const updated = await widgetsApi.publish(widget.id, widget.visibility === 'public');
      setWidget(updated);
      if (updated.visibility === 'public' && updated.slug) {
        const url = `${window.location.origin}/share/widget/${updated.slug}`;
        await navigator.clipboard.writeText(url).catch(() => {});
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } finally { setBusy(false); }
  };

  const doDelete = async () => {
    if (!widget || !window.confirm('Delete this widget?')) return;
    await widgetsApi.delete(widget.id);
    goBack();
  };

  if (!widget) return <div className="p-6"><div className="h-8 w-48 bg-gray-100 rounded animate-pulse" /></div>;

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4 mb-5">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={goBack} className="text-gray-400 hover:text-gray-600 shrink-0" aria-label="Back">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6" /></svg>
          </button>
          <div className="text-2xl shrink-0">{widget.emoji || '📊'}</div>
          <div className="min-w-0">
            <h1 className="text-lg font-semibold text-gray-900 truncate">{widget.title}</h1>
            {widget.description && <p className="text-xs text-gray-500 line-clamp-1">{widget.description}</p>}
          </div>
        </div>
        {widget.is_owner && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={doPublish}
              disabled={busy}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50"
            >
              {copied ? 'Link copied!' : widget.visibility === 'public' ? 'Unpublish' : 'Share'}
            </button>
            <button onClick={doDelete} className="px-2 py-1.5 text-xs text-gray-400 hover:text-red-500" aria-label="Delete">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6" /></svg>
            </button>
          </div>
        )}
      </div>

      {widget.visibility === 'public' && widget.slug && (
        <div className="mb-4 text-xs text-gray-500">
          Public at{' '}
          <a href={`/share/widget/${widget.slug}`} target="_blank" rel="noreferrer" className="text-emerald-600 hover:underline">
            /share/widget/{widget.slug}
          </a>
          {' · '}{widget.view_count} views · {widget.clone_count} clones
        </div>
      )}

      <WidgetCanvas spec={widget.spec} data={data} />
    </div>
  );
}
