import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, TextInput, StyleSheet, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Search, X, ArrowUpRight } from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { marketApi, watchlistApi } from '@/lib/api';
import { useStartChat } from '@/hooks/useStartChat';
import { COLORS, formatCurrency, formatPct } from '@/lib/constants';
import ScreenHeader from '@/components/ui/ScreenHeader';

// Financials: find a company, land on its statements. Filed numbers come from
// the statements themselves (with SEC links on the stock page); anything
// interpretive is handed to Finch in chat, labelled as such.

const DEEP_DIVES = [
  { label: 'Read the latest 10-K for me', prompt: (s: string) => `Read ${s}'s latest 10-K and give me: what changed vs. last year, the 3 biggest risks they disclosed, and anything buried in the footnotes. Quote the filing.` },
  { label: 'Is it cheap or expensive?', prompt: (s: string) => `Is ${s} cheap or expensive right now? Compare its valuation multiples to its own 5-year history and its closest peers, then take a stance.` },
  { label: 'Bull vs. bear case', prompt: (s: string) => `Give me the strongest bull case and the strongest bear case for ${s}, each backed by numbers from the financials. Then tell me which side you'd take.` },
];

export default function ResearchScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const startChat = useStartChat();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [mine, setMine] = useState<string[]>([]);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!user) return;
    watchlistApi.getWatchlist(user.id)
      .then(d => setMine((d.symbols || d.watchlist || []).map((i: any) => (typeof i === 'string' ? i : i.symbol)).filter(Boolean)))
      .catch(() => {});
  }, [user]);

  const onChange = useCallback((text: string) => {
    setQ(text);
    if (debounce.current) clearTimeout(debounce.current);
    if (!text.trim()) { setResults([]); return; }
    debounce.current = setTimeout(async () => {
      setSearching(true);
      try {
        const d = await marketApi.searchStocks(text.trim(), 10);
        setResults(d.results || d || []);
      } catch { setResults([]); }
      finally { setSearching(false); }
    }, 250);
  }, []);

  const open = (symbol: string) => router.push(`/stock/${symbol}?tab=financials`);
  const focusSymbol = mine[0] || 'AAPL';

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScreenHeader title="Financials" subtitle="Statements, filings, earnings calls" />
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <View style={styles.search}>
          <Search size={16} color={COLORS.gray400} />
          <TextInput
            testID="research-search"
            value={q}
            onChangeText={onChange}
            placeholder="Search a company or ticker"
            placeholderTextColor={COLORS.gray400}
            style={styles.input}
            autoCapitalize="characters"
            autoCorrect={false}
            autoFocus={!user}
          />
          {q ? (
            <TouchableOpacity onPress={() => onChange('')} style={{ padding: 4 }}><X size={16} color={COLORS.gray500} /></TouchableOpacity>
          ) : null}
        </View>

        {q.trim() ? (
          searching ? (
            <ActivityIndicator style={{ marginTop: 24 }} color={COLORS.gray500} />
          ) : (
            <View style={[styles.list, { marginTop: 12 }]}>
              {results.length === 0 ? (
                <Text style={styles.empty}>No matches for “{q}”.</Text>
              ) : results.map((r, i) => (
                <TouchableOpacity key={r.symbol} onPress={() => open(r.symbol)} style={[styles.row, i > 0 && styles.divider]} activeOpacity={0.6}>
                  <View style={{ flex: 1, marginRight: 10 }}>
                    <Text style={styles.sym}>{r.symbol}</Text>
                    <Text style={styles.name} numberOfLines={1}>{r.name}</Text>
                  </View>
                  {r.price != null && (
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text style={styles.price}>{formatCurrency(r.price, false, r.symbol)}</Text>
                      <Text style={[styles.chg, { color: (r.changesPercentage ?? 0) >= 0 ? COLORS.emerald : COLORS.red }]}>{formatPct(r.changesPercentage)}</Text>
                    </View>
                  )}
                </TouchableOpacity>
              ))}
            </View>
          )
        ) : (
          <>
            {mine.length > 0 && (
              <>
                <Text style={styles.section}>Your stocks</Text>
                <View style={styles.chips}>
                  {mine.slice(0, 16).map(s => (
                    <TouchableOpacity key={s} onPress={() => open(s)} style={styles.chip} activeOpacity={0.75}>
                      <Text style={styles.chipText}>{s}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </>
            )}

            <Text style={styles.section}>Have Finch dig in{mine.length > 0 ? ` · ${focusSymbol}` : ''}</Text>
            <View style={styles.list}>
              {DEEP_DIVES.map((d, i) => (
                <TouchableOpacity key={d.label} onPress={() => startChat(d.prompt(focusSymbol))} style={[styles.row, i > 0 && styles.divider]} activeOpacity={0.7}>
                  <Text style={[styles.name, { flex: 1, color: COLORS.gray900, fontSize: 14 }]}>{d.label}</Text>
                  <ArrowUpRight size={15} color={COLORS.gray400} />
                </TouchableOpacity>
              ))}
            </View>
            <Text style={styles.note}>
              Statements are as filed (via Financial Modeling Prep, with SEC links on each stock). Finch's read of them is AI-generated — check the source before acting.
            </Text>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fafaf9' },
  scroll: { paddingHorizontal: 16, paddingBottom: 40, maxWidth: 760, width: '100%', alignSelf: 'center' },
  search: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#fff', borderRadius: 14, borderWidth: 1, borderColor: COLORS.gray200, paddingHorizontal: 12 },
  input: { flex: 1, fontFamily: 'DMSans', fontSize: 15.5, color: COLORS.gray900, paddingVertical: 12 },
  section: { fontFamily: 'DMSans-Bold', fontSize: 15, color: '#1c1917', marginTop: 20, marginBottom: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, backgroundColor: '#fff', borderWidth: 1, borderColor: COLORS.gray200 },
  chipText: { fontFamily: 'DMSans-Bold', fontSize: 13, color: COLORS.gray900 },
  list: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: COLORS.gray100, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 12 },
  divider: { borderTopWidth: 1, borderTopColor: COLORS.gray100 },
  sym: { fontFamily: 'DMSans-Bold', fontSize: 15, color: COLORS.gray900 },
  name: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray500, marginTop: 1 },
  price: { fontFamily: 'DMSans-Medium', fontSize: 15, color: COLORS.gray900, fontVariant: ['tabular-nums'] },
  chg: { fontFamily: 'DMSans', fontSize: 12.5, fontVariant: ['tabular-nums'] },
  empty: { fontFamily: 'DMSans', fontSize: 14, color: COLORS.gray500, padding: 16, textAlign: 'center' },
  note: { fontFamily: 'DMSans', fontSize: 11.5, color: COLORS.gray400, marginTop: 14, lineHeight: 16 },
});
