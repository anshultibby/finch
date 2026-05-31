'use client';

import React, { useState, useEffect } from 'react';

interface TickerLogoProps {
  symbol: string;
  /** px size of the square badge */
  size?: number;
  className?: string;
  /** Tailwind rounding for the badge (default rounded-lg) */
  rounded?: string;
}

/**
 * Company logo for a ticker, sourced from FMP's CDN (constructible from the
 * symbol alone, so it works in search results, peers, watchlist, etc.).
 * Falls back to a clean monogram badge when no logo exists (ETFs, obscure
 * tickers) or the image fails to load — never a broken-image icon.
 */
export default function TickerLogo({ symbol, size = 32, className = '', rounded = 'rounded-lg' }: TickerLogoProps) {
  const clean = (symbol || '').toUpperCase().split('.')[0]; // strip exchange suffix (NVDA.NE → NVDA)
  const [failed, setFailed] = useState(false);

  // Reset when the symbol changes so a reused component re-tries the new logo.
  useEffect(() => { setFailed(false); }, [clean]);

  const box = { width: size, height: size };

  if (failed || !clean) {
    return (
      <div
        style={box}
        className={`flex items-center justify-center ${rounded} bg-gray-100 border border-gray-200 flex-shrink-0 ${className}`}
      >
        <span className="font-bold text-gray-500" style={{ fontSize: Math.round(size * 0.34) }}>
          {clean.slice(0, 2) || '—'}
        </span>
      </div>
    );
  }

  return (
    <img
      src={`https://images.financialmodelingprep.com/symbol/${clean}.png`}
      alt={clean}
      width={size}
      height={size}
      loading="lazy"
      onError={() => setFailed(true)}
      style={box}
      className={`${rounded} object-contain bg-white border border-gray-200 flex-shrink-0 ${className}`}
    />
  );
}
