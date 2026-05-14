'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { creditsApi, type CreditBalance, type CreditTransaction } from '@/lib/api';

interface CreditsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const MAX_CREDIT_OPTIONS = [
  { label: '2,500 credits / month', value: '2500', price: 50, daily: 100 },
  { label: '4,000 credits / month', value: '4000', price: 80, daily: 100 },
  { label: '6,000 credits / month', value: '6000', price: 120, daily: 100 },
  { label: '8,500 credits / month', value: '8500', price: 170, daily: 100 },
];

export default function CreditsModal({ isOpen, onClose }: CreditsModalProps) {
  const { user } = useAuth();
  const [tab, setTab] = useState<'plans' | 'history'>('plans');
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [upgrading, setUpgrading] = useState(false);
  const [maxCredits, setMaxCredits] = useState('2500');
  const [promoCode, setPromoCode] = useState('');
  const [promoStatus, setPromoStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [redeeming, setRedeeming] = useState(false);

  useEffect(() => {
    if (!isOpen || !user) return;
    setLoading(true);
    if (tab === 'history') {
      creditsApi.getHistory(user.id, 50).then(d => setTransactions(d.transactions)).catch(() => {}).finally(() => setLoading(false));
    } else {
      creditsApi.getBalance(user.id).then(setBalance).catch(() => {}).finally(() => setLoading(false));
    }
  }, [isOpen, user, tab]);

  const handleUpgrade = async () => {
    if (!user) return;
    setUpgrading(true);
    try {
      const { url } = await creditsApi.createCheckout(user.id);
      window.location.href = url;
    } catch {
      setUpgrading(false);
    }
  };

  if (!isOpen) return null;

  const selectedMax = MAX_CREDIT_OPTIONS.find(o => o.value === maxCredits)!;

  const handleRedeem = async () => {
    if (!promoCode.trim()) return;
    setRedeeming(true);
    setPromoStatus(null);
    try {
      const res = await creditsApi.redeemCode(promoCode.trim());
      setPromoStatus({ type: 'success', msg: res.message });
      setPromoCode('');
      if (user) creditsApi.getBalance(user.id).then(setBalance).catch(() => {});
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Invalid code';
      setPromoStatus({ type: 'error', msg });
    } finally {
      setRedeeming(false);
    }
  };

  const F = ({ icon, text }: { icon: React.ReactNode; text: string }) => (
    <li className="flex items-center gap-2 text-[12.5px] text-gray-600 leading-tight">
      <span className="text-gray-400 shrink-0">{icon}</span>
      {text}
    </li>
  );

  const Clock = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
  const Sparkles = () => <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor"><path d="M6 0L7.2 4.8 12 6 7.2 7.2 6 12 4.8 7.2 0 6 4.8 4.8z" /><path d="M12 9l.7 2.3L15 12l-2.3.7L12 15l-.7-2.3L9 12l2.3-.7z" /></svg>;
  const Doc = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" /></svg>;
  const Bar = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>;
  const Flask = () => (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v0a6 6 0 01-5.84-7.38l1.26-4.96A2 2 0 017.11 8h9.78a2 2 0 011.94 1.41l1.26 4.96z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 3v4m8-4v4m-8 0h8" />
    </svg>
  );

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-6 pt-5 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Upgrade to Finch Pro</h2>
            {balance && (
              <p className="text-sm text-gray-500 mt-0.5">
                <span className="font-medium text-gray-700">{balance.credits.toLocaleString()}</span> credits remaining
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 -mr-1">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 flex gap-1 mt-2 mb-3">
          {(['plans', 'history'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                tab === t ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'plans' ? 'Plans' : 'Usage History'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="px-6 pb-5">
          {tab === 'plans' ? (
            <>
            <div className="grid grid-cols-3 gap-3">
              {/* ── Free ── */}
              <div className="rounded-xl border border-gray-200 p-4 flex flex-col">
                <div className="flex items-baseline gap-1 mb-0.5">
                  <span className="text-2xl font-bold text-gray-900">$0</span>
                  <span className="text-xs text-gray-400">/ month</span>
                </div>
                <p className="text-xs text-gray-500 mb-3">Get started for free</p>
                <button disabled className="w-full py-2 rounded-full text-xs font-medium bg-gray-100 text-gray-400 cursor-default mb-3">
                  Current Plan
                </button>
                <ul className="space-y-2.5">
                  <F icon={<Sparkles />} text="1,000 credits on signup" />
                  <F icon={<Clock />} text="100 credits daily refresh" />
                  <F icon={<Doc />} text="AI stock analysis" />
                  <F icon={<Bar />} text="Portfolio tracking" />
                </ul>
              </div>

              {/* ── Pro ── */}
              <div className="rounded-xl border-2 border-blue-500 shadow-[0_0_0_1px_rgba(59,130,246,0.2)] p-4 flex flex-col">
                <div className="flex items-baseline gap-1 mb-0.5">
                  <span className="text-2xl font-bold text-gray-900">$20</span>
                  <span className="text-xs text-gray-400">/ month</span>
                </div>
                <p className="text-xs text-gray-500 mb-3">For active investors</p>
                <button
                  onClick={handleUpgrade}
                  disabled={upgrading}
                  className="w-full py-2 rounded-full text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors mb-3"
                >
                  {upgrading ? 'Redirecting...' : 'Upgrade'}
                </button>
                <ul className="space-y-2.5">
                  <F icon={<Sparkles />} text="1,000 credits / month" />
                  <F icon={<Clock />} text="100 credits daily refresh" />
                  <F icon={<Doc />} text="In-depth research" />
                  <F icon={<Bar />} text="Advanced analysis tools" />
                  <F icon={<Flask />} text="Early access to features" />
                </ul>
              </div>

              {/* ── Max ── */}
              <div className="rounded-xl border border-gray-200 p-4 flex flex-col">
                <div className="flex items-baseline gap-1 mb-0.5">
                  <span className="text-2xl font-bold text-gray-900">${selectedMax.price}</span>
                  <span className="text-xs text-gray-400">/ month</span>
                </div>
                <p className="text-xs text-gray-500 mb-3">Customizable usage</p>
                <button
                  onClick={handleUpgrade}
                  disabled={upgrading}
                  className="w-full py-2 rounded-full text-xs font-medium bg-gray-900 text-white hover:bg-gray-800 transition-colors mb-2"
                >
                  {upgrading ? 'Redirecting...' : 'Upgrade'}
                </button>
                <div className="relative mb-3">
                  <select
                    value={maxCredits}
                    onChange={e => setMaxCredits(e.target.value)}
                    className="w-full appearance-none text-xs border border-gray-200 rounded-full px-3 py-1.5 text-gray-700 bg-gray-50 focus:outline-none focus:ring-1 focus:ring-gray-300 cursor-pointer pr-7"
                  >
                    {MAX_CREDIT_OPTIONS.map(o => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  <svg className="w-3.5 h-3.5 text-gray-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
                <ul className="space-y-2.5">
                  <F icon={<Sparkles />} text={`${parseInt(maxCredits).toLocaleString()} credits on activation`} />
                  <F icon={<Clock />} text={`${selectedMax.daily} credits daily refresh`} />
                  <F icon={<Doc />} text="Extended research & analysis" />
                  <F icon={<Bar />} text="Batch analysis tools" />
                  <F icon={<Flask />} text="Early access to features" />
                </ul>
              </div>
            </div>

            {/* Promo code */}
            <div className="mt-4 flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={promoCode}
                  onChange={e => { setPromoCode(e.target.value.toUpperCase()); setPromoStatus(null); }}
                  placeholder="Have a code?"
                  className="w-full text-sm border border-gray-200 rounded-full px-4 py-2 focus:outline-none focus:ring-1 focus:ring-blue-300 placeholder:text-gray-400"
                  onKeyDown={e => e.key === 'Enter' && handleRedeem()}
                />
              </div>
              <button
                onClick={handleRedeem}
                disabled={redeeming || !promoCode.trim()}
                className="px-4 py-2 text-sm font-medium rounded-full bg-gray-900 text-white hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 transition-colors"
              >
                {redeeming ? 'Applying...' : 'Apply'}
              </button>
            </div>
            {promoStatus && (
              <p className={`mt-2 text-xs ${promoStatus.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
                {promoStatus.msg}
              </p>
            )}
            </>
          ) : loading ? (
            <p className="text-center py-8 text-sm text-gray-400">Loading...</p>
          ) : transactions.length > 0 ? (
            <div className="max-h-[50vh] overflow-y-auto space-y-1">
              {transactions.map(tx => (
                <div key={tx.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-gray-900 truncate">{tx.description}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {tx.created_at ? new Date(tx.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                    </p>
                  </div>
                  <span className={`text-sm font-medium tabular-nums ml-3 ${tx.amount > 0 ? 'text-green-600' : 'text-gray-700'}`}>
                    {tx.amount > 0 ? '+' : ''}{tx.amount}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-sm text-gray-400">No transactions yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
