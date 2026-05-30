'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useCredits } from '@/contexts/CreditsContext';
import { creditsApi, type CreditTransaction } from '@/lib/api';

const TOPUP_OPTIONS = [
  { cents: 500, credits: 500, label: '$5', desc: '500 credits' },
  { cents: 1000, credits: 1_050, label: '$10', desc: '1,050 credits', bonus: '+5%' },
  { cents: 2500, credits: 2_750, label: '$25', desc: '2,750 credits', bonus: '+10%' },
] as const;

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function CreditsModal() {
  const { user } = useAuth();
  const {
    credits, plan, isPro, subscriptionStatus, cancelAtPeriodEnd, currentPeriodEnd,
    refresh, modalOpen, closeModal,
  } = useCredits();
  const [tab, setTab] = useState<'credits' | 'history'>('credits');
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [upgrading, setUpgrading] = useState(false);
  const [toppingUp, setToppingUp] = useState<number | null>(null);
  const [cancelStep, setCancelStep] = useState<'idle' | 'confirming' | 'cancelling'>('idle');
  const [cancelReason, setCancelReason] = useState<string | null>(null);
  const [cancelOtherText, setCancelOtherText] = useState('');
  const [resubscribing, setResubscribing] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [promoStatus, setPromoStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [redeeming, setRedeeming] = useState(false);

  useEffect(() => {
    if (!modalOpen) {
      setCancelStep('idle');
      setCancelReason(null);
      setCancelOtherText('');
      return;
    }
    if (tab === 'history' && user) {
      setLoadingHistory(true);
      creditsApi.getHistory(user.id, 50).then(d => setTransactions(d.transactions)).catch(() => {}).finally(() => setLoadingHistory(false));
    }
  }, [modalOpen, user, tab]);

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

  const handleTopup = async (cents: number) => {
    if (!user) return;
    setToppingUp(cents);
    try {
      const { url } = await creditsApi.createTopup(user.id, cents);
      window.location.href = url;
    } catch {
      setToppingUp(null);
    }
  };

  const handleCancel = async () => {
    if (!user) return;
    setCancelStep('cancelling');
    try {
      const reason = cancelReason === 'Other' && cancelOtherText.trim()
        ? `Other: ${cancelOtherText.trim()}`
        : cancelReason || undefined;
      await creditsApi.cancelSubscription(user.id, reason);
      await refresh();
      setCancelStep('idle');
      setCancelReason(null);
      setCancelOtherText('');
    } catch {
      setCancelStep('idle');
    }
  };

  const handleResubscribe = async () => {
    if (!user) return;
    setResubscribing(true);
    try {
      const res = await creditsApi.resubscribe(user.id);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
        return;
      }
      await refresh();
    } catch {}
    setResubscribing(false);
  };

  const handleRedeem = async () => {
    if (!promoCode.trim()) return;
    setRedeeming(true);
    setPromoStatus(null);
    try {
      const res = await creditsApi.redeemCode(promoCode.trim());
      setPromoStatus({ type: 'success', msg: res.message });
      setPromoCode('');
      await refresh();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Invalid code';
      setPromoStatus({ type: 'error', msg });
    } finally {
      setRedeeming(false);
    }
  };

  if (!modalOpen) return null;

  const isCancelling = cancelAtPeriodEnd && subscriptionStatus === 'active';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={closeModal}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-6 pt-5 pb-3 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Credits</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              <span className="font-semibold text-gray-900 text-xl tabular-nums">{credits.toLocaleString()}</span>
              <span className="ml-1">remaining</span>
              {isPro && <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-medium">Pro</span>}
            </p>
          </div>
          <button onClick={closeModal} className="text-gray-400 hover:text-gray-600 p-1 -mr-1">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 flex gap-1 mb-3">
          {(['credits', 'history'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                tab === t ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'credits' ? 'Add Credits' : 'History'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="px-6 pb-5">
          {tab === 'credits' ? (
            <>
              {/* Subscription card */}
              <div className="rounded-xl border border-gray-200 p-4">
                {cancelStep === 'confirming' ? (
                  <div>
                    <p className="text-sm font-medium text-gray-900">Why are you cancelling?</p>
                    <div className="mt-2 space-y-1.5">
                      {['Too expensive', 'Not using it enough', 'Missing features I need', 'Just trying it out', 'Other'].map(reason => (
                        <button
                          key={reason}
                          onClick={() => setCancelReason(reason)}
                          className={`w-full text-left px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                            cancelReason === reason
                              ? 'border-blue-300 bg-blue-50 text-blue-700'
                              : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                          }`}
                        >
                          {reason}
                        </button>
                      ))}
                      {cancelReason === 'Other' && (
                        <input
                          type="text"
                          autoFocus
                          value={cancelOtherText}
                          onChange={e => setCancelOtherText(e.target.value)}
                          placeholder="Tell us more..."
                          className="w-full mt-1 px-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-300"
                        />
                      )}
                    </div>
                    <p className="text-[11px] text-gray-400 mt-2">
                      Active until {currentPeriodEnd ? formatDate(currentPeriodEnd) : 'end of billing period'}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <button
                        onClick={() => { setCancelStep('idle'); setCancelReason(null); }}
                        className="flex-1 py-1.5 text-xs font-medium rounded-full border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
                      >
                        Keep Pro
                      </button>
                      <button
                        onClick={handleCancel}
                        disabled={!cancelReason || (cancelReason === 'Other' && !cancelOtherText.trim())}
                        className="flex-1 py-1.5 text-xs font-medium rounded-full border border-red-200 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-40"
                      >
                        Cancel Subscription
                      </button>
                    </div>
                  </div>
                ) : cancelStep === 'cancelling' ? (
                  <div className="flex items-center justify-center py-2">
                    <p className="text-sm text-gray-500">Cancelling...</p>
                  </div>
                ) : isCancelling ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900">Finch Pro</p>
                        <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">Cancelling</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Active until {currentPeriodEnd ? formatDate(currentPeriodEnd) : '...'}
                      </p>
                    </div>
                    <button
                      onClick={handleResubscribe}
                      disabled={resubscribing}
                      className="shrink-0 ml-3 px-3 py-1.5 text-xs font-medium rounded-full bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
                    >
                      {resubscribing ? 'Loading...' : 'Resubscribe'}
                    </button>
                  </div>
                ) : isPro ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900">Finch Pro</p>
                        <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-medium">Active</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {currentPeriodEnd ? `Renews ${formatDate(currentPeriodEnd)}` : '1,000 bonus credits/mo + 100 daily refresh'}
                      </p>
                    </div>
                    {plan !== 'admin' && (
                      <button
                        onClick={() => setCancelStep('confirming')}
                        className="shrink-0 ml-3 px-3 py-1.5 text-xs font-medium rounded-full border border-gray-300 text-gray-500 hover:text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                ) : (
                  <div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">Finch Pro — $20/mo</p>
                      </div>
                      <button
                        onClick={handleUpgrade}
                        disabled={upgrading}
                        className="shrink-0 ml-3 px-3 py-1.5 text-xs font-medium rounded-full bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
                      >
                        {upgrading ? 'Loading...' : 'Upgrade'}
                      </button>
                    </div>
                    <ul className="mt-3 space-y-1.5 text-xs text-gray-500">
                      <li className="flex items-center gap-1.5"><span className="text-blue-500">+</span> 1,000 bonus credits on signup</li>
                      <li className="flex items-center gap-1.5"><span className="text-blue-500">+</span> 100 credits daily refresh</li>
                      <li className="flex items-center gap-1.5"><span className="text-blue-500">+</span> In-depth research reports</li>
                      <li className="flex items-center gap-1.5"><span className="text-blue-500">+</span> Advanced analysis tools</li>
                      <li className="flex items-center gap-1.5"><span className="text-blue-500">+</span> Early access to new features</li>
                    </ul>
                  </div>
                )}
              </div>

              {/* Top-up buttons */}
              <div className="mt-4 space-y-2">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Top up</p>
                <div className="grid grid-cols-3 gap-2">
                  {TOPUP_OPTIONS.map(opt => (
                    <button
                      key={opt.cents}
                      onClick={() => handleTopup(opt.cents)}
                      disabled={toppingUp !== null}
                      className="relative flex flex-col items-center py-3 px-2 rounded-xl border border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 transition-colors disabled:opacity-50"
                    >
                      {'bonus' in opt && (
                        <span className="absolute -top-2 right-1 text-[10px] font-semibold bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">{opt.bonus}</span>
                      )}
                      <span className="text-lg font-bold text-gray-900">{opt.label}</span>
                      <span className="text-xs text-gray-500 mt-0.5">
                        {toppingUp === opt.cents ? 'Redirecting...' : opt.desc}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Promo code */}
              <div className="mt-4 flex items-center gap-2">
                <input
                  type="text"
                  value={promoCode}
                  onChange={e => { setPromoCode(e.target.value.toUpperCase()); setPromoStatus(null); }}
                  placeholder="Promo code"
                  className="flex-1 text-sm border border-gray-200 rounded-full px-4 py-2 focus:outline-none focus:ring-1 focus:ring-blue-300 placeholder:text-gray-400"
                  onKeyDown={e => e.key === 'Enter' && handleRedeem()}
                />
                <button
                  onClick={handleRedeem}
                  disabled={redeeming || !promoCode.trim()}
                  className="px-4 py-2 text-sm font-medium rounded-full bg-gray-900 text-white hover:bg-gray-800 disabled:bg-gray-200 disabled:text-gray-400 transition-colors"
                >
                  {redeeming ? '...' : 'Apply'}
                </button>
              </div>
              {promoStatus && (
                <p className={`mt-2 text-xs ${promoStatus.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
                  {promoStatus.msg}
                </p>
              )}
            </>
          ) : loadingHistory ? (
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
