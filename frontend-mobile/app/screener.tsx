import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, TextInput, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Sparkles, ArrowUp, Eye } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { marketApi, jobsApi, type ScreenerFilters, type ScreenerResult } from '@/lib/api';
import { useStartChat } from '@/hooks/useStartChat';
import { COLORS, formatCurrency } from '@/lib/constants';
import ScreenHeader from '@/components/ui/ScreenHeader';
import DataError from '@/components/ui/DataError';
import { SkeletonRows } from '@/components/ui/Skeleton';

// Two ways in: say it in plain English (Finch runs the screen in chat, shows
// the filters it used, ranks and explains), or tap exact filters here. Either
// way a screen can become a watcher that only pings on NEW matches.

type Cap = 'small' | 'mid' | 'large' | 'mega';
type Beta = 'low' | 'high';
type Draft = { sector?: string; cap?: Cap; beta?: Beta; dividend?: boolean };

const SECTORS = [
  'Technology', 'Healthcare', 'Financial Services', 'Consumer Cyclical', 'Industrials',
  'Communication Services', 'Consumer Defensive', 'Energy', 'Utilities', 'Real Estate', 'Basic Materials',
];

const CAPS: { key: Cap; label: string; min?: number; max?: number }[] = [
  { key: 'small', label: 'Small', min: 300e6, max: 2e9 },
  { key: 'mid', label: 'Mid', min: 2e9, max: 10e9 },
  { key: 'large', label: 'Large', min: 10e9, max: 200e9 },
  { key: 'mega', label: 'Mega', min: 200e9 },
];

const PRESETS: { label: string; draft: Draft }[] = [
  { label: 'Mega-cap leaders', draft: { cap: 'mega' } },
  { label: 'Dividend payers', draft: { cap: 'large', dividend: true } },
  { label: 'Steady compounders', draft: { cap: 'large', beta: 'low' } },
  { label: 'High-beta movers', draft: { cap: 'mid', beta: 'high' } },
  { label: 'Small-cap tech', draft: { sector: 'Technology', cap: 'small' } },
  { label: 'Healthcare mid-caps', draft: { sector: 'Healthcare', cap: 'mid' } },
];

const NL_EXAMPLES = [
  'Profitable software companies growing revenue 20%+',
  'Beaten-down large caps with strong balance sheets',
  'Dividend stocks yielding 3%+ that raised the payout 5 years running',
];

function toFilters(d: Draft): ScreenerFilters {
  const cap = CAPS.find(c => c.key === d.cap);
  return {
    sector: d.sector,
    market_cap_min: cap?.min ?? 300e6,
    market_cap_max: cap?.max,
    beta_max: d.beta === 'low' ? 0.8 : undefined,
    beta_min: d.beta === 'high' ? 1.5 : undefined,
    dividend_min: d.dividend ? 0.5 : undefined,
    volume_min: 100_000,
  };
}

function describe(d: Draft): string {
  const parts: string[] = [];
  if (d.cap) parts.push(`${CAPS.find(c => c.key === d.cap)?.label.toLowerCase()}-cap`);
  if (d.sector) parts.push(d.sector);
  parts.push('US stocks');
  if (d.beta === 'low') parts.push('with beta under 0.8');
  if (d.beta === 'high') parts.push('with beta over 1.5');
  if (d.dividend) parts.push('that pay a dividend');
  return parts.join(' ');
}

function nextWeekdayAt(hour: number): string {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  if (d.getTime() <= Date.now()) d.setDate(d.getDate() + 1);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  return d.toISOString();
}

function Chip({ label, active, onPress }: { label: string; active?: boolean; onPress: () => void }) {
  return (
    <TouchableOpacity onPress={() => { Haptics.selectionAsync(); onPress(); }} activeOpacity={0.75} style={[styles.chip, active && styles.chipActive]}>
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

export default function ScreenerScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const startChat = useStartChat();
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState<Draft>(PRESETS[0].draft);
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [watching, setWatching] = useState(false);

  const filters = useMemo(() => toFilters(draft), [draft]);

  const run = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      setResults(await marketApi.screen(filters, 40));
    } catch {
      setError(true);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { run(); }, [run]);

  const askFinch = (q: string) => {
    const text = q.trim();
    if (!text) return;
    startChat(
      `Screen the market for: ${text}\n\nUse the stock screener and fundamentals. Show the exact filters you applied, then a ranked table of the top 10 with one line on why each made the cut. Flag anything that barely qualifies. End by offering to watch this screen and ping me only when new names qualify.`,
    );
  };

  const watchScreen = async () => {
    if (!user) { router.push('/(auth)/login'); return; }
    setWatching(true);
    try {
      const label = describe(draft);
      await jobsApi.create({
        name: `Watch screen: ${label}`,
        message: `Run this stock screen: ${label} (US-listed, average volume over 100k). Compare against the names you reported last time and tell me ONLY about new names that now qualify, with one line on why each is interesting. If nothing new qualifies, say so in one sentence and don't notify me.`,
        run_at: nextWeekdayAt(9),
        recurrence: 'weekdays',
      });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      Alert.alert('Watching this screen', 'Finch will re-run it every weekday morning and tell you only when new names qualify. Manage it under Watching.');
    } catch (e: any) {
      Alert.alert("Couldn't set that up", e?.response?.data?.detail || 'You may have reached your plan\'s automation limit.');
    } finally {
      setWatching(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="Screener" subtitle="Describe it, or tap the filters" />
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        {/* Plain-English screen → Finch */}
        <View style={styles.askCard}>
          <View style={styles.askRow}>
            <Sparkles size={16} color={COLORS.emerald} />
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder="Describe the stocks you want…"
              placeholderTextColor={COLORS.gray400}
              style={styles.askInput}
              returnKeyType="send"
              onSubmitEditing={() => askFinch(query)}
              multiline={false}
            />
            <TouchableOpacity
              onPress={() => askFinch(query)}
              disabled={!query.trim()}
              style={[styles.send, { backgroundColor: query.trim() ? COLORS.emerald : COLORS.gray200 }]}
              accessibilityLabel="Ask Finch to screen"
            >
              <ArrowUp size={16} color="#fff" strokeWidth={2.6} />
            </TouchableOpacity>
          </View>
          {NL_EXAMPLES.map(ex => (
            <TouchableOpacity key={ex} onPress={() => askFinch(ex)} style={styles.example} activeOpacity={0.7}>
              <Text style={styles.exampleText} numberOfLines={1}>“{ex}”</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Presets */}
        <Text style={styles.section}>Start from</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {PRESETS.map(p => (
            <Chip key={p.label} label={p.label} active={JSON.stringify(p.draft) === JSON.stringify(draft)} onPress={() => setDraft(p.draft)} />
          ))}
        </ScrollView>

        {/* Exact, editable filters */}
        <Text style={styles.section}>Filters</Text>
        <View style={styles.filterCard}>
          <Text style={styles.filterLabel}>Size</Text>
          <View style={styles.wrapRow}>
            <Chip label="Any" active={!draft.cap} onPress={() => setDraft(d => ({ ...d, cap: undefined }))} />
            {CAPS.map(c => <Chip key={c.key} label={c.label} active={draft.cap === c.key} onPress={() => setDraft(d => ({ ...d, cap: c.key }))} />)}
          </View>
          <Text style={styles.filterLabel}>Volatility</Text>
          <View style={styles.wrapRow}>
            <Chip label="Any" active={!draft.beta} onPress={() => setDraft(d => ({ ...d, beta: undefined }))} />
            <Chip label="Steady (β<0.8)" active={draft.beta === 'low'} onPress={() => setDraft(d => ({ ...d, beta: 'low' }))} />
            <Chip label="Jumpy (β>1.5)" active={draft.beta === 'high'} onPress={() => setDraft(d => ({ ...d, beta: 'high' }))} />
          </View>
          <Text style={styles.filterLabel}>Income</Text>
          <View style={styles.wrapRow}>
            <Chip label="Any" active={!draft.dividend} onPress={() => setDraft(d => ({ ...d, dividend: undefined }))} />
            <Chip label="Pays a dividend" active={!!draft.dividend} onPress={() => setDraft(d => ({ ...d, dividend: true }))} />
          </View>
          <Text style={styles.filterLabel}>Sector</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
            <Chip label="All" active={!draft.sector} onPress={() => setDraft(d => ({ ...d, sector: undefined }))} />
            {SECTORS.map(s => <Chip key={s} label={s} active={draft.sector === s} onPress={() => setDraft(d => ({ ...d, sector: s }))} />)}
          </ScrollView>
        </View>

        {/* Results */}
        <View style={styles.resultsHead}>
          <Text style={styles.section}>{loading ? 'Screening…' : `${results.length} matches`}</Text>
          <TouchableOpacity onPress={watchScreen} disabled={watching} style={styles.watchBtn} activeOpacity={0.8}>
            {watching ? <ActivityIndicator size="small" color={COLORS.emerald} /> : <Eye size={14} color={COLORS.emerald} />}
            <Text style={styles.watchText}>Watch this screen</Text>
          </TouchableOpacity>
        </View>
        {loading ? (
          <SkeletonRows count={6} />
        ) : error ? (
          <DataError message="Couldn't run that screen" onRetry={run} />
        ) : results.length === 0 ? (
          <Text style={styles.empty}>Nothing matches. Loosen a filter, or describe what you want above.</Text>
        ) : (
          <View style={styles.list}>
            {results.map((r, i) => (
              <TouchableOpacity
                key={r.symbol}
                onPress={() => router.push(`/stock/${r.symbol}`)}
                style={[styles.row, i > 0 && styles.rowDivider]}
                activeOpacity={0.6}
              >
                <View style={{ flex: 1, marginRight: 12 }}>
                  <Text style={styles.sym}>{r.symbol}</Text>
                  <Text style={styles.name} numberOfLines={1}>{r.name}{r.industry ? ` · ${r.industry}` : ''}</Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <Text style={styles.price}>{formatCurrency(r.price)}</Text>
                  <Text style={styles.cap}>{formatCurrency(r.market_cap, true)} cap</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}
        <Text style={styles.source}>Data: Financial Modeling Prep. Filters are exact; Finch's explanations are AI-generated.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fafaf9' },
  scroll: { paddingHorizontal: 16, paddingBottom: 40, maxWidth: 760, width: '100%', alignSelf: 'center' },
  askCard: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: '#d1fae5', padding: 12 },
  askRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingLeft: 4 },
  askInput: { flex: 1, fontFamily: 'DMSans', fontSize: 15, color: COLORS.gray900, paddingVertical: 8 },
  send: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  example: { paddingVertical: 6, paddingHorizontal: 4 },
  exampleText: { fontFamily: 'DMSans', fontSize: 13, color: COLORS.gray500 },
  section: { fontFamily: 'DMSans-Bold', fontSize: 12, color: COLORS.gray500, textTransform: 'uppercase', letterSpacing: 0.6, marginTop: 20, marginBottom: 8 },
  chipRow: { gap: 8, paddingRight: 8 },
  wrapRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, backgroundColor: '#fff', borderWidth: 1, borderColor: COLORS.gray200 },
  chipActive: { backgroundColor: '#ecfdf5', borderColor: '#6ee7b7' },
  chipText: { fontFamily: 'DMSans-Medium', fontSize: 13, color: COLORS.gray700 },
  chipTextActive: { color: '#047857' },
  filterCard: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, padding: 14, gap: 8 },
  filterLabel: { fontFamily: 'DMSans-Bold', fontSize: 13, color: COLORS.gray900, marginTop: 4 },
  resultsHead: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' },
  watchBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, backgroundColor: '#ecfdf5', marginBottom: 6 },
  watchText: { fontFamily: 'DMSans-Bold', fontSize: 12.5, color: COLORS.emerald },
  list: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 12 },
  rowDivider: { borderTopWidth: 1, borderTopColor: COLORS.gray100 },
  sym: { fontFamily: 'DMSans-Bold', fontSize: 15, color: COLORS.gray900 },
  name: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray500, marginTop: 1 },
  price: { fontFamily: 'DMSans-Medium', fontSize: 15, color: COLORS.gray900, fontVariant: ['tabular-nums'] },
  cap: { fontFamily: 'DMSans', fontSize: 12, color: COLORS.gray400, fontVariant: ['tabular-nums'] },
  empty: { fontFamily: 'DMSans', fontSize: 14, color: COLORS.gray500, paddingVertical: 20, textAlign: 'center' },
  source: { fontFamily: 'DMSans', fontSize: 11, color: COLORS.gray400, marginTop: 14, textAlign: 'center' },
});
