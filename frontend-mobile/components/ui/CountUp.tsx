import React, { useEffect, useRef, useState } from 'react';
import { Text, TextProps, TextStyle } from 'react-native';

/**
 * Animates a number from its previous value to the new one whenever `value`
 * changes (eases out over `duration`). JS-driven via requestAnimationFrame so
 * it works identically on iOS, Android, and web. Pass a `format` fn to render
 * currency/percent/etc.
 */
export function CountUp({
  value,
  format = (n) => n.toFixed(2),
  duration = 700,
  style,
  ...rest
}: {
  value: number;
  format?: (n: number) => string;
  duration?: number;
  style?: TextStyle | TextStyle[];
} & TextProps) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const rafRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const from = fromRef.current;
    const to = value;
    if (!isFinite(to)) { setDisplay(to); return; }
    if (from === to) return;

    let start: number | null = null;
    const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

    const tick = (ts: number) => {
      if (start === null) start = ts;
      const p = Math.min(1, (ts - start) / duration);
      setDisplay(from + (to - from) * easeOutCubic(p));
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = to;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      fromRef.current = to; // ensure next change animates from the latest target
    };
  }, [value, duration]);

  return <Text style={style} {...rest}>{format(display)}</Text>;
}
