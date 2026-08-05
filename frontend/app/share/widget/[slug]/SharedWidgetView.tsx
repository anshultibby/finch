'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { initAnalytics, track } from '@/lib/analytics';
import { widgetsApi } from '@/lib/api';
import WidgetCanvas from '@/components/widgets/WidgetCanvas';
import type { PublicWidget, WidgetData } from '@/components/widgets/types';

export default function SharedWidgetView({ widget, slug }: { widget: PublicWidget | null; slug: string }) {
  const [data, setData] = useState<WidgetData | undefined>();

  useEffect(() => {
    initAnalytics();
    track('shared_widget_viewed', { slug, found: !!widget });
  }, [slug, widget]);

  // Public live data, polled while the tab is visible.
  useEffect(() => {
    if (!widget) return;
    let timer: ReturnType<typeof setInterval> | null = null;
    const load = () => {
      if (document.visibilityState !== 'visible') return;
      widgetsApi.getSharedData(slug).then(setData).catch(() => {});
    };
    load();
    const intervalMs = Math.max(60, widget.spec?.refresh?.interval_seconds || 60) * 1000;
    timer = setInterval(load, intervalMs);
    const onVis = () => { if (document.visibilityState === 'visible') load(); };
    document.addEventListener('visibilitychange', onVis);
    return () => { if (timer) clearInterval(timer); document.removeEventListener('visibilitychange', onVis); };
  }, [widget, slug]);

  if (!widget) {
    return (
      <div className="min-h-dvh flex flex-col items-center justify-center bg-[#fafaf9] px-6 text-center">
        <div className="text-4xl mb-3">📊</div>
        <h1 className="text-xl font-semibold text-gray-900">Widget not found</h1>
        <p className="text-sm text-gray-500 mt-1">This widget may have been unpublished.</p>
        <Link href="/" className="mt-6 px-5 py-2.5 rounded-full bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500">
          Try Finch free
        </Link>
      </div>
    );
  }

  const cloneHref = `/?clone=${encodeURIComponent(widget.id)}`;

  return (
    <div className="min-h-dvh bg-[#fafaf9] pb-24">
      {/* header */}
      <header className="sticky top-0 z-10 bg-[#fafaf9]/90 backdrop-blur border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-2xl shrink-0">{widget.emoji || '📊'}</span>
            <div className="min-w-0">
              <h1 className="text-base font-semibold text-gray-900 truncate">{widget.title}</h1>
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-600">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live · refreshes automatically
              </div>
            </div>
          </div>
          <Link
            href={cloneHref}
            onClick={() => track('shared_widget_cta_clicked', { placement: 'header', slug })}
            className="shrink-0 px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg"
          >
            Clone this widget
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
        {widget.description && <p className="text-sm text-gray-500 mb-5 max-w-2xl">{widget.description}</p>}
        <WidgetCanvas spec={widget.spec} data={data} />
      </main>

      {/* bottom banner */}
      <div className="fixed bottom-0 inset-x-0 z-10 bg-white/95 backdrop-blur border-t border-gray-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <p className="text-xs sm:text-sm text-gray-600 min-w-0 truncate">
            Made with <span className="font-semibold text-gray-900">Finch</span> — build a live widget for any market, event, or your portfolio.
          </p>
          <Link
            href={cloneHref}
            onClick={() => track('shared_widget_cta_clicked', { placement: 'banner', slug })}
            className="shrink-0 px-4 py-1.5 text-xs font-medium text-white bg-gray-900 hover:bg-gray-800 rounded-full"
          >
            Clone &amp; customize
          </Link>
        </div>
      </div>
    </div>
  );
}
