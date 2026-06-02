'use client';

import React, { useState, KeyboardEvent, useRef, useEffect, DragEvent } from 'react';
import { TrendingUp, Scale, Landmark, Trophy, Search, LineChart, Plus, X, FileText, Loader2 } from 'lucide-react';
import type { ModelOption, ImageAttachment, FileAttachment } from '@/lib/types';
import { chatFilesApi } from '@/lib/api';
import ModelPicker from './ModelPicker';

interface NewChatWelcomeProps {
  onSendMessage: (message: string, images?: ImageAttachment[], skills?: string[], files?: FileAttachment[]) => void;
  disabled?: boolean;
  prefillMessage?: string;
  prefillLabel?: string;
  models?: ModelOption[];
  model?: string;
  onModelChange?: (id: string) => void;
}

// Example prompts shown as one-click starters. Mirrors the landing page so the
// empty chat feels alive and teaches what Finch can do.
const SUGGESTIONS: { icon: React.ElementType; label: string; prompt: string }[] = [
  { icon: TrendingUp, label: 'Valuation check', prompt: 'Is NVDA overvalued right now?' },
  { icon: Scale, label: 'Compare companies', prompt: 'Compare Apple and Microsoft margins over the last 5 years' },
  { icon: Search, label: 'Insider activity', prompt: 'Which insiders bought their own stock this week?' },
  { icon: Landmark, label: 'Macro & rates', prompt: 'What are prediction markets pricing for the next Fed decision?' },
  { icon: Trophy, label: 'My portfolio', prompt: 'Show me my biggest winners this month' },
  { icon: LineChart, label: 'Build a screen', prompt: 'Find profitable small-cap tech stocks growing revenue over 20%' },
];

const DOCUMENT_TYPES = ['application/pdf', 'text/csv', 'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];

export default function NewChatWelcome({ onSendMessage, disabled = false, prefillMessage, prefillLabel, models, model, onModelChange }: NewChatWelcomeProps) {
  const [message, setMessage] = useState('');
  const [images, setImages] = useState<ImageAttachment[]>([]);
  const [files, setFiles] = useState<FileAttachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // A stable id used only to address the per-user sandbox for uploads made before
  // the first message creates the real chat. The backend falls back to the
  // authenticated user when no chat row exists, and the sandbox is per-user, so
  // files land in /home/user/uploads regardless and are visible in the new chat.
  const draftChatIdRef = useRef<string>(typeof crypto !== 'undefined' ? crypto.randomUUID() : 'draft');

  useEffect(() => {
    if (prefillMessage) {
      setMessage(prefillMessage);
      setTimeout(() => {
        const t = textareaRef.current;
        if (!t) return;
        t.focus();
        t.style.height = 'auto';
        t.style.height = Math.min(t.scrollHeight, 220) + 'px';
        t.setSelectionRange(t.value.length, t.value.length);
      }, 50);
    }
  }, [prefillMessage]);

  const processFile = async (file: File) => {
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        setImages(prev => [...prev, { data: result.split(',')[1], media_type: file.type }]);
      };
      reader.readAsDataURL(file);
    } else if (DOCUMENT_TYPES.includes(file.type) || file.name.endsWith('.pdf') || file.name.endsWith('.csv')) {
      setUploading(true);
      try {
        const attachment = await chatFilesApi.uploadFile(draftChatIdRef.current, file);
        setFiles(prev => [...prev, attachment]);
      } catch (e) {
        console.error('File upload failed:', e);
      } finally {
        setUploading(false);
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files || []).forEach(f => processFile(f));
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    Array.from(e.dataTransfer.files).forEach(f => processFile(f));
  };

  const handleSubmit = () => {
    if ((message.trim() || images.length > 0 || files.length > 0) && !disabled && !uploading) {
      let fullMessage = message;
      if (files.length > 0) {
        const fileList = files.map(f => f.path).join('\n');
        fullMessage = `[Uploaded files]\n${fileList}\n\n${message}`;
      }
      onSendMessage(
        fullMessage,
        images.length > 0 ? images : undefined,
        undefined,
        files.length > 0 ? files : undefined,
      );
      setMessage('');
      setImages([]);
      setFiles([]);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSend = (message.trim() || images.length > 0 || files.length > 0) && !disabled && !uploading;

  return (
    <div className="flex flex-col h-full items-center justify-center px-5">
      <div className="w-full max-w-3xl -mt-20">
        <h1 className="text-4xl font-light text-gray-800 text-center mb-2 tracking-tight">Finch</h1>
        <p className="text-sm text-gray-400 text-center mb-8">Research smarter. Invest better.</p>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf,.csv,.xlsx,.xls"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />

        <div
          className={`rounded-2xl border bg-white shadow-sm transition-all ${
            isDragging ? 'border-gray-400 bg-gray-50' : 'border-gray-200 focus-within:border-gray-300 focus-within:shadow-md'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {(images.length > 0 || files.length > 0 || uploading) && (
            <div className="flex flex-wrap gap-2 px-3 pt-3">
              {images.map((img, idx) => (
                <div key={`img-${idx}`} className="relative group">
                  <img
                    src={`data:${img.media_type};base64,${img.data}`}
                    alt={`Attachment ${idx + 1}`}
                    className="h-14 w-14 object-cover rounded-lg border border-gray-200"
                  />
                  <button
                    onClick={() => setImages(prev => prev.filter((_, i) => i !== idx))}
                    className="absolute -top-1.5 -right-1.5 bg-gray-800 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs leading-none hover:bg-gray-900 transition-colors"
                  >
                    ×
                  </button>
                </div>
              ))}
              {files.map((f, idx) => (
                <div key={`file-${idx}`} className="flex items-center gap-1.5 bg-gray-100 rounded-lg px-2.5 py-1.5 text-sm text-gray-700">
                  <FileText className="w-4 h-4 text-red-500 flex-shrink-0" />
                  <span className="truncate max-w-[150px]">{f.name}</span>
                  <button
                    onClick={() => setFiles(prev => prev.filter((_, i) => i !== idx))}
                    className="text-gray-400 hover:text-gray-600 ml-0.5"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {uploading && (
                <div className="flex items-center gap-1.5 bg-gray-50 rounded-lg px-2.5 py-1.5 text-sm text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </div>
              )}
            </div>
          )}

          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              const t = e.target;
              t.style.height = 'auto';
              t.style.height = Math.min(t.scrollHeight, 200) + 'px';
            }}
            onKeyDown={handleKeyDown}
            placeholder={isDragging ? 'Drop file here...' : 'Ask anything...'}
            disabled={disabled}
            rows={2}
            autoFocus
            className="w-full resize-none bg-transparent px-5 py-4 text-gray-900 placeholder-gray-400 focus:outline-none text-[15px] leading-relaxed disabled:cursor-not-allowed"
            style={{ minHeight: '64px', maxHeight: '200px' }}
          />
          <div className="flex items-center justify-between px-3 py-2 gap-2">
            <div className="flex items-center gap-1">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled}
                title="Attach file"
                className="flex items-center justify-center w-8 h-8 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-40 transition-all"
              >
                <Plus className="w-4 h-4" />
              </button>
              {models && models.length > 0 && onModelChange && (
                <ModelPicker models={models} value={model} onChange={onModelChange} disabled={disabled} />
              )}
            </div>
            <button
              onClick={handleSubmit}
              disabled={!canSend}
              className="p-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-full transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        {/* One-click starters */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {SUGGESTIONS.map(({ icon: Icon, label, prompt }) => (
            <button
              key={label}
              onClick={() => !disabled && onSendMessage(prompt)}
              disabled={disabled}
              className="group flex items-center gap-3 text-left rounded-xl border border-gray-200 bg-white px-4 py-3 transition-all hover:border-emerald-300 hover:shadow-sm hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100 transition-colors">
                <Icon className="w-4 h-4" strokeWidth={2} />
              </span>
              <span className="min-w-0">
                <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400 group-hover:text-emerald-600 transition-colors">{label}</span>
                <span className="block text-[13px] text-gray-700 truncate">{prompt}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
