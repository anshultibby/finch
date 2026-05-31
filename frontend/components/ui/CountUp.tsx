'use client';

import React, { useEffect, useRef, useState } from 'react';

interface CountUpProps {
  value: number;
  /** ms */
  duration?: number;
  decimals?: number;
  /** Custom formatter (e.g. currency). Overrides `decimals`. */
  format?: (n: number) => string;
  className?: string;
}

/**
 * Animates a number from its previous value to the new one with an easeOut
 * curve. On first mount it eases from ~2% below the target so prices feel like
 * they "tick into place" without a jarring 0→value sweep. Honors
 * prefers-reduced-motion (snaps straight to the value).
 */
export default function CountUp({ value, duration = 650, decimals = 2, format, className }: CountUpProps) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value * 0.98);
  const rafRef = useRef<number>();
  const startRef = useRef<number | undefined>();

  useEffect(() => {
    const reduce =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setDisplay(value);
      fromRef.current = value;
      return;
    }

    const from = fromRef.current;
    const to = value;
    if (from === to) {
      setDisplay(to);
      return;
    }

    startRef.current = undefined;
    const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
    const step = (ts: number) => {
      if (startRef.current === undefined) startRef.current = ts;
      const p = Math.min((ts - startRef.current) / duration, 1);
      setDisplay(from + (to - from) * easeOutCubic(p));
      if (p < 1) rafRef.current = requestAnimationFrame(step);
      else fromRef.current = to;
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [value, duration]);

  const text = format ? format(display) : display.toFixed(decimals);
  return <span className={className}>{text}</span>;
}
