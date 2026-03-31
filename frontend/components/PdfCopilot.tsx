'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfCopilotProps {
  /** URL to fetch the PDF from (sandbox proxy endpoint) */
  pdfUrl: string;
  /** Display filename */
  filename: string;
  /** Which section the agent is currently filling */
  activeSection?: string;
  /** Bump to re-fetch the PDF (e.g. after agent fills fields) */
  refreshTrigger?: number;
  /** Chat ID for saving filled fields back */
  chatId?: string;
  /** Sandbox path to the PDF (for save-back) */
  sandboxPath?: string;
  onClose: () => void;
}

/**
 * Extract all form field values from the annotation layer DOM.
 * react-pdf renders PDF form fields as real <input>/<select>/<textarea> elements
 * inside .react-pdf__Page__annotations containers.
 */
function extractFieldValues(containerEl: HTMLElement): Record<string, string> {
  const values: Record<string, string> = {};
  const inputs = containerEl.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(
    '.react-pdf__Page__annotations input, .react-pdf__Page__annotations textarea, .react-pdf__Page__annotations select'
  );
  inputs.forEach((el) => {
    const name = el.name || el.getAttribute('data-annotation-id') || el.id;
    if (!name) return;
    if (el instanceof HTMLInputElement && el.type === 'checkbox') {
      values[name] = el.checked ? 'Yes' : 'Off';
    } else if (el instanceof HTMLInputElement && el.type === 'radio') {
      if (el.checked) values[name] = el.value;
    } else {
      values[name] = el.value;
    }
  });
  return values;
}

export default function PdfCopilot({
  pdfUrl,
  filename,
  activeSection,
  refreshTrigger,
  chatId,
  sandboxPath,
  onClose,
}: PdfCopilotProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [hasEdits, setHasEdits] = useState(false);
  const [pdfKey, setPdfKey] = useState(0); // force re-render on refresh
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(600);

  // Measure container
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Re-load PDF when refreshTrigger bumps
  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) {
      setPdfKey(k => k + 1);
    }
  }, [refreshTrigger]);

  // Track edits in annotation layer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const handler = () => setHasEdits(true);
    container.addEventListener('input', handler);
    container.addEventListener('change', handler);
    return () => {
      container.removeEventListener('input', handler);
      container.removeEventListener('change', handler);
    };
  }, []);

  const onDocumentLoadSuccess = useCallback(({ numPages: n }: { numPages: number }) => {
    setNumPages(n);
    setLoadError(null);
  }, []);

  const onDocumentLoadError = useCallback((error: Error) => {
    setLoadError(error.message || 'Failed to load PDF');
  }, []);

  // Save filled fields back to sandbox via backend fill_form
  const handleSave = useCallback(async () => {
    if (!containerRef.current || !chatId || !sandboxPath) return;
    setSaving(true);
    try {
      const fieldValues = extractFieldValues(containerRef.current);
      if (Object.keys(fieldValues).length === 0) {
        setSaving(false);
        return;
      }

      // Call backend to fill the PDF with the extracted values
      const { getApiBaseUrl } = await import('@/lib/utils');
      const baseUrl = getApiBaseUrl();

      // Write a fill script that the sandbox can run
      const filledPath = sandboxPath.replace('.pdf', '_filled.pdf');
      const script = JSON.stringify({
        input_pdf: sandboxPath,
        output_pdf: filledPath,
        field_values: fieldValues,
      });

      // Use the write endpoint to save field values, then agent can fill
      await fetch(`${baseUrl}/api/chat-files/${chatId}/write`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: sandboxPath.replace('.pdf', '_fields.json'),
          content: JSON.stringify(fieldValues, null, 2),
        }),
      });

      setHasEdits(false);
    } catch (e) {
      console.error('Save failed:', e);
    } finally {
      setSaving(false);
    }
  }, [chatId, sandboxPath]);

  const pageWidth = Math.min(containerWidth - 32, 800) * scale;

  // Build URL with cache-bust for refreshes
  const effectiveUrl = pdfKey > 0 ? `${pdfUrl}&_t=${pdfKey}` : pdfUrl;

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 sm:py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className="hidden md:flex items-center gap-1.5 flex-shrink-0">
            <button
              onClick={onClose}
              className="w-3 h-3 rounded-full bg-[#ff5f57] hover:bg-[#ff3b30] active:bg-[#ff1f17] transition-colors group relative"
              title="Close"
            >
              <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 text-[8px] text-black font-bold">x</span>
            </button>
            <div className="w-3 h-3 rounded-full bg-[#febc2e] cursor-default" />
            <div className="w-3 h-3 rounded-full bg-[#28c840] cursor-default" />
          </div>
          <div className="flex items-center gap-2 md:ml-3 min-w-0">
            <div className="w-5 h-5 rounded flex items-center justify-center flex-shrink-0 bg-gradient-to-br from-red-500 to-rose-600">
              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
              </svg>
            </div>
            <span className="text-sm text-gray-800 font-semibold truncate">{filename}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {activeSection && (
            <span className="hidden sm:flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full font-medium">
              <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
              {activeSection}
            </span>
          )}
          {saving && (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <div className="w-3 h-3 rounded-full border border-gray-300 border-t-blue-500 animate-spin" />
            </span>
          )}
          <button
            onClick={onClose}
            className="md:hidden p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            style={{ minHeight: '36px', minWidth: '36px' }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50/50 border-b border-gray-100">
        {/* Page nav */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M15 19l-7-7 7-7" /></svg>
          </button>
          <span className="text-xs text-gray-600 tabular-nums min-w-[60px] text-center">
            {currentPage} / {numPages || '...'}
          </span>
          <button
            onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))}
            disabled={currentPage >= numPages}
            className="p-1 rounded hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M9 5l7 7-7 7" /></svg>
          </button>
        </div>

        {/* Zoom */}
        <div className="flex items-center gap-1.5">
          <button onClick={() => setScale(s => Math.max(0.5, s - 0.15))} className="p-1 rounded hover:bg-gray-200 transition-colors" title="Zoom out">
            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M5 12h14" /></svg>
          </button>
          <span className="text-xs text-gray-500 tabular-nums min-w-[40px] text-center">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale(s => Math.min(2.0, s + 0.15))} className="p-1 rounded hover:bg-gray-200 transition-colors" title="Zoom in">
            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
          </button>
          <button onClick={() => setScale(1.0)} className="text-xs text-gray-500 hover:text-gray-700 px-1.5 py-0.5 rounded hover:bg-gray-200 transition-colors">Fit</button>
        </div>
      </div>

      {/* PDF Content — annotation layer makes form fields interactive */}
      <div ref={containerRef} className="flex-1 overflow-auto bg-gray-100 pdf-fillable-container">
        {loadError ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3 p-4">
            <svg className="w-10 h-10 text-red-300" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm text-red-500 text-center">{loadError}</span>
            <button onClick={() => { setLoadError(null); setCurrentPage(1); }} className="text-xs text-blue-600 hover:underline">Retry</button>
          </div>
        ) : (
          <div className="flex flex-col items-center py-4 gap-4 min-h-full">
            <Document
              key={pdfKey}
              file={effectiveUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                  <div className="w-10 h-10 rounded-full border-2 border-gray-200 border-t-red-500 animate-spin" />
                  <span className="text-sm text-gray-400">Loading PDF...</span>
                </div>
              }
            >
              {/* Render all pages so user can scroll through the form */}
              {Array.from({ length: numPages }, (_, i) => (
                <Page
                  key={`page-${i + 1}`}
                  pageNumber={i + 1}
                  width={pageWidth}
                  className="shadow-lg rounded-sm mb-4"
                  renderAnnotationLayer={true}
                  renderTextLayer={true}
                  loading={
                    <div className="flex items-center justify-center py-20">
                      <div className="w-8 h-8 rounded-full border-2 border-gray-200 border-t-red-400 animate-spin" />
                    </div>
                  }
                />
              ))}
            </Document>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
        <span className="text-xs text-gray-400">
          {numPages > 0 ? `${numPages} page${numPages !== 1 ? 's' : ''}` : ''}
        </span>
        <div className="flex items-center gap-3">
          {hasEdits && chatId && sandboxPath && (
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-xs text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 px-3 py-1 rounded-md font-medium transition-colors"
            >
              {saving ? 'Saving...' : 'Save Fields'}
            </button>
          )}
          <a href={pdfUrl} download={filename} className="text-xs text-blue-600 hover:text-blue-700 hover:underline">
            Download
          </a>
        </div>
      </div>
    </div>
  );
}
