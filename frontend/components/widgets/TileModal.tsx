'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { TileBody } from './Tiles';
import type { Tile, TileData } from './types';

export interface WidgetMeta {
  title: string;
  emoji?: string | null;
  slug?: string | null;
}

// Expanded tile view + branded PNG export. The exported card is the Reddit
// posting unit: claim title + chart + source/finch footer baked into one image
// (static images vastly outperform links as posts; the live link goes in the
// comments).

const EXPORT_W = 1600; // 2x of an ~800px card
const PAD = 48;

async function exportTilePng(node: HTMLElement, tile: Tile, data: TileData | undefined, meta: WidgetMeta) {
  const dark = tile.options?.theme === 'dark';
  const bg = dark ? '#101314' : '#ffffff';
  const ink = dark ? '#f9fafb' : '#111827';
  const muted = dark ? '#8b949e' : '#9ca3af';

  // 1) Grab the chart image: Plotly div (chart_spec) or lightweight-charts canvases.
  let chartImg: HTMLCanvasElement | HTMLImageElement | null = null;
  let chartW = 0;
  let chartH = 0;

  const plotDiv = node.querySelector<HTMLElement>('.js-plotly-plot');
  if (plotDiv) {
    // @ts-expect-error — plotly.js ships no types for the dist bundle
    const Plotly = (await import('plotly.js/dist/plotly')).default as any;
    const url = await Plotly.toImage(plotDiv, {
      format: 'png', width: plotDiv.clientWidth || 800, height: plotDiv.clientHeight || 450, scale: 2,
    });
    chartImg = await new Promise<HTMLImageElement>((res, rej) => {
      const img = new Image();
      img.onload = () => res(img);
      img.onerror = rej;
      img.src = url;
    });
    chartW = chartImg.naturalWidth;
    chartH = chartImg.naturalHeight;
  } else {
    const canvases = Array.from(node.querySelectorAll('canvas')).filter((c) => c.width > 50);
    if (!canvases.length) throw new Error('no exportable chart in this tile');
    const scale = canvases[0].width / canvases[0].getBoundingClientRect().width || 1;
    const merged = document.createElement('canvas');
    merged.width = Math.max(...canvases.map((c) => c.width));
    merged.height = Math.max(...canvases.map((c) => c.height));
    const mctx = merged.getContext('2d')!;
    for (const c of canvases) mctx.drawImage(c, 0, 0);
    chartImg = merged;
    chartW = merged.width;
    chartH = merged.height;
    void scale;
  }

  // 2) Compose the card.
  const drawW = EXPORT_W - PAD * 2;
  const drawH = Math.round((chartH / chartW) * drawW);
  const titleSize = 40;
  const footerH = 72;
  const legendNode = node.querySelector<HTMLElement>('[data-tile-legend]');
  const headerH = PAD + titleSize + 24 + (legendNode ? 0 : 0);
  const H = headerH + drawH + footerH + PAD;

  const out = document.createElement('canvas');
  out.width = EXPORT_W;
  out.height = H;
  const ctx = out.getContext('2d')!;
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, EXPORT_W, H);

  const font = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = ink;
  ctx.font = `600 ${titleSize}px ${font}`;
  ctx.fillText(tile.title || meta.title, PAD, PAD + titleSize - 6, drawW);

  ctx.drawImage(chartImg, PAD, headerH, drawW, drawH);

  // Footer: source + asof left, finch link right.
  const src = (data as any)?.source?.label as string | undefined;
  const asof = (data as any)?.asof ? new Date((data as any).asof).toLocaleString() : '';
  ctx.font = `400 22px ${font}`;
  ctx.fillStyle = muted;
  const footY = headerH + drawH + 46;
  ctx.fillText([src, asof && `as of ${asof}`].filter(Boolean).join(' · '), PAD, footY);
  const link = meta.slug ? `live + clone: finchapp.ai/share/widget/${meta.slug}` : 'made with finchapp.ai';
  ctx.font = `600 22px ${font}`;
  ctx.fillStyle = dark ? '#34d399' : '#059669';
  const lw = ctx.measureText(link).width;
  ctx.fillText(link, EXPORT_W - PAD - lw, footY);

  // 3) Download.
  const a = document.createElement('a');
  a.download = `${(meta.slug || meta.title).replace(/[^a-z0-9-]+/gi, '-').toLowerCase()}-${tile.id}.png`;
  a.href = out.toDataURL('image/png');
  a.click();
}

export default function TileModal({
  tile, data, meta, onClose,
}: {
  tile: Tile;
  data?: TileData;
  meta: WidgetMeta;
  onClose: () => void;
}) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [onClose]);

  const canExport = tile.type === 'chart' || tile.type === 'chart_spec';
  const doExport = useCallback(async () => {
    if (!bodyRef.current) return;
    setExporting(true);
    setErr(null);
    try {
      await exportTilePng(bodyRef.current, tile, data, meta);
    } catch (e: any) {
      setErr(e?.message || 'export failed');
    } finally {
      setExporting(false);
    }
  }, [tile, data, meta]);

  const dark = tile.options?.theme === 'dark';
  // Blow the chart up for the large view.
  const bigTile: Tile = {
    ...tile,
    options: { ...tile.options, height: tile.type === 'chart_spec' ? 560 : 480 },
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 sm:p-8" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative w-full max-w-5xl max-h-full overflow-y-auto rounded-2xl border shadow-2xl p-6 ${dark ? 'bg-[#101314] border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="flex items-start justify-between gap-4 mb-4">
          <h2 className={`text-lg font-semibold ${dark ? 'text-gray-50' : 'text-gray-900'}`}>
            {tile.title || meta.title}
          </h2>
          <div className="flex items-center gap-2 shrink-0">
            {canExport && (
              <button
                onClick={doExport}
                disabled={exporting}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50 flex items-center gap-1.5"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                {exporting ? 'Exporting…' : 'Download PNG'}
              </button>
            )}
            <button onClick={onClose} aria-label="Close"
              className={`p-1.5 rounded-lg ${dark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>
        </div>
        {err && <div className="mb-3 text-xs text-red-500">{err}</div>}
        <div ref={bodyRef}>
          <TileBody tile={bigTile} data={data} />
        </div>
        {(data as any)?.source?.label && (
          <div className={`mt-3 pt-2 border-t text-[11px] ${dark ? 'border-gray-800 text-gray-500' : 'border-gray-100 text-gray-400'}`}>
            {(data as any).source.label}
          </div>
        )}
      </div>
    </div>
  );
}
