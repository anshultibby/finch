/**
 * Human-readable timestamps, shared by anything that lists past or upcoming
 * runs (the Automations panel, the sidebar's run list).
 */

/** "5m ago", "3h ago", "in 2d" — signed, so it reads correctly either way. */
export function relativeTime(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  const abs = Math.abs(diff);
  const m = Math.round(abs / 60000), h = Math.round(abs / 3600000), d = Math.round(abs / 86400000);
  const rel = m < 1 ? 'now' : m < 60 ? `${m}m` : h < 24 ? `${h}h` : `${d}d`;
  return diff >= 0 ? `in ${rel}` : `${rel} ago`;
}

/** "Aug 17, 3:42 PM" */
export function exactTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

/**
 * How a past run is stamped in a list: "12m ago" while that still means
 * something, an actual date and time once it doesn't. A daily automation's
 * runs are told apart by their clock time, so keep it past the day boundary.
 */
export function runTimestamp(iso: string): string {
  const age = Date.now() - new Date(iso).getTime();
  return age < 86_400_000 ? relativeTime(iso) : exactTime(iso);
}
