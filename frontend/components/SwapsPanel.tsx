'use client';

import React, { useState, useEffect } from 'react';
import type { SwapData, BrokerageAccount, SubstituteCandidate } from '@/lib/types';
import PriceRangeChart from '@/components/ui/PriceRangeChart';
import { snaptradeApi, alpacaBrokerApi } from '@/lib/api';
import AlpacaOnboarding from '@/components/AlpacaOnboarding';

export interface StoredSwap extends SwapData {
  id: string;
  chatId: string;
  receivedAt: string;
  status: 'pending' | 'approved' | 'rejected' | 'dismissed';
  reminderSet?: boolean;
  selected_buy_symbol?: string; // which substitute the user picked (defaults to buy_symbol)
}

interface SwapsPanelProps {
  swaps: StoredSwap[];
  userId: string;
  onApprove: (swap: StoredSwap) => void;
  onReject: (swap: StoredSwap) => void;
  onDismiss: (swap: StoredSwap) => void;
  onSelectCandidate: (swap: StoredSwap, buySymbol: string) => void;
  onChatAboutSwap?: (message: string) => void;
}

// ─── Modals ───────────────────────────────────────────────────────────────────

function ReminderModal({ swap, onClose, userId, onSuccess }: {
  swap: StoredSwap; onClose: () => void; userId: string; onSuccess: () => void;
}) {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const remindDate = new Date();
  remindDate.setDate(remindDate.getDate() + 61);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId, symbol_sold: swap.sell_symbol, symbol_bought: swap.buy_symbol,
          loss_amount: Math.abs(swap.sell_loss), sale_date: new Date().toISOString().split('T')[0],
        }),
      });
      setSubmitted(true);
      onSuccess();
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
        {submitted ? (
          <div className="text-center py-4">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            </div>
            <div className="font-semibold text-gray-900 mb-1">Reminder set!</div>
            <div className="text-sm text-gray-500">
              We&apos;ll email you on <strong>{remindDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}</strong>{' '}
              when you can safely repurchase {swap.sell_symbol}.
            </div>
            <button onClick={onClose} className="mt-4 text-sm text-gray-400 hover:text-gray-600">Close</button>
          </div>
        ) : (
          <>
            <div className="font-semibold text-gray-900 mb-0.5">61-day repurchase reminder</div>
            <div className="text-sm text-gray-500 mb-5">
              We&apos;ll email you on{' '}
              <strong>{remindDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</strong>{' '}
              when the wash sale window clears for <strong>{swap.sell_symbol}</strong>.
            </div>
            <div className="flex gap-2">
              <button onClick={onClose} className="flex-1 px-3 py-2.5 border border-gray-200 text-gray-600 text-sm rounded-xl hover:bg-gray-50">Cancel</button>
              <button onClick={handleSubmit} disabled={loading}
                className="flex-1 px-3 py-2.5 bg-emerald-600 text-white text-sm rounded-xl hover:bg-emerald-700 disabled:opacity-50 font-medium">
                {loading ? 'Setting...' : 'Set reminder'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

type ExecuteStep = 'choose' | 'manual' | 'finch_onboarding' | 'snaptrade_confirm' | 'snaptrade_executing' | 'snaptrade_done';

const TRADEABLE_BROKERS = ['ALPACA', 'INTERACTIVE_BROKERS', 'QUESTRADE', 'TRADIER'];

// Best available deep links per broker.
// Robinhood & Fidelity accept symbol/qty params. Others go to their trade/portfolio page.
const BROKER_TRADE_URLS: Record<string, (symbol: string, qty?: number) => string> = {
  ROBINHOOD:             (s)    => `https://robinhood.com/stocks/${s}`,
  RH:                    (s)    => `https://robinhood.com/stocks/${s}`,
  FIDELITY:              (s, q) => `https://digital.fidelity.com/ftgw/digital/trade-equity/index.cvs?action=sell&SYMBOL=${s}${q ? `&QUANTITY=${q}` : ''}`,
  FIDELITY_INVESTMENTS:  (s, q) => `https://digital.fidelity.com/ftgw/digital/trade-equity/index.cvs?action=sell&SYMBOL=${s}${q ? `&QUANTITY=${q}` : ''}`,
  SCHWAB:                ()     => 'https://client.schwab.com/app/trade/tradingticket/#/',
  CHARLES_SCHWAB:        ()     => 'https://client.schwab.com/app/trade/tradingticket/#/',
  ETRADE:                ()     => 'https://us.etrade.com/e/t/invest/tradingcenter',
  E_TRADE:               ()     => 'https://us.etrade.com/e/t/invest/tradingcenter',
  INTERACTIVE_BROKERS:   ()     => 'https://client2.interactivebrokers.com/portal/#/',
  IB:                    ()     => 'https://client2.interactivebrokers.com/portal/#/',
  IBKR:                  ()     => 'https://client2.interactivebrokers.com/portal/#/',
  ALPACA:                ()     => 'https://app.alpaca.markets/live/dashboard/overview',
  TRADIER:               ()     => 'https://dash.tradier.com/',
  QUESTRADE:             ()     => 'https://www.questrade.com/trading/',
  TD:                    (s)    => `https://invest.ameritrade.com/grid/p/site#r=jPage/cgi-bin/apps/u/TradeOrder&symbol=${s}`,
  TD_AMERITRADE:         (s)    => `https://invest.ameritrade.com/grid/p/site#r=jPage/cgi-bin/apps/u/TradeOrder&symbol=${s}`,
  WEBULL:                ()     => 'https://app.webull.com/trade',
  MOOMOO:                ()     => 'https://www.moomoo.com/us/trade',
  WEALTHSIMPLE:          ()     => 'https://my.wealthsimple.com/',
};

function getBrokerUrl(acct: BrokerageAccount, symbol: string, qty?: number): string | null {
  // Try broker_id first (SnapTrade slugs), then derived from broker_name
  const byId = (acct.broker_id || '').toUpperCase().replace(/[\s-]/g, '_');
  const byName = (acct.broker_name || '').toUpperCase().replace(/[\s-]/g, '_').replace(/[^A-Z_]/g, '');
  const fn = BROKER_TRADE_URLS[byId] || BROKER_TRADE_URLS[byName];
  // Also try partial name matches (e.g. broker_name="Robinhood Roth IRA" → "ROBINHOOD")
  if (!fn) {
    for (const key of Object.keys(BROKER_TRADE_URLS)) {
      if (byName.startsWith(key) || byId.startsWith(key)) {
        return BROKER_TRADE_URLS[key](symbol, qty);
      }
    }
  }
  return fn ? fn(symbol, qty) : null;
}

function AlpacaSignupModal({ onClose, userId, approvedCount, approvedSavings, swap, onManualDone }: {
  onClose: () => void;
  userId: string;
  approvedCount?: number;
  approvedSavings?: number;
  swap?: StoredSwap;
  onManualDone?: () => void;
}) {
  const [step, setStep] = useState<ExecuteStep>('choose');
  const [tradeableAccounts, setTradeableAccounts] = useState<BrokerageAccount[]>([]);
  const [allAccounts, setAllAccounts] = useState<BrokerageAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<BrokerageAccount | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [alpacaBrokerAccountId, setAlpacaBrokerAccountId] = useState<string | null>(null);
  const [isUsingBrokerAccount, setIsUsingBrokerAccount] = useState(false);

  // Approximate current position value from loss + loss %
  const approxValue = swap
    ? Math.round(Math.abs(swap.sell_loss) * (100 / Math.abs(swap.sell_loss_pct) - 1))
    : 0;

  // Fetch SnapTrade accounts + Alpaca Broker account on mount
  useEffect(() => {
    let cancelled = false;
    setAccountsLoading(true);
    Promise.all([
      snaptradeApi.getAccounts(userId).then(res => {
        if (cancelled) return;
        const accounts = res.accounts || [];
        setAllAccounts(accounts);
        setTradeableAccounts(accounts.filter(a =>
          TRADEABLE_BROKERS.includes(a.broker_id?.toUpperCase?.() ?? '')
        ));
      }).catch(() => {}),
      alpacaBrokerApi.getAccountStatus(userId).then(res => {
        if (cancelled) return;
        if (res.exists && res.status === 'ACTIVE' && res.alpaca_account_id) {
          setAlpacaBrokerAccountId(res.alpaca_account_id);
        }
      }).catch(() => {}),
    ]).finally(() => { if (!cancelled) setAccountsLoading(false); });
    return () => { cancelled = true; };
  }, [userId]);

  const handleSnaptradeExecute = async () => {
    if (!swap) return;
    setStep('snaptrade_executing');
    setError('');
    try {
      if (isUsingBrokerAccount && alpacaBrokerAccountId) {
        await alpacaBrokerApi.executeBrokerSwap({
          user_id: userId,
          alpaca_account_id: alpacaBrokerAccountId,
          sell_symbol: swap.sell_symbol,
          sell_qty: swap.sell_qty,
          buy_symbol: swap.buy_symbol,
          buy_notional: approxValue,
        });
      } else if (selectedAccount) {
        await alpacaBrokerApi.executeSwap({
          user_id: userId,
          account_id: selectedAccount.account_id,
          sell_symbol: swap.sell_symbol,
          sell_qty: swap.sell_qty,
          buy_symbol: swap.buy_symbol,
          buy_notional: approxValue,
        });
      } else {
        return;
      }
      setStep('snaptrade_done');
    } catch {
      setError('Trade execution failed. Please try again or execute manually.');
      setStep('snaptrade_confirm');
    }
  };

  // If finch_onboarding, render that component directly
  if (step === 'finch_onboarding') {
    return (
      <AlpacaOnboarding
        userId={userId}
        onClose={onClose}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center px-4 pb-4 sm:pb-0"
      style={{ background: 'rgba(0,0,0,0.5)' }} onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
        onClick={e => e.stopPropagation()}>

        {/* ── Choose path ── */}
        {step === 'choose' && (
          <div className="px-6 pt-6 pb-6">
            <div className="font-bold text-gray-900 text-base mb-1">How would you like to execute?</div>
            <div className="text-sm text-gray-400 mb-5">
              {swap
                ? `${swap.sell_symbol} → ${swap.buy_symbol} · ~$${swap.estimated_savings.toLocaleString()} savings`
                : approvedCount && approvedCount > 0
                  ? `${approvedCount} approved swap${approvedCount > 1 ? 's' : ''} · ~$${(approvedSavings || 0).toLocaleString()} savings`
                  : 'Choose how to execute your approved swaps'}
            </div>

            <div className="space-y-2">
              {/* ── Finch agent account (Alpaca Broker API) ── */}
              {!accountsLoading && alpacaBrokerAccountId && (
                <button
                  onClick={() => { setIsUsingBrokerAccount(true); setStep('snaptrade_confirm'); }}
                  className="w-full text-left rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 hover:bg-emerald-50 transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
                      <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-emerald-800 text-sm">Try in sandbox</span>
                        <span className="text-[8px] font-bold uppercase tracking-wider text-amber-600 bg-amber-50 border border-amber-200 px-1 py-px rounded">Paper</span>
                      </div>
                      <div className="text-xs text-emerald-600/70 mt-0.5">Model this trade risk-free · No real money</div>
                    </div>
                  </div>
                </button>
              )}

              {/* ── Connected tradeable accounts (SnapTrade) ── */}
              {!accountsLoading && tradeableAccounts.map(acct => (
                <button
                  key={acct.account_id}
                  onClick={() => { setSelectedAccount(acct); setIsUsingBrokerAccount(false); setStep('snaptrade_confirm'); }}
                  className="w-full text-left rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 hover:bg-emerald-50 transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
                      <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </div>
                    <div>
                      <div className="font-semibold text-emerald-800 text-sm">
                        Execute via {acct.broker_name || acct.broker_id}
                      </div>
                      <div className="text-xs text-emerald-600/70 mt-0.5">
                        {acct.name || acct.number} · Commission-free · Executes in seconds
                      </div>
                    </div>
                  </div>
                </button>
              ))}

              {accountsLoading && (
                <div className="rounded-xl border border-gray-100 p-4 flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-gray-200 border-t-emerald-500 rounded-full animate-spin flex-shrink-0" />
                  <span className="text-sm text-gray-400">Checking connected accounts...</span>
                </div>
              )}

              {/* ── Open agent account (if none exists) ── */}
              {!alpacaBrokerAccountId && (
                <button onClick={() => setStep('finch_onboarding')}
                  className="w-full text-left rounded-xl border border-gray-200 bg-white p-4 hover:border-gray-300 hover:bg-gray-50 transition-all group">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 group-hover:bg-gray-200 transition-colors">
                      <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082" />
                      </svg>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-800 text-sm">Open an agent account</span>
                        <span className="text-[8px] font-bold uppercase tracking-wider text-amber-600 bg-amber-50 border border-amber-200 px-1 py-px rounded">Sandbox</span>
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5">Test account powered by Alpaca · No real money</div>
                    </div>
                  </div>
                </button>
              )}

              {/* ── Do it myself ── */}
              <button onClick={() => setStep('manual')}
                className="w-full text-left rounded-xl border border-gray-200 p-4 hover:border-gray-300 hover:bg-gray-50 transition-all group">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 group-hover:bg-gray-200 transition-colors">
                    <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <div>
                    <div className="font-semibold text-gray-800 text-sm">Do it myself</div>
                    <div className="text-xs text-gray-400 mt-0.5">Step-by-step instructions · Ready now</div>
                  </div>
                </div>
              </button>
            </div>

            <button onClick={onClose} className="w-full text-center text-xs text-gray-400 hover:text-gray-600 mt-4">
              Not now
            </button>
          </div>
        )}

        {/* ── Confirm (SnapTrade or Alpaca Broker) ── */}
        {step === 'snaptrade_confirm' && swap && (isUsingBrokerAccount ? !!alpacaBrokerAccountId : !!selectedAccount) && (
          <div>
            <div className="px-5 pt-5 pb-4">
              <button onClick={() => setStep('choose')}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 mb-4">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </button>

              <div className="font-bold text-gray-900 text-base mb-0.5">Confirm trade</div>
              <div className="text-xs text-gray-400 mb-4">
                Via <span className="font-semibold text-gray-600">
                  {isUsingBrokerAccount ? 'Finch Agent Account (Alpaca)' : (selectedAccount?.broker_name || selectedAccount?.broker_id || '')}
                </span>
                {!isUsingBrokerAccount && selectedAccount?.name ? ` · ${selectedAccount.name}` : ''}
              </div>

              <div className="space-y-2.5 mb-4">
                <div className="rounded-xl border border-red-100 bg-red-50/40 p-3.5">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-4 h-4 rounded-full bg-red-100 border border-red-200 flex items-center justify-center flex-shrink-0">
                      <span className="text-[9px] font-bold text-red-600">S</span>
                    </div>
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wide">Sell</span>
                  </div>
                  <div className="text-sm font-semibold text-gray-900">
                    {swap.sell_qty} shares of <span className="text-red-600">{swap.sell_symbol}</span>
                  </div>
                  {approxValue > 0 && (
                    <div className="text-xs text-gray-400 mt-0.5">~${approxValue.toLocaleString()} proceeds</div>
                  )}
                </div>

                <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-3.5">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-4 h-4 rounded-full bg-emerald-100 border border-emerald-200 flex items-center justify-center flex-shrink-0">
                      <span className="text-[9px] font-bold text-emerald-600">B</span>
                    </div>
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wide">Buy</span>
                  </div>
                  <div className="text-sm font-semibold text-gray-900">
                    ~${approxValue.toLocaleString()} of <span className="text-emerald-600">{swap.buy_symbol}</span>
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">Market order</div>
                </div>
              </div>

              {error && <div className="text-xs text-red-500 font-medium mb-3">{error}</div>}
            </div>

            <div className="px-5 pb-5 border-t border-gray-100 pt-4">
              <button
                onClick={handleSnaptradeExecute}
                disabled={loading}
                className="w-full py-2.5 text-sm font-bold text-white rounded-xl disabled:opacity-40"
                style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)', boxShadow: '0 2px 8px rgba(16,185,129,0.25)' }}>
                Execute trades
              </button>
            </div>
          </div>
        )}

        {/* ── SnapTrade executing ── */}
        {step === 'snaptrade_executing' && (
          <div className="px-6 py-10 text-center">
            <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4">
              <svg className="w-7 h-7 text-emerald-400 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
            <div className="font-semibold text-gray-900 mb-1">Placing orders...</div>
            <div className="text-sm text-gray-400">This usually takes a few seconds.</div>
          </div>
        )}

        {/* ── SnapTrade done ── */}
        {step === 'snaptrade_done' && swap && (
          <div className="px-6 py-8 text-center">
            <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4">
              <svg className="w-7 h-7 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div className="font-bold text-gray-900 text-base mb-2">Orders placed!</div>
            <div className="text-sm text-gray-500 mb-1">Sell order placed.</div>
            <div className="text-sm text-gray-500 mb-6">Buy order placed.</div>
            <button
              onClick={() => { onManualDone?.(); onClose(); }}
              className="w-full py-2.5 text-sm font-bold text-white rounded-xl mb-2"
              style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)', boxShadow: '0 2px 8px rgba(16,185,129,0.25)' }}>
              Set 61-day reminder
            </button>
            <button onClick={onClose} className="w-full text-xs text-gray-400 hover:text-gray-600 py-1">
              Done (no reminder)
            </button>
          </div>
        )}

        {/* ── Manual execution ── */}
        {step === 'manual' && swap && (
          <div>
            <div className="px-5 pt-5 pb-4">
              <button onClick={() => setStep('choose')}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 mb-4">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </button>

              <div className="font-bold text-gray-900 text-base mb-0.5">Execute this trade yourself</div>
              <div className="text-xs text-gray-400 mb-4">Do these steps in your brokerage account today</div>

              {/* Go to broker — shown first so it's the CTA */}
              {allAccounts.length > 0 && (
                <div className="mb-4">
                  <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">Open your broker</div>
                  <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
                    {allAccounts.map(acct => {
                      const url = getBrokerUrl(acct, swap.sell_symbol, swap.sell_qty);
                      return (
                        <a
                          key={acct.account_id}
                          href={url || undefined}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => !url && e.preventDefault()}
                          className={`flex items-center justify-between px-3.5 py-3 rounded-xl border transition-all ${url ? 'border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/30 cursor-pointer' : 'border-gray-100 opacity-40 cursor-default'}`}
                        >
                          <div>
                            <div className="text-sm font-semibold text-gray-800">{acct.broker_name || acct.broker_id}</div>
                            {acct.name && <div className="text-xs text-gray-400">{acct.name}</div>}
                          </div>
                          {url && (
                            <div className="flex items-center gap-1 text-xs font-semibold text-emerald-600 flex-shrink-0">
                              Open
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </div>
                          )}
                        </a>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Order summary — copyable */}
              <div className="rounded-xl border border-gray-100 bg-gray-50/60 p-3.5 mb-3">
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Order details</span>
                  <button
                    onClick={() => {
                      const text = `Sell ${swap.sell_qty} shares of ${swap.sell_symbol}${approxValue > 0 ? ` (~$${approxValue.toLocaleString()} proceeds)` : ''}\nBuy ${swap.buy_symbol} for ~$${approxValue > 0 ? approxValue.toLocaleString() : '?'}\n⚠ Do NOT buy ${swap.sell_symbol} back for 61 days (wash sale rule)`;
                      navigator.clipboard.writeText(text).then(() => {
                        setCopied(true);
                        setTimeout(() => setCopied(false), 2000);
                      });
                    }}
                    className="flex items-center gap-1 text-[10px] font-semibold text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {copied ? (
                      <><svg className="w-3 h-3 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg><span className="text-emerald-500">Copied</span></>
                    ) : (
                      <><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>Copy</>
                    )}
                  </button>
                </div>
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <span className="text-[10px] font-bold text-red-500 bg-red-50 border border-red-100 px-1.5 py-0.5 rounded-md flex-shrink-0 mt-0.5">SELL</span>
                    <div>
                      <span className="text-sm font-semibold text-gray-900">{swap.sell_qty} shares of {swap.sell_symbol}</span>
                      {approxValue > 0 && <span className="text-xs text-gray-400 ml-1.5">~${approxValue.toLocaleString()} proceeds</span>}
                      <div className="text-xs text-gray-400">Locks in ${Math.abs(swap.sell_loss).toLocaleString()} capital loss</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded-md flex-shrink-0 mt-0.5">BUY</span>
                    <div>
                      <span className="text-sm font-semibold text-gray-900">{swap.buy_symbol}</span>
                      {approxValue > 0 && <span className="text-xs text-gray-400 ml-1.5">~${approxValue.toLocaleString()} · same-day market order</span>}
                      <div className="text-xs text-gray-400">{swap.buy_reason}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Wash sale warning */}
              <div className="rounded-xl border border-amber-100 bg-amber-50/40 px-3.5 py-3 flex items-start gap-2.5">
                <svg className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div className="text-xs text-gray-600 leading-relaxed">
                  Do <strong>not</strong> repurchase <strong>{swap.sell_symbol}</strong> for <strong>61 days</strong> — the IRS wash sale rule will disallow your loss deduction. Also disable DRIP for {swap.sell_symbol}.
                </div>
              </div>
            </div>

            <div className="px-5 pb-5 flex flex-col gap-2 border-t border-gray-100 pt-4">
              <button
                onClick={() => { onManualDone?.(); onClose(); }}
                className="w-full py-2.5 text-sm font-bold text-white rounded-xl"
                style={{ background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)', boxShadow: '0 2px 8px rgba(16,185,129,0.25)' }}>
                Done — set 61-day reminder
              </button>
              <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600 text-center">
                Close (no reminder)
              </button>
            </div>
          </div>
        )}

        {/* ── No swap provided for manual path ── */}
        {step === 'manual' && !swap && (
          <div className="px-6 py-8 text-center">
            <div className="text-sm text-gray-500 mb-4">
              Open the individual swap to see step-by-step instructions for that trade.
            </div>
            <button onClick={() => setStep('choose')} className="text-sm text-gray-500 border border-gray-200 px-4 py-2 rounded-xl hover:bg-gray-50">
              Back
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Detail view (full-screen overlay) ───────────────────────────────────────

function SwapDetailView({
  swap, userId, onBack, onApprove, onReject, onReminderSet, onSelectCandidate, onChatAboutSwap,
}: {
  swap: StoredSwap; userId: string;
  onBack: () => void;
  onApprove: (s: StoredSwap) => void;
  onReject: (s: StoredSwap) => void;
  onReminderSet: (s: StoredSwap) => void;
  onSelectCandidate: (s: StoredSwap, buySymbol: string) => void;
  onChatAboutSwap?: (message: string) => void;
}) {
  const [showReminder, setShowReminder] = useState(false);
  const [showAlpaca, setShowAlpaca] = useState(false);
  const [chatMessage, setChatMessage] = useState('');

  const isPending = swap.status === 'pending';
  const isApproved = swap.status === 'approved';
  const isRejected = swap.status === 'rejected';
  const hasReminder = swap.reminderSet;

  // Build candidate list — use substitute_candidates if available, else fall back to the single buy
  const candidates: SubstituteCandidate[] = swap.substitute_candidates?.length
    ? swap.substitute_candidates
    : [{ symbol: swap.buy_symbol, correlation: swap.correlation, quality: '', reason: swap.buy_reason, is_sector_peer: false }];

  // The active buy symbol: persisted on StoredSwap, defaults to buy_symbol (primary pick)
  const activeBuySymbol = swap.selected_buy_symbol || swap.buy_symbol;
  const selectedIdx = Math.max(0, candidates.findIndex(c => c.symbol === activeBuySymbol));
  const selected = candidates[selectedIdx] ?? candidates[0];

  const chartSeries = [
    { symbol: swap.sell_symbol, color: '#ef4444' },
    { symbol: selected.symbol, color: '#10b981' },
  ];

  const handleChatSubmit = () => {
    const msg = chatMessage.trim();
    if (!msg || !onChatAboutSwap) return;
    onChatAboutSwap(msg);
    setChatMessage('');
  };

  return (
    <div className="absolute inset-0 bg-white z-10 flex flex-col overflow-hidden">
      {/* Back nav */}
      <div className="flex-shrink-0 flex items-center gap-2 px-4 pt-4 pb-2 border-b border-gray-100">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Opportunities
        </button>
        {isApproved && (
          <span className="ml-auto text-xs text-emerald-700 font-semibold bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
            {hasReminder ? '✓ Reminder set' : '✓ Approved'}
          </span>
        )}
        {isRejected && (
          <span className="ml-auto text-xs text-gray-400 font-semibold bg-gray-50 border border-gray-200 px-2 py-0.5 rounded-full">Skipped</span>
        )}
      </div>

      {/* Chart — compact, not scrollable */}
      <div className="flex-shrink-0 px-4 pt-2 pb-0 bg-white">
        <PriceRangeChart series={chartSeries} defaultDays={365} height={150} />
      </div>

      {/* Drawer — scrollable content below the graph */}
      <div className="flex-1 overflow-y-auto bg-gray-50/30 min-h-0">
        <div className="px-4 pt-3 pb-0 space-y-2">

          {/* Key stats — compact single row */}
          <div className="grid grid-cols-3 divide-x divide-gray-100 border border-gray-100 rounded-xl overflow-hidden bg-white">
            <div className="px-3 py-2">
              <div className="text-[9px] font-bold text-gray-400 tracking-widest uppercase mb-0.5">Loss</div>
              <div className="text-sm font-bold text-red-500">${Math.abs(swap.sell_loss).toLocaleString()}</div>
              <div className="text-[11px] text-red-400">{swap.sell_loss_pct.toFixed(1)}% · {swap.sell_qty} sh</div>
            </div>
            <div className="px-3 py-2">
              <div className="text-[9px] font-bold text-gray-400 tracking-widest uppercase mb-0.5">Tax Savings</div>
              <div className="text-sm font-bold text-emerald-600">${swap.estimated_savings.toLocaleString()}</div>
              <div className="text-[11px] text-gray-400">buy {selected.symbol}</div>
            </div>
            <div className="px-3 py-2">
              <div className="text-[9px] font-bold text-gray-400 tracking-widest uppercase mb-0.5">Correlation</div>
              <div className="text-sm font-bold text-gray-700">{(selected.correlation * 100).toFixed(0)}%</div>
              <div className="text-[11px] text-gray-400">{selected.quality || '1-yr R'}</div>
            </div>
          </div>

          {/* Substitute candidates */}
          {candidates.length > 1 && (
            <div className="rounded-xl border border-gray-100 bg-white px-3 py-2.5">
              <div className="text-[9px] font-bold text-gray-400 tracking-widest uppercase mb-2">Substitute options</div>
              <div className="flex gap-1.5 flex-wrap">
                {candidates.map((c, i) => (
                  <button
                    key={c.symbol}
                    onClick={() => onSelectCandidate(swap, c.symbol)}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all ${
                      i === selectedIdx
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                        : 'bg-gray-50 border-gray-200 text-gray-500 hover:border-gray-300'
                    }`}
                  >
                    {c.symbol}
                    <span className={`text-[10px] ${i === selectedIdx ? 'text-emerald-500' : 'text-gray-400'}`}>
                      {(c.correlation * 100).toFixed(0)}%
                    </span>
                    {c.is_sector_peer && (
                      <span className={`text-[9px] ${i === selectedIdx ? 'text-emerald-400' : 'text-gray-300'}`}>★</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Why this substitute */}
          <div className="rounded-xl border border-gray-100 bg-white px-3 py-2">
            <div className="text-[9px] font-bold text-gray-400 tracking-widest uppercase mb-0.5">Why {selected.symbol}</div>
            <div className="text-sm text-gray-600 leading-relaxed">{selected.reason || swap.buy_reason}</div>
          </div>

        </div>
      </div>

      {/* Footer — chat input + compact actions */}
      <div className="flex-shrink-0 px-4 pt-2 pb-4 border-t border-gray-100 bg-white">

        {/* Chat input — primary focus */}
        {onChatAboutSwap && (
          <div className="flex gap-2 mb-3">
            <input
              value={chatMessage}
              onChange={e => setChatMessage(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleChatSubmit(); }}
              placeholder="Ask a question about this swap…"
              className="flex-1 px-3.5 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-300 placeholder-gray-300 bg-white shadow-sm"
            />
            <button
              onClick={handleChatSubmit}
              disabled={!chatMessage.trim()}
              className="px-2.5 py-2 bg-gray-600 text-white rounded-xl hover:bg-gray-700 disabled:opacity-25 transition-all flex-shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          </div>
        )}

        {/* Action buttons — segmented toggle */}
        {isPending && (
          <div className="flex rounded-xl overflow-hidden border border-gray-200">
            <button onClick={() => onReject(swap)}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium text-gray-500 bg-white hover:bg-gray-50 transition-colors border-r border-gray-200">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Skip
            </button>
            <button onClick={() => onApprove(swap)}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
              Approve
            </button>
          </div>
        )}

        {isApproved && !hasReminder && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-600 font-medium">✓ Approved</span>
            <button onClick={() => setShowAlpaca(true)}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-700 bg-gray-50 border border-gray-200 rounded-xl hover:bg-gray-100 transition-all">
              Execute this swap
              <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        )}

        {isApproved && hasReminder && (
          <div className="flex items-center gap-2 text-sm text-emerald-600">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
            <span className="font-medium">Reminder set — 61 days</span>
          </div>
        )}

        {isRejected && (
          <div className="text-sm text-gray-400">Skipped.</div>
        )}
      </div>

      {showReminder && (
        <ReminderModal swap={swap} onClose={() => setShowReminder(false)} userId={userId}
          onSuccess={() => { setShowReminder(false); onReminderSet(swap); }} />
      )}
      {showAlpaca && (
        <AlpacaSignupModal
          onClose={() => setShowAlpaca(false)}
          userId={userId}
          approvedCount={1}
          approvedSavings={swap.estimated_savings}
          swap={{ ...swap, buy_symbol: selected.symbol, buy_reason: selected.reason || swap.buy_reason }}
          onManualDone={() => { setShowAlpaca(false); setShowReminder(true); }}
        />
      )}
    </div>
  );
}

// ─── Compact card (grid tile) ─────────────────────────────────────────────────

function SwapCard({ swap, index, onOpen }: {
  swap: StoredSwap; index: number; onOpen: (s: StoredSwap) => void;
}) {
  const isPending = swap.status === 'pending';
  const isApproved = swap.status === 'approved';
  const isRejected = swap.status === 'rejected';

  return (
    <button
      onClick={() => onOpen(swap)}
      className={`w-full text-left rounded-2xl overflow-hidden transition-all duration-150 active:scale-[0.98] ${isRejected ? 'opacity-40' : ''}`}
      style={{
        background: '#fff',
        boxShadow: isPending
          ? '0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.05)'
          : '0 1px 3px rgba(0,0,0,0.05)',
        border: isPending ? '1px solid #e5e7eb' : isApproved ? '1px solid #d1fae5' : '1px solid #e5e7eb',
      }}
    >
      {/* Accent bar */}
      <div className={`h-1 w-full ${isPending ? 'bg-gradient-to-r from-emerald-400 to-teal-400' : isApproved ? 'bg-emerald-300' : 'bg-gray-200'}`} />

      <div className="p-3">
        {/* Symbols */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <span className="font-black text-base text-red-500">{swap.sell_symbol}</span>
            <svg className="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
            <span className="font-black text-base text-emerald-500">{swap.buy_symbol}</span>
          </div>
          {isApproved && (
            <span className="text-[9px] text-emerald-700 font-bold bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded-full">
              {swap.reminderSet ? '✓ Reminded' : '✓ Approved'}
            </span>
          )}
          {isRejected && (
            <span className="text-[9px] text-gray-400 font-bold bg-gray-50 border border-gray-100 px-1.5 py-0.5 rounded-full">Skipped</span>
          )}
        </div>

        {/* Key numbers */}
        <div className="grid grid-cols-3 gap-1 text-[11px]">
          <div className="rounded-lg px-2 py-1.5 bg-red-50/80">
            <div className="text-[9px] font-bold text-gray-400 tracking-widest mb-0.5">LOSS</div>
            <div className="text-red-500 font-bold">${Math.abs(swap.sell_loss).toLocaleString()}</div>
            <div className="text-red-400">{swap.sell_loss_pct.toFixed(1)}%</div>
          </div>
          <div className="rounded-lg px-2 py-1.5 bg-emerald-50/80">
            <div className="text-[9px] font-bold text-gray-400 tracking-widest mb-0.5">SAVES</div>
            <div className="text-emerald-600 font-bold">${swap.estimated_savings.toLocaleString()}</div>
            <div className="text-gray-400">{swap.sell_qty} sh</div>
          </div>
          <div className="rounded-lg px-2 py-1.5 bg-gray-50">
            <div className="text-[9px] font-bold text-gray-400 tracking-widest mb-0.5">CORR</div>
            <div className="text-gray-700 font-bold">{(swap.correlation * 100).toFixed(0)}%</div>
            <div className="text-gray-400 truncate">
              {swap.buy_symbol}
              {swap.substitute_candidates && swap.substitute_candidates.length > 1 && (
                <span className="ml-1 text-gray-300">+{swap.substitute_candidates.length - 1}</span>
              )}
            </div>
          </div>
        </div>

        {isPending && (
          <div className="mt-2.5 text-center text-[10px] text-gray-400">
            Tap to review & approve →
          </div>
        )}
      </div>
    </button>
  );
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export default function SwapsPanel({ swaps, userId, onApprove, onReject, onDismiss, onSelectCandidate, onChatAboutSwap }: SwapsPanelProps) {
  const [activeSwap, setActiveSwap] = useState<StoredSwap | null>(null);
  const [reminderSet, setReminderSet] = useState<Set<string>>(new Set());
  const [showWaitlistBanner, setShowWaitlistBanner] = useState(true);
  const [showBannerWaitlist, setShowBannerWaitlist] = useState(false);

  const pending = swaps.filter(s => s.status === 'pending');
  const decided = swaps.filter(s => s.status !== 'pending' && s.status !== 'dismissed');
  const totalPendingSavings = pending.reduce((sum, s) => sum + s.estimated_savings, 0);
  const approved = swaps.filter(s => s.status === 'approved');
  const storedApprovedCount = approved.length;
  const storedApprovedSavings = approved.reduce((sum, s) => sum + s.estimated_savings, 0);

  const handleReminderSet = (swap: StoredSwap) => setReminderSet(prev => new Set(Array.from(prev).concat(swap.id)));
  const enrich = (s: StoredSwap) => ({ ...s, reminderSet: reminderSet.has(s.id) });

  // Sync active swap when its status changes (e.g. approved from detail view)
  useEffect(() => {
    if (activeSwap) {
      const updated = swaps.find(s => s.id === activeSwap.id);
      if (updated) setActiveSwap({ ...updated, reminderSet: reminderSet.has(updated.id) });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [swaps, reminderSet]);

  if (swaps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-6 py-12">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
          style={{ background: 'linear-gradient(145deg, #f0fdf4, #d1fae5)', border: '1px solid rgba(16,185,129,0.15)' }}>
          <svg className="w-8 h-8 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z" />
          </svg>
        </div>
        <div className="text-sm font-semibold text-gray-700 mb-1.5">No opportunities yet</div>
        <div className="text-xs text-gray-400 max-w-[220px] leading-relaxed mb-5">
          Connect a brokerage and ask your agent to scan for tax-loss harvesting opportunities.
        </div>
        <div className="space-y-2 text-left max-w-[220px]">
          {[
            'Connect your portfolio in Connections',
            'Ask your agent to find TLH opportunities',
            'Review and approve swap recommendations',
          ].map((step, i) => (
            <div key={step} className="flex items-start gap-2.5">
              <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-400 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                {i + 1}
              </span>
              <span className="text-xs text-gray-500">{step}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-full overflow-hidden">
      {/* Detail overlay — covers the entire panel including the header below */}
      {activeSwap && (
        <SwapDetailView
          swap={enrich(activeSwap)}
          userId={userId}
          onBack={() => setActiveSwap(null)}
          onApprove={(s) => { onApprove(s); }}
          onReject={(s) => { onReject(s); }}
          onReminderSet={(s) => { handleReminderSet(s); }}
          onSelectCandidate={onSelectCandidate}
          onChatAboutSwap={onChatAboutSwap}
        />
      )}

      {/* Stats bar */}
      {pending.length > 0 && (
        <div className="flex-shrink-0 px-4 py-2.5 border-b border-gray-100 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            <span className="font-semibold text-gray-700">{pending.length}</span> pending
          </span>
          <span className="text-xs font-bold text-emerald-600">
            ~${totalPendingSavings.toLocaleString()} total savings
          </span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-3 py-3">
        {/* Banner */}
        {showBannerWaitlist && (
          <AlpacaSignupModal
            onClose={() => setShowBannerWaitlist(false)}
            userId={userId}
            approvedCount={storedApprovedCount}
            approvedSavings={storedApprovedSavings}
          />
        )}
        {showWaitlistBanner && (
          <div className="mb-3 rounded-2xl overflow-hidden relative"
            style={{ background: 'linear-gradient(135deg, #111827 0%, #1f2937 100%)' }}>
            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
            <div className="p-3.5 flex items-center gap-3">
              <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center">
                <svg className="w-4.5 h-4.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-white">Live trade execution</div>
                <div className="text-[10px] text-gray-400">Automated swaps coming soon</div>
              </div>
              <span className="text-[9px] font-bold uppercase tracking-wider text-amber-400 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded-full flex-shrink-0">
                Soon
              </span>
              <button onClick={() => setShowWaitlistBanner(false)} className="text-gray-600 hover:text-gray-400 flex-shrink-0">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Pending grid */}
        {pending.length > 0 && (
          <div className="grid grid-cols-2 gap-2.5 mb-3">
            {pending.map((swap, i) => (
              <SwapCard key={swap.id} swap={enrich(swap)} index={i} onOpen={setActiveSwap} />
            ))}
          </div>
        )}

        {/* Decided */}
        {decided.length > 0 && (
          <>
            {pending.length > 0 && (
              <div className="text-[10px] text-gray-300 font-bold uppercase tracking-wider px-1 mb-2">Decided</div>
            )}
            <div className="grid grid-cols-2 gap-2.5">
              {decided.map((swap, i) => (
                <SwapCard key={swap.id} swap={enrich(swap)} index={pending.length + i} onOpen={setActiveSwap} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
