import React, { useMemo } from 'react';
import { View, Text } from 'react-native';
import { WebView } from 'react-native-webview';
import type { TileData } from '@/lib/types';

// The LLM emits a Plotly figure ({data, layout}) in tile.options.figure. If the
// tile also has a data query, live data is bound into the traces by substituting
// $-refs (identical to the web PlotlyTile):
//   $t              → shared time axis (first series' timestamps)
//   $series.LABEL   → that series' values      (series payloads)
//   $col.NAME       → that column's values     (table payloads)
//   $value          → the number               (number payloads)
function bindFigure(figure: any, data?: TileData): any {
  if (!figure) return { data: [], layout: {} };
  if (!data || data.shape === 'static' || data.shape === 'error' || data.shape === 'empty') {
    return figure;
  }
  const lut: Record<string, any> = {};
  if (data.shape === 'series') {
    const series = (data as any).series || [];
    if (series[0]) lut['$t'] = series[0].points.map((p: any) => p.t);
    for (const s of series) lut[`$series.${s.label}`] = s.points.map((p: any) => p.v);
  } else if (data.shape === 'table') {
    const t = data as any;
    (t.columns || []).forEach((c: string, i: number) => { lut[`$col.${c}`] = t.rows.map((r: any[]) => r[i]); });
  } else if (data.shape === 'number') {
    lut['$value'] = (data as any).value;
  }
  const sub = (v: any): any => {
    if (typeof v === 'string' && v.startsWith('$')) return v in lut ? lut[v] : v;
    if (Array.isArray(v)) return v.map(sub);
    if (v && typeof v === 'object') {
      const o: any = {};
      for (const k in v) o[k] = sub(v[k]);
      return o;
    }
    return v;
  };
  return { ...figure, data: sub(figure.data || []) };
}

// Finch chart theme — applied under the LLM's layout (transparent bg so the card
// shows through, emerald-led colorway, quiet gridlines).
const THEME_LAYOUT = {
  autosize: true,
  margin: { l: 44, r: 16, t: 28, b: 36 },
  font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', size: 11, color: '#57534e' },
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  colorway: ['#10b981', '#6366f1', '#f59e0b', '#ef4444', '#0ea5e9', '#ec4899', '#14b8a6'],
  xaxis: { gridcolor: '#f3f4f6', zerolinecolor: '#e5e7eb', automargin: true },
  yaxis: { gridcolor: '#f3f4f6', zerolinecolor: '#e5e7eb', automargin: true },
  legend: { orientation: 'h', y: -0.2, font: { size: 10 } },
  hoverlabel: { bgcolor: '#1c1917', font: { color: '#fff', size: 11 } },
};

// Plotly has no React Native build; we render it inside a WebView (Plotly from
// CDN). The figure is inert data, so this is a self-contained static document.
export default function PlotlyTile({ figure, data, height = 260 }: { figure: any; data?: TileData; height?: number }) {
  const html = useMemo(() => {
    const bound = bindFigure(figure, data);
    if (!bound?.data?.length) return null;
    const layout = { ...THEME_LAYOUT, ...(bound.layout || {}) };
    return `<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>html,body{margin:0;padding:0;background:transparent;overflow:hidden}#c{width:100%;height:100vh}</style>
</head><body><div id="c"></div><script>
try {
  Plotly.newPlot('c', ${JSON.stringify(bound.data)}, ${JSON.stringify(layout)},
    { displaylogo:false, displayModeBar:false, responsive:true });
} catch (e) {}
</script></body></html>`;
  }, [figure, data]);

  if (!html) {
    return (
      <View style={{ height, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ color: '#9ca3af', fontSize: 12, fontFamily: 'DMSans' }}>No chart data</Text>
      </View>
    );
  }

  return (
    <View style={{ height }}>
      <WebView
        source={{ html }}
        style={{ flex: 1, backgroundColor: 'transparent' }}
        originWhitelist={['*']}
        javaScriptEnabled
        scrollEnabled={false}
        showsVerticalScrollIndicator={false}
        showsHorizontalScrollIndicator={false}
        automaticallyAdjustContentInsets={false}
      />
    </View>
  );
}
