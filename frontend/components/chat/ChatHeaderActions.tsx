'use client';

import React, { useState, useRef, useEffect } from 'react';
import { MoreHorizontal, Share2, Pencil, Trash2, Copy, Check, X } from 'lucide-react';
import { chatApi } from '@/lib/api';

interface ChatHeaderActionsProps {
  chatId: string;
  title: string | null;
  isPublic?: boolean;
  shareToken?: string | null;
  onRenamed: (title: string) => void;
  onDeleted: () => void;
  onShareChange: (isPublic: boolean, shareToken: string | null) => void;
}

/**
 * Top-right chat toolbar: a dedicated Share button plus a "…" menu
 * (rename / delete). Mirrors the per-chat actions in ChatItemMenu but
 * laid out for the conversation header instead of the sidebar list.
 */
export default function ChatHeaderActions({
  chatId,
  title,
  isPublic = false,
  shareToken = null,
  onRenamed,
  onDeleted,
  onShareChange,
}: ChatHeaderActionsProps) {
  const [open, setOpen] = useState(false);
  const [modal, setModal] = useState<'none' | 'rename' | 'share'>('none');
  const [renameValue, setRenameValue] = useState(title || '');
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const shareUrl = shareToken
    ? `${typeof window !== 'undefined' ? window.location.origin : ''}/share/chat/${shareToken}`
    : '';

  const openShare = async () => {
    setOpen(false);
    setModal('share');
    if (!isPublic || !shareToken) {
      setBusy(true);
      try {
        const res = await chatApi.shareChat(chatId);
        onShareChange(res.is_public, res.share_token);
      } catch (err) {
        console.error('Failed to share chat:', err);
      } finally {
        setBusy(false);
      }
    }
  };

  const unshare = async () => {
    setBusy(true);
    try {
      const res = await chatApi.shareChat(chatId); // toggles off (was public)
      onShareChange(res.is_public, res.share_token);
      setModal('none');
    } catch (err) {
      console.error('Failed to unshare chat:', err);
    } finally {
      setBusy(false);
    }
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* ignore */ }
  };

  const openRename = () => {
    setRenameValue(title || '');
    setOpen(false);
    setModal('rename');
  };

  const submitRename = async () => {
    const next = renameValue.trim();
    if (!next || next === title) { setModal('none'); return; }
    setBusy(true);
    try {
      await chatApi.renameChat(chatId, next);
      onRenamed(next);
      setModal('none');
    } catch (err) {
      console.error('Failed to rename chat:', err);
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    setOpen(false);
    if (!window.confirm('Delete this chat? This cannot be undone.')) return;
    try {
      await chatApi.deleteChat(chatId);
      onDeleted();
    } catch (err) {
      console.error('Failed to delete chat:', err);
    }
  };

  return (
    <div ref={menuRef} className="relative flex items-center gap-1">
      <button
        onClick={openShare}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
        title="Share chat"
      >
        <Share2 className="w-4 h-4" /> Share
      </button>
      <button
        onClick={() => setOpen(v => !v)}
        className="p-1.5 rounded-lg text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors"
        title="Chat options"
        aria-label="Chat options"
      >
        <MoreHorizontal className="w-5 h-5" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-44 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          <button onClick={openShare} className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
            <Share2 className="w-4 h-4 text-gray-500" /> Share
          </button>
          <button onClick={openRename} className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
            <Pencil className="w-4 h-4 text-gray-500" /> Rename
          </button>
          <div className="my-1 border-t border-gray-100" />
          <button onClick={handleDelete} className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors">
            <Trash2 className="w-4 h-4" /> Delete
          </button>
        </div>
      )}

      {/* Rename modal */}
      {modal === 'rename' && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30" onClick={() => setModal('none')}>
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 w-[90%] max-w-sm p-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Rename chat</h3>
            <input
              autoFocus
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') submitRename(); if (e.key === 'Escape') setModal('none'); }}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="Chat title"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setModal('none')} className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">Cancel</button>
              <button onClick={submitRename} disabled={busy} className="px-3 py-1.5 text-sm text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors disabled:opacity-50">Save</button>
            </div>
          </div>
        </div>
      )}

      {/* Share modal */}
      {modal === 'share' && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30" onClick={() => setModal('none')}>
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 w-[90%] max-w-md p-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-semibold text-gray-900">Share public link</h3>
              <button onClick={() => setModal('none')} className="p-1 text-gray-400 hover:text-gray-700 rounded"><X className="w-4 h-4" /></button>
            </div>
            <p className="text-xs text-gray-500 mb-3">Anyone with this link can view a read-only copy of this conversation.</p>
            {busy && !shareUrl ? (
              <div className="flex items-center gap-2 text-sm text-gray-500 py-2">
                <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" /> Creating link…
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                  <span className="text-xs text-gray-700 truncate flex-1">{shareUrl}</span>
                  <button onClick={copyLink} className="flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-600 flex-shrink-0">
                    {copied ? <><Check className="w-3.5 h-3.5" /> Copied</> : <><Copy className="w-3.5 h-3.5" /> Copy</>}
                  </button>
                </div>
                <div className="flex justify-end mt-4">
                  <button onClick={unshare} disabled={busy} className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50">
                    Unshare
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
