import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { Feather, Sparkles } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { useAuth } from '@/contexts/AuthContext';
import {
  thesesApi, VERDICT_META, THESIS_STATUS_META,
  type Thesis, type ThesisCheck, type ThesisStance,
} from '@/lib/api';
import { useStartChat } from '@/hooks/useStartChat';
import { COLORS } from '@/lib/constants';

const STANCES: { key: ThesisStance; label: string }[] = [
  { key: 'own', label: 'I own it' },
  { key: 'watch', label: 'Watching' },
  { key: 'avoid', label: 'Avoiding' },
];

/**
 * "Your thesis" on a stock: why the user owns/watches it and what would make
 * them wrong. Finch judges every move, earnings report and dividend change on
 * this name against it (backend: services/theses.py, stored in the memory
 * store at store/theses/{SYMBOL}.md). Shows today's check and the story log.
 */
export default function ThesisCard({ symbol }: { symbol: string }) {
  const { user } = useAuth();
  const startChat = useStartChat();
  const [thesis, setThesis] = useState<Thesis | null | undefined>(undefined);
  const [check, setCheck] = useState<ThesisCheck | null>(null);
  const [editing, setEditing] = useState(false);
  const [why, setWhy] = useState('');
  const [breaks, setBreaks] = useState('');
  const [stance, setStance] = useState<ThesisStance>('own');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const t = await thesesApi.get(symbol);
      setThesis(t);
      if (t) thesesApi.check(symbol).then(setCheck).catch(() => {});
    } catch {
      setThesis(null);
    }
  }, [user, symbol]);

  useEffect(() => { load(); }, [load]);

  if (!user || thesis === undefined) return null;

  const startEdit = () => {
    setWhy(thesis?.why || '');
    setBreaks(thesis?.breaks || '');
    setStance(thesis?.stance || 'own');
    setError(null);
    setEditing(true);
  };

  const save = async () => {
    if (!why.trim()) { setError('Say why in a sentence — that’s what Finch checks against.'); return; }
    setSaving(true);
    try {
      const t = await thesesApi.save(symbol, { why: why.trim(), breaks: breaks.trim(), stance });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setThesis(t);
      setEditing(false);
      setCheck(null);
      thesesApi.check(symbol).then(setCheck).catch(() => {});
    } catch {
      setError("Couldn't save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  const draftWithFinch = () => startChat(
    `Help me write my thesis on ${symbol}. Ask me why I own or am watching it and what would make me wrong — push me to make the "wrong if" concrete and checkable. When I confirm, save it with save_thesis.`,
  );

  // ── empty / editing ──
  if (!thesis || editing) {
    return (
      <View style={styles.card}>
        <View style={styles.head}>
          <Feather size={15} color={COLORS.emerald} />
          <Text style={styles.title}>{thesis ? `Edit your ${symbol} thesis` : `Why ${symbol}?`}</Text>
        </View>
        {!thesis && !editing ? (
          <>
            <Text style={styles.sub}>
              Write down why you own or watch it, and what would make you wrong. Finch will judge every move, earnings report and dividend change against your words.
            </Text>
            <View style={styles.row}>
              <TouchableOpacity onPress={startEdit} style={styles.primary} activeOpacity={0.85}>
                <Text style={styles.primaryText}>Write it</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={draftWithFinch} style={styles.secondary} activeOpacity={0.85}>
                <Sparkles size={13} color={COLORS.emerald} />
                <Text style={styles.secondaryText}>Draft it with Finch</Text>
              </TouchableOpacity>
            </View>
          </>
        ) : (
          <>
            <View style={styles.stances}>
              {STANCES.map(s => (
                <TouchableOpacity key={s.key} onPress={() => setStance(s.key)} activeOpacity={0.8}
                  style={[styles.stance, stance === s.key && styles.stanceOn]}>
                  <Text style={[styles.stanceText, stance === s.key && styles.stanceTextOn]}>{s.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <Text style={styles.label}>Why</Text>
            <TextInput value={why} onChangeText={setWhy} multiline placeholder="e.g. Ad tier keeps revenue growing 12%+ with margins expanding"
              placeholderTextColor={COLORS.gray400} style={styles.input} />
            <Text style={styles.label}>I'm wrong if…</Text>
            <TextInput value={breaks} onChangeText={setBreaks} multiline placeholder="e.g. Subscriber growth stalls two quarters running"
              placeholderTextColor={COLORS.gray400} style={styles.input} />
            {error && <Text style={styles.error}>{error}</Text>}
            <View style={styles.row}>
              <TouchableOpacity onPress={save} disabled={saving} style={styles.primary} activeOpacity={0.85}>
                {saving ? <ActivityIndicator size="small" color="#fff" /> : <Text style={styles.primaryText}>Save thesis</Text>}
              </TouchableOpacity>
              {thesis && (
                <TouchableOpacity onPress={() => setEditing(false)} style={styles.secondary}>
                  <Text style={[styles.secondaryText, { color: COLORS.gray500 }]}>Cancel</Text>
                </TouchableOpacity>
              )}
            </View>
          </>
        )}
      </View>
    );
  }

  // ── saved thesis ──
  return (
    <View style={styles.card}>
      <View style={[styles.head, { justifyContent: 'space-between' }]}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <Feather size={15} color={COLORS.emerald} />
          <Text style={styles.title}>Your thesis</Text>
          <Text style={styles.stancePill}>{STANCES.find(s => s.key === thesis.stance)?.label}</Text>
        </View>
        <TouchableOpacity onPress={startEdit}><Text style={styles.edit}>Edit</Text></TouchableOpacity>
      </View>
      <Text style={styles.why}>{thesis.why}</Text>
      {!!thesis.breaks && (
        <Text style={styles.breaks}><Text style={{ fontFamily: 'DMSans-Bold', color: COLORS.gray900 }}>Wrong if: </Text>{thesis.breaks}</Text>
      )}

      {check?.check ? (
        <View style={styles.today}>
          <View style={[styles.chip, { backgroundColor: THESIS_STATUS_META[check.check.status].bg }]}>
            <Text style={[styles.chipText, { color: THESIS_STATUS_META[check.check.status].fg }]}>
              Today · {THESIS_STATUS_META[check.check.status].label}
            </Text>
          </View>
          <Text style={styles.reason}>{check.check.reason}</Text>
        </View>
      ) : !check ? (
        <View style={[styles.today, { flexDirection: 'row', alignItems: 'center', gap: 6 }]}>
          <ActivityIndicator size="small" color={COLORS.gray400} />
          <Text style={styles.reason}>Checking today against your thesis…</Text>
        </View>
      ) : null}

      {thesis.log.length > 0 && (
        <View style={{ marginTop: 10 }}>
          <Text style={styles.label}>Story so far</Text>
          {thesis.log.slice(-3).reverse().map((e, i) => (
            <View key={`${e.date}-${i}`} style={styles.logRow}>
              <Text style={styles.logDate}>{new Date(`${e.date}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</Text>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', gap: 4, marginBottom: 2 }}>
                  {e.verdict && VERDICT_META[e.verdict] && (
                    <Text style={[styles.tiny, { color: VERDICT_META[e.verdict].fg, backgroundColor: VERDICT_META[e.verdict].bg }]}>{VERDICT_META[e.verdict].label}</Text>
                  )}
                  {e.status && (
                    <Text style={[styles.tiny, { color: THESIS_STATUS_META[e.status].fg, backgroundColor: THESIS_STATUS_META[e.status].bg }]}>{e.status}</Text>
                  )}
                </View>
                <Text style={styles.logNote} numberOfLines={3}>{e.note}</Text>
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#fff', borderRadius: 16, borderWidth: 1, borderColor: '#d1fae5', padding: 14, marginTop: 12 },
  head: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  title: { fontFamily: 'DMSans-Bold', fontSize: 15, color: COLORS.gray900 },
  sub: { fontFamily: 'DMSans', fontSize: 13, color: COLORS.gray500, lineHeight: 18 },
  row: { flexDirection: 'row', gap: 8, marginTop: 12, alignItems: 'center' },
  primary: { backgroundColor: COLORS.emerald, borderRadius: 999, paddingHorizontal: 16, paddingVertical: 9, minWidth: 90, alignItems: 'center' },
  primaryText: { color: '#fff', fontFamily: 'DMSans-Bold', fontSize: 13.5 },
  secondary: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 12, paddingVertical: 9, borderRadius: 999, backgroundColor: '#ecfdf5' },
  secondaryText: { fontFamily: 'DMSans-Bold', fontSize: 13, color: COLORS.emerald },
  stances: { flexDirection: 'row', gap: 6, marginBottom: 6 },
  stance: { paddingHorizontal: 11, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: COLORS.gray200 },
  stanceOn: { backgroundColor: '#ecfdf5', borderColor: '#6ee7b7' },
  stanceText: { fontFamily: 'DMSans-Medium', fontSize: 12.5, color: COLORS.gray700 },
  stanceTextOn: { color: '#047857' },
  label: { fontFamily: 'DMSans-Bold', fontSize: 12, color: COLORS.gray500, textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 8, marginBottom: 4 },
  input: { borderWidth: 1, borderColor: COLORS.gray200, borderRadius: 12, padding: 10, minHeight: 56, fontFamily: 'DMSans', fontSize: 14, color: COLORS.gray900, textAlignVertical: 'top' },
  error: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.red, marginTop: 6 },
  stancePill: { fontFamily: 'DMSans-Medium', fontSize: 11, color: COLORS.gray500, backgroundColor: COLORS.gray100, paddingHorizontal: 6, paddingVertical: 1, borderRadius: 6, overflow: 'hidden' },
  edit: { fontFamily: 'DMSans-Bold', fontSize: 13, color: COLORS.emerald },
  why: { fontFamily: 'DMSans', fontSize: 14, color: COLORS.gray900, lineHeight: 20 },
  breaks: { fontFamily: 'DMSans', fontSize: 13, color: COLORS.gray700, lineHeight: 19, marginTop: 6 },
  today: { marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: COLORS.gray100 },
  chip: { alignSelf: 'flex-start', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2, marginBottom: 4 },
  chipText: { fontFamily: 'DMSans-Bold', fontSize: 11 },
  reason: { fontFamily: 'DMSans', fontSize: 13, color: COLORS.gray700, lineHeight: 18 },
  logRow: { flexDirection: 'row', gap: 10, paddingVertical: 6 },
  logDate: { fontFamily: 'DMSans-Medium', fontSize: 12, color: COLORS.gray400, width: 44, marginTop: 1 },
  tiny: { fontFamily: 'DMSans-Bold', fontSize: 10, paddingHorizontal: 5, paddingVertical: 1, borderRadius: 5, overflow: 'hidden' },
  logNote: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray700, lineHeight: 17 },
});
