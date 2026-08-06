import React, { useMemo, useState } from 'react';
import { View, Text } from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop } from 'react-native-svg';
import type { SeriesData } from '@/lib/types';

// Categorical palette — matches the web WidgetChart SERIES_PALETTE so a widget
// reads identically on both platforms.
export const SERIES_PALETTE = ['#10b981', '#6366f1', '#f59e0b', '#ef4444', '#0ea5e9', '#ec4899'];

const fmt = (v: number, kind?: 'pct' | 'currency' | 'number') => {
  if (kind === 'pct') return `${v.toFixed(2)}%`;
  if (kind === 'currency') return v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(2)}`;
  return Math.abs(v) >= 1000 ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : v.toFixed(2);
};

// Multi-series line chart (single series → area wash), drawn with react-native-svg.
// The web renders this with lightweight-charts; the visual language (emerald-led
// palette, thin lines, endpoint legend with % change) is preserved.
export default function WidgetChart({
  data,
  height = 200,
  yFormat = 'number',
  showLegend = true,
}: {
  data: SeriesData;
  height?: number;
  yFormat?: 'pct' | 'currency' | 'number';
  showLegend?: boolean;
}) {
  const [width, setWidth] = useState(0);

  const series = useMemo(
    () => (data.series || []).map((s) => ({ label: s.label, pts: (s.points || []).filter((p) => p.v != null) })),
    [data],
  );
  const hasData = series.some((s) => s.pts.length >= 2);
  const single = series.length === 1;

  const paths = useMemo(() => {
    const all = series.flatMap((s) => s.pts.map((p) => p.v as number));
    if (!all.length || width <= 0) return [] as { line: string; area: string }[];
    let mn = Math.min(...all);
    let mx = Math.max(...all);
    if (mn === mx) { mn -= 1; mx += 1; }
    const range = mx - mn;
    const padY = 6;
    const h = height - padY * 2;
    return series.map((s) => {
      const n = s.pts.length;
      if (n < 2) return { line: '', area: '' };
      const xs = (i: number) => (i / (n - 1)) * width;
      const ys = (v: number) => padY + (1 - (v - mn) / range) * h;
      const line = s.pts
        .map((p, i) => `${i === 0 ? 'M' : 'L'}${xs(i).toFixed(1)},${ys(p.v as number).toFixed(1)}`)
        .join(' ');
      const area = `${line} L${xs(n - 1).toFixed(1)},${height} L0,${height} Z`;
      return { line, area };
    });
  }, [series, width, height]);

  const legend = series.map((s, i) => {
    const first = s.pts[0]?.v as number | undefined;
    const last = s.pts[s.pts.length - 1]?.v as number | undefined;
    const chg = first != null && last != null && first !== 0 ? ((last - first) / Math.abs(first)) * 100 : null;
    return { label: s.label, color: SERIES_PALETTE[i % SERIES_PALETTE.length], last, chg };
  });

  if (!hasData) {
    return (
      <View style={{ height, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ color: '#9ca3af', fontSize: 12, fontFamily: 'DMSans' }}>No data</Text>
      </View>
    );
  }

  return (
    <View>
      {showLegend && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 8 }}>
          {legend.map((r) => (
            <View key={r.label} style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}>
              <View style={{ width: 9, height: 9, borderRadius: 2, backgroundColor: r.color }} />
              <Text style={{ fontSize: 12, color: '#4b5563', fontFamily: 'DMSans' }}>{r.label}</Text>
              {r.last != null && (
                <Text style={{ fontSize: 12, color: '#111827', fontFamily: 'DMSans-Medium' }}>{fmt(r.last, yFormat)}</Text>
              )}
              {r.chg != null && (
                <Text style={{ fontSize: 12, fontFamily: 'DMSans-Medium', color: r.chg >= 0 ? '#059669' : '#ef4444' }}>
                  {r.chg >= 0 ? '+' : ''}{r.chg.toFixed(1)}%
                </Text>
              )}
            </View>
          ))}
        </View>
      )}
      <View onLayout={(e) => setWidth(e.nativeEvent.layout.width)} style={{ height }}>
        {width > 0 && (
          <Svg width={width} height={height}>
            <Defs>
              {paths.map((_, i) => (
                <LinearGradient key={i} id={`wgfill${i}`} x1="0" y1="0" x2="0" y2="1">
                  <Stop offset="0" stopColor={SERIES_PALETTE[i % SERIES_PALETTE.length]} stopOpacity={0.15} />
                  <Stop offset="1" stopColor={SERIES_PALETTE[i % SERIES_PALETTE.length]} stopOpacity={0} />
                </LinearGradient>
              ))}
            </Defs>
            {single && paths[0]?.area ? <Path d={paths[0].area} fill="url(#wgfill0)" /> : null}
            {paths.map((p, i) =>
              p.line ? (
                <Path
                  key={i}
                  d={p.line}
                  fill="none"
                  stroke={SERIES_PALETTE[i % SERIES_PALETTE.length]}
                  strokeWidth={2}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              ) : null,
            )}
          </Svg>
        )}
      </View>
    </View>
  );
}
