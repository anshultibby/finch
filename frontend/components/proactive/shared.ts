// Helpers shared by the proactive home and its six tool views. Mirrors the
// mobile screens (frontend-mobile/app/{index,screener,calendar,watching}.tsx)
// so both apps rank, phrase and schedule things the same way.

export function dayDiff(dateStr: string): number {
  const d = new Date(`${dateStr}T12:00:00`);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  return Math.round((d.getTime() - today.getTime()) / 86_400_000);
}

export function whenLabel(dateStr: string, time?: string) {
  const diff = dayDiff(dateStr);
  const day = diff === 0 ? 'today' : diff === 1 ? 'tomorrow'
    : new Date(`${dateStr}T12:00:00`).toLocaleDateString('en-US', { weekday: 'long' });
  const t = (time || '').toLowerCase();
  const slot = t === 'bmo' ? ' before the open' : t === 'amc' ? ' after the close' : '';
  return `${day}${slot}`;
}

export const EARNINGS_SLOT: Record<string, string> = { bmo: 'Before open', amc: 'After close', dmh: 'During hours' };

export const ymd = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

// US regular session in New York time. Holidays aren't modelled — header hint only.
export function marketStatus(): string {
  try {
    const ny = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const day = ny.getDay();
    const mins = ny.getHours() * 60 + ny.getMinutes();
    if (day === 0 || day === 6) return 'Markets closed';
    if (mins >= 570 && mins < 960) return 'Markets open';
    if (mins >= 240 && mins < 570) return 'Pre-market';
    if (mins >= 960 && mins < 1200) return 'After hours';
    return 'Markets closed';
  } catch {
    return '';
  }
}

export function greeting(d = new Date()) {
  const h = d.getHours();
  if (h < 5) return 'Up late';
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export function earningsPreviewPrompt(sym: string, thesis?: { why: string; breaks: string } | null) {
  const base = `Give me an earnings preview for ${sym}: consensus EPS and revenue, the options-implied move, the 2-3 things that will decide the reaction, and what it means for my position or watchlist interest. Take a stance.`;
  return thesis
    ? `${base} My thesis: "${thesis.why}". I said I'd be wrong if: "${thesis.breaks || 'not stated'}". Tell me exactly what in this report would confirm or break it.`
    : base;
}

/** Next weekday at `hour` local time; `weekly` pins it to Friday. */
export function nextRunAt(hour: number, weekly = false): string {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  if (d.getTime() <= Date.now()) d.setDate(d.getDate() + 1);
  if (weekly) while (d.getDay() !== 5) d.setDate(d.getDate() + 1);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  return d.toISOString();
}

export function cadenceLabel(r: string | null | undefined) {
  if (!r) return 'Once';
  if (r === 'weekdays') return 'Weekdays';
  const m = /^every_(\d+)m$/.exec(r);
  if (m) {
    const mins = Number(m[1]);
    if (mins === 1440) return 'Daily';
    return mins % 60 === 0 ? `Every ${mins / 60}h` : `Every ${mins} min`;
  }
  return r.charAt(0).toUpperCase() + r.slice(1);
}

export function shortWhen(iso: string) {
  return new Date(iso).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' });
}

export function fmtUsd(n: number | null | undefined, compact = false) {
  if (typeof n !== 'number' || !Number.isFinite(n)) return '—';
  if (compact) {
    if (Math.abs(n) >= 1e12) return `$${(n / 1e12).toFixed(1)}T`;
    if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
    if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  }
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function fmtPct(n: number | null | undefined) {
  if (typeof n !== 'number' || !Number.isFinite(n)) return '—';
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

/** Recurring checks a user can add in one click (Watching). */
export const CHECK_TEMPLATES: { label: string; name: string; message: string; recurrence: 'weekdays' | 'weekly'; hour: number }[] = [
  {
    label: 'Tell me when anything I own or watch moves 5%+, and why',
    name: 'Big-move watch',
    message: 'Check my holdings and watchlist for moves that are unusual for each stock (use explain_move from the finch_api skill: today vs its typical daily move, market/sector share, volume). For each one that is unusual, tell me why it moved — macro, sector or company — and whether it\'s routine, news with the story intact, or a change in narrative, with what to watch next. Skip anything routine; if nothing qualifies, do not notify me.',
    recurrence: 'weekdays',
    hour: 15,
  },
  {
    label: 'Every Friday, review my portfolio against my goal',
    name: 'Weekly goal review',
    message: 'Review my week against my mission and profile. Start with the macro and sector story that drove markets this week, then my book: performance vs. SPY, which moves were noise and which changed a story, pace toward my goal, concentration and risk. End with the one change you would make, or say plainly that nothing warrants a change. Take a clear stance.',
    recurrence: 'weekly',
    hour: 16,
  },
  {
    label: 'Flag news that changes the story on my holdings',
    name: 'Thesis-change watch',
    message: 'Scan news, filings, analyst actions and macro developments touching my holdings since the last check. Only report items that change the narrative — the reason to own or avoid the stock — not routine price moves or noise. For each: what changed, whether it\'s company-specific or a macro/sector read-through, the source quoted, and what would confirm it. If nothing qualifies, do not notify me.',
    recurrence: 'weekdays',
    hour: 8,
  },
];

/** Shared card/list styling so every view reads as one system. */
export const ui = {
  page: 'max-w-3xl mx-auto px-5 py-7',
  card: 'bg-white border border-stone-200/80 rounded-2xl',
  section: 'text-[15px] font-bold text-stone-900 mt-7 mb-2.5',
  row: 'w-full flex items-center gap-3 px-4 py-3 text-left border-t first:border-t-0 border-stone-100 hover:bg-stone-50 transition-colors',
  chip: 'px-3 py-1.5 rounded-full text-[13px] font-medium border transition-colors',
  chipOn: 'bg-emerald-50 border-emerald-300 text-emerald-700',
  chipOff: 'bg-white border-stone-200 text-stone-700 hover:border-stone-300',
};
