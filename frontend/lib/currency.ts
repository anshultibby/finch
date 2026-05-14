type CurrencyInfo = { symbol: string; code: string; locale: string };

const INR: CurrencyInfo = { symbol: '₹', code: 'INR', locale: 'en-IN' };
const USD: CurrencyInfo = { symbol: '$', code: 'USD', locale: 'en-US' };

export function getCurrency(ticker?: string): CurrencyInfo {
  if (!ticker) return USD;
  if (/\.(NS|BO)$/i.test(ticker) || /^\^(NSEI|BSESN|NSEBANK)$/.test(ticker)) return INR;
  return USD;
}

export function formatCurrency(value: number, ticker?: string): string {
  const c = getCurrency(ticker);
  return new Intl.NumberFormat(c.locale, {
    style: 'currency', currency: c.code, minimumFractionDigits: 2,
  }).format(value);
}

export function formatCurrencyCompact(value: number, ticker?: string): string {
  const { symbol } = getCurrency(ticker);
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}${symbol}${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}${symbol}${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}${symbol}${(abs / 1e6).toFixed(1)}M`;
  return formatCurrency(value, ticker);
}
