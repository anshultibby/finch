import {
  formatCurrency,
  formatPct,
  formatVolume,
  currencySymbol,
  isIndianStock,
} from '../../lib/constants';

describe('isIndianStock / currencySymbol', () => {
  it('recognizes NSE/BSE suffixes and indices', () => {
    expect(isIndianStock('RELIANCE.NS')).toBe(true);
    expect(isIndianStock('TCS.BO')).toBe(true);
    expect(isIndianStock('^NSEI')).toBe(true);
    expect(isIndianStock('AAPL')).toBe(false);
    expect(isIndianStock(undefined)).toBe(false);
  });

  it('picks the right currency symbol', () => {
    expect(currencySymbol('AAPL')).toBe('$');
    expect(currencySymbol('RELIANCE.NS')).toBe('₹');
  });
});

describe('formatCurrency', () => {
  it('formats USD with two decimals', () => {
    expect(formatCurrency(1234.5)).toBe('$1,234.50');
  });

  it('uses ₹ for Indian symbols', () => {
    expect(formatCurrency(1000, false, 'RELIANCE.NS').startsWith('₹')).toBe(true);
  });

  it('compacts large values when asked', () => {
    expect(formatCurrency(2_500_000_000, true)).toBe('$2.5B');
    expect(formatCurrency(3_400, true)).toBe('$3.4K');
  });
});

describe('formatPct', () => {
  it('adds a sign and two decimals', () => {
    expect(formatPct(1.5)).toBe('+1.50%');
    expect(formatPct(-2)).toBe('-2.00%');
    expect(formatPct(0)).toBe('+0.00%');
  });
});

describe('formatVolume', () => {
  it('abbreviates by magnitude', () => {
    expect(formatVolume(1_500_000_000)).toBe('1.5B');
    expect(formatVolume(2_300_000)).toBe('2.3M');
    expect(formatVolume(4_500)).toBe('4.5K');
    expect(formatVolume(750)).toBe('750');
  });
});
