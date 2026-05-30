'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { creditsApi, type CreditBalance } from '@/lib/api';

interface CreditsState {
  credits: number;
  plan: string;
  subscriptionStatus: string | null;
  cancelAtPeriodEnd: boolean;
  currentPeriodEnd: string | null;
  loading: boolean;
}

interface CreditsContextValue extends CreditsState {
  refresh: () => Promise<void>;
  isPro: boolean;
  modalOpen: boolean;
  openModal: () => void;
  closeModal: () => void;
}

const CreditsContext = createContext<CreditsContextValue | null>(null);

export function CreditsProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);
  const [state, setState] = useState<CreditsState>({
    credits: 0,
    plan: 'free',
    subscriptionStatus: null,
    cancelAtPeriodEnd: false,
    currentPeriodEnd: null,
    loading: true,
  });

  const refresh = useCallback(async () => {
    if (!user?.id) return;
    try {
      const b = await creditsApi.getBalance(user.id);
      setState({
        credits: b.credits,
        plan: b.plan,
        subscriptionStatus: b.subscription_status,
        cancelAtPeriodEnd: b.cancel_at_period_end,
        currentPeriodEnd: b.current_period_end,
        loading: false,
      });
    } catch {
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [user?.id]);

  useEffect(() => {
    if (user?.id) refresh();
  }, [user?.id, refresh]);

  const isPro = state.plan === 'pro' || state.plan === 'admin';
  const openModal = useCallback(() => setModalOpen(true), []);
  const closeModal = useCallback(() => setModalOpen(false), []);

  return (
    <CreditsContext.Provider value={{ ...state, refresh, isPro, modalOpen, openModal, closeModal }}>
      {children}
    </CreditsContext.Provider>
  );
}

export function useCredits() {
  const ctx = useContext(CreditsContext);
  if (!ctx) throw new Error('useCredits must be used within CreditsProvider');
  return ctx;
}
