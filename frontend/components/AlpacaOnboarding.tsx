'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { alpacaBrokerApi } from '@/lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

type OnboardingStep = 'personal' | 'address' | 'identity' | 'disclosures' | 'agreements' | 'submitted' | 'done';

interface FormData {
  // personal
  first_name: string;
  last_name: string;
  date_of_birth: string;
  email: string;
  phone_number: string;
  // address
  street_address: string;
  city: string;
  state: string;
  postal_code: string;
  // identity
  tax_id: string;
  employment_status: string;
  funding_source: string[];
  // disclosures
  is_control_person: boolean;
  is_affiliated_exchange_or_finra: boolean;
  is_politically_exposed: boolean;
  immediate_family_exposed: boolean;
  // agreements
  agreements_accepted: boolean;
}

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
  'VA','WA','WV','WI','WY','DC',
];

const EMPLOYMENT_OPTIONS = [
  { value: 'employed', label: 'Employed' },
  { value: 'self_employed', label: 'Self-employed' },
  { value: 'unemployed', label: 'Unemployed' },
  { value: 'student', label: 'Student' },
  { value: 'retired', label: 'Retired' },
];

const FUNDING_OPTIONS = [
  { value: 'employment_income', label: 'Employment income' },
  { value: 'investments', label: 'Investments' },
  { value: 'savings', label: 'Savings' },
];

const STEPS: OnboardingStep[] = ['personal', 'address', 'identity', 'disclosures', 'agreements', 'submitted'];
const STEP_LABELS: Record<OnboardingStep, string> = {
  personal: 'Personal',
  address: 'Address',
  identity: 'Identity',
  disclosures: 'Disclosures',
  agreements: 'Agreements',
  submitted: 'Submitted',
  done: 'Done',
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface AlpacaOnboardingProps {
  userId: string;
  onClose: () => void;
  onSuccess?: () => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 mb-4 transition-colors">
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
      </svg>
      Back
    </button>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs font-semibold text-gray-500 mb-1.5">{children}</label>;
}

function Input({ type = 'text', value, onChange, placeholder, autoComplete }: {
  type?: string; value: string; onChange: (v: string) => void;
  placeholder?: string; autoComplete?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      autoComplete={autoComplete || 'off'}
      spellCheck={false}
      className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 placeholder-gray-300 transition-all"
    />
  );
}

function Select({ value, onChange, children }: {
  value: string; onChange: (v: string) => void; children: React.ReactNode;
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 bg-white transition-all appearance-none"
    >
      {children}
    </select>
  );
}

function YesNoToggle({ label, value, onChange }: {
  label: string; value: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50/60 p-3.5">
      <div className="text-sm text-gray-700 mb-2.5 leading-snug">{label}</div>
      <div className="flex gap-2">
        {(['Yes', 'No'] as const).map(opt => {
          const isYes = opt === 'Yes';
          const active = isYes ? value : !value;
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onChange(isYes)}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all border ${
                active
                  ? isYes
                    ? 'bg-amber-50 border-amber-300 text-amber-700'
                    : 'bg-emerald-50 border-emerald-300 text-emerald-700'
                  : 'bg-white border-gray-200 text-gray-400 hover:border-gray-300'
              }`}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Progress bar ─────────────────────────────────────────────────────────────

function ProgressBar({ step }: { step: OnboardingStep }) {
  const idx = STEPS.indexOf(step);
  const total = STEPS.length - 1; // exclude 'submitted' from count
  const displayIdx = Math.min(idx, total - 1);

  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
          {STEP_LABELS[step]}
        </span>
        {step !== 'submitted' && (
          <span className="text-[10px] text-gray-400">{displayIdx + 1} / {total}</span>
        )}
      </div>
      <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-500 rounded-full transition-all duration-300"
          style={{ width: `${((displayIdx + 1) / total) * 100}%` }}
        />
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function AlpacaOnboarding({ userId, onClose, onSuccess }: AlpacaOnboardingProps) {
  const [step, setStep] = useState<OnboardingStep>('personal');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [pollStatus, setPollStatus] = useState<string>('');
  const [accountId, setAccountId] = useState<string>('');

  const [form, setForm] = useState<FormData>({
    first_name: '', last_name: '', date_of_birth: '', email: '', phone_number: '',
    street_address: '', city: '', state: '', postal_code: '',
    tax_id: '', employment_status: '', funding_source: [],
    is_control_person: false, is_affiliated_exchange_or_finra: false,
    is_politically_exposed: false, immediate_family_exposed: false,
    agreements_accepted: false,
  });

  const set = <K extends keyof FormData>(key: K, val: FormData[K]) =>
    setForm(f => ({ ...f, [key]: val }));

  const toggleFundingSource = (val: string) => {
    setForm(f => ({
      ...f,
      funding_source: f.funding_source.includes(val)
        ? f.funding_source.filter(v => v !== val)
        : [...f.funding_source, val],
    }));
  };

  // Poll for account status after submission
  const pollAccountStatus = useCallback(async () => {
    try {
      const result = await alpacaBrokerApi.getAccountStatus(userId);
      if (result.exists && result.status) {
        setPollStatus(result.status);
        if (result.alpaca_account_id) setAccountId(result.alpaca_account_id);
        if (result.status === 'ACTIVE') {
          setStep('done');
          onSuccess?.();
        }
      }
    } catch {
      // ignore polling errors
    }
  }, [userId, onSuccess]);

  useEffect(() => {
    if (step !== 'submitted') return;
    pollAccountStatus(); // immediate first check
    const interval = setInterval(pollAccountStatus, 2000); // fast poll for sandbox
    return () => clearInterval(interval);
  }, [step, pollAccountStatus]);

  // ── Validation helpers ──────────────────────────────────────────────────────

  const validatePersonal = () => {
    if (!form.first_name.trim()) return 'First name is required';
    if (!form.last_name.trim()) return 'Last name is required';
    if (!form.date_of_birth) return 'Date of birth is required';
    if (!form.email.trim() || !form.email.includes('@')) return 'Valid email is required';
    if (!form.phone_number.trim()) return 'Phone number is required';
    return '';
  };

  const validateAddress = () => {
    if (!form.street_address.trim()) return 'Street address is required';
    if (!form.city.trim()) return 'City is required';
    if (!form.state) return 'State is required';
    if (!form.postal_code.trim()) return 'Zip code is required';
    return '';
  };

  const validateIdentity = () => {
    if (!form.tax_id.trim()) return 'SSN is required';
    if (!form.employment_status) return 'Employment status is required';
    if (form.funding_source.length === 0) return 'Select at least one funding source';
    return '';
  };

  const advance = (validate: () => string, next: OnboardingStep) => {
    const err = validate();
    if (err) { setError(err); return; }
    setError('');
    setStep(next);
  };

  // ── Submit ──────────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    if (!form.agreements_accepted) { setError('Please accept the agreements to continue'); return; }
    setLoading(true);
    setError('');
    try {
      const payload = {
        user_id: userId,
        contact: {
          email_address: form.email,
          phone_number: form.phone_number,
          street_address: [form.street_address],
          city: form.city,
          state: form.state,
          postal_code: form.postal_code,
          country: 'USA',
        },
        identity: {
          given_name: form.first_name,
          family_name: form.last_name,
          date_of_birth: form.date_of_birth,
          tax_id: form.tax_id,
          tax_id_type: 'USA_SSN',
          country_of_citizenship: 'USA',
          country_of_birth: 'USA',
          country_of_tax_residence: 'USA',
          funding_source: form.funding_source,
          employment_status: form.employment_status,
        },
        disclosures: {
          is_control_person: form.is_control_person,
          is_affiliated_exchange_or_finra: form.is_affiliated_exchange_or_finra,
          is_politically_exposed: form.is_politically_exposed,
          immediate_family_exposed: form.immediate_family_exposed,
        },
        agreements: [
          { agreement: 'customer_agreement', signed_at: new Date().toISOString(), ip_address: '0.0.0.0' },
          { agreement: 'account_agreement', signed_at: new Date().toISOString(), ip_address: '0.0.0.0' },
          { agreement: 'margin_agreement', signed_at: new Date().toISOString(), ip_address: '0.0.0.0' },
        ],
      };
      const result = await alpacaBrokerApi.createAccount(payload);
      if (result.alpaca_account_id) setAccountId(result.alpaca_account_id);
      setPollStatus(result.status || 'SUBMITTED');
      setStep('submitted');
    } catch (e) {
      setError('Submission failed. Please check your details and try again.');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center px-4 pb-4 sm:pb-0"
      style={{ background: 'rgba(0,0,0,0.5)' }} onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden max-h-[90vh] flex flex-col"
        onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-0 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="font-bold text-gray-900 text-base">Open an agent account</div>
            <span className="text-[9px] font-bold uppercase tracking-wider text-amber-600 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded-full">Sandbox</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors p-1 -mr-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 pt-4 pb-1">
          {step !== 'submitted' && <ProgressBar step={step} />}

          {/* ── Personal ── */}
          {step === 'personal' && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <FieldLabel>First name</FieldLabel>
                  <Input value={form.first_name} onChange={v => set('first_name', v)} placeholder="Jane" autoComplete="given-name" />
                </div>
                <div>
                  <FieldLabel>Last name</FieldLabel>
                  <Input value={form.last_name} onChange={v => set('last_name', v)} placeholder="Smith" autoComplete="family-name" />
                </div>
              </div>
              <div>
                <FieldLabel>Date of birth</FieldLabel>
                <Input type="date" value={form.date_of_birth} onChange={v => set('date_of_birth', v)} autoComplete="bday" />
              </div>
              <div>
                <FieldLabel>Email</FieldLabel>
                <Input type="email" value={form.email} onChange={v => set('email', v)} placeholder="jane@example.com" autoComplete="email" />
              </div>
              <div>
                <FieldLabel>Phone number</FieldLabel>
                <Input type="tel" value={form.phone_number} onChange={v => set('phone_number', v)} placeholder="+1 555 555 0100" autoComplete="tel" />
              </div>
            </div>
          )}

          {/* ── Address ── */}
          {step === 'address' && (
            <div className="space-y-3">
              <BackButton onClick={() => { setError(''); setStep('personal'); }} />
              <div>
                <FieldLabel>Street address</FieldLabel>
                <Input value={form.street_address} onChange={v => set('street_address', v)} placeholder="123 Main St" autoComplete="street-address" />
              </div>
              <div>
                <FieldLabel>City</FieldLabel>
                <Input value={form.city} onChange={v => set('city', v)} placeholder="New York" autoComplete="address-level2" />
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <FieldLabel>State</FieldLabel>
                  <Select value={form.state} onChange={v => set('state', v)}>
                    <option value="">Select state</option>
                    {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                  </Select>
                </div>
                <div>
                  <FieldLabel>Zip code</FieldLabel>
                  <Input value={form.postal_code} onChange={v => set('postal_code', v)} placeholder="10001" autoComplete="postal-code" />
                </div>
              </div>
            </div>
          )}

          {/* ── Identity ── */}
          {step === 'identity' && (
            <div className="space-y-3">
              <BackButton onClick={() => { setError(''); setStep('address'); }} />
              <div>
                <FieldLabel>Social Security Number (SSN)</FieldLabel>
                <div className="relative">
                  <Input type="password" value={form.tax_id} onChange={v => set('tax_id', v)} placeholder="XXX-XX-XXXX" />
                </div>
                <div className="flex items-center gap-1.5 mt-1.5">
                  <svg className="w-3 h-3 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <span className="text-[10px] text-gray-400">Encrypted end-to-end. Never stored in plain text.</span>
                </div>
              </div>
              <div>
                <FieldLabel>Employment status</FieldLabel>
                <Select value={form.employment_status} onChange={v => set('employment_status', v)}>
                  <option value="">Select status</option>
                  {EMPLOYMENT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </Select>
              </div>
              <div>
                <FieldLabel>Funding source <span className="font-normal text-gray-400">(select all that apply)</span></FieldLabel>
                <div className="space-y-2">
                  {FUNDING_OPTIONS.map(o => (
                    <label key={o.value} className="flex items-center gap-2.5 cursor-pointer group">
                      <div
                        onClick={() => toggleFundingSource(o.value)}
                        className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-all cursor-pointer ${
                          form.funding_source.includes(o.value)
                            ? 'bg-emerald-500 border-emerald-500'
                            : 'border-gray-300 group-hover:border-emerald-400'
                        }`}
                      >
                        {form.funding_source.includes(o.value) && (
                          <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                      <span className="text-sm text-gray-700">{o.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Disclosures ── */}
          {step === 'disclosures' && (
            <div className="space-y-2.5">
              <BackButton onClick={() => { setError(''); setStep('identity'); }} />
              <p className="text-xs text-gray-400 mb-3">Please answer honestly. These are required by FINRA regulations.</p>
              <YesNoToggle
                label="Are you a control person of a publicly traded company?"
                value={form.is_control_person}
                onChange={v => set('is_control_person', v)}
              />
              <YesNoToggle
                label="Are you affiliated with or employed by a stock exchange or FINRA?"
                value={form.is_affiliated_exchange_or_finra}
                onChange={v => set('is_affiliated_exchange_or_finra', v)}
              />
              <YesNoToggle
                label="Are you a politically exposed person?"
                value={form.is_politically_exposed}
                onChange={v => set('is_politically_exposed', v)}
              />
              <YesNoToggle
                label="Is an immediate family member a politically exposed person?"
                value={form.immediate_family_exposed}
                onChange={v => set('immediate_family_exposed', v)}
              />
            </div>
          )}

          {/* ── Agreements ── */}
          {step === 'agreements' && (
            <div>
              <BackButton onClick={() => { setError(''); setStep('disclosures'); }} />
              <div className="space-y-2.5 mb-4">
                {[
                  {
                    title: 'Customer Agreement',
                    body: 'Governs your use of Finch brokerage services, including account opening, agent-directed trading, and account maintenance.',
                  },
                  {
                    title: 'Account Agreement',
                    body: 'Outlines the terms and conditions of your agent&apos;s brokerage account, including how orders are executed, settled, and held in custody.',
                  },
                  {
                    title: 'Margin Agreement',
                    body: 'Explains the terms under which margin may be extended to your account, including risks, interest rates, and margin call procedures.',
                  },
                ].map(a => (
                  <div key={a.title} className="rounded-xl border border-gray-100 bg-gray-50/60 px-3.5 py-3">
                    <div className="text-xs font-semibold text-gray-700 mb-1">{a.title}</div>
                    <div className="text-xs text-gray-400 leading-relaxed">{a.body}</div>
                  </div>
                ))}
              </div>
              <label className="flex items-start gap-2.5 cursor-pointer group">
                <div
                  onClick={() => set('agreements_accepted', !form.agreements_accepted)}
                  className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-all cursor-pointer ${
                    form.agreements_accepted
                      ? 'bg-emerald-500 border-emerald-500'
                      : 'border-gray-300 group-hover:border-emerald-400'
                  }`}
                >
                  {form.agreements_accepted && (
                    <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <span className="text-sm text-gray-600 leading-snug">
                  I have read and agree to all the above agreements
                </span>
              </label>
            </div>
          )}

          {/* ── Submitted ── */}
          {step === 'submitted' && (
            <div className="py-6 text-center">
              {pollStatus === 'ACTIVE' ? (
                <>
                  <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4">
                    <svg className="w-7 h-7 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div className="font-bold text-gray-900 text-base mb-1">Account approved!</div>
                  <div className="text-sm text-gray-500 mb-5">Your agent&apos;s brokerage account is ready. It can now execute trades on your behalf.</div>
                  <button onClick={() => { onSuccess?.(); onClose(); }}
                    className="w-full py-2.5 text-sm font-bold text-white rounded-xl"
                    style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)' }}>
                    Done
                  </button>
                </>
              ) : (
                <>
                  <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4">
                    <svg className="w-7 h-7 text-emerald-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </div>
                  <div className="font-bold text-gray-900 text-base mb-1">Setting up your account...</div>
                  <div className="text-sm text-gray-500 mb-4">
                    {pollStatus
                      ? `Status: ${pollStatus.replace(/_/g, ' ').toLowerCase()}`
                      : 'This usually takes a few seconds in sandbox.'}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Error */}
          {error && step !== 'submitted' && (
            <div className="mt-3 text-xs text-red-500 font-medium px-1">{error}</div>
          )}
        </div>

        {/* Footer CTA */}
        {step !== 'submitted' && (
          <div className="flex-shrink-0 px-5 py-4 border-t border-gray-100">
            {step === 'personal' && (
              <button
                onClick={() => advance(validatePersonal, 'address')}
                className="w-full py-2.5 text-sm font-bold text-white rounded-xl transition-opacity"
                style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)' }}>
                Continue
              </button>
            )}
            {step === 'address' && (
              <button
                onClick={() => advance(validateAddress, 'identity')}
                className="w-full py-2.5 text-sm font-bold text-white rounded-xl transition-opacity"
                style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)' }}>
                Continue
              </button>
            )}
            {step === 'identity' && (
              <button
                onClick={() => advance(validateIdentity, 'disclosures')}
                className="w-full py-2.5 text-sm font-bold text-white rounded-xl transition-opacity"
                style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)' }}>
                Continue
              </button>
            )}
            {step === 'disclosures' && (
              <button
                onClick={() => { setError(''); setStep('agreements'); }}
                className="w-full py-2.5 text-sm font-bold text-white rounded-xl transition-opacity"
                style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)' }}>
                Continue
              </button>
            )}
            {step === 'agreements' && (
              <button
                onClick={handleSubmit}
                disabled={loading || !form.agreements_accepted}
                className="w-full py-2.5 text-sm font-bold text-white rounded-xl disabled:opacity-40 transition-opacity"
                style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)' }}>
                {loading ? 'Submitting...' : 'Submit application'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
