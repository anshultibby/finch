'use client';

// Live pending trade approvals, shared app-wide (sidebar chip, home ledger).
// Cached under one key so every consumer sees the same list and a decision
// made anywhere (approve/reject) can refresh all of them at once.

import { useMemo } from 'react';
import { useCachedResource, invalidateCache } from './useCachedResource';
import { pendingTradesApi, type PendingTradeItem } from '@/lib/api';

const KEY = 'pending-trades';

/** Call after approving/rejecting a trade so chips/badges update immediately. */
export function invalidatePendingTrades() {
  invalidateCache(KEY);
}

export function usePendingTrades(enabled = true) {
  const { data, refresh } = useCachedResource<{ pending_trades: PendingTradeItem[] }>(
    KEY,
    () => pendingTradesApi.list(),
    { ttl: 60_000, enabled },
  );

  // Drop client-side-expired proposals so a stale chip never nags about a
  // trade that can no longer be approved.
  const trades = useMemo(
    () => (data?.pending_trades || []).filter(
      (t) => !t.expires_at || new Date(t.expires_at).getTime() > Date.now(),
    ),
    [data],
  );

  return { trades, refresh };
}
