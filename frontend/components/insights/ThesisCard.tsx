'use client';

/**
 * ThesisCard — "Your thesis" on a stock: why the user owns/watches it and what
 * would make them wrong. Finch judges every move, earnings report and dividend
 * change on this name against it (backend: services/theses.py, stored in the
 * memory store at store/theses/{SYMBOL}.md). Mirrors the mobile ThesisCard.
 */
import { useCallback, useEffect, useState } from 'react';
import { Feather, Sparkles, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigation } from '@/contexts/NavigationContext';
import {
  thesesApi, VERDICT_META, THESIS_STATUS_META,
  type Thesis, type ThesisCheck, type ThesisStance,
} from '@/lib/api';

const STANCES: { key: ThesisStance; label: string }[] = [
  { key: 'own', label: 'I own it' },
  { key: 'watch', label: 'Watching' },
  { key: 'avoid', label: 'Avoiding' },
];

// Plain-language prompts per stance. "What would make me wrong" is what's
// stored (`breaks`), but people think in terms of the decision it triggers.
const COPY: Record<ThesisStance, { why: string; breaks: string; breaksLabel: string }> = {
  own: { why: 'Why do you own it?', breaks: 'What would make you sell?', breaksLabel: 'Sell if' },
  watch: { why: 'Why are you watching it?', breaks: 'What would make you buy — or move on?', breaksLabel: 'Act if' },
  avoid: { why: 'Why are you avoiding it?', breaks: 'What would change your mind?', breaksLabel: 'Reconsider if' },
};

export default function ThesisCard({ symbol }: { symbol: string }) {
  const { user } = useAuth();
  const { openChatWithPrompt } = useNavigation();
  const [thesis, setThesis] = useState<Thesis | null | undefined>(undefined);
  const [check, setCheck] = useState<ThesisCheck | null>(null);
  const [editing, setEditing] = useState(false);
  const [why, setWhy] = useState('');
  const [breaks, setBreaks] = useState('');
  const [stance, setStance] = useState<ThesisStance>('own');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) return;
    setCheck(null);
    try {
      const t = await thesesApi.get(symbol);
      setThesis(t);
      if (t) thesesApi.check(symbol).then(setCheck).catch(() => {});
    } catch {
      setThesis(null);
    }
  }, [user, symbol]);

  useEffect(() => { load(); }, [load]);

  if (!user || thesis === undefined) return null;

  const startEdit = () => {
    setWhy(thesis?.why || '');
    setBreaks(thesis?.breaks || '');
    setStance(thesis?.stance || 'own');
    setError(null);
    setEditing(true);
  };

  const save = async () => {
    if (!why.trim()) { setError('Say why in a sentence — that’s what Finch checks against.'); return; }
    if (!breaks.trim()) { setError(`Answer “${COPY[stance].breaks}” — it’s the line every alert gets checked against.`); return; }
    setSaving(true);
    try {
      const t = await thesesApi.save(symbol, { why: why.trim(), breaks: breaks.trim(), stance });
      setThesis(t);
      setEditing(false);
      setCheck(null);
      thesesApi.check(symbol).then(setCheck).catch(() => {});
    } catch {
      setError("Couldn't save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  const draftWithFinch = () => openChatWithPrompt(
    `Help me write my thesis on ${symbol}. Ask me why I own or am watching it and what would make me sell — push me to make that line concrete and checkable (a number, a date, an event). When I confirm, save it with save_thesis.`,
    `${symbol} thesis`,
  );

  const card = 'bg-white border border-emerald-100 rounded-2xl p-4';

  if (!thesis || editing) {
    return (
      <div className={card}>
        <div className="flex items-center gap-1.5 mb-1.5">
          <Feather className="w-4 h-4 text-emerald-600" />
          <span className="text-[15px] font-bold text-gray-900">{thesis ? `Edit your ${symbol} thesis` : `Why ${symbol}?`}</span>
        </div>
        {!thesis && !editing ? (
          <>
            <p className="text-[13px] text-stone-500 leading-relaxed">
              One line on why, and one on what would make you sell. Finch judges every move, earnings report and dividend change on {symbol} against your words.
            </p>
            <div className="flex gap-2 mt-3">
              <button onClick={startEdit} className="px-4 py-2 rounded-full bg-emerald-600 text-white text-[13px] font-bold hover:bg-emerald-700">Write it</button>
              <button onClick={draftWithFinch} className="flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-emerald-50 text-emerald-700 text-[13px] font-bold hover:bg-emerald-100">
                <Sparkles className="w-3.5 h-3.5" /> Draft it with Finch
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="flex gap-1.5 mb-2">
              {STANCES.map(s => (
                <button key={s.key} onClick={() => setStance(s.key)}
                  className={`px-3 py-1 rounded-full text-[12.5px] font-medium border ${stance === s.key ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : 'border-stone-200 text-stone-600'}`}>
                  {s.label}
                </button>
              ))}
            </div>
            <label className="block text-[11.5px] font-bold text-stone-500 uppercase tracking-wider mt-2 mb-1">{COPY[stance].why}</label>
            <textarea value={why} onChange={e => setWhy(e.target.value)} rows={2}
              placeholder="e.g. Revenue keeps growing 15%+ while margins expand"
              className="w-full border border-stone-200 rounded-xl px-3 py-2 text-[14px] focus:outline-none focus:border-emerald-300" />
            <label className="block text-[11.5px] font-bold text-stone-500 uppercase tracking-wider mt-2 mb-1">{COPY[stance].breaks}</label>
            <textarea value={breaks} onChange={e => setBreaks(e.target.value)} rows={2}
              placeholder="e.g. Growth drops below 10% two quarters in a row"
              className="w-full border border-stone-200 rounded-xl px-3 py-2 text-[14px] focus:outline-none focus:border-emerald-300" />
            {error && <p className="text-[12.5px] text-red-600 mt-1.5">{error}</p>}
            <div className="flex gap-2 mt-3">
              <button onClick={save} disabled={saving}
                className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-emerald-600 text-white text-[13px] font-bold hover:bg-emerald-700 disabled:opacity-70">
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Save thesis
              </button>
              {thesis && <button onClick={() => setEditing(false)} className="px-3 py-2 text-[13px] font-semibold text-stone-500">Cancel</button>}
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={card}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <Feather className="w-4 h-4 text-emerald-600" />
          <span className="text-[15px] font-bold text-gray-900">Your thesis</span>
          <span className="text-[11px] font-medium text-stone-500 bg-stone-100 px-1.5 py-0.5 rounded-md">
            {STANCES.find(s => s.key === thesis.stance)?.label}
          </span>
        </div>
        <button onClick={startEdit} className="text-[13px] font-bold text-emerald-700 hover:underline">Edit</button>
      </div>
      <p className="text-[14px] text-gray-900 leading-relaxed">{thesis.why}</p>
      {thesis.breaks && <p className="text-[13px] text-stone-600 leading-relaxed mt-1.5"><span className="font-bold text-gray-900">{COPY[thesis.stance].breaksLabel}: </span>{thesis.breaks}</p>}

      <div className="mt-3 pt-3 border-t border-stone-100">
        {check?.check ? (
          <>
            <span className="inline-block rounded-md px-1.5 py-0.5 text-[11px] font-bold mb-1"
              style={{ color: THESIS_STATUS_META[check.check.status].fg, background: THESIS_STATUS_META[check.check.status].bg }}>
              Today · {THESIS_STATUS_META[check.check.status].label}
            </span>
            <p className="text-[13px] text-stone-700 leading-relaxed">{check.check.reason}</p>
          </>
        ) : !check ? (
          <p className="flex items-center gap-1.5 text-[13px] text-stone-500"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Checking today against your thesis…</p>
        ) : null}
      </div>

      {thesis.log.length > 0 && (
        <div className="mt-3">
          <div className="text-[11.5px] font-bold text-stone-500 uppercase tracking-wider mb-1">Story so far</div>
          {thesis.log.slice(-3).reverse().map((e, i) => (
            <div key={`${e.date}-${i}`} className="flex gap-3 py-1.5">
              <span className="text-[12px] text-stone-400 w-12 flex-shrink-0">
                {new Date(`${e.date}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </span>
              <div className="min-w-0">
                <div className="flex gap-1 mb-0.5">
                  {e.verdict && VERDICT_META[e.verdict] && (
                    <span className="text-[10px] font-bold px-1.5 rounded" style={{ color: VERDICT_META[e.verdict].fg, background: VERDICT_META[e.verdict].bg }}>{VERDICT_META[e.verdict].label}</span>
                  )}
                  {e.status && (
                    <span className="text-[10px] font-bold px-1.5 rounded" style={{ color: THESIS_STATUS_META[e.status].fg, background: THESIS_STATUS_META[e.status].bg }}>{e.status}</span>
                  )}
                </div>
                <p className="text-[12.5px] text-stone-700 leading-snug line-clamp-3">{e.note}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
