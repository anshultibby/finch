// Client-side table filter/sort/search — pure port of the web
// frontend/components/widgets/TableControls.tsx logic (no data refetch; operates
// on already-fetched rows). Keep behaviour identical across web & mobile.
import type { Control, TableData } from '@/lib/types';

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
