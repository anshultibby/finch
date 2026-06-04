'use client';

import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { marketApi } from '@/lib/api';
import { formatCurrencyCompact as fmtB, getCurrency, isIndianTicker, formatDate } from '@/lib/currency';

type EarningsSubTab = 'overview' | 'transcript' | 'documents';

interface EarningsQuarter {
  date: string;
  eps: number | null;
  epsEstimated: number | null;
  revenue: number | null;
  revenueEstimated: number | null;
  fiscalDateEnding: string | null;
  time: string | null;
  fiscalLabel: string;
  fiscalYear: number;
  fiscalQ: number;
  isUpcoming: boolean;
  epsSurprisePct: number | null;
  revSurprisePct: number | null;
}

function deriveFiscalLabel(fiscalDateEnding: string | null, date: string, india: boolean): { label: string; year: number; q: number } {
  const fde = fiscalDateEnding || date;
  const d = new Date(fde);
  const month = d.getMonth() + 1;
  const calYear = d.getFullYear();

  if (india) {
    // Indian fiscal year runs Apr–Mar; Q1 = Apr–Jun. FY is named by its ending
    // calendar year (a quarter ending Jun 2024 → Q1 FY25).
    let q: number;
    let fy: number;
    if (month >= 4) { q = Math.floor((month - 4) / 3) + 1; fy = calYear + 1; }
    else { q = 4; fy = calYear; }
    return { label: `Q${q} FY${String(fy).slice(-2)}`, year: fy, q };
  }

  let q: number;
  if (month <= 3) q = 1;
  else if (month <= 6) q = 2;
  else if (month <= 9) q = 3;
  else q = 4;
  return { label: `Q${q} ${calYear}`, year: calYear, q };
}

function processQuarters(history: any[], india: boolean): EarningsQuarter[] {
  return history.map(e => {
    const { label, year, q } = deriveFiscalLabel(e.fiscalDateEnding, e.date, india);
    const isUpcoming = e.eps == null;
    const epsSurprisePct = e.eps != null && e.epsEstimated != null && e.epsEstimated !== 0
      ? ((e.eps - e.epsEstimated) / Math.abs(e.epsEstimated)) * 100
      : null;
    const revSurprisePct = e.revenue != null && e.revenueEstimated != null && e.revenueEstimated !== 0
      ? ((e.revenue - e.revenueEstimated) / Math.abs(e.revenueEstimated)) * 100
      : null;
    return {
      ...e,
      fiscalLabel: label,
      fiscalYear: year,
      fiscalQ: q,
      isUpcoming,
      epsSurprisePct,
      revSurprisePct,
    };
  }).sort((a, b) => b.date.localeCompare(a.date));
}

// ── Quarter Pills ────────────────────────────────────────────────────────────

function QuarterPills({ quarters, selectedIdx, onSelect }: {
  quarters: EarningsQuarter[];
  selectedIdx: number;
  onSelect: (i: number) => void;
}) {
  return (
    <div className="flex gap-2 overflow-x-auto scrollbar-none pb-2">
      {quarters.map((q, i) => {
        const active = i === selectedIdx;
        const beat = q.epsSurprisePct != null && q.epsSurprisePct > 0;
        const miss = q.epsSurprisePct != null && q.epsSurprisePct < 0;

        let badge = '';
        let badgeColor = '';
        if (q.isUpcoming) {
          const daysUntil = Math.ceil((new Date(q.date).getTime() - Date.now()) / 86400000);
          badge = daysUntil > 0 ? `in ${daysUntil}d` : 'Today';
          badgeColor = 'text-gray-500';
        } else if (beat) {
          badge = `+${q.epsSurprisePct!.toFixed(2)}%`;
          badgeColor = 'text-emerald-600';
        } else if (miss) {
          badge = `${q.epsSurprisePct!.toFixed(2)}%`;
          badgeColor = 'text-red-500';
        } else if (q.epsSurprisePct != null) {
          badge = '0.00%';
          badgeColor = 'text-gray-500';
        }

        return (
          <button key={i} onClick={() => onSelect(i)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
              active
                ? 'bg-gray-900 text-white'
                : 'text-gray-500 hover:bg-gray-100'
            }`}>
            <span>{q.fiscalLabel}</span>
            {badge && (
              <span className={`ml-1.5 font-semibold ${active ? 'text-gray-300' : badgeColor}`}>
                {badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ── Quarter Detail Card ──────────────────────────────────────────────────────

function QuarterDetail({ q, symbol, onListen }: { q: EarningsQuarter; symbol: string; onListen?: () => void }) {
  const dateStr = formatDate(q.date, {
    weekday: 'short', year: 'numeric', month: 'long', day: 'numeric',
  }, isIndianTicker(symbol));
  const timeStr = q.time === 'bmo' ? 'Before Market Open' : q.time === 'amc' ? 'After Market Close' : '';

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold text-gray-900">
            {symbol} {q.fiscalLabel} Earnings{q.isUpcoming ? '' : ' Call'}
          </h3>
          <div className="text-sm text-gray-400 mt-0.5">
            {dateStr}{timeStr && ` · ${timeStr}`}
          </div>
        </div>
        {q.isUpcoming ? (
          <span className="px-3 py-1 bg-amber-50 text-amber-700 text-xs font-semibold rounded-full">
            Upcoming
          </span>
        ) : (
          <div className="flex items-center gap-2">
            <a href={`https://www.youtube.com/results?search_query=${encodeURIComponent(`${symbol} ${q.fiscalLabel} earnings call`)}`}
              target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0C.488 3.45.029 5.804 0 12c.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0C23.512 20.55 23.971 18.196 24 12c-.029-6.185-.484-8.549-4.385-8.816zM9 16V8l8 4-8 4z" />
              </svg>
              Watch Call
            </a>
            {onListen && (
              <button onClick={onListen}
                className="flex items-center gap-1.5 px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
                Read Aloud
              </button>
            )}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-500 text-xs">
              <th className="text-left py-2.5 px-4 font-medium w-[120px]"></th>
              <th className="text-right py-2.5 px-4 font-medium">Estimated</th>
              {!q.isUpcoming && <th className="text-right py-2.5 px-4 font-medium">Actual</th>}
              {!q.isUpcoming && <th className="text-right py-2.5 px-4 font-medium">Surprise</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <tr>
              <td className="py-3 px-4 font-medium text-gray-700">Revenue</td>
              <td className="py-3 px-4 text-right text-gray-500 tabular-nums">
                {q.revenueEstimated != null ? fmtB(q.revenueEstimated, symbol) : '--'}
              </td>
              {!q.isUpcoming && (
                <td className="py-3 px-4 text-right font-semibold text-gray-900 tabular-nums">
                  {q.revenue != null ? fmtB(q.revenue, symbol) : '--'}
                </td>
              )}
              {!q.isUpcoming && (
                <td className="py-3 px-4 text-right">
                  {q.revSurprisePct != null ? (
                    <span className={`font-semibold tabular-nums ${q.revSurprisePct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {q.revSurprisePct >= 0 ? 'Beat' : 'Miss'} {q.revSurprisePct >= 0 ? '+' : ''}{q.revSurprisePct.toFixed(2)}%
                    </span>
                  ) : '--'}
                </td>
              )}
            </tr>
            <tr>
              <td className="py-3 px-4 font-medium text-gray-700">EPS (Adj.)</td>
              <td className="py-3 px-4 text-right text-gray-500 tabular-nums">
                {q.epsEstimated != null ? `${getCurrency(symbol).symbol}${q.epsEstimated.toFixed(2)}` : '--'}
              </td>
              {!q.isUpcoming && (
                <td className="py-3 px-4 text-right font-semibold text-gray-900 tabular-nums">
                  {q.eps != null ? `${getCurrency(symbol).symbol}${q.eps.toFixed(2)}` : '--'}
                </td>
              )}
              {!q.isUpcoming && (
                <td className="py-3 px-4 text-right">
                  {q.epsSurprisePct != null ? (
                    <span className={`font-semibold tabular-nums ${q.epsSurprisePct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {q.epsSurprisePct >= 0 ? 'Beat' : 'Miss'} {q.epsSurprisePct >= 0 ? '+' : ''}{q.epsSurprisePct.toFixed(2)}%
                    </span>
                  ) : '--'}
                </td>
              )}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Overview Sub-tab ─────────────────────────────────────────────────────────

function EarningsOverview({ quarters, selectedIdx, symbol }: { quarters: EarningsQuarter[]; selectedIdx: number; symbol: string }) {
  const q = quarters[selectedIdx];
  const reported = quarters.filter(x => !x.isUpcoming);
  const beats = reported.filter(x => x.epsSurprisePct != null && x.epsSurprisePct > 0);
  const beatRate = reported.length > 0 ? ((beats.length / reported.length) * 100).toFixed(0) : '--';

  let beatStreak = 0;
  for (const r of reported) {
    if (r.epsSurprisePct != null && r.epsSurprisePct > 0) beatStreak++;
    else break;
  }

  const sameQLastYear = quarters.find(
    x => x.fiscalQ === q.fiscalQ && x.fiscalYear === q.fiscalYear - 1 && !x.isUpcoming
  );

  const epsYoY = q.eps != null && sameQLastYear?.eps != null && sameQLastYear.eps !== 0
    ? ((q.eps - sameQLastYear.eps) / Math.abs(sameQLastYear.eps)) * 100
    : null;
  const revYoY = q.revenue != null && sameQLastYear?.revenue != null && sameQLastYear.revenue !== 0
    ? ((q.revenue - sameQLastYear.revenue) / Math.abs(sameQLastYear.revenue)) * 100
    : null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {!q.isUpcoming && epsYoY != null && (
        <div className="rounded-xl border border-gray-100 p-4">
          <div className="text-xs text-gray-400 mb-1">EPS YoY</div>
          <div className={`text-lg font-bold tabular-nums ${epsYoY >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {epsYoY >= 0 ? '+' : ''}{epsYoY.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-400 mt-1">
            vs {sameQLastYear!.fiscalLabel}: {getCurrency(symbol).symbol}{sameQLastYear!.eps!.toFixed(2)}
          </div>
        </div>
      )}
      {!q.isUpcoming && revYoY != null && (
        <div className="rounded-xl border border-gray-100 p-4">
          <div className="text-xs text-gray-400 mb-1">Revenue YoY</div>
          <div className={`text-lg font-bold tabular-nums ${revYoY >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {revYoY >= 0 ? '+' : ''}{revYoY.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-400 mt-1">
            vs {sameQLastYear!.fiscalLabel}: {fmtB(sameQLastYear!.revenue!, symbol)}
          </div>
        </div>
      )}
      <div className="rounded-xl border border-gray-100 p-4">
        <div className="text-xs text-gray-400 mb-1">Beat Rate</div>
        <div className="text-lg font-bold text-gray-900">{beatRate}%</div>
        <div className="text-xs text-gray-400 mt-1">
          {beats.length}/{reported.length} quarters
        </div>
      </div>
      <div className="rounded-xl border border-gray-100 p-4">
        <div className="text-xs text-gray-400 mb-1">Beat Streak</div>
        <div className="text-lg font-bold text-gray-900">{beatStreak}</div>
        <div className="text-xs text-gray-400 mt-1">
          consecutive beats
        </div>
      </div>
    </div>
  );
}

// ── Transcript Sub-tab ───────────────────────────────────────────────────────

interface TranscriptSection {
  speaker: string;
  text: string;
  rawIdx: number;
}

function splitIntoParagraphs(text: string): string {
  const sentences = text.match(/[^.!?]+[.!?]+(?:\s|$)/g) || [text];
  const paragraphs: string[] = [];
  let current = '';
  for (const s of sentences) {
    current += s;
    if (current.length > 300) {
      paragraphs.push(current.trim());
      current = '';
    }
  }
  if (current.trim()) paragraphs.push(current.trim());
  return paragraphs.join('\n\n');
}

function parseTranscriptSections(raw: string): TranscriptSection[] {
  const lines = raw.split(/\n+/).filter(p => p.trim());
  const sections: TranscriptSection[] = [];
  let currentSpeaker = '';

  for (let i = 0; i < lines.length; i++) {
    const p = lines[i].trim();
    const speakerMatch = p.match(/^([A-Z][a-zA-Z\s.'\-]+):\s*/);
    if (speakerMatch) {
      currentSpeaker = speakerMatch[1];
      const rest = p.slice(speakerMatch[0].length).trim();
      if (rest) {
        sections.push({ speaker: currentSpeaker, text: splitIntoParagraphs(rest), rawIdx: i });
      }
    } else if (currentSpeaker) {
      const last = sections[sections.length - 1];
      if (last && last.speaker === currentSpeaker) {
        last.text += '\n\n' + splitIntoParagraphs(p);
      } else {
        sections.push({ speaker: currentSpeaker, text: splitIntoParagraphs(p), rawIdx: i });
      }
    } else {
      sections.push({ speaker: '', text: splitIntoParagraphs(p), rawIdx: i });
    }
  }
  return sections;
}

type TranscriptFilter = 'all' | 'prepared' | 'qa';

function classifySections(sections: TranscriptSection[]): { preparedEnd: number } {
  const qaKeywords = ['question-and-answer', 'q&a', 'question and answer', 'open the line', 'open it up for questions'];
  for (let i = 0; i < sections.length; i++) {
    const lower = sections[i].text.toLowerCase();
    if (qaKeywords.some(k => lower.includes(k))) {
      return { preparedEnd: i };
    }
  }
  return { preparedEnd: sections.length };
}

function EarningsTranscript({ symbol, quarter }: { symbol: string; quarter: EarningsQuarter }) {
  const [transcript, setTranscript] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [filter, setFilter] = useState<TranscriptFilter>('all');
  const [playingSectionIdx, setPlayingSectionIdx] = useState(-1);
  const [paused, setPaused] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    setTranscript(null);
    setLoaded(false);
    setLoading(true);
    stopPlayback();

    const fde = quarter.fiscalDateEnding || quarter.date;
    const d = new Date(fde);
    const month = d.getMonth() + 1;
    const year = d.getFullYear();
    let q: number;
    if (month <= 3) q = 1;
    else if (month <= 6) q = 2;
    else if (month <= 9) q = 3;
    else q = 4;

    marketApi.getEarningsTranscript(symbol, q, year)
      .then(data => setTranscript(data?.content || null))
      .catch(() => setTranscript(null))
      .finally(() => { setLoading(false); setLoaded(true); });
  }, [symbol, quarter.date]);

  useEffect(() => {
    return () => { speechSynthesis.cancel(); };
  }, []);

  const stopPlayback = useCallback(() => {
    speechSynthesis.cancel();
    setPlayingSectionIdx(-1);
    setPaused(false);
  }, []);

  const playSectionFrom = useCallback((sections: TranscriptSection[], idx: number) => {
    if (idx >= sections.length) {
      stopPlayback();
      return;
    }
    setPlayingSectionIdx(idx);
    setPaused(false);

    const el = sectionRefs.current[idx];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });

    const text = `${sections[idx].speaker}. ${sections[idx].text}`;
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 1.1;
    utt.onend = () => playSectionFrom(sections, idx + 1);
    utt.onerror = (e) => { if (e.error !== 'canceled') stopPlayback(); };
    speechSynthesis.speak(utt);
  }, [stopPlayback]);

  const handlePlaySection = useCallback((sections: TranscriptSection[], idx: number) => {
    speechSynthesis.cancel();
    playSectionFrom(sections, idx);
  }, [playSectionFrom]);

  const handleTogglePlayPause = useCallback(() => {
    if (paused) {
      speechSynthesis.resume();
      setPaused(false);
    } else {
      speechSynthesis.pause();
      setPaused(true);
    }
  }, [paused]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (loaded && !transcript) {
    return (
      <div className="rounded-xl border border-gray-100 bg-gray-50 flex items-center justify-center py-16 text-sm text-gray-400">
        No transcript available for {quarter.fiscalLabel}
      </div>
    );
  }

  if (!transcript) return null;

  const sections = parseTranscriptSections(transcript);
  const { preparedEnd } = classifySections(sections);
  const filtered = filter === 'prepared'
    ? sections.slice(0, preparedEnd)
    : filter === 'qa'
    ? sections.slice(preparedEnd)
    : sections;

  const isPlaying = playingSectionIdx >= 0;

  return (
    <div className="rounded-xl border border-gray-100 bg-white overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div className="flex items-center gap-3">
          {isPlaying ? (
            <div className="flex items-center gap-1.5">
              <button onClick={handleTogglePlayPause}
                className="w-8 h-8 flex items-center justify-center bg-gray-900 text-white rounded-full hover:bg-gray-800 transition-colors">
                {paused ? (
                  <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                ) : (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" /></svg>
                )}
              </button>
              <button onClick={stopPlayback}
                className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 6h12v12H6z" /></svg>
              </button>
              <div className="flex items-center gap-2 ml-1 text-xs text-gray-400">
                <span className={`w-1.5 h-1.5 rounded-full ${paused ? 'bg-amber-400' : 'bg-emerald-500 animate-pulse'}`} />
                {paused ? 'Paused' : 'Playing'}
              </div>
            </div>
          ) : (
            <button onClick={() => handlePlaySection(filtered, 0)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
              Read Aloud
            </button>
          )}
        </div>
        <select value={filter} onChange={e => setFilter(e.target.value as TranscriptFilter)}
          className="text-sm font-medium text-gray-600 bg-transparent border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-gray-300 cursor-pointer">
          <option value="all">Full Transcript</option>
          <option value="prepared">Prepared Remarks</option>
          <option value="qa">Q&A Session</option>
        </select>
      </div>

      {/* Transcript body */}
      <div ref={scrollContainerRef} className="max-h-[600px] overflow-y-auto">
        {filtered.map((section, i) => {
          const isActive = playingSectionIdx >= 0 && sections.indexOf(section) === playingSectionIdx;
          return (
            <div key={section.rawIdx}
              ref={el => { sectionRefs.current[sections.indexOf(section)] = el; }}
              className={`px-5 py-4 border-b border-gray-50 last:border-b-0 transition-colors ${isActive ? 'bg-amber-50/50' : ''}`}>
              {section.speaker && (
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-emerald-700">{section.speaker}</span>
                  <button onClick={() => handlePlaySection(sections, sections.indexOf(section))}
                    className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                  </button>
                </div>
              )}
              <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                {section.text}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Documents Sub-tab ────────────────────────────────────────────────────────

const FILING_LABELS: Record<string, { label: string; tag: string }> = {
  '10-K': { label: 'Annual report', tag: 'Report' },
  '10-Q': { label: 'Quarterly report', tag: 'Report' },
  '8-K': { label: 'Earnings release', tag: 'Report' },
  '10-K/A': { label: 'Annual report (amended)', tag: 'Amendment' },
  '10-Q/A': { label: 'Quarterly report (amended)', tag: 'Amendment' },
};

function EarningsDocuments({ symbol, quarter }: { symbol: string; quarter: EarningsQuarter }) {
  const [filings, setFilings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    marketApi.getSecFilings(symbol, undefined, 200)
      .then(data => setFilings(Array.isArray(data) ? data : []))
      .catch(() => setFilings([]))
      .finally(() => setLoading(false));
  }, [symbol]);

  const relevantFilings = useMemo(() => {
    if (!quarter.date) return [];
    const earningsDate = new Date(quarter.date);
    return filings
      .filter(f => {
        if (!f.fillingDate) return false;
        const filingDate = new Date(f.fillingDate);
        const diffDays = Math.abs((filingDate.getTime() - earningsDate.getTime()) / 86400000);
        return diffDays <= 30 && ['10-K', '10-Q', '8-K', '10-K/A', '10-Q/A'].includes(f.type);
      })
      .sort((a, b) => new Date(b.fillingDate).getTime() - new Date(a.fillingDate).getTime());
  }, [filings, quarter.date]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (relevantFilings.length === 0) {
    return (
      <div className="rounded-xl border border-gray-100 bg-gray-50 flex items-center justify-center py-16 text-sm text-gray-400">
        No filings found near {quarter.fiscalLabel} earnings date
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 overflow-hidden divide-y divide-gray-100">
      {relevantFilings.map((f, i) => {
        const info = FILING_LABELS[f.type] || { label: f.type, tag: 'Filing' };
        const filingDate = formatDate(f.fillingDate, {
          year: 'numeric', month: 'long', day: 'numeric',
        }, isIndianTicker(symbol));
        return (
          <div key={i} className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-gray-900">{info.label}</span>
                <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs font-medium rounded">
                  {info.tag}
                </span>
              </div>
              <div className="text-xs text-gray-400">
                {f.type} filing · {filingDate}
              </div>
            </div>
            <a href={f.finalLink || f.link} target="_blank" rel="noopener noreferrer"
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-sm font-medium text-gray-700 rounded-lg transition-colors flex-shrink-0">
              View
            </a>
          </div>
        );
      })}
    </div>
  );
}

// ── Main EarningsTab ─────────────────────────────────────────────────────────

export default function EarningsTab({ symbol, earningsHistory }: { symbol: string; earningsHistory: any[] }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [subTab, setSubTab] = useState<EarningsSubTab>('overview');

  const quarters = useMemo(() => processQuarters(earningsHistory, isIndianTicker(symbol)), [earningsHistory, symbol]);

  useEffect(() => {
    setSelectedIdx(0);
    setSubTab('overview');
  }, [symbol]);

  if (quarters.length === 0) {
    return (
      <div className="rounded-xl border border-gray-100 bg-gray-50 flex items-center justify-center py-16 text-sm text-gray-400">
        No earnings data available
      </div>
    );
  }

  const selected = quarters[selectedIdx];
  const SUB_TABS: { key: EarningsSubTab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'transcript', label: 'Transcript' },
    { key: 'documents', label: 'Documents' },
  ];

  return (
    <div className="space-y-4">
      <QuarterPills quarters={quarters} selectedIdx={selectedIdx} onSelect={setSelectedIdx} />
      <QuarterDetail q={selected} symbol={symbol} onListen={() => setSubTab('transcript')} />

      {/* Sub-tabs */}
      <div className="flex flex-wrap gap-1">
        {SUB_TABS.map(tab => (
          <button key={tab.key} onClick={() => setSubTab(tab.key)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              subTab === tab.key
                ? 'bg-gray-900 text-white'
                : 'text-gray-500 hover:bg-gray-100'
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {subTab === 'overview' && (
        <EarningsOverview quarters={quarters} selectedIdx={selectedIdx} symbol={symbol} />
      )}
      {subTab === 'transcript' && (
        <EarningsTranscript symbol={symbol} quarter={selected} />
      )}
      {subTab === 'documents' && (
        <EarningsDocuments symbol={symbol} quarter={selected} />
      )}
    </div>
  );
}
