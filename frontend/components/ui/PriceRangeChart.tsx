'use client';

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { createChart, ColorType, LineStyle, CrosshairMode, LineSeries, AreaSeries } from 'lightweight-charts';
import type {
  IChartApi,
  ISeriesApi,
  MouseEventParams,
  Time,
  SingleValueData,
} from 'lightweight-charts';

export interface PriceSeriesConfig {
  symbol: string;
  color: string;
  label?: string;
}

export interface RangeOption {
  label: string;
  days: number;
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export const DEFAULT_RANGES: RangeOption[] = [
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: 'All', days: 3650 },
];

export const ytdDays = () =>
  Math.ceil((Date.now() - new Date(new Date().getFullYear(), 0, 1).getTime()) / 86400000);

export const getStockRanges = (): RangeOption[] => [
  { label: '1D', days: 1 },
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: 'YTD', days: ytdDays() },
  { label: '1Y', days: 365 },
  { label: 'MAX', days: 3650 },
];

type BaseProps = {
  height?: number;
  className?: string;
  ranges?: RangeOption[];
  format?: 'pct' | 'currency';
  hideHeader?: boolean;
  hideRangeTabs?: boolean;
  tabsPosition?: 'top' | 'bottom';
  onHoverChange?: (info: { date: string; value: number; periodEndValue: number } | null) => void;
  onPeriodChange?: (periodEndValue: number) => void;
  headerRight?: React.ReactNode;
};

type SymbolProps = BaseProps & {
  series: PriceSeriesConfig[];
  defaultDays?: number;
  currentPrice?: number;
  previousClose?: number;
  onRangeChange?: (days: number, label: string) => void;
  data?: undefined;
};

type DataProps = BaseProps & {
  data: SeriesPoint[];
  color?: string;
  label?: string;
  series?: undefined;
  selectedDays?: number;
  onRangeChange?: (days: number, label: string) => void;
};

type Props = SymbolProps | DataProps;

const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
const fmtCurrency = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);

function toUTCTimestamp(dateStr: string): Time {
  const d = new Date(dateStr.includes('T') || dateStr.includes(' ') ? dateStr.replace(' ', 'T') : dateStr + 'T12:00:00');
  return Math.floor(d.getTime() / 1000) as Time;
}

export default function PriceRangeChart(props: Props) {
  const {
    height = 200,
    className = '',
    ranges = DEFAULT_RANGES,
    format = 'pct',
    hideHeader,
    hideRangeTabs,
    tabsPosition = 'top',
    onHoverChange,
    onPeriodChange,
    headerRight,
  } = props;

  const isSymbolMode = 'series' in props && !!props.series;

  const [internalDays, setInternalDays] = useState(isSymbolMode ? (props as SymbolProps).defaultDays ?? 365 : 365);
  const days = isSymbolMode ? internalDays : (props as DataProps).selectedDays ?? internalDays;
  const setDays = (d: number, label: string) => {
    if (isSymbolMode) {
      setInternalDays(d);
      (props as SymbolProps).onRangeChange?.(d, label);
    } else {
      (props as DataProps).onRangeChange?.(d, label);
      setInternalDays(d);
    }
  };

  const [fetched, setFetched] = useState<Record<string, SeriesPoint[]> | null>(null);
  const [fetchLoading, setFetchLoading] = useState(isSymbolMode);
  const symbolsKey = isSymbolMode ? (props as SymbolProps).series.map(s => s.symbol).join(',') : '';
  useEffect(() => {
    if (!isSymbolMode) return;
    setFetched(null);
    setFetchLoading(true);
    fetch(`/api/market-prices?symbols=${symbolsKey}&days=${days}`)
      .then(r => r.json())
      .then((d: Record<string, Array<{ date: string; pct: number }>>) => {
        const mapped: Record<string, SeriesPoint[]> = {};
        for (const [sym, pts] of Object.entries(d || {})) {
          mapped[sym] = (pts ?? []).map(p => ({ date: p.date, value: p.pct }));
        }
        setFetched(mapped);
        setFetchLoading(false);
      })
      .catch(() => setFetchLoading(false));
  }, [isSymbolMode, symbolsKey, days]);

  const currentPrice = isSymbolMode ? (props as SymbolProps).currentPrice : undefined;

  type Line = { label: string; color: string; data: SeriesPoint[] };
  const lines: Line[] = useMemo(() => {
    if (isSymbolMode) {
      const s = (props as SymbolProps).series;
      return s.map(cfg => {
        const data = fetched?.[cfg.symbol] ?? [];
        const lastVal = data[data.length - 1]?.value ?? 0;
        return {
          label: cfg.label ?? cfg.symbol,
          color: cfg.color || (lastVal >= 0 ? '#10b981' : '#ef4444'),
          data,
        };
      });
    }
    const dp = props as DataProps;
    const first = dp.data[0]?.value ?? 0;
    const last = dp.data[dp.data.length - 1]?.value ?? 0;
    const isUp = last >= first;
    return [{
      label: dp.label ?? '',
      color: dp.color ?? (isUp ? '#10b981' : '#ef4444'),
      data: dp.data,
    }];
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSymbolMode, fetched, isSymbolMode ? symbolsKey : (props as DataProps).data]);

  const singleSeries = lines.length === 1;
  const loading = isSymbolMode && fetchLoading;
  const hasData = lines.some(l => l.data.length >= 2);

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRefs = useRef<ISeriesApi<any>[]>([]);

  const periodEndValue = useMemo(() => {
    const refPts = lines[0]?.data ?? [];
    return refPts.length ? refPts[refPts.length - 1].value : 0;
  }, [lines]);

  useEffect(() => {
    if (hasData) onPeriodChange?.(periodEndValue);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodEndValue, hasData]);

  const [hoverValue, setHoverValue] = useState<number | null>(null);
  const [hoverInfo, setHoverInfo] = useState<{ x: number; y: number; date: string; value: number } | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const getDisplayValue = useCallback((pts: SeriesPoint[]) => {
    return hoverValue ?? pts[pts.length - 1]?.value ?? 0;
  }, [hoverValue]);

  useEffect(() => {
    if (!containerRef.current || loading || !hasData) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      seriesRefs.current = [];
    }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: 11,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: '#f3f4f6', style: LineStyle.Solid },
      },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: {
          width: 1,
          color: '#d1d5db',
          style: LineStyle.Dashed,
          labelVisible: false,
        },
        horzLine: {
          width: 1,
          color: '#d1d5db',
          style: LineStyle.Dashed,
          labelVisible: false,
        },
      },
      rightPriceScale: {
        visible: false,
      },
      leftPriceScale: {
        visible: true,
        borderVisible: false,
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        visible: true,
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: false,
      handleScale: false,
    });

    chartRef.current = chart;

    lines.forEach((line, li) => {
      if (line.data.length < 2) return;

      const lineColor = line.color;
      const chartData = line.data.map(p => ({
        time: toUTCTimestamp(p.date),
        value: p.value,
      }));

      if (singleSeries) {
        const series = chart.addSeries(AreaSeries, {
          lineColor,
          lineWidth: 2,
          topColor: lineColor + '30',
          bottomColor: lineColor + '05',
          crosshairMarkerVisible: true,
          crosshairMarkerRadius: 5,
          crosshairMarkerBorderColor: '#ffffff',
          crosshairMarkerBorderWidth: 2,
          crosshairMarkerBackgroundColor: lineColor,
          priceLineVisible: false,
          lastValueVisible: false,
          priceScaleId: 'left',
        });
        series.setData(chartData as any);

        if (format === 'pct' && line.data.length > 0) {
          series.createPriceLine({
            price: line.data[0].value,
            color: '#d1d5db',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: false,
          });
        }

        seriesRefs.current.push(series);
      } else {
        const series = chart.addSeries(LineSeries, {
          color: lineColor,
          lineWidth: 2,
          crosshairMarkerVisible: true,
          crosshairMarkerRadius: 4,
          crosshairMarkerBorderColor: '#ffffff',
          crosshairMarkerBorderWidth: 2,
          crosshairMarkerBackgroundColor: lineColor,
          priceLineVisible: false,
          lastValueVisible: false,
          priceScaleId: 'left',
        });
        series.setData(chartData as any);
        seriesRefs.current.push(series);
      }
    });

    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove((param: MouseEventParams) => {
      if (!param.time || !param.seriesData || param.seriesData.size === 0) {
        setHoverValue(null);
        setHoverInfo(null);
        onHoverChange?.(null);
        return;
      }

      const firstSeries = seriesRefs.current[0];
      if (!firstSeries) return;
      const sd = param.seriesData.get(firstSeries) as SingleValueData | undefined;
      if (!sd || sd.value === undefined) {
        setHoverValue(null);
        setHoverInfo(null);
        onHoverChange?.(null);
        return;
      }

      const timeVal = param.time as number;
      const d = new Date(timeVal * 1000);
      const dateStr = d.toISOString();
      const isIntraday = lines[0]?.data[0]?.date?.includes('T');
      const formattedDate = isIntraday
        ? d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })
        : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

      const point = param.point;
      if (point) {
        setHoverInfo({ x: point.x, y: point.y, date: formattedDate, value: sd.value });
      }

      setHoverValue(sd.value);
      onHoverChange?.({
        date: dateStr,
        value: sd.value,
        periodEndValue,
      });
    });

    const ro = new ResizeObserver(([entry]) => {
      chart.applyOptions({ width: entry.contentRect.width });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRefs.current = [];
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, hasData, lines, height, singleSeries, format]);

  return (
    <div className={`flex flex-col ${className}`}>
      {!hideHeader && isSymbolMode && hasData && (
        <div className="flex items-end gap-6 mb-1">
          {lines.map((l, li) => {
            const v = getDisplayValue(l.data);
            const displayColor = lines.length > 1 ? l.color : (v >= 0 ? '#10b981' : '#ef4444');
            const dollarAmt = currentPrice ? currentPrice - currentPrice / (1 + v / 100) : null;
            return (
              <div
                key={li}
                className="text-sm font-semibold tabular-nums leading-none transition-colors"
                style={{ color: displayColor }}
              >
                {dollarAmt !== null && (
                  <>{dollarAmt >= 0 ? '+' : '-'}{fmtCurrency(Math.abs(dollarAmt))} </>
                )}
                ({fmtPct(v)})
              </div>
            );
          })}
          {headerRight}
        </div>
      )}

      {!hideRangeTabs && tabsPosition === 'top' && (
        <div className="flex items-center gap-0.5 mb-3">
          {ranges.map(r => (
            <button
              key={r.label}
              onClick={() => setDays(r.days, r.label)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                days === r.days
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      )}

      <div ref={containerRef} className="relative select-none [&_a[href*='tradingview']]:hidden [&_a[href*='tradingview']]:!hidden" style={{ height }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
          </div>
        )}
        {!loading && !hasData && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-400">
            No price data available
          </div>
        )}
        {hoverInfo && (
          <div
            ref={tooltipRef}
            className="absolute z-10 pointer-events-none bg-white border border-gray-200 rounded-xl shadow-lg px-3.5 py-2.5"
            style={{
              left: Math.min(Math.max(hoverInfo.x - 70, 8), (containerRef.current?.clientWidth ?? 300) - 180),
              top: Math.max(hoverInfo.y - (currentPrice ? 90 : 76), 4),
            }}
          >
            <div className="text-[11px] text-gray-400 font-medium">{hoverInfo.date}</div>
            {currentPrice && format === 'pct' && (
              <div className="text-[13px] font-bold tabular-nums mt-0.5 text-gray-900">
                {fmtCurrency(currentPrice / (1 + (periodEndValue / 100)) * (1 + (hoverInfo.value / 100)))}
              </div>
            )}
            <div className={`text-[12px] font-semibold tabular-nums ${currentPrice ? '' : 'mt-0.5'} ${
              hoverInfo.value >= 0 ? 'text-emerald-600' : 'text-red-500'
            }`}>
              {format === 'currency' ? fmtCurrency(hoverInfo.value) : fmtPct(hoverInfo.value)}
            </div>
          </div>
        )}
      </div>

      {!hideRangeTabs && tabsPosition === 'bottom' && (
        <div className="flex items-center gap-0.5 mt-3">
          {ranges.map(r => (
            <button
              key={r.label}
              onClick={() => setDays(r.days, r.label)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                days === r.days
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
