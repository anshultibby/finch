// ═══════════════════════════════════════════════════════════════════════════
// Tax Form Data Types, Calculations, and Sandbox I/O
// ═══════════════════════════════════════════════════════════════════════════

import { getApiBaseUrl } from './utils';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export type FilingStatus =
  | 'single'
  | 'married_jointly'
  | 'married_separately'
  | 'head_of_household'
  | 'qualifying_widow';

export interface PersonalInfo {
  first_name: string;
  middle_initial: string;
  last_name: string;
  ssn: string;
  address: string;
  city: string;
  state: string;
  zip: string;
}

export interface SpouseInfo {
  first_name: string;
  middle_initial: string;
  last_name: string;
  ssn: string;
}

export interface Dependent {
  name: string;
  ssn: string;
  relationship: string;
  child_tax_credit: boolean;
}

export interface Income {
  w2_wages: number;
  interest: number;
  dividends: number;
  capital_gains: number;
  ira_distributions: number;
  pensions: number;
  social_security: number;
  other_income: number;
}

export interface Adjustments {
  educator_expenses: number;
  hsa_deduction: number;
  student_loan_interest: number;
  ira_deduction: number;
  self_employment_tax_deduction: number;
}

export interface ItemizedDeductions {
  medical: number;
  state_local_taxes: number;
  mortgage_interest: number;
  charitable: number;
  other: number;
}

export interface Deductions {
  type: 'standard' | 'itemized';
  itemized: ItemizedDeductions;
}

export interface Credits {
  child_tax_credit: number;
  other_dependent_credit: number;
  education_credits: number;
  earned_income_credit: number;
  other_credits: number;
}

export interface OtherTaxes {
  self_employment_tax: number;
  additional_medicare: number;
  other: number;
}

export interface Payments {
  federal_withholding: number;
  estimated_tax_paid: number;
  other_payments: number;
}

export interface TaxFormData {
  tax_year: number;
  filing_status: FilingStatus;
  personal_info: PersonalInfo;
  spouse_info: SpouseInfo | null;
  dependents: Dependent[];
  income: Income;
  adjustments: Adjustments;
  deductions: Deductions;
  credits: Credits;
  other_taxes: OtherTaxes;
  payments: Payments;
  metadata: {
    completed_sections: string[];
    last_updated: string;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Defaults
// ─────────────────────────────────────────────────────────────────────────────

export const EMPTY_FORM: TaxFormData = {
  tax_year: 2025,
  filing_status: 'single',
  personal_info: {
    first_name: '', middle_initial: '', last_name: '', ssn: '',
    address: '', city: '', state: '', zip: '',
  },
  spouse_info: null,
  dependents: [],
  income: {
    w2_wages: 0, interest: 0, dividends: 0, capital_gains: 0,
    ira_distributions: 0, pensions: 0, social_security: 0, other_income: 0,
  },
  adjustments: {
    educator_expenses: 0, hsa_deduction: 0, student_loan_interest: 0,
    ira_deduction: 0, self_employment_tax_deduction: 0,
  },
  deductions: {
    type: 'standard',
    itemized: { medical: 0, state_local_taxes: 0, mortgage_interest: 0, charitable: 0, other: 0 },
  },
  credits: {
    child_tax_credit: 0, other_dependent_credit: 0, education_credits: 0,
    earned_income_credit: 0, other_credits: 0,
  },
  other_taxes: { self_employment_tax: 0, additional_medicare: 0, other: 0 },
  payments: { federal_withholding: 0, estimated_tax_paid: 0, other_payments: 0 },
  metadata: { completed_sections: [], last_updated: '' },
};

// ─────────────────────────────────────────────────────────────────────────────
// Tax Calculations (2025 rates)
// ─────────────────────────────────────────────────────────────────────────────

const STANDARD_DEDUCTIONS: Record<FilingStatus, number> = {
  single: 15000,
  married_jointly: 30000,
  married_separately: 15000,
  head_of_household: 22500,
  qualifying_widow: 30000,
};

const BRACKETS: Record<FilingStatus, [number, number][]> = {
  single: [
    [11925, 0.10], [48475, 0.12], [103350, 0.22],
    [197300, 0.24], [250525, 0.32], [626350, 0.35], [Infinity, 0.37],
  ],
  married_jointly: [
    [23850, 0.10], [96950, 0.12], [206700, 0.22],
    [394600, 0.24], [501050, 0.32], [751600, 0.35], [Infinity, 0.37],
  ],
  married_separately: [
    [11925, 0.10], [48475, 0.12], [103350, 0.22],
    [197300, 0.24], [250525, 0.32], [375800, 0.35], [Infinity, 0.37],
  ],
  head_of_household: [
    [17000, 0.10], [64850, 0.12], [103350, 0.22],
    [197300, 0.24], [250500, 0.32], [626350, 0.35], [Infinity, 0.37],
  ],
  qualifying_widow: [
    [23850, 0.10], [96950, 0.12], [206700, 0.22],
    [394600, 0.24], [501050, 0.32], [751600, 0.35], [Infinity, 0.37],
  ],
};

export function computeIncomeTax(taxableIncome: number, status: FilingStatus): number {
  const brackets = BRACKETS[status];
  let tax = 0;
  let prev = 0;
  for (const [limit, rate] of brackets) {
    const taxable = Math.min(taxableIncome, limit) - prev;
    if (taxable <= 0) break;
    tax += taxable * rate;
    prev = limit;
  }
  return Math.round(tax);
}

export function getStandardDeduction(status: FilingStatus): number {
  return STANDARD_DEDUCTIONS[status];
}

/** Compute all derived values from form data */
export function computeDerived(data: TaxFormData) {
  const inc = data.income;
  const adj = data.adjustments;
  const ded = data.deductions;
  const cred = data.credits;
  const otx = data.other_taxes;
  const pay = data.payments;

  const totalIncome =
    inc.w2_wages + inc.interest + inc.dividends + inc.capital_gains +
    inc.ira_distributions + inc.pensions + inc.social_security + inc.other_income;

  const totalAdjustments =
    adj.educator_expenses + adj.hsa_deduction + adj.student_loan_interest +
    adj.ira_deduction + adj.self_employment_tax_deduction;

  const agi = totalIncome - totalAdjustments;

  const standardDed = getStandardDeduction(data.filing_status);
  const itemizedTotal = ded.type === 'itemized'
    ? ded.itemized.medical + ded.itemized.state_local_taxes +
      ded.itemized.mortgage_interest + ded.itemized.charitable + ded.itemized.other
    : 0;
  const deductionAmount = ded.type === 'standard' ? standardDed : itemizedTotal;

  const taxableIncome = Math.max(0, agi - deductionAmount);
  const incomeTax = computeIncomeTax(taxableIncome, data.filing_status);

  const totalCredits =
    cred.child_tax_credit + cred.other_dependent_credit +
    cred.education_credits + cred.earned_income_credit + cred.other_credits;

  const totalOtherTaxes =
    otx.self_employment_tax + otx.additional_medicare + otx.other;

  const totalTax = Math.max(0, incomeTax + totalOtherTaxes - totalCredits);

  const totalPayments = pay.federal_withholding + pay.estimated_tax_paid + pay.other_payments;

  const refundOrOwed = totalPayments - totalTax;

  return {
    totalIncome,
    totalAdjustments,
    agi,
    standardDeduction: standardDed,
    itemizedTotal,
    deductionAmount,
    taxableIncome,
    incomeTax,
    totalCredits,
    totalOtherTaxes,
    totalTax,
    totalPayments,
    refundOrOwed,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Sandbox I/O
// ─────────────────────────────────────────────────────────────────────────────

function progressPath(botDir: string) { return `${botDir}/tax/data/progress.json`; }

export async function fetchTaxForm(chatId: string, botDir = '/home/user'): Promise<TaxFormData | null> {
  try {
    const url = `${getApiBaseUrl()}/api/chat-files/${chatId}/sandbox-file?path=${encodeURIComponent(progressPath(botDir))}`;
    const res = await fetch(url);
    if (!res.ok) return null;
    const data = await res.json();
    // Merge with defaults so missing fields don't break the UI
    return deepMerge(EMPTY_FORM, data) as TaxFormData;
  } catch {
    return null;
  }
}

export async function saveTaxForm(chatId: string, data: TaxFormData, botDir = '/home/user'): Promise<boolean> {
  try {
    const url = `${getApiBaseUrl()}/api/chat-files/${chatId}/write`;
    const res = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: progressPath(botDir), content: JSON.stringify(data, null, 2) }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function deepMerge(target: any, source: any): any {
  if (!source) return target;
  const result = { ...target };
  for (const key of Object.keys(source)) {
    if (
      source[key] &&
      typeof source[key] === 'object' &&
      !Array.isArray(source[key]) &&
      target[key] &&
      typeof target[key] === 'object'
    ) {
      result[key] = deepMerge(target[key], source[key]);
    } else if (source[key] !== undefined) {
      result[key] = source[key];
    }
  }
  return result;
}

export function formatCurrency(n: number): string {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 });
}
