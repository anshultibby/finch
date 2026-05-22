'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { BarChart3 } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SharedVizMeta {
  title: string | null;
  description: string | null;
  category: string | null;
  created_at: string | null;
}

export default function SharedVisualizationPage() {
  const { token } = useParams<{ token: string }>();
  const [meta, setMeta] = useState<SharedVizMeta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!token) return;

    fetch(`${API_BASE_URL}/api/visualizations/shared/${token}`)
      .then(r => {
        if (!r.ok) throw new Error('Not found');
        return r.json();
      })
      .then(setMeta)
      .catch(() => setError('This visualization is not available or has been unshared.'));

    fetch(`${API_BASE_URL}/api/visualizations/shared/${token}/render`)
      .then(r => {
        if (!r.ok) throw new Error('Not found');
        return r.text();
      })
      .then(html => {
        const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
        setBlobUrl(url);
      })
      .catch(() => {});

    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [token]);

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <div className="p-4 rounded-2xl bg-white/5 inline-block mb-4">
            <BarChart3 className="w-8 h-8 text-gray-500" />
          </div>
          <p className="text-gray-400 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2.5 bg-[#111] border-b border-white/10">
        <div className="p-1.5 rounded-lg bg-emerald-500/10">
          <BarChart3 className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-white truncate">
            {meta?.title || 'Loading...'}
          </h1>
          {meta?.category && (
            <span className="text-[10px] text-gray-500 font-medium">
              {meta.category}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-gray-500">Created by Finch</span>
          <a
            href="https://finchapp.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors"
          >
            Try Finch
          </a>
        </div>
      </div>

      {/* Iframe */}
      <div className="flex-1 relative">
        {!blobUrl && !error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex items-center gap-2 text-gray-500 text-sm">
              <div className="w-4 h-4 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
              Loading...
            </div>
          </div>
        )}
        {blobUrl && (
          <iframe
            ref={iframeRef}
            src={blobUrl}
            sandbox="allow-scripts"
            className="w-full h-[calc(100vh-49px)] border-0"
            title={meta?.title || 'Shared Visualization'}
          />
        )}
      </div>
    </div>
  );
}
