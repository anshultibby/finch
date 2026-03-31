import React, { useState, useEffect, KeyboardEvent, useRef, DragEvent, ClipboardEvent } from 'react';
import type { ImageAttachment, FileAttachment } from '@/lib/types';
import { chatFilesApi } from '@/lib/api';

interface ChatInputProps {
  onSendMessage: (message: string, images?: ImageAttachment[], skills?: string[], files?: FileAttachment[]) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
  prefillMessage?: string;
  chatId?: string;
}

export default function ChatInput({
  onSendMessage,
  onStop,
  disabled = false,
  isStreaming = false,
  placeholder = 'Ask me anything...',
  prefillMessage,
  chatId,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [images, setImages] = useState<ImageAttachment[]>([]);
  const [files, setFiles] = useState<FileAttachment[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (prefillMessage) {
      setMessage(prefillMessage);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [prefillMessage]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if ((message.trim() || images.length > 0 || files.length > 0) && !disabled && !uploading) {
      // If files are attached, prepend their sandbox paths so the agent knows about them
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
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const DOCUMENT_TYPES = ['application/pdf', 'text/csv', 'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];

  const processFile = async (file: File) => {
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        setImages(prev => [...prev, { data: result.split(',')[1], media_type: file.type }]);
      };
      reader.readAsDataURL(file);
    } else if (DOCUMENT_TYPES.includes(file.type) || file.name.endsWith('.pdf') || file.name.endsWith('.csv')) {
      if (!chatId) return;
      setUploading(true);
      try {
        const attachment = await chatFilesApi.uploadFile(chatId, file);
        setFiles(prev => [...prev, attachment]);
      } catch (e) {
        console.error('File upload failed:', e);
      } finally {
        setUploading(false);
      }
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    Array.from(e.dataTransfer.files).forEach(f => processFile(f));
  };

  const handlePaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    for (let i = 0; i < e.clipboardData.items.length; i++) {
      if (e.clipboardData.items[i].type.startsWith('image/')) {
        const file = e.clipboardData.items[i].getAsFile();
        if (file) processFile(file);
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files || []).forEach(f => processFile(f));
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const canSend = (message.trim() || images.length > 0 || files.length > 0) && !disabled && !uploading;

  return (
    <div
      className={`p-3 sm:p-4 safe-area-bottom transition-colors ${isDragging ? 'bg-primary-50' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.pdf,.csv,.xlsx,.xls"
        multiple
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Image previews */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {images.map((img, idx) => (
            <div key={idx} className="relative group">
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
        </div>
      )}

      {/* File attachment chips */}
      {(files.length > 0 || uploading) && (
        <div className="flex flex-wrap gap-2 mb-2">
          {files.map((f, idx) => (
            <div key={idx} className="flex items-center gap-1.5 bg-gray-100 rounded-lg px-2.5 py-1.5 text-sm text-gray-700">
              <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
              </svg>
              <span className="truncate max-w-[150px]">{f.name}</span>
              <button
                onClick={() => setFiles(prev => prev.filter((_, i) => i !== idx))}
                className="text-gray-400 hover:text-gray-600 ml-0.5"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          {uploading && (
            <div className="flex items-center gap-1.5 bg-gray-50 rounded-lg px-2.5 py-1.5 text-sm text-gray-400">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Uploading...
            </div>
          )}
        </div>
      )}

      {/* Input container */}
      <div className={`rounded-2xl border transition-colors shadow-sm ${
        isDragging
          ? 'border-primary-400 bg-primary-50'
          : 'border-gray-200 bg-white focus-within:border-gray-300 focus-within:shadow-md'
      }`}>
        <div className="flex items-end gap-2 px-3 py-3">
          {/* Image attach button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            title="Attach file"
            className="flex items-center justify-center w-8 h-8 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 disabled:opacity-40 transition-colors flex-shrink-0"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={isDragging ? 'Drop file here...' : placeholder}
            disabled={disabled}
            rows={1}
            className="flex-1 resize-none bg-transparent py-2 text-gray-900 placeholder-gray-400 focus:outline-none disabled:cursor-not-allowed"
            style={{ minHeight: '24px', maxHeight: '200px', fontSize: '15px', lineHeight: '1.5' }}
            onInput={(e) => {
              const t = e.target as HTMLTextAreaElement;
              t.style.height = 'auto';
              t.style.height = Math.min(t.scrollHeight, 200) + 'px';
            }}
          />

          {/* Stop / Send buttons */}
          {isStreaming ? (
            <button
              onClick={onStop}
              title="Stop generating"
              className="flex items-center justify-center w-8 h-8 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 16 16">
                <rect x="3" y="3" width="10" height="10" rx="1.5" />
              </svg>
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!canSend}
              title="Send message"
              className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Helper text */}
      <p className="text-[11px] text-gray-400 mt-1.5 hidden sm:block px-1">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
