'use client';

import React, { useCallback, useRef, useState } from 'react';
import { watchlistApi } from '@/lib/api';

type Picked = { id: string; dataUrl: string; name: string };
type Result = {
  added: number;
  symbols: { symbol: string; name?: string }[];
  unresolved: string[];
};

// Downscale large phone screenshots before upload — keeps the request small and
// speeds up the vision pass with no readability loss for ticker text.
async function fileToDataUrl(file: File): Promise<string> {
  const raw = await new Promise<string>((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result as string);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
  return new Promise<string>((resolve) => {
    const img = new Image();
    img.onload = () => {
      const maxW = 1400;
      const scale = Math.min(1, maxW / img.width);
      const w = Math.round(img.width * scale);
      const h = Math.round(img.height * scale);
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      if (!ctx) { resolve(raw); return; }
      ctx.drawImage(img, 0, 0, w, h);
      resolve(canvas.toDataURL('image/jpeg', 0.85));
    };
    img.onerror = () => resolve(raw);
    img.src = raw;
  });
}

export default function WatchlistImportModal({
  userId, listId, listName, onClose, onImported,
}: {
  userId: string;
  listId: string | null;
  listName: string;
  onClose: () => void;
  onImported: () => void;
}) {
  const [picked, setPicked] = useState<Picked[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback(async (files: FileList | File[]) => {
    setError(null);
    const imgs = Array.from(files).filter(f => f.type.startsWith('image/')).slice(0, 8);
    const next = await Promise.all(imgs.map(async (f) => ({
      id: `${f.name}-${f.size}-${f.lastModified}`,
      dataUrl: await fileToDataUrl(f),
      name: f.name,
    })));
    setPicked(prev => {
      const seen = new Set(prev.map(p => p.id));
      return [...prev, ...next.filter(n => !seen.has(n.id))].slice(0, 8);
    });
  }, []);

  const handleImport = async () => {
    if (!picked.length) return;
    setBusy(true);
    setError(null);
    try {
      const res = await watchlistApi.importScreenshot(userId, picked.map(p => p.dataUrl), listId || undefined);
      setResult({ added: res.added, symbols: res.symbols || [], unresolved: res.unresolved || [] });
      if (res.added > 0) onImported();
    } catch {
      setError("Couldn't read those screenshots. Try a clearer image.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
      onClick={onClose}>
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden"
        onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h3 className="text-base font-semibold text-gray-900">Import from screenshot</h3>
            <p className="text-xs text-gray-400 mt-0.5">Adds to {listName}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          {result ? (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="flex items-center justify-center w-8 h-8 rounded-full bg-emerald-50 text-emerald-600">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {result.added > 0 ? `Added ${result.added} ${result.added === 1 ? 'stock' : 'stocks'}` : 'No new tickers found'}
                </span>
              </div>
              {result.symbols.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {result.symbols.map(s => (
                    <span key={s.symbol} title={s.name}
                      className="px-2 py-1 text-xs font-semibold rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100">
                      {s.symbol}
                    </span>
                  ))}
                </div>
              )}
              {result.unresolved.length > 0 && (
                <p className="text-xs text-gray-400 mb-3">
                  Couldn&apos;t match: {result.unresolved.join(', ')}
                </p>
              )}
              <button onClick={onClose}
                className="w-full py-2.5 text-sm font-semibold text-white rounded-xl transition-colors"
                style={{ background: '#059669' }}>
                Done
              </button>
            </div>
          ) : (
            <div>
              {/* Drop zone */}
              <button
                onClick={() => inputRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}
                className={`w-full flex flex-col items-center justify-center gap-2 py-8 rounded-xl border-2 border-dashed transition-colors ${
                  dragOver ? 'border-emerald-400 bg-emerald-50' : 'border-gray-200 hover:border-gray-300 bg-gray-50'
                }`}>
                <svg className="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5V18a2 2 0 002 2h14a2 2 0 002-2v-1.5M7 9l5-5 5 5M12 4v12" />
                </svg>
                <span className="text-sm text-gray-500">
                  Drop screenshots or <span className="text-emerald-600 font-medium">browse</span>
                </span>
                <span className="text-xs text-gray-400">Robinhood, Fidelity, anywhere — up to 8 images</span>
              </button>
              <input ref={inputRef} type="file" accept="image/*" multiple className="hidden"
                onChange={e => e.target.files && addFiles(e.target.files)} />

              {picked.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {picked.map(p => (
                    <div key={p.id} className="relative group">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={p.dataUrl} alt={p.name}
                        className="w-16 h-16 object-cover rounded-lg border border-gray-200" />
                      <button onClick={() => setPicked(prev => prev.filter(x => x.id !== p.id))}
                        className="absolute -top-1.5 -right-1.5 w-5 h-5 flex items-center justify-center rounded-full bg-gray-900 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {error && <p className="text-xs text-red-500 mt-3">{error}</p>}

              <button onClick={handleImport} disabled={!picked.length || busy}
                className="w-full mt-4 py-2.5 text-sm font-semibold text-white rounded-xl transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
                style={{ background: '#059669' }}>
                {busy ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
                    </svg>
                    Reading screenshots…
                  </>
                ) : `Add ${picked.length ? picked.length + ' image' + (picked.length > 1 ? 's' : '') : ''}`.trim() || 'Add'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
