'use client';

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type {
  FormSchema, FormData, FieldDef, CalculationDef, SectionDef,
} from '@/lib/formSchema';
import {
  fetchFormSchema, fetchFormData, saveFormData,
  computeAllCalculations, getNestedValue, setNestedValue,
  formatCurrency, findChangedPaths,
} from '@/lib/formSchema';

interface FormCopilotProps {
  chatId: string;
  onClose: () => void;
  /** Bump to trigger a re-fetch */
  refreshTrigger?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Field renderers
// ─────────────────────────────────────────────────────────────────────────────

function CurrencyField({ field, value, onChange, highlight }: {
  field: FieldDef; value: number; onChange: (v: number) => void; highlight: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 py-1.5 transition-colors duration-700 rounded px-2 -mx-2 ${highlight ? 'bg-amber-50' : ''}`}>
      <div className="flex-1 min-w-0">
        <label className="text-xs text-gray-600 block truncate">
          {field.line && <span className="text-gray-400 mr-1">{field.line}</span>}
          {field.label}
        </label>
      </div>
      <div className="relative w-28 flex-shrink-0">
        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">$</span>
        <input
          type="number"
          value={value || ''}
          onChange={(e) => onChange(Number(e.target.value) || 0)}
          placeholder={field.placeholder}
          className="w-full text-right text-sm border border-gray-200 rounded-md py-1 pl-5 pr-2 focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400 tabular-nums"
        />
      </div>
    </div>
  );
}

function NumberField({ field, value, onChange, highlight }: {
  field: FieldDef; value: number; onChange: (v: number) => void; highlight: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 py-1.5 transition-colors duration-700 rounded px-2 -mx-2 ${highlight ? 'bg-amber-50' : ''}`}>
      <div className="flex-1 min-w-0">
        <label className="text-xs text-gray-600 block truncate">
          {field.line && <span className="text-gray-400 mr-1">{field.line}</span>}
          {field.label}
        </label>
      </div>
      <input
        type="number"
        value={value || ''}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
        placeholder={field.placeholder}
        className="w-28 text-right text-sm border border-gray-200 rounded-md py-1 px-2 focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400 tabular-nums flex-shrink-0"
      />
    </div>
  );
}

function TextField({ field, value, onChange, highlight }: {
  field: FieldDef; value: string; onChange: (v: string) => void; highlight: boolean;
}) {
  return (
    <div className={`py-1.5 transition-colors duration-700 rounded px-2 -mx-2 ${highlight ? 'bg-amber-50' : ''}`}>
      <label className="text-xs text-gray-600 block mb-0.5">
        {field.line && <span className="text-gray-400 mr-1">{field.line}</span>}
        {field.label}
      </label>
      <input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.placeholder}
        className="w-full text-sm border border-gray-200 rounded-md py-1 px-2 focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
      />
    </div>
  );
}

function SelectField({ field, value, onChange, highlight }: {
  field: FieldDef; value: string; onChange: (v: string) => void; highlight: boolean;
}) {
  return (
    <div className={`py-1.5 transition-colors duration-700 rounded px-2 -mx-2 ${highlight ? 'bg-amber-50' : ''}`}>
      <label className="text-xs text-gray-600 block mb-0.5">
        {field.line && <span className="text-gray-400 mr-1">{field.line}</span>}
        {field.label}
      </label>
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full text-sm border border-gray-200 rounded-md py-1 px-2 focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400 bg-white"
      >
        <option value="">Select...</option>
        {(field.options || []).map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function RadioField({ field, value, onChange, highlight }: {
  field: FieldDef; value: string; onChange: (v: string) => void; highlight: boolean;
}) {
  return (
    <div className={`py-1.5 transition-colors duration-700 rounded px-2 -mx-2 ${highlight ? 'bg-amber-50' : ''}`}>
      <label className="text-xs text-gray-600 block mb-1">
        {field.line && <span className="text-gray-400 mr-1">{field.line}</span>}
        {field.label}
      </label>
      <div className="grid grid-cols-1 gap-0.5">
        {(field.options || []).map(o => (
          <label key={o.value} className="flex items-center gap-2 py-0.5 cursor-pointer text-sm text-gray-700 hover:text-gray-900">
            <input
              type="radio"
              name={field.key}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
              className="accent-blue-600"
            />
            {o.label}
          </label>
        ))}
      </div>
    </div>
  );
}

function CheckboxField({ field, value, onChange, highlight }: {
  field: FieldDef; value: boolean; onChange: (v: boolean) => void; highlight: boolean;
}) {
  return (
    <div className={`py-1.5 transition-colors duration-700 rounded px-2 -mx-2 ${highlight ? 'bg-amber-50' : ''}`}>
      <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 hover:text-gray-900">
        <input
          type="checkbox"
          checked={!!value}
          onChange={(e) => onChange(e.target.checked)}
          className="accent-blue-600"
        />
        {field.line && <span className="text-gray-400 text-xs">{field.line}</span>}
        {field.label}
      </label>
    </div>
  );
}

function ComputedRow({ calc, value }: { calc: CalculationDef; value: number }) {
  const isNegative = value < 0;
  return (
    <div className={`flex items-center justify-between py-1.5 px-2 -mx-2 ${calc.large ? 'bg-gray-50 rounded-md' : ''}`}>
      <span className={calc.large ? 'text-sm font-semibold text-gray-800' : 'text-xs text-gray-500'}>
        {calc.line && <span className="text-gray-400 mr-1">{calc.line}</span>}
        {calc.label}
      </span>
      <span className={`tabular-nums font-mono ${
        calc.large
          ? `text-base font-bold ${isNegative ? 'text-red-600' : 'text-emerald-600'}`
          : `text-sm ${isNegative ? 'text-red-600' : 'text-gray-700'}`
      }`}>
        {formatCurrency(Math.abs(value))}
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Generic field renderer
// ─────────────────────────────────────────────────────────────────────────────

function FormField({ field, data, onChange, highlight }: {
  field: FieldDef; data: FormData; onChange: (key: string, value: any) => void; highlight: boolean;
}) {
  const value = getNestedValue(data, field.key);
  const handleChange = (v: any) => onChange(field.key, v);

  switch (field.type) {
    case 'currency':
      return <CurrencyField field={field} value={value ?? 0} onChange={handleChange} highlight={highlight} />;
    case 'number':
      return <NumberField field={field} value={value ?? 0} onChange={handleChange} highlight={highlight} />;
    case 'select':
      return <SelectField field={field} value={value ?? ''} onChange={handleChange} highlight={highlight} />;
    case 'radio':
      return <RadioField field={field} value={value ?? ''} onChange={handleChange} highlight={highlight} />;
    case 'checkbox':
      return <CheckboxField field={field} value={value ?? false} onChange={handleChange} highlight={highlight} />;
    default:
      return <TextField field={field} value={value ?? ''} onChange={handleChange} highlight={highlight} />;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Section wrapper
// ─────────────────────────────────────────────────────────────────────────────

function Section({ def, data, computed, changedFields, onChange }: {
  def: SectionDef; data: FormData; computed: Record<string, number>;
  changedFields: Set<string>; onChange: (key: string, value: any) => void;
}) {
  const [open, setOpen] = useState(def.defaultOpen !== false);

  // Group fields by width for layout
  const rows: FieldDef[][] = [];
  let currentRow: FieldDef[] = [];
  let currentWidth = 0;

  for (const field of def.fields) {
    const w = field.width === 'third' ? 1 : field.width === 'half' ? 2 : 3;
    if (currentWidth + w > 3 && currentRow.length > 0) {
      rows.push(currentRow);
      currentRow = [];
      currentWidth = 0;
    }
    currentRow.push(field);
    currentWidth += w;
  }
  if (currentRow.length > 0) rows.push(currentRow);

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-2.5 px-3 hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-semibold text-gray-800">{def.title}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
        >
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="px-3 pb-3">
          {rows.map((row, ri) => {
            if (row.length === 1 && (row[0].width === 'full' || !row[0].width)) {
              return <FormField key={row[0].key} field={row[0]} data={data} onChange={onChange} highlight={changedFields.has(row[0].key)} />;
            }
            const cols = row.length === 3 ? 'grid-cols-3' : row.length === 2 ? 'grid-cols-2' : 'grid-cols-1';
            return (
              <div key={ri} className={`grid ${cols} gap-x-3`}>
                {row.map(f => (
                  <FormField key={f.key} field={f} data={data} onChange={onChange} highlight={changedFields.has(f.key)} />
                ))}
              </div>
            );
          })}
          {def.calculations && def.calculations.length > 0 && (
            <div className="border-t border-gray-100 mt-2 pt-1">
              {def.calculations.map(calc => (
                <ComputedRow key={calc.key} calc={calc} value={computed[calc.key] ?? 0} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

export default function FormCopilot({ chatId, onClose, refreshTrigger }: FormCopilotProps) {
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [data, setData] = useState<FormData>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set());
  const saveTimer = useRef<NodeJS.Timeout | null>(null);
  const prevDataRef = useRef<string>('');

  // Load schema and data
  const load = useCallback(async () => {
    const [s, d] = await Promise.all([
      fetchFormSchema(chatId),
      fetchFormData(chatId),
    ]);
    if (s) setSchema(s);
    if (d) {
      const newJson = JSON.stringify(d);
      if (prevDataRef.current && prevDataRef.current !== newJson) {
        const prev = JSON.parse(prevDataRef.current);
        const changed = findChangedPaths(prev, d);
        if (changed.length > 0) {
          setChangedFields(new Set(changed));
          setTimeout(() => setChangedFields(new Set()), 2000);
        }
      }
      prevDataRef.current = newJson;
      setData(d);
    }
    setLoading(false);
  }, [chatId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (refreshTrigger && refreshTrigger > 0) load(); }, [refreshTrigger, load]);

  // Debounced save
  const scheduleAutosave = useCallback((updated: FormData) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      setSaving(true);
      await saveFormData(chatId, updated);
      prevDataRef.current = JSON.stringify(updated);
      setSaving(false);
    }, 800);
  }, [chatId]);

  const handleFieldChange = useCallback((key: string, value: any) => {
    setData(prev => {
      const updated = setNestedValue(prev, key, value);
      scheduleAutosave(updated);
      return updated;
    });
  }, [scheduleAutosave]);

  // Computed values
  const computed = useMemo(() => {
    if (!schema) return {};
    return computeAllCalculations(schema, data);
  }, [schema, data]);

  if (loading) {
    return (
      <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-xl">
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-full border-2 border-gray-200 border-t-blue-500 animate-spin" />
            <span className="text-sm text-gray-400">Loading form...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
          <span className="text-sm font-semibold text-gray-800">Form</span>
          <button onClick={onClose} className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center text-gray-400">
            <p className="text-sm">No form schema found.</p>
            <p className="text-xs mt-1">The agent will create one when you start filling a form.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-3 min-w-0">
          <div className="hidden md:flex items-center gap-1.5 flex-shrink-0">
            <button onClick={onClose} className="w-3 h-3 rounded-full bg-[#ff5f57] hover:bg-[#ff3b30] transition-colors group relative" title="Close">
              <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 text-[8px] text-black font-bold">x</span>
            </button>
            <div className="w-3 h-3 rounded-full bg-[#febc2e] cursor-default" />
            <div className="w-3 h-3 rounded-full bg-[#28c840] cursor-default" />
          </div>
          <div className="min-w-0 md:ml-3">
            <span className="text-sm font-semibold text-gray-800 block truncate">{schema.name}</span>
            {schema.subtitle && (
              <span className="text-[10px] text-gray-400 block truncate">{schema.subtitle}{schema.year ? ` (${schema.year})` : ''}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {saving && (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <div className="w-3 h-3 rounded-full border border-gray-300 border-t-blue-500 animate-spin" />
              Saving
            </span>
          )}
          <button onClick={onClose} className="md:hidden p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      {/* Scrollable form body */}
      <div className="flex-1 overflow-y-auto">
        {schema.sections.map((section, i) => (
          <Section
            key={i}
            def={section}
            data={data}
            computed={computed}
            changedFields={changedFields}
            onChange={handleFieldChange}
          />
        ))}
        <div className="h-4" />
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
        <span className="text-[10px] text-gray-400">
          {(data as any).metadata?.last_updated
            ? `Saved ${new Date((data as any).metadata.last_updated).toLocaleTimeString()}`
            : 'Not saved yet'}
        </span>
        <button
          onClick={onClose}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium hover:underline"
        >
          Done
        </button>
      </div>
    </div>
  );
}
