type CurrencyInfo = { symbol: string; code: string; locale: string };

const INR: CurrencyInfo = { symbol: '₹', code: 'INR', locale: 'en-IN' };
const USD: CurrencyInfo = { symbol: '$', code: 'USD', locale: 'en-US' };

export function isIndianTicker(ticker?: string): boolean {
  if (!ticker) return false;
  return /\.(NS|BO)$/i.test(ticker) || /^\^(NSEI|BSESN|NSEBANK)$/.test(ticker);
}

export function getCurrency(ticker?: string): CurrencyInfo {
  return isIndianTicker(ticker) ? INR : USD;
}

export function formatCurrency(value: number, ticker?: string): string {
  const c = getCurrency(ticker);
  return new Intl.NumberFormat(c.locale, {
    style: 'currency', currency: c.code, minimumFractionDigits: 2,
  }).format(value);
}

export function formatCurrencyCompact(value: number, ticker?: string): string {
  const c = getCurrency(ticker);
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  // Indian numbering: lakh (1e5) and crore (1e7). Market caps / revenues are
  // conventionally quoted in crore, with "lakh crore" for the very largest.
  if (c.code === 'INR') {
    if (abs >= 1e7) {
      const cr = abs / 1e7;
      if (cr >= 1e5) return `${sign}₹${(cr / 1e5).toFixed(2)} Lakh Cr`;
      return `${sign}₹${cr.toFixed(2)} Cr`;
    }
    if (abs >= 1e5) return `${sign}₹${(abs / 1e5).toFixed(2)} Lakh`;
    return formatCurrency(value, ticker);
  }

  if (abs >= 1e12) return `${sign}${c.symbol}${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}${c.symbol}${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}${c.symbol}${(abs / 1e6).toFixed(1)}M`;
  return formatCurrency(value, ticker);
}

/**
 * Region-aware date formatter. Indian markets display dates as d/m/y;
 * US markets keep the provided en-US options. Pass `india` from either
 * `isIndianTicker(symbol)` or the `market` toggle (`market === 'india'`).
 */
export function formatDate(
  value: string | number | Date,
  opts?: Intl.DateTimeFormatOptions,
  india = false,
): string {
  const d = value instanceof Date ? value : new Date(value);
  if (isNaN(d.getTime())) return '';
  if (india) return d.toLocaleDateString('en-GB'); // dd/mm/yyyy
  return d.toLocaleDateString('en-US', opts);
}
