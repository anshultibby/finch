'use client';

/**
 * ProfileEditor — the editable view of the user's mission + profile, for the
 * Settings page. Same instrument components as the onboarding ProfileWizard,
 * laid out as a single scrolling form (no steps). Loads the stored Goal, lets
 * the user change the mission kind, numbers, risk, options and preferences, and
 * saves via goalApi.setGoal (which also refreshes /home/user/store/profile.md).
 */
import React, { useEffect, useState } from 'react';
import { goalApi, type Goal } from '@/lib/api';
import {
  Draft, emptyDraft, goalToDraft, draftToRequest,
  NumbersInstrument, RiskInstrument, PreferencesFields,
} from './instruments';

const KINDS: { k: Draft['kind']; icon: string; t: string }[] = [
  { k: 'number', icon: '🎯', t: 'Hit a number' },
  { k: 'grow', icon: '🌱', t: 'Grow long-term' },
  { k: 'income', icon: '💵', t: 'Monthly income' },
  { k: 'protect', icon: '🛡️', t: 'Watch & protect' },
];

export default function ProfileEditor({ userId }: { userId: string }) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    goalApi.getGoal(userId)
      .then((g: Goal | null) => { if (!cancelled) setDraft(g ? goalToDraft(g) : { ...emptyDraft(), kind: 'number' }); })
      .catch(() => { if (!cancelled) setError('Could not load your profile.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [userId]);

  const set = (patch: Partial<Draft>) => { setDraft(d => (d ? { ...d, ...patch } : d)); setSaved(false); };

  const save = async () => {
    if (!draft) return;
    setSaving(true); setError(null);
    try {
      await goalApi.setGoal(userId, draftToRequest(draft));
      setSaved(true);
    } catch {
      setError('Could not save. Try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="h-40 animate-pulse bg-stone-100 rounded-2xl" />;
  if (!draft) return <div className="text-sm text-red-600">{error ?? 'Could not load your profile.'}</div>;

  return (
    <div className="flex flex-col gap-4">
      {/* mission kind */}
      <div>
        <div className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-emerald-700 mb-2">◆ mission</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {KINDS.map(x => (
            <button type="button" key={x.k} onClick={() => set({ kind: x.k })}
              className={`rounded-xl border px-3 py-2.5 text-center transition-all ${
                draft.kind === x.k ? 'border-emerald-600 bg-emerald-50/60 ring-1 ring-emerald-600' : 'border-gray-200 bg-white hover:border-emerald-300'
              }`}>
              <div className="text-lg">{x.icon}</div>
              <div className="text-xs font-semibold text-gray-900 mt-0.5">{x.t}</div>
            </button>
          ))}
        </div>
      </div>

      <NumbersInstrument draft={draft} set={set} />
      {draft.kind !== 'protect' && <RiskInstrument value={draft.risk} onChange={risk => set({ risk })} />}
      {draft.kind === 'number' && (
        <div className="grid grid-cols-2 gap-3">
          {([[true, 'Use options'], [false, 'Stocks only']] as const).map(([v, t]) => (
            <button type="button" key={t} onClick={() => set({ options: v })}
              className={`rounded-xl border py-3 text-center text-sm font-semibold transition-all ${
                draft.options === v ? 'border-emerald-600 bg-emerald-50/60 ring-1 ring-emerald-600 text-gray-900' : 'border-gray-200 bg-white text-gray-700 hover:border-emerald-300'
              }`}>
              {t}
            </button>
          ))}
        </div>
      )}

      <PreferencesFields draft={draft} set={set} />

      <div className="flex items-center gap-3 pt-1">
        <button type="button" onClick={save} disabled={saving}
          className="inline-flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors disabled:opacity-50">
          {saving ? 'Saving…' : 'Save profile'}
        </button>
        {saved && <span className="text-sm text-emerald-700">Saved ✓</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </div>
  );
}
