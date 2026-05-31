import React, { useEffect, useState, useMemo } from 'react';
import { View } from 'react-native';
import Svg, { Path, Circle } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedProps,
  withTiming,
  interpolate,
  Extrapolation,
} from 'react-native-reanimated';
import { marketApi } from '@/lib/api';
import { EASE_OUT, DUR } from '@/lib/animations';

const AnimatedPath = Animated.createAnimatedComponent(Path);
const AnimatedCircle = Animated.createAnimatedComponent(Circle);

interface MiniSparklineProps {
  symbol: string;
  width?: number;
  height?: number;
  color?: string;
  days?: number;
}

export default function MiniSparkline({
  symbol,
  width = 60,
  height = 24,
  color,
  days = 30,
}: MiniSparklineProps) {
  const [data, setData] = useState<number[]>([]);

  useEffect(() => {
    marketApi.getPrices([symbol], days)
      .then((d: any) => {
        const series = d[symbol] || d[symbol.toUpperCase()] || [];
        if (Array.isArray(series)) {
          setData(series.map((p: any) => p.close ?? p.pct ?? 0));
        }
      })
      .catch(() => {});
  }, [symbol, days]);

  const { path, lastPoint, length } = useMemo(() => {
    if (data.length < 2) return { path: '', lastPoint: null, length: 0 };
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = 2;
    const w = width - pad * 2;
    const h = height - pad * 2;

    const pts = data.map((v, i) => ({
      x: pad + (i / (data.length - 1)) * w,
      y: pad + (1 - (v - min) / range) * h,
    }));

    const pathStr = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    let len = 0;
    for (let i = 1; i < pts.length; i++) {
      len += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    }

    return { path: pathStr, lastPoint: pts[pts.length - 1], length: len };
  }, [data, width, height]);

  const isUp = data.length >= 2 ? data[data.length - 1] >= data[0] : true;
  const lineColor = color || (isUp ? '#10b981' : '#ef4444');

  // Draw-in: stroke reveals from start to end, then the end dot pops.
  const progress = useSharedValue(0);
  useEffect(() => {
    if (!path) return;
    progress.value = 0;
    progress.value = withTiming(1, { duration: DUR.slow, easing: EASE_OUT });
  }, [path, progress]);

  const pathProps = useAnimatedProps(() => ({
    strokeDashoffset: length * (1 - progress.value),
  }));
  const dotProps = useAnimatedProps(() => ({
    opacity: interpolate(progress.value, [0.6, 1], [0, 1], Extrapolation.CLAMP),
    r: 2 * interpolate(progress.value, [0.6, 1], [0.2, 1], Extrapolation.CLAMP),
  }));

  if (!path) return <View style={{ width, height }} />;

  return (
    <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <AnimatedPath
        d={path}
        fill="none"
        stroke={lineColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={length}
        animatedProps={pathProps}
      />
      {lastPoint && (
        <AnimatedCircle cx={lastPoint.x} cy={lastPoint.y} fill={lineColor} animatedProps={dotProps} />
      )}
    </Svg>
  );
}
