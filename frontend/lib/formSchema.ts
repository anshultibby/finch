// ═══════════════════════════════════════════════════════════════════════════
// Generic Form Schema — defines any interactive form the agent can create
// ═══════════════════════════════════════════════════════════════════════════

import { getApiBaseUrl } from './utils';

// ─────────────────────────────────────────────────────────────────────────────
// Schema types — the agent writes this to define a form
// ─────────────────────────────────────────────────────────────────────────────

export type FieldType = 'text' | 'currency' | 'number' | 'select' | 'radio' | 'checkbox';

export interface FieldDef {
  key: string;            // dot-path into form data, e.g. "income.wages"
  label: string;
  type: FieldType;
  line?: string;          // reference line number (e.g. "1a", "Line 7")
  placeholder?: string;
  options?: { value: string; label: string }[];  // for select/radio
  default?: any;
  width?: 'full' | 'half' | 'third';  // layout hint
}

export interface CalculationDef {
  key: string;            // dot-path where result is stored
  label: string;
  line?: string;
  formula: string;        // expression referencing field keys, e.g. "wages + interest - adjustments"
  large?: boolean;        // render prominently
}

export interface SectionDef {
  title: string;
  defaultOpen?: boolean;  // default true
  fields: FieldDef[];
  calculations?: CalculationDef[];
}

export interface FormSchema {
  name: string;           // e.g. "Form 1040", "Schedule C"
  subtitle?: string;      // e.g. "U.S. Individual Income Tax Return"
  year?: number;
  sections: SectionDef[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Form data — flat key-value store the component works with
// ─────────────────────────────────────────────────────────────────────────────

export type FormData = Record<string, any>;

// ─────────────────────────────────────────────────────────────────────────────
// Calculation engine — evaluates formula strings against form data
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Evaluate a formula string against form data.
 * Supports: field references (dot paths), +, -, *, /, parentheses, numbers.
 * E.g. "income.wages + income.interest - adjustments.total"
 */
export function evaluateFormula(formula: string, data: FormData): number {
  // Replace field references with their numeric values
  // Match dot-path identifiers like "income.wages" or simple "wages"
  const expr = formula.replace(/[a-zA-Z_][a-zA-Z0-9_.]*/g, (match) => {
    // Skip math keywords
    if (['Math', 'max', 'min', 'abs', 'round'].includes(match)) return match;
    const val = getNestedValue(data, match);
    return String(Number(val) || 0);
  });

  try {
    // Safe eval — only allows numbers, operators, parens, Math functions
    if (!/^[\d\s+\-*/().,%]*$/.test(expr.replace(/Math\.\w+/g, ''))) {
      return 0;
    }
    const result = new Function(`return (${expr})`)();
    return typeof result === 'number' && isFinite(result) ? Math.round(result) : 0;
  } catch {
    return 0;
  }
}

/**
 * Compute all calculations in a schema against form data.
 * Returns a map of calculation key → computed value.
 */
export function computeAllCalculations(schema: FormSchema, data: FormData): Record<string, number> {
  const results: Record<string, number> = {};

  // First pass: compute all formulas (some may reference other calculations)
  // Do two passes to handle simple dependencies
  for (let pass = 0; pass < 2; pass++) {
    const merged = { ...data, ...results };
    for (const section of schema.sections) {
      for (const calc of section.calculations || []) {
        results[calc.key] = evaluateFormula(calc.formula, merged);
      }
    }
  }

  return results;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sandbox I/O
// ─────────────────────────────────────────────────────────────────────────────

function schemaPath(botDir: string) { return `${botDir}/tax/data/form_schema.json`; }
function dataPath(botDir: string) { return `${botDir}/tax/data/progress.json`; }

async function fetchSandboxJson(chatId: string, path: string): Promise<any | null> {
  try {
    const url = `${getApiBaseUrl()}/api/chat-files/${chatId}/sandbox-file?path=${encodeURIComponent(path)}`;
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function writeSandboxJson(chatId: string, path: string, data: any): Promise<boolean> {
  try {
    const url = `${getApiBaseUrl()}/api/chat-files/${chatId}/write`;
    const res = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content: JSON.stringify(data, null, 2) }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchFormSchema(chatId: string, botDir = '/home/user'): Promise<FormSchema | null> {
  return fetchSandboxJson(chatId, schemaPath(botDir));
}

export async function fetchFormData(chatId: string, botDir = '/home/user'): Promise<FormData | null> {
  return fetchSandboxJson(chatId, dataPath(botDir));
}

export async function saveFormData(chatId: string, data: FormData, botDir = '/home/user'): Promise<boolean> {
  return writeSandboxJson(chatId, dataPath(botDir), {
    ...data,
    metadata: { ...((data as any).metadata || {}), last_updated: new Date().toISOString() },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

export function getNestedValue(obj: any, path: string): any {
  return path.split('.').reduce((o, k) => o?.[k], obj);
}

export function setNestedValue(obj: any, path: string, value: any): any {
  const keys = path.split('.');
  const result = JSON.parse(JSON.stringify(obj)); // deep clone
  let current = result;
  for (let i = 0; i < keys.length - 1; i++) {
    if (!current[keys[i]] || typeof current[keys[i]] !== 'object') {
      current[keys[i]] = {};
    }
    current = current[keys[i]];
  }
  current[keys[keys.length - 1]] = value;
  return result;
}

export function formatCurrency(n: number): string {
  const abs = Math.abs(n);
  const formatted = abs.toLocaleString('en-US', {
    style: 'currency', currency: 'USD',
    minimumFractionDigits: 0, maximumFractionDigits: 0,
  });
  return n < 0 ? `-${formatted}` : formatted;
}

/** Find which dot-paths changed between two flat-ish objects */
export function findChangedPaths(prev: any, next: any, prefix = ''): string[] {
  const changed: string[] = [];
  if (!prev || !next) return changed;
  for (const key of Object.keys(next)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof next[key] === 'object' && next[key] !== null && !Array.isArray(next[key])) {
      changed.push(...findChangedPaths(prev[key], next[key], path));
    } else if (JSON.stringify(prev[key]) !== JSON.stringify(next[key])) {
      changed.push(path);
    }
  }
  return changed;
}
