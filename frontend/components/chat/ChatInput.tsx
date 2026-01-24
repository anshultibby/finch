import React, { useState, KeyboardEvent, useRef, DragEvent, ClipboardEvent } from 'react';
import type { ImageAttachment } from '@/lib/types';

interface ChatInputProps {
  onSendMessage: (message: string, images?: ImageAttachment[]) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
}

export default function ChatInput({ 
  onSendMessage, 
  onStop,
  disabled = false,
  isStreaming = false,
  placeholder = "Type your message..."
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [images, setImages] = useState<ImageAttachment[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    if ((message.trim() || images.length > 0) && !disabled) {
      onSendMessage(message, images.length > 0 ? images : undefined);
      setMessage('');
      setImages([]);
    }
  };

  const handleStop = () => {
    onStop?.();
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const processFile = (file: File) => {
    if (!file.type.startsWith('image/')) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      // Remove the data:image/xxx;base64, prefix
      const base64Data = result.split(',')[1];
      const mediaType = file.type;
      
      setImages(prev => [...prev, { data: base64Data, media_type: mediaType }]);
    };
    reader.readAsDataURL(file);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    files.forEach(processFile);
  };

  const handlePaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith('image/')) {
        const file = items[i].getAsFile();
        if (file) processFile(file);
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach(processFile);
    // Reset input so same file can be selected again
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  // When streaming, allow sending (which will interrupt)
  const canSend = (message.trim() || images.length > 0) && !disabled;

  return (
    <div 
      className={`border-t border-gray-200 bg-white p-3 sm:p-4 safe-area-bottom transition-colors ${isDragging ? 'bg-blue-50 border-blue-300' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Image previews */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {images.map((img, idx) => (
            <div key={idx} className="relative group">
              <img 
                src={`data:${img.media_type};base64,${img.data}`}
                alt={`Attachment ${idx + 1}`}
                className="h-16 w-16 object-cover rounded-lg border border-gray-200"
              />
              <button
                onClick={() => removeImage(idx)}
                className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-6 h-6 sm:w-5 sm:h-5 flex items-center justify-center text-xs touch-manipulation"
                style={{ minHeight: '24px', minWidth: '24px' }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      
      <div className="flex items-end gap-1.5 sm:gap-2">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        
        {/* Image upload button - optimized touch target for mobile */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="p-2.5 sm:p-3 text-gray-500 hover:text-gray-700 active:text-gray-900 hover:bg-gray-100 active:bg-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-manipulation flex-shrink-0"
          title="Attach image"
          style={{ minHeight: '44px', minWidth: '44px' }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </button>
        
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          onPaste={handlePaste}
          placeholder={isDragging ? "Drop image here..." : placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 sm:px-4 py-2.5 sm:py-3 text-base focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed touch-manipulation"
          style={{ minHeight: '44px', maxHeight: '120px', fontSize: '16px' }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = Math.min(target.scrollHeight, 120) + 'px';
          }}
        />
        {/* Stop button - subtle circular design with better touch target */}
        {isStreaming && (
          <button
            onClick={handleStop}
            className="w-11 h-11 sm:w-10 sm:h-10 flex items-center justify-center rounded-full border border-gray-300 bg-white hover:bg-gray-50 active:bg-gray-100 text-gray-600 hover:text-gray-800 transition-colors touch-manipulation flex-shrink-0"
            title="Stop generating"
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
              <rect x="3" y="3" width="10" height="10" rx="1" />
            </svg>
          </button>
        )}
        
        {/* Send button - optimized for mobile */}
        <button
          onClick={handleSubmit}
          disabled={!canSend}
          className="rounded-lg bg-primary-600 px-4 sm:px-6 py-2.5 sm:py-3 text-white font-medium hover:bg-primary-700 active:bg-primary-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors touch-manipulation flex-shrink-0"
          style={{ minHeight: '44px' }}
        >
          <span className="hidden xs:inline">Send</span>
          <span className="xs:hidden">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </span>
        </button>
      </div>
      <p className="text-[11px] sm:text-xs text-gray-500 mt-2 hidden sm:block">
        Press Enter to send, Shift+Enter for new line • Paste or drop images to attach
      </p>
    </div>
  );
}
