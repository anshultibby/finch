'use client';

/**
 * ProfileWizard — traditional stepped onboarding (replaces the old fake-chat
 * GoalWizard). Collects the user's investing profile: goal kind → the numbers →
 * risk → options → preferences (watch / notify / experience / constraints) →
 * connect. Predictable, on-brand (Finch tokens), no LLM/regex routing. Steps are
 * dynamic per kind (protect skips risk; only `number` shows options).
 *
 * State is a single flat `Draft` so the same instrument components drive both
 * this wizard and the Settings profile editor. On finish it hands a
 * SetGoalRequest to onComplete(); `onSkip` (if given) lets the user in without a
 * profile (soft gate).
 */
import React, { useMemo, useState } from 'react';
import type { SetGoalRequest, GoalKind } from '@/lib/api';
import {
  Draft, emptyDraft, draftToRequest, Card,
  NumbersInstrument, RiskInstrument, PreferencesFields,
} from './instruments';

type StepKey = 'kind' | 'numbers' | 'risk' | 'options' | 'prefs' | 'connect';

const META: Record<StepKey, { t: string; sub: string }> = {
  kind:    { t: 'What are we doing?', sub: "Pick the shape of your mission. You can change it later." },
  numbers: { t: 'The numbers',        sub: "Drag to set it — I'll show you what it takes." },
  risk:    { t: 'How hard to push',   sub: 'This sets my default aggressiveness. You approve every trade.' },
  options: { t: 'Options?',           sub: 'Options add range; I keep the downside boxed in either way.' },
  prefs:   { t: 'A bit about you',    sub: 'So I tailor what I surface — and what I never do.' },
  connect: { t: 'Connect an account', sub: "So I plan from what you actually own. Nothing trades without your say-so." },
};

const KINDS: { k: GoalKind; icon: string; t: string; sub: string }[] = [
  { k: 'number',  icon: '🎯', t: 'Hit a number',   sub: 'A dollar target by a deadline' },
  { k: 'grow',    icon: '🌱', t: 'Grow long-term', sub: 'Steady compounding over years' },
  { k: 'income',  icon: '💵', t: 'Monthly income', sub: 'Cash flow from what I hold' },
  { k: 'protect', icon: '🛡️', t: 'Watch & protect', sub: 'Just keep an eye out, warn me' },
];

function stepsFor(kind: GoalKind | null): StepKey[] {
  const s: StepKey[] = ['kind', 'numbers'];
  if (kind && kind !== 'protect') s.push('risk');
  if (kind === 'number') s.push('options');
  s.push('prefs', 'connect');
  return s;
}

export default function ProfileWizard({ onComplete, onSkip }: {
  onComplete: (g: SetGoalRequest) => void | Promise<void>;
  onSkip?: () => void;
}) {
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [i, setI] = useState(0);
  const [saving, setSaving] = useState(false);

  const steps = useMemo(() => stepsFor(draft.kind), [draft.kind]);
  const key = steps[Math.min(i, steps.length - 1)];
  const set = (patch: Partial<Draft>) => setDraft(d => ({ ...d, ...patch }));

  const canNext = key === 'kind' ? !!draft.kind : key === 'options' ? draft.options !== null : true;
  const isLast = key === 'connect';

  const next = () => { if (isLast) finish(); else setI(v => Math.min(v + 1, steps.length - 1)); };
  const back = () => setI(v => Math.max(0, v - 1));

  const finish = async () => {
    setSaving(true);
    await onComplete(draftToRequest(draft));
  };

  if (saving) {
    return (
      <div className="fixed inset-0 z-[60] grid place-items-center"
        style={{ background: 'radial-gradient(1100px 380px at 82% -12%, #f1efeb, transparent), #fafaf9' }}>
        <div className="text-center">
          <div className="w-14 h-14 rounded-full mx-auto mb-4 bg-gradient-to-br from-emerald-400 to-emerald-700 shadow-lg shadow-emerald-600/40" />
          <div className="text-lg font-semibold text-gray-900" style={{ fontFamily: 'var(--font-numeric), sans-serif' }}>Mission set.</div>
          <div className="text-sm text-stone-500 mt-1">Setting up your cockpit…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[60] flex flex-col"
      style={{ background: 'radial-gradient(1100px 380px at 82% -12%, #f1efeb, transparent), #fafaf9' }}>
      {/* top bar */}
      <div className="w-full max-w-[560px] mx-auto px-5 pt-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-700" />
          <span className="font-mono text-[10.5px] tracking-[0.2em] text-stone-400 uppercase">Finch · Onboarding</span>
        </div>
        {onSkip && (
          <button type="button" onClick={onSkip} className="text-xs text-stone-400 hover:text-stone-700 transition-colors">
            Skip for now →
          </button>
        )}
      </div>

      {/* centered step stack */}
      <div className="flex-1 overflow-y-auto flex flex-col">
        <div className="my-auto w-full max-w-[560px] mx-auto px-5 py-6">
          <div className="flex items-center gap-1.5">
            {steps.map((_, idx) => (
              <div key={idx} className={`h-1.5 rounded-full transition-all ${idx < i ? 'bg-emerald-500 w-6' : idx === i ? 'bg-gray-900 w-8' : 'bg-stone-200 w-6'}`} />
            ))}
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <h1 className="text-[22px] font-semibold tracking-tight text-gray-900" style={{ fontFamily: 'var(--font-numeric), sans-serif' }}>{META[key].t}</h1>
            <span className="text-xs text-stone-400">{i + 1} / {steps.length}</span>
          </div>
          <p className="text-[13px] text-stone-500 mt-1">{META[key].sub}</p>

          <div className="mt-6">
            {key === 'kind' && (
              <div className="grid grid-cols-2 gap-3">
                {KINDS.map(x => (
                  <button type="button" key={x.k} onClick={() => set({ kind: x.k })}
                    className={`text-left rounded-2xl border p-4 transition-all ${
                      draft.kind === x.k ? 'border-emerald-600 bg-emerald-50/60 ring-1 ring-emerald-600' : 'border-gray-200 bg-white hover:border-emerald-300'
                    }`}>
                    <div className="text-2xl mb-2">{x.icon}</div>
                    <div className="text-sm font-semibold text-gray-900">{x.t}</div>
                    <div className="text-xs text-stone-500 mt-0.5">{x.sub}</div>
                  </button>
                ))}
              </div>
            )}

            {key === 'numbers' && <NumbersInstrument draft={draft} set={set} />}
            {key === 'risk' && <RiskInstrument value={draft.risk} onChange={risk => set({ risk })} />}

            {key === 'options' && (
              <div className="grid grid-cols-2 gap-3">
                {([[true, 'Use options', 'more range, capped downside'], [false, 'Stocks only', 'keep it simple']] as const).map(([v, t, sub]) => (
                  <button type="button" key={t} onClick={() => set({ options: v })}
                    className={`rounded-2xl border p-5 text-center transition-all ${
                      draft.options === v ? 'border-emerald-600 bg-emerald-50/60 ring-1 ring-emerald-600' : 'border-gray-200 bg-white hover:border-emerald-300'
                    }`}>
                    <div className="text-sm font-semibold text-gray-900">{t}</div>
                    <div className="text-[11px] text-stone-400 mt-1">{sub}</div>
                  </button>
                ))}
              </div>
            )}

            {key === 'prefs' && <PreferencesFields draft={draft} set={set} />}

            {key === 'connect' && (
              <Card>
                <div className="font-mono text-[10.5px] tracking-[0.14em] uppercase text-emerald-700 mb-3">◆ connect an account</div>
                <div className="flex flex-col gap-2.5">
                  <ConnectBtn logo="RH" logoBg="#0b7d3e" title="Robinhood" sub="read positions + place trades you approve" onClick={finish} />
                  <ConnectBtn logo="◆" logoBg="#141210" title="Connect via SnapTrade" sub="Schwab · Fidelity · IBKR · Webull + 20 more" onClick={finish} />
                  <button type="button" onClick={finish}
                    className="text-center text-[12.5px] text-stone-500 underline underline-offset-[3px] py-2 hover:text-stone-700 transition-colors">
                    Skip — start me with a watchlist
                  </button>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* footer nav */}
      <div className="sticky bottom-0" style={{ background: 'linear-gradient(transparent, #fafaf9 40%)' }}>
        <div className="max-w-[560px] mx-auto px-5 pt-3 pb-6 flex items-center gap-3">
          <button type="button" onClick={back}
            className={`px-4 py-2.5 rounded-full text-sm font-semibold text-stone-600 hover:text-gray-900 transition-colors ${i === 0 ? 'invisible' : ''}`}>
            ← Back
          </button>
          <div className="flex-1" />
          {!isLast && (
            <button type="button" onClick={next} disabled={!canNext}
              className="px-6 py-2.5 rounded-full bg-gray-900 text-white text-sm font-semibold hover:bg-black transition-colors disabled:opacity-30">
              Continue
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ConnectBtn({ logo, logoBg, title, sub, onClick }: { logo: string; logoBg: string; title: string; sub: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className="finch-surface rounded-xl px-4 py-3.5 flex gap-3 items-center text-left w-full text-sm hover:border-emerald-600 transition-colors">
      <span className="w-9 h-9 rounded-lg flex-none grid place-items-center text-white font-bold text-[15px]" style={{ background: logoBg, fontFamily: 'var(--font-numeric), sans-serif' }}>{logo}</span>
      <span className="flex-1">
        <span className="block font-semibold text-gray-900">{title}</span>
        <span className="block text-xs text-stone-500">{sub}</span>
      </span>
      <span className="text-stone-400 text-lg">→</span>
    </button>
  );
}
