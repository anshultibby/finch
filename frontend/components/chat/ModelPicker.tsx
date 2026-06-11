import React, { useEffect, useRef, useState } from 'react';
import type { ModelOption } from '@/lib/types';

interface ModelPickerProps {
  models: ModelOption[];
  value?: string;            // selected model id (undefined = default)
  onChange: (id: string) => void;
  disabled?: boolean;
}

/**
 * Compact dropdown for picking the chat's LLM model. Renders nothing until the
 * model list has loaded. Sits inline in the chat composer.
 */
export default function ModelPicker({ models, value, onChange, disabled }: ModelPickerProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  if (!models || models.length === 0) return null;

  const selected = models.find(m => m.id === value) ?? models[0];
  // claude.ai-style short label: "Opus 4.8" rather than "Claude Opus 4.8"
  const shortLabel = (selected?.label ?? 'Model').replace(/^Claude\s+/, '');

  return (
    <div ref={ref} className="relative flex-shrink-0">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(o => !o)}
        title={selected?.label ?? 'Choose model'}
        className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-[13px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 disabled:opacity-40 transition-colors"
      >
        <span className="max-w-[140px] truncate">{shortLabel}</span>
        <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute bottom-full right-0 mb-1 z-20 min-w-[200px] rounded-xl border border-gray-200 bg-white py-1 shadow-lg">
          {models.map(m => {
            const active = m.id === selected?.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => { onChange(m.id); setOpen(false); }}
                className={`flex w-full items-center justify-between gap-3 px-3 py-1.5 text-left text-sm transition-colors ${
                  active ? 'bg-gray-50 text-gray-900' : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <span className="flex flex-col">
                  <span className="font-medium leading-tight">{m.label}</span>
                  {m.provider && <span className="text-xs text-gray-400 leading-tight">{m.provider}</span>}
                </span>
                {active && (
                  <svg className="w-4 h-4 text-gray-900 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
