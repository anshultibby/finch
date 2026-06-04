import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop, Line, Circle } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedProps,
  withTiming,
  interpolate,
  Extrapolation,
} from 'react-native-reanimated';
import { marketApi } from '@/lib/api';
import { formatPct } from '@/lib/constants';
import { EASE_OUT, DUR } from '@/lib/animations';
import SegmentedControl from '@/components/ui/SegmentedControl';

const AnimatedPath = Animated.createAnimatedComponent(Path);
const AnimatedCircle = Animated.createAnimatedComponent(Circle);

type Range = '1W' | '1M' | '3M' | '1Y';
const RANGES: Range[] = ['1W', '1M', '3M', '1Y'];
const RANGE_DAYS: Record<Range, number> = { '1W': 7, '1M': 30, '3M': 90, '1Y': 365 };
const RANGE_LABEL: Record<Range, string> = { '1W': 'past week', '1M': 'past month', '3M': 'past 3 months', '1Y': 'past year' };

const HEIGHT = 170;
const PAD_V = 10;

/**
 * Full-width price line + area chart with a timeframe toggle. The line draws in
 * from left to right, colored by the period's direction, with a dashed baseline
 * at the period's opening price (Robinhood-style).
 */
export default function PriceChart({ symbol }: { symbol: string }) {
  const [range, setRange] = useState<Range>('1M');
  // `mode` distinguishes the two shapes /market/prices can return: raw closes
  // ('price') or a series already rebased to cumulative % return from day 0
  // ('pct'). They need different baselines and return math.
  const [series, setSeries] = useState<{ values: number[]; mode: 'price' | 'pct' }>({ values: [], mode: 'price' });
  const [width, setWidth] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    marketApi
      .getPrices([symbol], RANGE_DAYS[range])
      .then((d: any) => {
        if (cancelled) return;
        const raw = d[symbol] || d[symbol?.toUpperCase()] || [];
        const arr = Array.isArray(raw) ? raw : [];
        const hasClose = arr.some((p: any) => p?.close != null);
        const values = arr
          .map((p: any) => Number(hasClose ? p.close : p.pct))
          .filter(Number.isFinite);
        setSeries({ values, mode: hasClose ? 'price' : 'pct' });
      })
      .catch(() => {
        if (!cancelled) setSeries({ values: [], mode: 'price' });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, range]);

  const data = series.values;
  // Baseline the chart is measured against: opening price, or 0 for a rebased
  // % series.
  const baselineValue = series.mode === 'pct' ? 0 : data[0];

  const { linePath, areaPath, baselineY, lastPoint, length } = useMemo(() => {
    if (data.length < 2 || width === 0) {
      return { linePath: '', areaPath: '', baselineY: 0, lastPoint: null, length: 0 };
    }
    // Keep the baseline inside the visible domain so the dashed line shows.
    const min = Math.min(...data, baselineValue);
    const max = Math.max(...data, baselineValue);
    const span = max - min || 1;
    const h = HEIGHT - PAD_V * 2;
    const yFor = (v: number) => PAD_V + (1 - (v - min) / span) * h;

    const pts = data.map((v, i) => ({
      x: (i / (data.length - 1)) * width,
      y: yFor(v),
    }));

    const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const area = `${line} L${width.toFixed(1)},${HEIGHT} L0,${HEIGHT} Z`;

    let len = 0;
    for (let i = 1; i < pts.length; i++) {
      len += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    }

    return { linePath: line, areaPath: area, baselineY: yFor(baselineValue), lastPoint: pts[pts.length - 1], length: len };
  }, [data, width, baselineValue]);

  const last = data[data.length - 1] ?? 0;
  // pct series already expresses cumulative return; price series is converted.
  const changePct = series.mode === 'pct' ? last : data[0] ? ((last - data[0]) / data[0]) * 100 : 0;
  const isUp = changePct >= 0;
  const color = isUp ? '#10b981' : '#ef4444';

  // Draw-in: stroke reveals left→right, area fades up, end dot pops last.
  const progress = useSharedValue(0);
  useEffect(() => {
    if (!linePath) return;
    progress.value = 0;
    progress.value = withTiming(1, { duration: DUR.slow, easing: EASE_OUT });
  }, [linePath, progress]);

  const lineProps = useAnimatedProps(() => ({
    strokeDashoffset: length * (1 - progress.value),
  }));
  const areaProps = useAnimatedProps(() => ({
    opacity: interpolate(progress.value, [0, 1], [0, 1], Extrapolation.CLAMP),
  }));
  const dotProps = useAnimatedProps(() => ({
    opacity: interpolate(progress.value, [0.7, 1], [0, 1], Extrapolation.CLAMP),
  }));

  return (
    <View>
      {/* Period return */}
      <View style={styles.headerRow}>
        <Text style={[styles.changeText, { color }]}>
          {isUp ? '▲' : '▼'} {formatPct(changePct)}
        </Text>
        <Text style={styles.periodLabel}>{RANGE_LABEL[range]}</Text>
      </View>

      {/* Chart */}
      <View style={styles.chartArea} onLayout={(e) => setWidth(e.nativeEvent.layout.width)}>
        {!loading && linePath ? (
          <Svg width={width} height={HEIGHT}>
            <Defs>
              <LinearGradient id={`grad-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor={color} stopOpacity={0.18} />
                <Stop offset="1" stopColor={color} stopOpacity={0} />
              </LinearGradient>
            </Defs>

            {/* Opening-price baseline */}
            <Line
              x1={0}
              y1={baselineY}
              x2={width}
              y2={baselineY}
              stroke="#d1d5db"
              strokeWidth={1}
              strokeDasharray="3,3"
            />

            <AnimatedPath d={areaPath} fill={`url(#grad-${symbol})`} animatedProps={areaProps} />
            <AnimatedPath
              d={linePath}
              fill="none"
              stroke={color}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray={length}
              animatedProps={lineProps}
            />
            {lastPoint && <AnimatedCircle cx={lastPoint.x} cy={lastPoint.y} r={3.5} fill={color} animatedProps={dotProps} />}
          </Svg>
        ) : (
          <View style={[styles.placeholder, { width: width || '100%' }]}>
            <Text style={styles.placeholderText}>{loading ? '' : 'No price history'}</Text>
          </View>
        )}
      </View>

      {/* Timeframe toggle */}
      <View style={styles.controlWrap}>
        <SegmentedControl options={RANGES} selected={range} onChange={setRange} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 8,
    paddingHorizontal: 16,
    marginBottom: 6,
  },
  changeText: {
    fontSize: 14,
    fontFamily: 'DMSans-Bold',
  },
  periodLabel: {
    fontSize: 12,
    fontFamily: 'DMSans',
    color: '#9ca3af',
  },
  chartArea: {
    height: HEIGHT,
    justifyContent: 'center',
  },
  placeholder: {
    height: HEIGHT,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderText: {
    fontSize: 13,
    fontFamily: 'DMSans',
    color: '#d1d5db',
  },
  controlWrap: {
    paddingHorizontal: 16,
    marginTop: 8,
  },
});
