import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, TextInput, Linking } from 'react-native';
import Markdown from 'react-native-markdown-display';
import WidgetChart from './WidgetChart';
import WidgetSparkline from './WidgetSparkline';
import PlotlyTile from './PlotlyTile';
import { applyControls, initControlState, type ControlState } from './tableControls';
import type {
  Tile, TileData, Control, SeriesData, TableData, NumberData, OddsData, NewsData, MarkdownData,
} from '@/lib/types';

const num = (v: number | null | undefined, digits = 2) =>
  v == null ? '—' : v.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });

// Auto-compact for big standalone figures: 1,284 / 12.9K / $4.2M.
const compact = (v: number | null | undefined, prefix = '') => {
  if (v == null) return '—';
  const a = Math.abs(v);
  if (a >= 1e9) return `${prefix}${(v / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `${prefix}${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e4) return `${prefix}${(v / 1e3).toFixed(1)}K`;
  return `${prefix}${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};

const deltaColor = (v: number | null | undefined) => (v == null ? '#9ca3af' : v >= 0 ? '#059669' : '#ef4444');

const mdStyles = {
  body: { color: '#374151', fontSize: 13.5, lineHeight: 20, fontFamily: 'DMSans' },
  strong: { fontFamily: 'DMSans-Bold', color: '#111827' },
  heading1: { fontSize: 16, fontFamily: 'DMSans-Bold', color: '#111827', marginTop: 8, marginBottom: 4 },
  heading2: { fontSize: 15, fontFamily: 'DMSans-Bold', color: '#111827', marginTop: 6, marginBottom: 3 },
  link: { color: '#059669' },
  bullet_list: { marginVertical: 2 },
  paragraph: { marginTop: 0, marginBottom: 6 },
};

// ── states ────────────────────────────────────────────────────────────────
function EmptyTile({ reason }: { reason: string }) {
  const msg =
    reason === 'connect_portfolio' ? 'Connect your portfolio to see yours' :
    reason === 'empty_watchlist' ? 'Your watchlist is empty' :
    'No data';
  return (
    <View style={{ minHeight: 72, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16 }}>
      <Text style={{ color: '#9ca3af', fontSize: 13, fontFamily: 'DMSans', textAlign: 'center' }}>{msg}</Text>
    </View>
  );
}

function ErrorTile() {
  return (
    <View style={{ minHeight: 72, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16 }}>
      <Text style={{ color: '#9ca3af', fontSize: 12, fontFamily: 'DMSans', textAlign: 'center' }}>
        Couldn’t load this tile
      </Text>
    </View>
  );
}

// ── tiles ─────────────────────────────────────────────────────────────────
function ChartTile({ data, options }: { data: SeriesData; options?: Record<string, any> }) {
  return (
    <WidgetChart
      data={data}
      yFormat={options?.y_format || 'number'}
      showLegend={options?.show_legend !== false}
      height={options?.height || 200}
    />
  );
}

function StatTile({ data, options }: { data: NumberData; options?: Record<string, any> }) {
  const fmt = options?.format;
  const prefix = fmt === 'currency' ? '$' : '';
  const suffix = fmt === 'pct' ? '%' : '';
  const delta = data.delta_pct ?? data.delta;
  return (
    <View style={{ justifyContent: 'center' }}>
      {!!data.label && <Text style={{ fontSize: 12, color: '#6b7280', fontFamily: 'DMSans', marginBottom: 4 }} numberOfLines={1}>{data.label}</Text>}
      <Text style={{ fontSize: 34, lineHeight: 38, color: '#111827', fontFamily: 'DMSans-Bold', letterSpacing: -0.5 }}>
        {compact(data.value, prefix)}{suffix}
      </Text>
      {delta != null && (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 }}>
          <View style={{
            flexDirection: 'row', alignItems: 'center', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6,
            backgroundColor: delta >= 0 ? '#ecfdf5' : '#fef2f2',
          }}>
            <Text style={{ fontSize: 12, fontFamily: 'DMSans-Medium', color: delta >= 0 ? '#047857' : '#dc2626' }}>
              {delta >= 0 ? '▲' : '▼'} {data.delta != null ? num(Math.abs(data.delta)) : ''}
              {data.delta_pct != null ? ` (${num(Math.abs(data.delta_pct))}%)` : ''}
            </Text>
          </View>
          <Text style={{ fontSize: 11, color: '#9ca3af', fontFamily: 'DMSans' }}>today</Text>
        </View>
      )}
      {options?.show_sparkline !== false && data.sparkline && data.sparkline.length > 1 && (
        <View style={{ marginTop: 12 }}>
          <WidgetSparkline data={data.sparkline} width={150} height={36} />
        </View>
      )}
    </View>
  );
}

function OddsTile({ data }: { data: OddsData }) {
  const pct = data.prob == null ? null : Math.round(data.prob * 100);
  const close = data.close_date
    ? new Date(data.close_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : null;
  return (
    <View style={{ justifyContent: 'center' }}>
      <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8 }}>
        <Text style={{ fontSize: 38, lineHeight: 40, color: '#111827', fontFamily: 'DMSans-Bold', letterSpacing: -0.5 }}>
          {pct == null ? '—' : `${pct}%`}
        </Text>
        <Text style={{ fontSize: 11, color: '#9ca3af', fontFamily: 'DMSans', textTransform: 'uppercase', marginBottom: 4 }}>chance</Text>
      </View>
      {pct != null && (
        <View style={{ marginTop: 10, height: 8, borderRadius: 4, backgroundColor: '#d1fae5', overflow: 'hidden' }}>
          <View style={{ height: '100%', borderRadius: 4, backgroundColor: '#10b981', width: `${pct}%` }} />
        </View>
      )}
      {!!data.title && <Text style={{ fontSize: 12.5, color: '#4b5563', fontFamily: 'DMSans', marginTop: 10, lineHeight: 17 }} numberOfLines={2}>{data.title}</Text>}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 }}>
        {!!close && <Text style={{ fontSize: 11, color: '#9ca3af', fontFamily: 'DMSans' }}>Resolves {close}</Text>}
        {data.history && data.history.length > 1 && (
          <WidgetSparkline data={data.history.map((h) => h.v ?? 0)} color="#6366f1" width={70} height={20} />
        )}
      </View>
    </View>
  );
}

function NewsTile({ data, options }: { data: NewsData; options?: Record<string, any> }) {
  if (!data.items?.length) return <EmptyTile reason="no_news" />;
  return (
    <View>
      {data.items.map((n, i) => (
        <TouchableOpacity
          key={i}
          activeOpacity={0.6}
          onPress={() => n.url && Linking.openURL(n.url).catch(() => {})}
          style={{ paddingVertical: 8, borderTopWidth: i === 0 ? 0 : 1, borderTopColor: '#f3f4f6' }}
        >
          <Text style={{ fontSize: 13.5, color: '#1f2937', fontFamily: 'DMSans', lineHeight: 18 }} numberOfLines={2}>{n.title}</Text>
          {options?.compact !== true && (n.source || n.published_at) && (
            <Text style={{ fontSize: 11, color: '#9ca3af', fontFamily: 'DMSans', marginTop: 2 }}>
              {n.source}{n.source && n.published_at ? ' · ' : ''}
              {n.published_at ? new Date(n.published_at).toLocaleDateString() : ''}
            </Text>
          )}
        </TouchableOpacity>
      ))}
    </View>
  );
}

// ── table controls (RN control bar) ─────────────────────────────────────────
const chipBase = {
  paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, borderWidth: 1, marginRight: 6,
};
function TableControlBar({
  data, controls, state, onChange,
}: {
  data: TableData; controls: Control[]; state: ControlState; onChange: (id: string, v: any) => void;
}) {
  return (
    <View style={{ marginBottom: 10, gap: 8 }}>
      {controls.map((ctrl) => {
        if (ctrl.type === 'search') {
          return (
            <TextInput
              key={ctrl.id}
              value={state[ctrl.id] || ''}
              onChangeText={(t) => onChange(ctrl.id, t)}
              placeholder={ctrl.label || 'Search…'}
              placeholderTextColor="#9ca3af"
              style={{
                borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 7,
                fontSize: 13, fontFamily: 'DMSans', color: '#374151', backgroundColor: '#fff',
              }}
            />
          );
        }
        if (ctrl.type === 'select') {
          const i = data.columns.indexOf(ctrl.column);
          const opts = ctrl.options || (i >= 0
            ? Array.from(new Set(data.rows.map((r) => String(r[i] ?? '')).filter(Boolean))).sort()
            : []);
          const cur = state[ctrl.id] || '';
          return (
            <View key={ctrl.id}>
              <Text style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'DMSans-Medium', textTransform: 'uppercase', marginBottom: 4 }}>{ctrl.label}</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {['', ...opts].map((o) => {
                  const active = cur === o;
                  return (
                    <TouchableOpacity
                      key={o || '__all'}
                      onPress={() => onChange(ctrl.id, o)}
                      style={[chipBase, { borderColor: active ? '#10b981' : '#e5e7eb', backgroundColor: active ? '#ecfdf5' : '#fff' }]}
                    >
                      <Text style={{ fontSize: 12.5, fontFamily: 'DMSans-Medium', color: active ? '#047857' : '#6b7280' }}>{o || 'All'}</Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>
            </View>
          );
        }
        if (ctrl.type === 'range') {
          const [lo, hi] = (state[ctrl.id] as [number, number]) || [ctrl.min ?? 0, ctrl.max ?? 0];
          return (
            <View key={ctrl.id}>
              <Text style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'DMSans-Medium', textTransform: 'uppercase', marginBottom: 4 }}>{ctrl.label}</Text>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <TextInput
                  value={String(lo)} keyboardType="numeric"
                  onChangeText={(t) => onChange(ctrl.id, [Number(t) || 0, hi])}
                  style={{ width: 70, borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 6, fontSize: 13, fontFamily: 'DMSans', color: '#374151' }}
                />
                <Text style={{ color: '#d1d5db' }}>–</Text>
                <TextInput
                  value={String(hi)} keyboardType="numeric"
                  onChangeText={(t) => onChange(ctrl.id, [lo, Number(t) || 0])}
                  style={{ width: 70, borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 6, fontSize: 13, fontFamily: 'DMSans', color: '#374151' }}
                />
              </View>
            </View>
          );
        }
        // sort
        const cur = state[ctrl.id] || { column: '', desc: true };
        return (
          <View key={ctrl.id}>
            <Text style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'DMSans-Medium', textTransform: 'uppercase', marginBottom: 4 }}>{ctrl.label}</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {ctrl.columns.map((c) => {
                const active = cur.column === c;
                return (
                  <TouchableOpacity
                    key={c}
                    onPress={() => onChange(ctrl.id, active ? { ...cur, desc: !cur.desc } : { ...cur, column: c })}
                    style={[chipBase, { flexDirection: 'row', alignItems: 'center', gap: 3, borderColor: active ? '#10b981' : '#e5e7eb', backgroundColor: active ? '#ecfdf5' : '#fff' }]}
                  >
                    <Text style={{ fontSize: 12.5, fontFamily: 'DMSans-Medium', color: active ? '#047857' : '#6b7280' }}>{c.replace(/_/g, ' ')}</Text>
                    {active && <Text style={{ fontSize: 11, color: '#047857' }}>{cur.desc ? '▼' : '▲'}</Text>}
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>
        );
      })}
    </View>
  );
}

function TableTile({ data, options, controls }: { data: TableData; options?: Record<string, any>; controls?: Control[] }) {
  const hasControls = !!controls?.length;
  const [state, setState] = useState<ControlState>(() => (hasControls ? initControlState(data, controls!) : {}));
  const shown = hasControls ? applyControls(data, controls!, state) : data;

  let cols = data.columns || [];
  let colIdx = cols.map((_, i) => i);
  if (options?.columns?.length) {
    colIdx = options.columns.map((c: string) => data.columns.indexOf(c)).filter((i: number) => i >= 0);
    cols = colIdx.map((i: number) => data.columns[i]);
  }
  const pctCol = data.columns.findIndex((c) => c.includes('pct') || c.includes('change'));

  return (
    <View>
      {hasControls && (
        <TableControlBar data={data} controls={controls!} state={state} onChange={(id, v) => setState((s) => ({ ...s, [id]: v }))} />
      )}
      <ScrollView horizontal showsHorizontalScrollIndicator>
        <View>
          {/* header */}
          <View style={{ flexDirection: 'row' }}>
            {cols.map((c) => (
              <Text
                key={c}
                style={{ width: 110, fontSize: 10.5, color: '#9ca3af', fontFamily: 'DMSans-Medium', textTransform: 'uppercase', paddingHorizontal: 6, paddingVertical: 4 }}
                numberOfLines={1}
              >
                {c.replace(/_/g, ' ')}
              </Text>
            ))}
          </View>
          {shown.rows.map((row, r) => (
            <View key={r} style={{ flexDirection: 'row', borderTopWidth: 1, borderTopColor: '#f3f4f6' }}>
              {colIdx.map((ci: number, c: number) => {
                const val = row[ci];
                const isPct = ci === pctCol && typeof val === 'number';
                return (
                  <Text
                    key={c}
                    style={{
                      width: 110, paddingHorizontal: 6, paddingVertical: 7, fontSize: 13,
                      fontFamily: c === 0 ? 'DMSans-Medium' : 'DMSans',
                      color: isPct ? deltaColor(val as number) : '#1f2937',
                    }}
                    numberOfLines={1}
                  >
                    {typeof val === 'number' ? num(val) + (isPct ? '%' : '') : (val ?? '—')}
                  </Text>
                );
              })}
            </View>
          ))}
          {shown.rows.length === 0 && (
            <Text style={{ paddingVertical: 16, textAlign: 'center', color: '#9ca3af', fontSize: 12, fontFamily: 'DMSans' }}>No matches</Text>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

function TextTile({ data }: { data: MarkdownData }) {
  return <Markdown style={mdStyles as any}>{data.text || ''}</Markdown>;
}

// ── dispatcher ──────────────────────────────────────────────────────────────
export function TileBody({ tile, data }: { tile: Tile; data?: TileData }) {
  // chart_spec keys off the tile (Plotly figure in options), not the data shape.
  if (tile.type === 'chart_spec') {
    const figure = tile.options?.figure;
    const hasQuery = !!tile.query;
    if (hasQuery && !data) return <Skeleton h={200} />;
    if (data?.shape === 'error') return <ErrorTile />;
    return <PlotlyTile figure={figure} data={data} height={tile.options?.height} />;
  }

  if (!data) return <Skeleton h={80} />;
  if (data.shape === 'error') return <ErrorTile />;
  if (data.shape === 'empty') return <EmptyTile reason={(data as any).reason} />;

  switch (data.shape) {
    case 'series': return <ChartTile data={data} options={tile.options} />;
    case 'number': return <StatTile data={data} options={tile.options} />;
    case 'odds': return <OddsTile data={data} />;
    case 'news': return <NewsTile data={data} options={tile.options} />;
    case 'table': return <TableTile data={data} options={tile.options} controls={tile.controls} />;
    case 'markdown': return <TextTile data={data} />;
    default: return <ErrorTile />;
  }
}

function Skeleton({ h }: { h: number }) {
  return <View style={{ minHeight: h, borderRadius: 8, backgroundColor: '#f3f4f6' }} />;
}
