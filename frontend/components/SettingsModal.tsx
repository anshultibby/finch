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
  const [briefPhoneDraft, setBriefPhoneDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !user?.id) return;
    setLoading(true);
    accountApi
      .getPreferences(user.id)
      .then((p) => {
        setPrefs(p);
        setBriefPhoneDraft(p.morning_brief_phone || '');
      })
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

  const savePrefs = async (updates: Partial<UserPreferences>) => {
    if (!user?.id || !prefs) return;
    const previous = prefs;
    setPrefs({ ...prefs, ...updates }); // optimistic
    setSaving(true);
    setError(null);
    try {
      const updated = await accountApi.updatePreferences(user.id, updates);
      setPrefs(updated);
    } catch {
      setPrefs(previous); // revert on failure
      setError('Could not save. Try again.');
    } finally {
      setSaving(false);
    }
  };

  const setRequireApproval = (value: boolean) => savePrefs({ require_trade_approval: value });

  const setBriefEnabled = (value: boolean) =>
    savePrefs({
      morning_brief_enabled: value,
      // Pin the schedule to the user's current local timezone on every toggle,
      // so the brief lands at the right local hour without asking.
      morning_brief_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    });

  const setBriefTime = (time: string) => {
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) return;
    savePrefs({
      morning_brief_time: time,
      morning_brief_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    });
  };

  const saveBriefPhone = () => {
    const phone = briefPhoneDraft.trim();
    if (phone && !/^\+[1-9]\d{6,14}$/.test(phone)) {
      setError('WhatsApp number must be in international format, e.g. +15551234567.');
      return;
    }
    if (phone === (prefs?.morning_brief_phone ?? '')) return;
    savePrefs({ morning_brief_phone: phone });
  };

  if (!isOpen) return null;

  const requireApproval = prefs?.require_trade_approval ?? true;
  const briefEnabled = prefs?.morning_brief_enabled ?? false;
  const briefTime = prefs?.morning_brief_time ?? '08:00';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-6 pt-5 pb-3 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Settings</h2>
            <p className="text-sm text-gray-500 mt-0.5">Trading approvals and daily updates.</p>
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

          {!loading && (
            <div className="rounded-xl border border-gray-200 p-4 mt-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium text-gray-900">Daily morning brief</div>
                  <p className="text-sm text-gray-500 mt-1">
                    Every morning, Finch checks your holdings and watchlist — overnight moves,
                    news that matters, upcoming earnings — and sends you a short brief by
                    email and push.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={briefEnabled}
                  disabled={saving}
                  onClick={() => setBriefEnabled(!briefEnabled)}
                  className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
                    briefEnabled ? 'bg-emerald-600' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                      briefEnabled ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              {briefEnabled && (
                <>
                  <div className="mt-4 flex items-center gap-3">
                    <label htmlFor="brief-time" className="text-sm text-gray-600">Deliver at</label>
                    <input
                      id="brief-time"
                      type="time"
                      value={briefTime}
                      disabled={saving}
                      onChange={(e) => setBriefTime(e.target.value)}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-900 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
                    />
                    <span className="text-xs text-gray-400">
                      {Intl.DateTimeFormat().resolvedOptions().timeZone}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center gap-3">
                    <label htmlFor="brief-phone" className="text-sm text-gray-600">WhatsApp</label>
                    <input
                      id="brief-phone"
                      type="tel"
                      placeholder="+15551234567 (optional)"
                      value={briefPhoneDraft}
                      disabled={saving}
                      onChange={(e) => setBriefPhoneDraft(e.target.value)}
                      onBlur={saveBriefPhone}
                      className="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
                    />
                  </div>
                </>
              )}
            </div>
          )}

          {error && <div className="mt-4 text-sm text-red-600">{error}</div>}
        </div>
      </div>
    </div>
  );
}
