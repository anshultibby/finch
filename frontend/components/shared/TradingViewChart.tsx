'use client';

import React, { useEffect, useRef } from 'react';

interface TradingViewChartProps {
  symbol: string;
  height?: number;
  interval?: string;
  theme?: 'light' | 'dark';
  className?: string;
}

export default function TradingViewChart({
  symbol,
  height,
  interval = 'D',
  theme = 'light',
  className = '',
}: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef(`tv_${Math.random().toString(36).slice(2)}`);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.innerHTML = '';

    const containerId = widgetIdRef.current;
    const wrapper = document.createElement('div');
    wrapper.id = containerId;
    wrapper.style.height = '100%';
    wrapper.style.width = '100%';
    el.appendChild(wrapper);

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.async = true;
    script.onload = () => {
      if (typeof (window as any).TradingView !== 'undefined') {
        new (window as any).TradingView.widget({
          autosize: true,
          symbol,
          interval,
          timezone: 'Etc/UTC',
          theme,
          style: '1',
          locale: 'en',
          toolbar_bg: theme === 'light' ? '#fff' : '#1f2937',
          enable_publishing: false,
          allow_symbol_change: false,
          hide_top_toolbar: true,
          hide_legend: false,
          save_image: false,
          container_id: containerId,
        });
      }
    };
    el.appendChild(script);

    return () => { el.innerHTML = ''; };
  }, [symbol, interval, theme]);

  return (
    <div
      ref={containerRef}
      className={`w-full ${className}`}
      style={{ height: height ? `${height}px` : '100%' }}
    />
  );
}
