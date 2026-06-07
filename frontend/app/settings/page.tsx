'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { accountApi, type UserPreferences } from '@/lib/api';

export default function SettingsPage() {
  const { user } = useAuth();
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.id) return;
    accountApi
      .getPreferences(user.id)
      .then(setPrefs)
      .catch(() => setError('Could not load your settings.'))
      .finally(() => setLoading(false));
  }, [user?.id]);

  const setRequireApproval = async (value: boolean) => {
    if (!user?.id || !prefs) return;
    const previous = prefs;
    setPrefs({ ...prefs, require_trade_approval: value }); // optimistic
    setSaving(true);
    setError(null);
    try {
      const updated = await accountApi.updatePreferences(user.id, {
        require_trade_approval: value,
      });
      setPrefs(updated);
    } catch {
      setPrefs(previous); // revert on failure
      setError('Could not save. Try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fafaf9]">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <h1 className="text-2xl font-bold text-stone-900 mb-1">Settings</h1>
        <p className="text-sm text-stone-500 mb-8">Manage how Finch trades on your behalf.</p>

        <section className="bg-white border border-stone-200 rounded-2xl p-6">
          <h2 className="text-base font-semibold text-stone-900 mb-4">Trading</h2>

          {loading ? (
            <div className="h-16 animate-pulse bg-stone-100 rounded-lg" />
          ) : (
            <div className="flex items-start justify-between gap-6">
              <div>
                <div className="font-medium text-stone-900">Require approval for every trade</div>
                <p className="text-sm text-stone-500 mt-1 max-w-md">
                  When on, Finch never places an order without your one-click approval.
                  Turn off only if you want it to trade unattended — it will still respect
                  its risk limits and any dollar cap.
                </p>
              </div>

              <button
                type="button"
                role="switch"
                aria-checked={prefs?.require_trade_approval ?? true}
                disabled={saving}
                onClick={() => setRequireApproval(!(prefs?.require_trade_approval ?? true))}
                className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
                  prefs?.require_trade_approval ? 'bg-emerald-600' : 'bg-stone-300'
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                    prefs?.require_trade_approval ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
          )}

          {!loading && !prefs?.require_trade_approval && (
            <div className="mt-4 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              Unattended trading is on. Finch can place real orders on your agentic account
              without asking first.
            </div>
          )}

          {error && <div className="mt-4 text-sm text-red-600">{error}</div>}
        </section>
      </div>
    </div>
  );
}
