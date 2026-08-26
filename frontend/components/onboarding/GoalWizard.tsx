'use client';

/**
 * GoalWizard — conversational, generative onboarding.
 *
 * Finch chats and materialises a purpose-built instrument inline for whatever
 * the user is trying to do: a target dial (number), a compounding horizon
 * (grow), a monthly-income dial (income), or a watch picker (protect). The
 * result is a SetGoalRequest handed to onComplete(), which persists it.
 *
 * Light/futuristic in Finch's own tokens (emerald + #fafaf9, DM Sans / Space
 * Grotesk) — the styled-jsx block only carries the aurora + range styling that
 * Tailwind can't express cleanly.
 */
import React, { useEffect, useRef, useState } from 'react';
import type { GoalKind, SetGoalRequest } from '@/lib/api';

type Phase = 'ask' | 'target' | 'horizon' | 'income' | 'protect' | 'risk' | 'options' | 'connect' | 'saving';
type Msg = { who: 'finch' | 'you'; text: string };

const fmt = (n: number) => n.toLocaleString('en-US');

function categorize(t: string): GoalKind {
  const s = t.toLowerCase();
  if (/watch|monitor|keep an eye|warn|protect|don.?t lose|safe|guard/.test(s)) return 'protect';
  if (/income|monthly|cash ?flow|dividend|passive|premium/.test(s)) return 'income';
  if (/retire|long.?term|long run|years|decade|nest egg|build wealth|grow (my )?(savings|wealth|money|account)|steady/.test(s)) return 'grow';
  return 'number';
}

const STARTERS: { icon: string; label: string; fill: string }[] = [
  { icon: '🚀', label: 'make a quick $1k', fill: 'make about $1,000 in the next few weeks, ok with some risk' },
  { icon: '🌱', label: 'grow long-term', fill: 'grow my savings for the long term, steady and low-stress' },
  { icon: '💵', label: 'monthly income', fill: 'generate some steady monthly income from what I hold' },
  { icon: '🛡️', label: 'just watch & protect', fill: 'just keep an eye on my portfolio and warn me if something is off' },
];

function daysFromNowISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

// ── shared bits ──────────────────────────────────────────────────────────────
function Card({ children }: { children: React.ReactNode }) {
  return <div className="gw-card">{children}</div>;
}
function Klabel({ children }: { children: React.ReactNode }) {
  return <span className="gw-k">◆ {children}</span>;
}
function LockBtn({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return <button type="button" className="gw-go" onClick={onClick}>{children}</button>;
}

// ── instruments ──────────────────────────────────────────────────────────────
function TargetInstrument({ onLock }: { onLock: (d: Partial<SetGoalRequest>, label: string) => void }) {
  const [amt, setAmt] = useState(1000);
  const [days, setDays] = useState(21);
  const per = Math.round(amt / days);
  const pct = Math.round((amt / 5000) * 100);
  const lbl = days === 7 ? 'this week' : days === 21 ? '3 weeks' : days === 30 ? 'a month' : '3 months';
  const fill = ((amt - 200) / (5000 - 200)) * 100;
  const mx = 6 + (314 - 6) * 0.5, bow = 0.5 + (amt / 5000) * 0.5, my = 58 - (58 - 14) * bow * 0.55;
  const line = `M6 58 Q ${mx} ${my} 314 14`;
  return (
    <Card>
      <div className="gw-h"><Klabel>your target</Klabel><span className="gw-live">live</span></div>
      <div className="gw-amt">
        <button type="button" className="gw-stp" onClick={() => setAmt(a => Math.max(200, a - 100))}>−</button>
        <div className="gw-num">${fmt(amt)}</div>
        <button type="button" className="gw-stp" onClick={() => setAmt(a => Math.min(5000, a + 100))}>+</button>
      </div>
      <input type="range" min={200} max={5000} step={100} value={amt} className="gw-range"
        style={{ ['--fill' as any]: `${fill}%` }} onChange={e => setAmt(+e.target.value)} />
      <div className="gw-seg">
        {[[7, '1 wk'], [21, '3 wks'], [30, '1 mo'], [90, '3 mo']].map(([d, t]) => (
          <button type="button" key={d} className={days === d ? 'on' : ''} onClick={() => setDays(d as number)}>{t}</button>
        ))}
      </div>
      <svg className="gw-proj" viewBox="0 0 320 66" preserveAspectRatio="none" aria-hidden>
        <defs><linearGradient id="gwpg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#10b981" stopOpacity=".28" /><stop offset="1" stopColor="#10b981" stopOpacity="0" /></linearGradient></defs>
        <path d={`${line} L 314 58 Z`} fill="url(#gwpg)" />
        <path d={line} fill="none" stroke="#059669" strokeWidth={2.5} strokeLinecap="round" />
        <circle cx={314} cy={14} r={4} fill="#fff" stroke="#059669" strokeWidth={2.5} />
      </svg>
      <div className="gw-read">≈ <b>${per}/day</b> to hit <b>${fmt(amt)}</b> in {lbl} · a <b>{pct}%</b> run on ~$5k</div>
      <LockBtn onClick={() => onLock(
        { kind: 'number', target_amount: amt, deadline: daysFromNowISO(days), title: `Make $${fmt(amt)} in ${lbl}` },
        `→ make $${fmt(amt)} in ${lbl}`,
      )}>Lock in ${fmt(amt)} · {lbl} →</LockBtn>
    </Card>
  );
}

function HorizonInstrument({ onLock }: { onLock: (d: Partial<SetGoalRequest>, label: string) => void }) {
  const [yr, setYr] = useState(10);
  const [mo, setMo] = useState(500);
  const i = 0.0065, n = yr * 12;
  const fv = mo * ((Math.pow(1 + i, n) - 1) / i) + 5000 * Math.pow(1 + i, n);
  const put = 5000 + mo * yr * 12;
  const line = 'M6 62 Q 203 47 314 10';
  return (
    <Card>
      <div className="gw-h"><Klabel>your horizon</Klabel><span className="gw-live">live</span></div>
      <div className="gw-amt"><div className="gw-num" style={{ fontSize: 40 }}>{yr} <span style={{ fontSize: 19, color: 'var(--gw-ink3)' }}>years</span></div></div>
      <input type="range" min={1} max={30} value={yr} className="gw-range"
        style={{ ['--fill' as any]: `${((yr - 1) / 29) * 100}%` }} onChange={e => setYr(+e.target.value)} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, margin: '12px 0' }}>
        <span style={{ fontSize: 13, color: 'var(--gw-ink2)' }}>put in</span>
        <button type="button" className="gw-stp" onClick={() => setMo(m => Math.max(0, m - 100))}>−</button>
        <div className="gw-num" style={{ fontSize: 22 }}>${fmt(mo)}<span style={{ fontSize: 12, color: 'var(--gw-ink3)' }}>/mo</span></div>
        <button type="button" className="gw-stp" onClick={() => setMo(m => m + 100)}>+</button>
      </div>
      <svg className="gw-proj" viewBox="0 0 320 66" preserveAspectRatio="none" aria-hidden>
        <defs><linearGradient id="gwpg2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#10b981" stopOpacity=".28" /><stop offset="1" stopColor="#10b981" stopOpacity="0" /></linearGradient></defs>
        <path d={`${line} L 314 62 Z`} fill="url(#gwpg2)" />
        <path d={line} fill="none" stroke="#059669" strokeWidth={2.5} strokeLinecap="round" />
        <circle cx={314} cy={10} r={4} fill="#fff" stroke="#059669" strokeWidth={2.5} />
      </svg>
      <div className="gw-read">≈ <b>${fmt(Math.round(fv / 1000))}k</b> in {yr} yrs at ~8%/yr · you put in <b>${fmt(Math.round(put / 1000))}k</b>, growth adds the rest</div>
      <LockBtn onClick={() => onLock(
        { kind: 'grow', horizon_years: yr, monthly_contribution: mo, title: `Grow steadily over ${yr} years` },
        `→ grow ${yr} yrs · $${fmt(mo)}/mo`,
      )}>Lock it in →</LockBtn>
    </Card>
  );
}

function IncomeInstrument({ onLock }: { onLock: (d: Partial<SetGoalRequest>, label: string) => void }) {
  const [amt, setAmt] = useState(300);
  const yr = amt * 12, pct = ((yr / 5000) * 100).toFixed(1);
  return (
    <Card>
      <div className="gw-h"><Klabel>monthly income</Klabel><span className="gw-live">live</span></div>
      <div className="gw-amt">
        <button type="button" className="gw-stp" onClick={() => setAmt(a => Math.max(50, a - 50))}>−</button>
        <div className="gw-num">${fmt(amt)}<span style={{ fontSize: 17, color: 'var(--gw-ink3)' }}>/mo</span></div>
        <button type="button" className="gw-stp" onClick={() => setAmt(a => Math.min(2000, a + 50))}>+</button>
      </div>
      <input type="range" min={50} max={2000} step={50} value={amt} className="gw-range"
        style={{ ['--fill' as any]: `${((amt - 50) / 1950) * 100}%` }} onChange={e => setAmt(+e.target.value)} />
      <div className="gw-read" style={{ marginTop: 16 }}>≈ <b>${fmt(yr)}/yr</b> · about <b>{pct}%</b> on ~$5k — I&apos;d lean on covered calls &amp; dividends to get there</div>
      <LockBtn onClick={() => onLock(
        { kind: 'income', monthly_income: amt, title: `Generate ~$${fmt(amt)}/mo income` },
        `→ $${fmt(amt)}/mo income`,
      )}>Lock it in →</LockBtn>
    </Card>
  );
}

const WATCH_OPTS = ['big drops in my holdings', 'earnings for what I own', 'unusual options flow', 'my stop levels'];
function ProtectInstrument({ onLock }: { onLock: (d: Partial<SetGoalRequest>, label: string) => void }) {
  const [watch, setWatch] = useState<string[]>([WATCH_OPTS[0], WATCH_OPTS[1]]);
  const [notify, setNotify] = useState<'app' | 'both' | 'email'>('both');
  const toggle = (w: string) => setWatch(cur => cur.includes(w) ? cur.filter(x => x !== w) : [...cur, w]);
  return (
    <Card>
      <div className="gw-h"><Klabel>what should I watch</Klabel></div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {WATCH_OPTS.map(w => (
          <button type="button" key={w} className={`gw-pchip ${watch.includes(w) ? 'sel' : ''}`} onClick={() => toggle(w)}>{w}</button>
        ))}
      </div>
      <div className="gw-h"><Klabel>ping me via</Klabel></div>
      <div className="gw-seg">
        {(['app', 'both', 'email'] as const).map(v => (
          <button type="button" key={v} className={notify === v ? 'on' : ''} onClick={() => setNotify(v)}>{v === 'both' ? 'app + email' : v}</button>
        ))}
      </div>
      <LockBtn onClick={() => onLock(
        { kind: 'protect', title: 'Watch & protect my portfolio', config: { watch, notify } },
        '→ watch set',
      )}>Set my watch →</LockBtn>
    </Card>
  );
}

const RISK_DESC: Record<number, string> = {
  1: 'Featherweight — tiny positions, no options, I ask before I so much as sneeze.',
  2: 'Featherweight — tiny positions, no options, I ask before I so much as sneeze.',
  3: 'Cautious — small positions, nothing exotic without a heads-up.',
  4: 'Measured — steady entries, quick to take profits off the table.',
  5: 'Balanced — real positions, capped per name, I check in on the big calls.',
  6: 'Balanced — real positions, capped per name, I check in on the big calls.',
  7: 'Leaning aggressive — bigger size, faster triggers, still your call on every trade.',
  8: 'Aggressive — concentrated, options on, moving quickly.',
  9: 'Maximum conviction — big sizing, and you’ll hear what I did afterward. (You sure?)',
  10: 'Maximum conviction — big sizing, and you’ll hear what I did afterward. (You sure?)',
};
function RiskInstrument({ onLock }: { onLock: (risk: number, label: string) => void }) {
  const [v, setV] = useState(6);
  const word = v <= 3 ? 'careful' : v <= 7 ? 'balanced' : 'full send';
  return (
    <Card>
      <div className="gw-h"><Klabel>how hard to push</Klabel><span className="gw-live">live</span></div>
      <input type="range" min={1} max={10} value={v} className="gw-range"
        style={{ ['--fill' as any]: `${((v - 1) / 9) * 100}%` }} onChange={e => setV(+e.target.value)} />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--gw-ink3)', margin: '8px 2px 12px', fontFamily: 'var(--font-numeric)' }}>
        <span>careful</span><span>balanced</span><span>full send</span>
      </div>
      <div className="gw-read" style={{ minHeight: 40 }}>{RISK_DESC[v]}</div>
      <LockBtn onClick={() => onLock(v, `→ ${word} (${v}/10)`)}>Lock it in →</LockBtn>
    </Card>
  );
}

// ── main wizard ──────────────────────────────────────────────────────────────
export default function GoalWizard({ onComplete }: { onComplete: (g: SetGoalRequest) => void | Promise<void> }) {
  const [msgs, setMsgs] = useState<Msg[]>([
    { who: 'finch', text: "Hi — I'm Finch. What are we doing with your money? A number, a vibe, or “just please don't lose it” — all real answers." },
  ]);
  const [phase, setPhase] = useState<Phase>('ask');
  const [input, setInput] = useState('');
  const draft = useRef<SetGoalRequest>({ kind: 'number', options_enabled: false, config: {} });
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs, phase]);

  const say = (m: Msg) => setMsgs(cur => [...cur, m]);
  const finch = (text: string) => say({ who: 'finch', text });

  const submitGoal = (text: string) => {
    const cat = categorize(text);
    draft.current = { ...draft.current, kind: cat, objective: text };
    say({ who: 'you', text });
    setInput('');
    if (cat === 'number') { finch("Alright. Set the number and I'll show you what it actually takes — updates as you drag."); setPhase('target'); }
    else if (cat === 'grow') { finch('Good — the boring plan is usually the one that works. Pick a horizon.'); setPhase('horizon'); }
    else if (cat === 'income') { finch('Cash-flow mode. How much do you want showing up each month?'); setPhase('income'); }
    else { finch("Got it — I'll keep watch, not gamble. What should I keep an eye on?"); setPhase('protect'); }
  };

  const afterInstrument = (partial: Partial<SetGoalRequest>, label: string) => {
    draft.current = { ...draft.current, ...partial };
    say({ who: 'you', text: label });
    if (draft.current.kind === 'protect') {
      finch("Done. I won't bother you unless it matters. Last thing — connect an account so I'm watching the real thing.");
      setPhase('connect');
    } else if (draft.current.kind === 'number') {
      const pct = Math.round(((draft.current.target_amount || 0) / 5000) * 100);
      finch(`A ${pct}% run. Ambitious — not delusional. How aggressive should I be?`);
      setPhase('risk');
    } else if (draft.current.kind === 'grow') {
      finch('Solid and boring. My favorite. How much volatility can you stomach along the way?');
      setPhase('risk');
    } else {
      finch('Income means I stay conservative by default. How much risk on top of that?');
      setPhase('risk');
    }
  };

  const afterRisk = (risk: number, label: string) => {
    draft.current = { ...draft.current, risk };
    say({ who: 'you', text: label });
    if (draft.current.kind === 'number') {
      finch('Options too, or keep it to stocks? Options add range; I keep the downside boxed in either way.');
      setPhase('options');
    } else {
      finch("Last thing — connect an account so I'm planning from what you actually own. Nothing trades without your say-so.");
      setPhase('connect');
    }
  };

  const afterOptions = (useOptions: boolean) => {
    draft.current = { ...draft.current, options_enabled: useOptions };
    say({ who: 'you', text: useOptions ? '→ options are in' : '→ stocks only' });
    finch("Last thing — connect an account so I'm planning from what you actually own: your real concentration, gains, and idle cash. Nothing trades without your say-so.");
    setPhase('connect');
  };

  const finish = async () => {
    setPhase('saving');
    await onComplete(draft.current);
  };

  return (
    <div className="gw-root">
      <div className="gw-aurora"><div className="gw-grid" /></div>
      <div className="gw-col">
        <div className="gw-head">
          <div className="gw-orb" />
          <div className="gw-title">Let&apos;s set your mission</div>
          <div className="gw-tag">FINCH · ONBOARDING</div>
        </div>

        <div className="gw-tr">
          {msgs.map((m, i) => (
            <div key={i} className={`gw-row ${m.who}`}>
              {m.who === 'finch' && <div className="gw-av" />}
              <div className="gw-bub">{m.text}</div>
            </div>
          ))}

          {phase === 'target' && <div className="gw-wrow"><TargetInstrument onLock={afterInstrument} /></div>}
          {phase === 'horizon' && <div className="gw-wrow"><HorizonInstrument onLock={afterInstrument} /></div>}
          {phase === 'income' && <div className="gw-wrow"><IncomeInstrument onLock={afterInstrument} /></div>}
          {phase === 'protect' && <div className="gw-wrow"><ProtectInstrument onLock={afterInstrument} /></div>}
          {phase === 'risk' && <div className="gw-wrow"><RiskInstrument onLock={afterRisk} /></div>}
          {phase === 'options' && (
            <div className="gw-wrow"><Card>
              <div className="gw-h"><Klabel>options on the table?</Klabel></div>
              <div className="gw-yn">
                <button type="button" onClick={() => afterOptions(true)}>Use options<small>more range, capped downside</small></button>
                <button type="button" onClick={() => afterOptions(false)}>Stocks only<small>keep it simple</small></button>
              </div>
            </Card></div>
          )}
          {(phase === 'connect' || phase === 'saving') && (
            <div className="gw-wrow"><Card>
              <div className="gw-h"><Klabel>connect an account</Klabel></div>
              <div className="gw-connect">
                <button type="button" disabled={phase === 'saving'} onClick={finish}>
                  <span className="gw-logo" style={{ background: '#0b7d3e' }}>RH</span>
                  <span><b>Robinhood</b><br /><small>read positions + place trades you approve</small></span><span className="gw-arrow">→</span>
                </button>
                <button type="button" disabled={phase === 'saving'} onClick={finish}>
                  <span className="gw-logo" style={{ background: '#141210' }}>◆</span>
                  <span><b>Connect via SnapTrade</b><br /><small>Schwab · Fidelity · IBKR · Webull + 20 more</small></span><span className="gw-arrow">→</span>
                </button>
                <button type="button" className="gw-skip" disabled={phase === 'saving'} onClick={finish}>
                  {phase === 'saving' ? 'Setting up your mission…' : 'Skip — start me with a watchlist'}
                </button>
              </div>
            </Card></div>
          )}
          <div ref={endRef} />
        </div>

        {phase === 'ask' && (
          <div className="gw-dock">
            <div className="gw-composer">
              <textarea rows={1} value={input} placeholder="e.g. grow my savings, make $1k this month, or just watch my portfolio…"
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (input.trim()) submitGoal(input.trim()); } }} />
              <button type="button" className="gw-send" disabled={!input.trim()} onClick={() => input.trim() && submitGoal(input.trim())}>↑</button>
            </div>
            <div className="gw-quick">
              {STARTERS.map(s => (
                <button type="button" key={s.label} onClick={() => submitGoal(s.fill)}><span>{s.icon}</span>{s.label}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .gw-root{position:fixed;inset:0;z-index:60;overflow-y:auto;background:var(--finch-bg,#fbfbfa);
          --gw-ink:#141210;--gw-ink2:#57534e;--gw-ink3:#a8a29e;--gw-glass:rgba(255,255,255,.66);
          font-family:var(--font-body),system-ui,sans-serif;color:var(--gw-ink);display:flex;flex-direction:column}
        .gw-aurora{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden}
        .gw-aurora::before,.gw-aurora::after{content:"";position:absolute;border-radius:50%;filter:blur(70px);opacity:.5}
        .gw-aurora::before{width:60vw;height:60vw;left:-10vw;top:-24vw;background:radial-gradient(circle at 30% 30%,rgba(16,185,129,.55),transparent 60%);animation:gwd1 18s ease-in-out infinite}
        .gw-aurora::after{width:52vw;height:52vw;right:-14vw;top:-10vw;background:radial-gradient(circle at 60% 40%,rgba(99,102,241,.34),rgba(13,148,136,.28) 45%,transparent 62%);animation:gwd2 22s ease-in-out infinite}
        .gw-grid{position:absolute;inset:0;background-image:radial-gradient(rgba(20,18,16,.05) 1px,transparent 1px);background-size:24px 24px;-webkit-mask-image:linear-gradient(#000,transparent 78%);mask-image:linear-gradient(#000,transparent 78%)}
        @keyframes gwd1{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(6vw,4vw) scale(1.12)}}
        @keyframes gwd2{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-5vw,3vw) scale(1.08)}}
        @media (prefers-reduced-motion:reduce){.gw-aurora::before,.gw-aurora::after{animation:none}}
        .gw-col{position:relative;z-index:1;max-width:640px;width:100%;margin:0 auto;flex:1;display:flex;flex-direction:column;padding:46px 22px 0}
        .gw-head{text-align:center;margin-bottom:28px}
        .gw-orb{width:52px;height:52px;border-radius:50%;margin:0 auto 15px;background:radial-gradient(circle at 34% 30%,#6ee7b7,#059669 62%,#047857);box-shadow:0 0 0 1px rgba(255,255,255,.6),0 10px 34px -8px rgba(5,150,105,.75),inset 0 -6px 12px rgba(4,33,26,.35)}
        .gw-title{font-family:var(--font-numeric),var(--font-body),sans-serif;font-size:25px;font-weight:600;letter-spacing:-.02em}
        .gw-tag{font-family:ui-monospace,Menlo,monospace;font-size:10.5px;letter-spacing:.2em;color:var(--gw-ink3);margin-top:6px}
        .gw-tr{flex:1;display:flex;flex-direction:column;gap:15px;padding-bottom:18px}
        .gw-row{display:flex;gap:11px;align-items:flex-end;animation:gwspring .5s cubic-bezier(.2,.9,.25,1.04)}
        .gw-row.you{flex-direction:row-reverse}
        @keyframes gwspring{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:none}}
        .gw-av{width:30px;height:30px;border-radius:50%;flex:none;background:radial-gradient(circle at 34% 30%,#6ee7b7,#059669 65%);box-shadow:0 0 0 1px rgba(255,255,255,.5),0 4px 12px -3px rgba(5,150,105,.6)}
        .gw-bub{max-width:82%;padding:13px 16px;border-radius:17px;font-size:14.5px;line-height:1.58}
        .gw-row.finch .gw-bub{background:var(--gw-glass);border:1px solid rgba(255,255,255,.7);border-bottom-left-radius:5px;box-shadow:0 8px 26px -18px rgba(20,18,16,.5);backdrop-filter:blur(14px)}
        .gw-row.you .gw-bub{background:linear-gradient(150deg,#10b981,#047857);color:#fff;border-bottom-right-radius:5px;box-shadow:0 10px 24px -14px rgba(5,150,105,.8)}
        .gw-wrow{animation:gwin .55s cubic-bezier(.2,.9,.25,1.04)}
        @keyframes gwin{from{opacity:0;transform:translateY(16px) scale(.97)}to{opacity:1;transform:none}}
      `}</style>
      {/* global styles for the instrument cards (need to reach nested elements) */}
      <style jsx global>{`
        .gw-card{background:rgba(255,255,255,.66);border:1px solid rgba(255,255,255,.7);border-radius:20px;padding:17px 18px 18px;box-shadow:0 1px 0 rgba(255,255,255,.9) inset,0 20px 50px -26px rgba(20,18,16,.5);backdrop-filter:blur(16px);position:relative;overflow:hidden}
        .gw-card::before{content:"";position:absolute;left:0;right:0;top:0;height:1px;background:linear-gradient(90deg,transparent,rgba(16,185,129,.5),transparent)}
        .gw-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
        .gw-k{font-family:ui-monospace,Menlo,monospace;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:#047857}
        .gw-live{font-family:ui-monospace,Menlo,monospace;font-size:10.5px;color:#a8a29e;display:flex;align-items:center;gap:6px}
        .gw-live::before{content:"";width:6px;height:6px;border-radius:50%;background:#10b981;box-shadow:0 0 8px 1px rgba(16,185,129,.8)}
        .gw-amt{display:flex;align-items:center;justify-content:center;gap:16px;margin-bottom:4px}
        .gw-num{font-family:var(--font-numeric),sans-serif;font-size:44px;font-weight:600;letter-spacing:-.03em;font-variant-numeric:tabular-nums;--gw-ink3:#a8a29e}
        .gw-stp{width:34px;height:34px;border-radius:50%;border:1px solid rgba(20,18,16,.14);background:#fff;font-size:20px;color:#57534e;display:grid;place-items:center;line-height:1;transition:.14s;cursor:pointer}
        .gw-stp:hover{border-color:#059669;color:#047857;transform:translateY(-1px)}
        .gw-range{width:100%;-webkit-appearance:none;appearance:none;accent-color:#059669;height:6px;border-radius:99px;margin:12px 0 4px;outline:none;background:linear-gradient(90deg,#059669 var(--fill,40%),rgba(20,18,16,.09) var(--fill,40%));cursor:pointer}
        .gw-range::-webkit-slider-thumb{-webkit-appearance:none;width:22px;height:22px;border-radius:50%;background:#fff;cursor:pointer;box-shadow:0 0 0 2px #059669,0 4px 12px -2px rgba(5,150,105,.7)}
        .gw-range::-moz-range-thumb{width:22px;height:22px;border:none;border-radius:50%;background:#fff;box-shadow:0 0 0 2px #059669,0 4px 12px -2px rgba(5,150,105,.7)}
        .gw-seg{display:flex;gap:5px;background:rgba(20,18,16,.05);border-radius:11px;padding:4px;margin:12px 0}
        .gw-seg button{flex:1;font-size:12.5px;font-weight:600;padding:8px 4px;border-radius:8px;color:#57534e;border:none;background:none;cursor:pointer}
        .gw-seg button.on{background:#fff;color:#141210;box-shadow:0 2px 6px -2px rgba(20,18,16,.25)}
        .gw-proj{width:100%;height:66px;display:block;margin:4px 0 10px}
        .gw-read{text-align:center;font-size:13px;color:#57534e;margin-bottom:14px}
        .gw-read b{font-family:var(--font-numeric),sans-serif;color:#141210;font-weight:600}
        .gw-go{width:100%;padding:13px;border-radius:13px;background:#141210;color:#fff;font-size:14.5px;font-weight:600;border:none;cursor:pointer;transition:.15s}
        .gw-go:hover{background:#000;transform:translateY(-1px);box-shadow:0 12px 26px -12px rgba(20,18,16,.6)}
        .gw-yn{display:grid;grid-template-columns:1fr 1fr;gap:10px}
        .gw-yn button{padding:15px 12px;border-radius:14px;border:1.5px solid rgba(20,18,16,.14);background:#fff;text-align:center;font-size:14px;font-weight:600;cursor:pointer;transition:.15s}
        .gw-yn button small{display:block;font-size:11px;font-weight:500;color:#a8a29e;margin-top:3px}
        .gw-yn button:hover{border-color:#059669;color:#047857;transform:translateY(-2px);box-shadow:0 12px 26px -16px rgba(5,150,105,.6)}
        .gw-pchip{font-size:12.5px;font-weight:600;padding:8px 13px;border-radius:99px;border:1.5px solid rgba(20,18,16,.14);background:#fff;color:#57534e;cursor:pointer;transition:.14s}
        .gw-pchip:hover{border-color:#059669;color:#047857}
        .gw-pchip.sel{background:#141210;color:#fff;border-color:#141210}
        .gw-connect{display:flex;flex-direction:column;gap:9px}
        .gw-connect>button{background:#fff;border:1px solid rgba(20,18,16,.08);border-radius:14px;padding:14px 15px;display:flex;gap:13px;align-items:center;text-align:left;width:100%;cursor:pointer;transition:.16s;font-size:14px}
        .gw-connect>button:hover:not(:disabled){border-color:#059669;transform:translateY(-1px);box-shadow:0 12px 28px -18px rgba(5,150,105,.55)}
        .gw-connect>button:disabled{opacity:.6;cursor:default}
        .gw-connect small{font-size:12px;color:#57534e;font-weight:400}
        .gw-logo{width:38px;height:38px;border-radius:10px;flex:none;display:grid;place-items:center;font-family:var(--font-numeric),sans-serif;font-weight:700;font-size:15px;color:#fff}
        .gw-arrow{margin-left:auto;color:#a8a29e;font-size:18px}
        .gw-skip{justify-content:center!important;color:#57534e;font-size:12.5px!important;text-decoration:underline;text-underline-offset:3px}
        .gw-dock{position:sticky;bottom:0;z-index:2;background:linear-gradient(transparent,var(--finch-bg,#fbfbfa) 34%);padding:10px 0 22px}
        .gw-composer{background:rgba(255,255,255,.66);border:1.5px solid rgba(255,255,255,.75);border-radius:18px;padding:6px 6px 6px 17px;display:flex;align-items:flex-end;gap:10px;box-shadow:0 1px 0 rgba(255,255,255,.9) inset,0 12px 34px -20px rgba(20,18,16,.5);backdrop-filter:blur(14px)}
        .gw-composer:focus-within{border-color:#059669;box-shadow:0 0 0 4px rgba(5,150,105,.1),0 12px 34px -16px rgba(5,150,105,.5)}
        .gw-composer textarea{flex:1;border:none;resize:none;font-family:inherit;font-size:15px;line-height:1.5;color:#141210;background:none;padding:10px 0;max-height:120px;outline:none;caret-color:#059669}
        .gw-send{width:38px;height:38px;border-radius:12px;background:#141210;color:#fff;flex:none;display:grid;place-items:center;font-size:17px;border:none;cursor:pointer;transition:.15s}
        .gw-send:hover:not(:disabled){background:#000;transform:translateY(-1px)}
        .gw-send:disabled{opacity:.28;cursor:default}
        .gw-quick{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px;justify-content:center}
        .gw-quick button{font-size:12.5px;color:#57534e;padding:8px 14px;border-radius:99px;border:1px solid rgba(20,18,16,.08);background:rgba(255,255,255,.66);backdrop-filter:blur(10px);cursor:pointer;transition:.14s;display:flex;align-items:center;gap:6px}
        .gw-quick button:hover{border-color:#059669;color:#047857;transform:translateY(-1px)}
      `}</style>
    </div>
  );
}
