'use client';

import React from 'react';
import type { Control, TableData } from './types';

export type ControlState = Record<string, any>;

// ── pure apply: filter/sort a table's rows by the current control state ──────
export function applyControls(data: TableData, controls: Control[], state: ControlState): TableData {
  const idxOf = (c: string) => data.columns.indexOf(c);
  let rows = data.rows;

  for (const ctrl of controls) {
    const v = state[ctrl.id];

    if (ctrl.type === 'range') {
      const i = idxOf(ctrl.column);
      if (i < 0 || !v) continue;
      const [lo, hi] = v as [number, number];
      rows = rows.filter((r) => {
        const x = r[i];
        if (typeof x !== 'number') return true; // can't compare → keep
        return x >= lo && x <= hi;
      });
    } else if (ctrl.type === 'select') {
      const i = idxOf(ctrl.column);
      if (i < 0 || !v) continue; // '' = All
      rows = rows.filter((r) => String(r[i]) === v);
    } else if (ctrl.type === 'search') {
      if (!v) continue;
      const idxs = ctrl.columns.map(idxOf).filter((i) => i >= 0);
      const q = String(v).toLowerCase();
      rows = rows.filter((r) => idxs.some((i) => String(r[i] ?? '').toLowerCase().includes(q)));
    } else if (ctrl.type === 'sort') {
      const col = v?.column as string | undefined;
      if (!col) continue;
      const i = idxOf(col);
      if (i < 0) continue;
      const present = rows.filter((r) => r[i] != null);
      const missing = rows.filter((r) => r[i] == null);
      present.sort((a, b) => (a[i]! < b[i]! ? -1 : a[i]! > b[i]! ? 1 : 0));
      if (v.desc) present.reverse();
      rows = [...present, ...missing];
    }
  }
  return { ...data, rows };
}

// ── initial state so a fresh widget filters nothing until touched ────────────
export function initControlState(data: TableData, controls: Control[]): ControlState {
  const state: ControlState = {};
  for (const ctrl of controls) {
    if (ctrl.type === 'range') {
      const i = data.columns.indexOf(ctrl.column);
      const nums = i >= 0 ? (data.rows.map((r) => r[i]).filter((x) => typeof x === 'number') as number[]) : [];
      const lo = ctrl.min ?? (nums.length ? Math.min(...nums) : 0);
      const hi = ctrl.max ?? (nums.length ? Math.max(...nums) : 0);
      state[ctrl.id] = [lo, hi];
    } else if (ctrl.type === 'select') {
      state[ctrl.id] = '';
    } else if (ctrl.type === 'search') {
      state[ctrl.id] = '';
    } else if (ctrl.type === 'sort') {
      state[ctrl.id] = { column: '', desc: ctrl.default_desc ?? true };
    }
  }
  return state;
}

// ── control bar UI ───────────────────────────────────────────────────────────
const inputCls =
  'text-xs px-2 py-1 rounded-md border border-gray-200 bg-white text-gray-700 focus:border-emerald-400 focus:outline-none';

export function TableControls({
  data,
  controls,
  state,
  onChange,
}: {
  data: TableData;
  controls: Control[];
  state: ControlState;
  onChange: (id: string, value: any) => void;
}) {
  return (
    <div className="flex flex-wrap items-end gap-x-3 gap-y-2 mb-3">
      {controls.map((ctrl) => {
        if (ctrl.type === 'search') {
          return (
            <label key={ctrl.id} className="flex flex-col gap-0.5">
              <span className="text-[10px] uppercase tracking-wide text-gray-400">{ctrl.label}</span>
              <input
                type="text"
                value={state[ctrl.id] || ''}
                onChange={(e) => onChange(ctrl.id, e.target.value)}
                placeholder="Search…"
                className={`${inputCls} w-32`}
              />
            </label>
          );
        }
        if (ctrl.type === 'select') {
          const i = data.columns.indexOf(ctrl.column);
          const opts =
            ctrl.options ||
            (i >= 0
              ? Array.from(new Set(data.rows.map((r) => String(r[i] ?? '')).filter(Boolean))).sort()
              : []);
          return (
            <label key={ctrl.id} className="flex flex-col gap-0.5">
              <span className="text-[10px] uppercase tracking-wide text-gray-400">{ctrl.label}</span>
              <select value={state[ctrl.id] || ''} onChange={(e) => onChange(ctrl.id, e.target.value)} className={inputCls}>
                <option value="">All</option>
                {opts.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </label>
          );
        }
        if (ctrl.type === 'range') {
          const [lo, hi] = (state[ctrl.id] as [number, number]) || [ctrl.min ?? 0, ctrl.max ?? 0];
          return (
            <label key={ctrl.id} className="flex flex-col gap-0.5">
              <span className="text-[10px] uppercase tracking-wide text-gray-400">{ctrl.label}</span>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={lo}
                  step={ctrl.step}
                  onChange={(e) => onChange(ctrl.id, [Number(e.target.value), hi])}
                  className={`${inputCls} w-16`}
                />
                <span className="text-gray-300 text-xs">–</span>
                <input
                  type="number"
                  value={hi}
                  step={ctrl.step}
                  onChange={(e) => onChange(ctrl.id, [lo, Number(e.target.value)])}
                  className={`${inputCls} w-16`}
                />
              </div>
            </label>
          );
        }
        // sort
        const cur = state[ctrl.id] || { column: '', desc: true };
        return (
          <label key={ctrl.id} className="flex flex-col gap-0.5">
            <span className="text-[10px] uppercase tracking-wide text-gray-400">{ctrl.label}</span>
            <div className="flex items-center gap-1">
              <select
                value={cur.column}
                onChange={(e) => onChange(ctrl.id, { ...cur, column: e.target.value })}
                className={inputCls}
              >
                <option value="">—</option>
                {ctrl.columns.map((c) => (
                  <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => onChange(ctrl.id, { ...cur, desc: !cur.desc })}
                className="text-xs px-1.5 py-1 rounded-md border border-gray-200 text-gray-500 hover:text-emerald-600"
                aria-label="Toggle sort direction"
              >
                {cur.desc ? '▼' : '▲'}
              </button>
            </div>
          </label>
        );
      })}
    </div>
  );
}
