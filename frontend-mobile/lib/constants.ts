export const COLORS = {
  emerald: '#059669',
  emeraldLight: '#d1fae5',
  red: '#dc2626',
  redLight: '#fef2f2',
  amber: '#f59e0b',
  amberLight: '#fef3c7',
  blue: '#2563eb',
  violet: '#7c3aed',
  gray900: '#111827',
  gray700: '#374151',
  gray500: '#6b7280',
  gray400: '#9ca3af',
  gray200: '#e5e7eb',
  gray100: '#f3f4f6',
  gray50: '#f9fafb',
  bg: '#ffffff',
  white: '#ffffff',
} as const;

export function isIndianStock(symbol?: string): boolean {
  return !!symbol && (/\.(NS|BO)$/i.test(symbol) || /^\^(NSEI|BSESN|NSEBANK)$/.test(symbol));
}

export function currencySymbol(symbol?: string): string {
  return isIndianStock(symbol) ? '₹' : '$';
}

export function formatCurrency(value: number | null | undefined, compact = false, symbol?: string): string {
  const cs = currencySymbol(symbol);
  const n = typeof value === 'number' ? value : value == null ? NaN : Number(value);
  if (!Number.isFinite(n)) return '—';
  if (compact) {
    if (Math.abs(n) >= 1e12) return `${cs}${(n / 1e12).toFixed(1)}T`;
    if (Math.abs(n) >= 1e9) return `${cs}${(n / 1e9).toFixed(1)}B`;
    if (Math.abs(n) >= 1e6) return `${cs}${(n / 1e6).toFixed(1)}M`;
    if (Math.abs(n) >= 1e3) return `${cs}${(n / 1e3).toFixed(1)}K`;
  }
  const locale = isIndianStock(symbol) ? 'en-IN' : 'en-US';
  return `${cs}${n.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPct(value: number | null | undefined): string {
  const n = typeof value === 'number' ? value : value == null ? NaN : Number(value);
  if (!Number.isFinite(n)) return '—';
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

export function formatVolume(vol: number | null | undefined): string {
  const n = typeof vol === 'number' ? vol : vol == null ? NaN : Number(vol);
  if (!Number.isFinite(n)) return '—';
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toString();
}

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
