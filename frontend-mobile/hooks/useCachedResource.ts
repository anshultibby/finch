'use client';

// Stale-while-revalidate cache for read-only API data.
//
// Why this exists: the home tabs (Markets, Watchlist, Earnings, Trading Agent)
// are conditionally rendered, so switching tabs unmounts the active view and
// switching back remounts it — re-running its fetch and flashing a spinner every
// time. This hook keeps results in a module-level store keyed by a string, so a
// remount renders cached data instantly and only revalidates in the background
// when the data is older than `ttl`. In-flight requests for the same key are
// deduped, and any component reading a key re-renders when that key updates.

import { useCallback, useEffect, useRef, useState } from 'react';

interface Entry<T> {
  data?: T;
  error?: unknown;
  ts: number;            // last successful fetch (ms epoch); 0 until first success
  promise?: Promise<T>;  // in-flight request, used for dedup
}

const store = new Map<string, Entry<unknown>>();
const listeners = new Map<string, Set<() => void>>();

function notify(key: string) {
  listeners.get(key)?.forEach((fn) => fn());
}

/** Imperatively seed/overwrite a cache key (e.g. after a mutation). */
export function mutateCache<T>(key: string, data: T) {
  store.set(key, { data, ts: Date.now() });
  notify(key);
}

/** Drop one key (or everything when no key given) so the next read refetches. */
export function invalidateCache(key?: string) {
  if (key == null) {
    store.clear();
    listeners.forEach((_set, k) => notify(k));
    return;
  }
  store.delete(key);
  notify(key);
}

/** True when `key` holds data fetched within the last `ttl` ms. */
export function isCacheFresh(key: string, ttl: number): boolean {
  const entry = store.get(key);
  return !!entry && entry.data !== undefined && Date.now() - entry.ts < ttl;
}

/**
 * Record a fetch timestamp for `key` without going through the hook — for
 * imperative fetchers (screens that set many separate states) that just want
 * `isCacheFresh` gating to skip redundant refetches on every focus.
 */
export function touchCache(key: string, data: unknown = true): void {
  store.set(key, { data, ts: Date.now() });
}

interface Options {
  /** ms a successful result stays "fresh"; within this window remounts skip refetch. Default 30s. */
  ttl?: number;
  /** When false, no fetch is attempted (e.g. waiting on a userId). Default true. */
  enabled?: boolean;
}

interface Result<T> {
  data: T | undefined;
  error: unknown;
  /** True only when there is nothing cached yet — i.e. the first ever load. */
  isLoading: boolean;
  /** True while a background revalidation is in flight (cached data already shown). */
  isValidating: boolean;
  refresh: () => Promise<T | undefined>;
  mutate: (data: T) => void;
}

export function useCachedResource<T>(
  key: string | null,
  fetcher: () => Promise<T>,
  opts: Options = {},
): Result<T> {
  const { ttl = 30_000, enabled = true } = opts;

  // Keep the latest fetcher without making it a dependency (callers often pass inline closures).
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const [, force] = useState(0);
  const rerender = useCallback(() => force((n) => n + 1), []);

  // Subscribe this component to updates for `key`.
  useEffect(() => {
    if (!key) return;
    let set = listeners.get(key);
    if (!set) {
      set = new Set();
      listeners.set(key, set);
    }
    set.add(rerender);
    return () => {
      set!.delete(rerender);
      if (set!.size === 0) listeners.delete(key);
    };
  }, [key, rerender]);

  const revalidate = useCallback(async (): Promise<T | undefined> => {
    if (!key) return undefined;
    const existing = store.get(key) as Entry<T> | undefined;
    if (existing?.promise) return existing.promise; // dedupe concurrent fetches

    const promise = fetcherRef.current();
    store.set(key, { ...existing, ts: existing?.ts ?? 0, promise });
    try {
      const data = await promise;
      store.set(key, { data, ts: Date.now() });
    } catch (error) {
      const prev = store.get(key) as Entry<T> | undefined;
      store.set(key, { data: prev?.data, ts: prev?.ts ?? 0, error });
    } finally {
      notify(key);
    }
    return (store.get(key) as Entry<T> | undefined)?.data;
  }, [key]);

  // Fetch on mount / key change unless we have fresh data.
  useEffect(() => {
    if (!key || !enabled) return;
    const entry = store.get(key) as Entry<T> | undefined;
    const fresh = entry?.data !== undefined && Date.now() - entry.ts < ttl;
    if (!fresh) revalidate();
  }, [key, enabled, ttl, revalidate]);

  const entry = key ? (store.get(key) as Entry<T> | undefined) : undefined;
  return {
    data: entry?.data,
    error: entry?.error,
    isLoading: enabled && !!key && entry?.data === undefined && entry?.error === undefined,
    isValidating: !!entry?.promise,
    refresh: revalidate,
    mutate: (data: T) => {
      if (key) mutateCache(key, data);
    },
  };
}
