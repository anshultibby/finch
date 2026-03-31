'use client';

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  TaxFormData, EMPTY_FORM, FilingStatus,
  fetchTaxForm, saveTaxForm, computeDerived, formatCurrency, getStandardDeduction,
} from '@/lib/taxForm';

interface TaxFormCopilotProps {
  chatId: string;
  onClose: () => void;
  /** Bump this number to trigger a re-fetch (e.g. after agent tool completes) */
  refreshTrigger?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Number input that handles empty string gracefully
// ─────────────────────────────────────────────────────────────────────────────

function CurrencyInput({
  value, onChange, label, line, disabled, highlight,
}: {
  value: number; onChange: (v: number) => void;
  label: string; line?: string; disabled?: boolean; highlight?: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 py-1.5 transition-colors duration-700 rounded px-2 -mx-2 ${
      highlight ? 'bg-amber-50' : ''
    }`}>
      <div className="flex-1 min-w-0">
        <label className="text-xs text-gray-600 block truncate">
          {line && <span className="text-gray-400 mr-1">{line}</span>}
          {label}
        </label>
      </div>
      <div className="relative w-28 flex-shrink-0">
        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">$</span>
        <input
          type="number"
          value={value || ''}
          onChange={(e) => onChange(Number(e.target.value) || 0)}
          disabled={disabled}
          className="w-full text-right text-sm border border-gray-200 rounded-md py-1 pl-5 pr-2
            focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400
            disabled:bg-gray-50 disabled:text-gray-500 tabular-nums"
        />
      </div>
    </div>
  );
}

function TextInput({
  value, onChange, label, placeholder, highlight,
}: {
  value: string; onChange: (v: string) => void;
  label: string; placeholder?: string; highlight?: boolean;
}) {
  return (
    <div className={`py-1.5 transition-colors duration-700 rounded px-2 -mx-2 ${
      highlight ? 'bg-amber-50' : ''
    }`}>
      <label className="text-xs text-gray-600 block mb-0.5">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full text-sm border border-gray-200 rounded-md py-1 px-2
          focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
      />
    </div>
  );
}

function ComputedRow({ label, value, line, large }: {
  label: string; value: number; line?: string; large?: boolean;
}) {
  const isNegative = value < 0;
  return (
    <div className={`flex items-center justify-between py-1.5 px-2 -mx-2 ${
      large ? 'bg-gray-50 rounded-md' : ''
    }`}>
      <span className={`${large ? 'text-sm font-semibold text-gray-800' : 'text-xs text-gray-500'}`}>
        {line && <span className="text-gray-400 mr-1">{line}</span>}
        {label}
      </span>
      <span className={`tabular-nums font-mono ${
        large
          ? `text-base font-bold ${isNegative ? 'text-red-600' : 'text-emerald-600'}`
          : `text-sm ${isNegative ? 'text-red-600' : 'text-gray-700'}`
      }`}>
        {formatCurrency(Math.abs(value))}
        {isNegative && large && ' owed'}
        {!isNegative && large && value > 0 && ' refund'}
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section wrapper
// ─────────────────────────────────────────────────────────────────────────────

function Section({ title, children, defaultOpen = true }: {
  title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-2.5 px-3 hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-semibold text-gray-800">{title}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
        >
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="px-3 pb-3">{children}</div>}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

export default function TaxFormCopilot({ chatId, onClose, refreshTrigger }: TaxFormCopilotProps) {
  const [form, setForm] = useState<TaxFormData>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set());
  const saveTimer = useRef<NodeJS.Timeout | null>(null);
  const prevFormRef = useRef<string>('');

  // Fetch form data from sandbox
  const loadForm = useCallback(async () => {
    const data = await fetchTaxForm(chatId);
    if (data) {
      const newJson = JSON.stringify(data);
      // Detect which fields changed for highlight animation
      if (prevFormRef.current && prevFormRef.current !== newJson) {
        const prev = JSON.parse(prevFormRef.current);
        const changed = findChangedPaths(prev, data);
        if (changed.length > 0) {
          setChangedFields(new Set(changed));
          setTimeout(() => setChangedFields(new Set()), 2000);
        }
      }
      prevFormRef.current = newJson;
      setForm(data);
    }
    setLoading(false);
  }, [chatId]);

  // Initial load
  useEffect(() => { loadForm(); }, [loadForm]);

  // Re-fetch when refreshTrigger changes (agent updated progress.json)
  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) loadForm();
  }, [refreshTrigger, loadForm]);

  // Debounced save
  const scheduleAutosave = useCallback((updated: TaxFormData) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      setSaving(true);
      const toSave = { ...updated, metadata: { ...updated.metadata, last_updated: new Date().toISOString() } };
      await saveTaxForm(chatId, toSave);
      prevFormRef.current = JSON.stringify(toSave);
      setSaving(false);
    }, 800);
  }, [chatId]);

  // Update helpers
  const updateField = useCallback(<K extends keyof TaxFormData>(
    section: K,
    field: string,
    value: any,
  ) => {
    setForm(prev => {
      const updated = {
        ...prev,
        [section]: { ...(prev[section] as any), [field]: value },
      };
      scheduleAutosave(updated);
      return updated;
    });
  }, [scheduleAutosave]);

  const updateNested = useCallback((
    section: keyof TaxFormData,
    sub: string,
    field: string,
    value: any,
  ) => {
    setForm(prev => {
      const sectionData = prev[section] as any;
      const updated = {
        ...prev,
        [section]: {
          ...sectionData,
          [sub]: { ...sectionData[sub], [field]: value },
        },
      };
      scheduleAutosave(updated);
      return updated;
    });
  }, [scheduleAutosave]);

  const setFilingStatus = useCallback((status: FilingStatus) => {
    setForm(prev => {
      const updated = { ...prev, filing_status: status };
      scheduleAutosave(updated);
      return updated;
    });
  }, [scheduleAutosave]);

  const setDeductionType = useCallback((type: 'standard' | 'itemized') => {
    setForm(prev => {
      const updated = { ...prev, deductions: { ...prev.deductions, type } };
      scheduleAutosave(updated);
      return updated;
    });
  }, [scheduleAutosave]);

  // Computed values
  const derived = useMemo(() => computeDerived(form), [form]);
  const isHighlighted = (path: string) => changedFields.has(path);

  if (loading) {
    return (
      <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-xl">
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-full border-2 border-gray-200 border-t-blue-500 animate-spin" />
            <span className="text-sm text-gray-400">Loading tax form...</span>
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
            <button
              onClick={onClose}
              className="w-3 h-3 rounded-full bg-[#ff5f57] hover:bg-[#ff3b30] transition-colors group relative"
              title="Close"
            >
              <span className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 text-[8px] text-black font-bold">x</span>
            </button>
            <div className="w-3 h-3 rounded-full bg-[#febc2e] cursor-default" />
            <div className="w-3 h-3 rounded-full bg-[#28c840] cursor-default" />
          </div>
          <div className="flex items-center gap-2 md:ml-3 min-w-0">
            <span className="text-lg">1040</span>
            <div className="min-w-0">
              <span className="text-sm font-semibold text-gray-800 block truncate">
                U.S. Individual Income Tax Return
              </span>
              <span className="text-[10px] text-gray-400">Tax Year {form.tax_year}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {saving && (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <div className="w-3 h-3 rounded-full border border-gray-300 border-t-blue-500 animate-spin" />
              Saving
            </span>
          )}
          <button
            onClick={onClose}
            className="md:hidden p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Scrollable form body */}
      <div className="flex-1 overflow-y-auto">

        {/* Filing Status */}
        <Section title="Filing Status">
          <div className="grid grid-cols-1 gap-1">
            {([
              ['single', 'Single'],
              ['married_jointly', 'Married Filing Jointly'],
              ['married_separately', 'Married Filing Separately'],
              ['head_of_household', 'Head of Household'],
              ['qualifying_widow', 'Qualifying Surviving Spouse'],
            ] as [FilingStatus, string][]).map(([val, label]) => (
              <label key={val} className="flex items-center gap-2 py-1 cursor-pointer text-sm text-gray-700 hover:text-gray-900">
                <input
                  type="radio"
                  name="filing_status"
                  checked={form.filing_status === val}
                  onChange={() => setFilingStatus(val)}
                  className="accent-blue-600"
                />
                {label}
              </label>
            ))}
          </div>
        </Section>

        {/* Personal Info */}
        <Section title="Personal Information">
          <div className="grid grid-cols-2 gap-x-3">
            <TextInput label="First name" value={form.personal_info.first_name}
              onChange={v => updateField('personal_info', 'first_name', v)}
              highlight={isHighlighted('personal_info.first_name')} />
            <TextInput label="Last name" value={form.personal_info.last_name}
              onChange={v => updateField('personal_info', 'last_name', v)}
              highlight={isHighlighted('personal_info.last_name')} />
          </div>
          <div className="grid grid-cols-2 gap-x-3">
            <TextInput label="M.I." value={form.personal_info.middle_initial}
              onChange={v => updateField('personal_info', 'middle_initial', v)} />
            <TextInput label="SSN" value={form.personal_info.ssn} placeholder="XXX-XX-XXXX"
              onChange={v => updateField('personal_info', 'ssn', v)}
              highlight={isHighlighted('personal_info.ssn')} />
          </div>
          <TextInput label="Address" value={form.personal_info.address}
            onChange={v => updateField('personal_info', 'address', v)} />
          <div className="grid grid-cols-3 gap-x-3">
            <TextInput label="City" value={form.personal_info.city}
              onChange={v => updateField('personal_info', 'city', v)} />
            <TextInput label="State" value={form.personal_info.state}
              onChange={v => updateField('personal_info', 'state', v)} />
            <TextInput label="ZIP" value={form.personal_info.zip}
              onChange={v => updateField('personal_info', 'zip', v)} />
          </div>
        </Section>

        {/* Income */}
        <Section title="Income">
          <CurrencyInput label="Wages, salaries, tips (W-2)" line="1a" value={form.income.w2_wages}
            onChange={v => updateField('income', 'w2_wages', v)}
            highlight={isHighlighted('income.w2_wages')} />
          <CurrencyInput label="Taxable interest" line="2b" value={form.income.interest}
            onChange={v => updateField('income', 'interest', v)}
            highlight={isHighlighted('income.interest')} />
          <CurrencyInput label="Ordinary dividends" line="3b" value={form.income.dividends}
            onChange={v => updateField('income', 'dividends', v)}
            highlight={isHighlighted('income.dividends')} />
          <CurrencyInput label="Capital gain or (loss)" line="7" value={form.income.capital_gains}
            onChange={v => updateField('income', 'capital_gains', v)}
            highlight={isHighlighted('income.capital_gains')} />
          <CurrencyInput label="IRA distributions (taxable)" line="4b" value={form.income.ira_distributions}
            onChange={v => updateField('income', 'ira_distributions', v)} />
          <CurrencyInput label="Pensions and annuities (taxable)" line="5b" value={form.income.pensions}
            onChange={v => updateField('income', 'pensions', v)} />
          <CurrencyInput label="Social Security benefits (taxable)" line="6b" value={form.income.social_security}
            onChange={v => updateField('income', 'social_security', v)} />
          <CurrencyInput label="Other income" line="8" value={form.income.other_income}
            onChange={v => updateField('income', 'other_income', v)} />
          <div className="border-t border-gray-100 mt-2 pt-1">
            <ComputedRow label="Total income" value={derived.totalIncome} line="9" />
          </div>
        </Section>

        {/* Adjustments */}
        <Section title="Adjustments to Income" defaultOpen={false}>
          <CurrencyInput label="Educator expenses" value={form.adjustments.educator_expenses}
            onChange={v => updateField('adjustments', 'educator_expenses', v)} />
          <CurrencyInput label="HSA deduction" value={form.adjustments.hsa_deduction}
            onChange={v => updateField('adjustments', 'hsa_deduction', v)} />
          <CurrencyInput label="Student loan interest" value={form.adjustments.student_loan_interest}
            onChange={v => updateField('adjustments', 'student_loan_interest', v)} />
          <CurrencyInput label="IRA deduction" value={form.adjustments.ira_deduction}
            onChange={v => updateField('adjustments', 'ira_deduction', v)} />
          <CurrencyInput label="Self-employment tax deduction" value={form.adjustments.self_employment_tax_deduction}
            onChange={v => updateField('adjustments', 'self_employment_tax_deduction', v)} />
          <div className="border-t border-gray-100 mt-2 pt-1">
            <ComputedRow label="Total adjustments" value={derived.totalAdjustments} line="10" />
            <ComputedRow label="Adjusted gross income (AGI)" value={derived.agi} line="11" large />
          </div>
        </Section>

        {/* Deductions */}
        <Section title="Deductions">
          <div className="flex gap-3 mb-2">
            {(['standard', 'itemized'] as const).map(type => (
              <label key={type} className="flex items-center gap-1.5 cursor-pointer text-sm text-gray-700">
                <input
                  type="radio"
                  checked={form.deductions.type === type}
                  onChange={() => setDeductionType(type)}
                  className="accent-blue-600"
                />
                {type === 'standard'
                  ? `Standard (${formatCurrency(getStandardDeduction(form.filing_status))})`
                  : 'Itemized'}
              </label>
            ))}
          </div>
          {form.deductions.type === 'itemized' && (
            <div className="ml-2 border-l-2 border-gray-100 pl-3">
              <CurrencyInput label="Medical & dental" value={form.deductions.itemized.medical}
                onChange={v => updateNested('deductions', 'itemized', 'medical', v)} />
              <CurrencyInput label="State & local taxes (max $10k)" value={form.deductions.itemized.state_local_taxes}
                onChange={v => updateNested('deductions', 'itemized', 'state_local_taxes', v)} />
              <CurrencyInput label="Mortgage interest" value={form.deductions.itemized.mortgage_interest}
                onChange={v => updateNested('deductions', 'itemized', 'mortgage_interest', v)} />
              <CurrencyInput label="Charitable contributions" value={form.deductions.itemized.charitable}
                onChange={v => updateNested('deductions', 'itemized', 'charitable', v)} />
              <CurrencyInput label="Other deductions" value={form.deductions.itemized.other}
                onChange={v => updateNested('deductions', 'itemized', 'other', v)} />
            </div>
          )}
          <div className="border-t border-gray-100 mt-2 pt-1">
            <ComputedRow label="Deduction amount" value={derived.deductionAmount} line="13" />
            <ComputedRow label="Taxable income" value={derived.taxableIncome} line="15" large />
          </div>
        </Section>

        {/* Tax & Credits */}
        <Section title="Tax & Credits">
          <ComputedRow label="Income tax (from brackets)" value={derived.incomeTax} line="16" />
          <div className="border-t border-gray-100 mt-2 pt-1">
            <CurrencyInput label="Child tax credit" value={form.credits.child_tax_credit}
              onChange={v => updateField('credits', 'child_tax_credit', v)} />
            <CurrencyInput label="Other dependent credit" value={form.credits.other_dependent_credit}
              onChange={v => updateField('credits', 'other_dependent_credit', v)} />
            <CurrencyInput label="Education credits" value={form.credits.education_credits}
              onChange={v => updateField('credits', 'education_credits', v)} />
            <CurrencyInput label="Earned income credit" value={form.credits.earned_income_credit}
              onChange={v => updateField('credits', 'earned_income_credit', v)} />
            <CurrencyInput label="Other credits" value={form.credits.other_credits}
              onChange={v => updateField('credits', 'other_credits', v)} />
          </div>
          <div className="border-t border-gray-100 mt-2 pt-1">
            <ComputedRow label="Total credits" value={derived.totalCredits} />
          </div>
        </Section>

        {/* Other Taxes */}
        <Section title="Other Taxes" defaultOpen={false}>
          <CurrencyInput label="Self-employment tax" value={form.other_taxes.self_employment_tax}
            onChange={v => updateField('other_taxes', 'self_employment_tax', v)} />
          <CurrencyInput label="Additional Medicare tax" value={form.other_taxes.additional_medicare}
            onChange={v => updateField('other_taxes', 'additional_medicare', v)} />
          <CurrencyInput label="Other taxes" value={form.other_taxes.other}
            onChange={v => updateField('other_taxes', 'other', v)} />
          <div className="border-t border-gray-100 mt-2 pt-1">
            <ComputedRow label="Total tax" value={derived.totalTax} line="24" large />
          </div>
        </Section>

        {/* Payments */}
        <Section title="Payments">
          <CurrencyInput label="Federal tax withheld (W-2 box 2)" value={form.payments.federal_withholding}
            onChange={v => updateField('payments', 'federal_withholding', v)}
            highlight={isHighlighted('payments.federal_withholding')} />
          <CurrencyInput label="Estimated tax payments" value={form.payments.estimated_tax_paid}
            onChange={v => updateField('payments', 'estimated_tax_paid', v)} />
          <CurrencyInput label="Other payments" value={form.payments.other_payments}
            onChange={v => updateField('payments', 'other_payments', v)} />
          <div className="border-t border-gray-100 mt-2 pt-1">
            <ComputedRow label="Total payments" value={derived.totalPayments} line="33" />
          </div>
        </Section>

        {/* Refund / Amount Owed */}
        <div className="px-3 py-4 bg-gray-50">
          <ComputedRow
            label={derived.refundOrOwed >= 0 ? 'Your refund' : 'Amount you owe'}
            value={derived.refundOrOwed}
            line={derived.refundOrOwed >= 0 ? '34' : '37'}
            large
          />
        </div>

        {/* Bottom padding */}
        <div className="h-4" />
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
        <span className="text-[10px] text-gray-400">
          {form.metadata.last_updated
            ? `Saved ${new Date(form.metadata.last_updated).toLocaleTimeString()}`
            : 'Not saved yet'}
        </span>
        <button
          onClick={() => {
            // Trigger PDF export - the agent should handle this via chat
            // For now, just close and let user ask
            onClose();
          }}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium hover:underline"
        >
          Export PDF
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Diff helper: find which dot-paths changed between two objects
// ─────────────────────────────────────────────────────────────────────────────

function findChangedPaths(prev: any, next: any, prefix = ''): string[] {
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
