'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { accountApi, type UserPreferences } from '@/lib/api';

/**
 * Trading & approvals settings as a floating modal (same shell as CreditsModal),
 * not a route — so opening it never unmounts whatever's behind it. That keeps an
 * in-flight chat stream alive while the user flips a setting.
 */
export default function SettingsModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !user?.id) return;
    setLoading(true);
    accountApi
      .getPreferences(user.id)
      .then(setPrefs)
      .catch(() => setError('Could not load your settings.'))
      .finally(() => setLoading(false));
  }, [isOpen, user?.id]);

  // Esc to close, matching common modal affordances.
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  const setRequireApproval = async (value: boolean) => {
    if (!user?.id || !prefs) return;
    const previous = prefs;
    setPrefs({ ...prefs, require_trade_approval: value }); // optimistic
    setSaving(true);
    setError(null);
    try {
      const updated = await accountApi.updatePreferences(user.id, { require_trade_approval: value });
      setPrefs(updated);
    } catch {
      setPrefs(previous); // revert on failure
      setError('Could not save. Try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const requireApproval = prefs?.require_trade_approval ?? true;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-6 pt-5 pb-3 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Trading &amp; approvals</h2>
            <p className="text-sm text-gray-500 mt-0.5">Manage how Finch trades on your behalf.</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 -mr-1">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 pb-5">
          {loading ? (
            <div className="h-16 animate-pulse bg-gray-100 rounded-lg" />
          ) : (
            <div className="rounded-xl border border-gray-200 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium text-gray-900">Require approval for every trade</div>
                  <p className="text-sm text-gray-500 mt-1">
                    When on, Finch never places an order without your one-click approval.
                    Turn off only if you want it to trade unattended — it will still respect
                    its risk limits and any dollar cap.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={requireApproval}
                  disabled={saving}
                  onClick={() => setRequireApproval(!requireApproval)}
                  className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
                    requireApproval ? 'bg-emerald-600' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                      requireApproval ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              {!requireApproval && (
                <div className="mt-4 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                  Unattended trading is on. Finch can place real orders on your agentic account
                  without asking first.
                </div>
              )}
            </div>
          )}

          {error && <div className="mt-4 text-sm text-red-600">{error}</div>}
        </div>
      </div>
    </div>
  );
}
