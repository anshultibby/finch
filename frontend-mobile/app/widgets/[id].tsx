import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Alert, Share, AppState } from 'react-native';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Share2, Trash2, Copy, Lock } from 'lucide-react-native';
import { widgetsApi } from '@/lib/api';
import WidgetCanvas from '@/components/widgets/WidgetCanvas';
import type { Widget, WidgetData } from '@/lib/types';

// Public share links open the web app (mobile has no in-app shared route).
const WEB_BASE_URL = process.env.EXPO_PUBLIC_WEB_URL || 'https://finchapp.ai';

export default function WidgetDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [widget, setWidget] = useState<Widget | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [data, setData] = useState<WidgetData | undefined>();
  const [busy, setBusy] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!id) return;
    widgetsApi.get(id).then(setWidget).catch(() => setNotFound(true));
  }, [id]);

  const refresh = useCallback(() => {
    if (!id || AppState.currentState !== 'active') return;
    widgetsApi.getData(id).then(setData).catch(() => {});
  }, [id]);

  // View-driven polling on the widget's interval, paused while backgrounded.
  useEffect(() => {
    if (!widget || !id) return;
    refresh();
    const intervalMs = Math.max(60, widget.spec?.refresh?.interval_seconds || 60) * 1000;
    const start = () => { if (!timerRef.current) timerRef.current = setInterval(refresh, intervalMs); };
    const stop = () => { if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; } };
    start();
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') { refresh(); start(); } else stop();
    });
    return () => { stop(); sub.remove(); };
  }, [widget, id, refresh]);

  const onShare = async () => {
    if (!widget) return;
    setBusy(true);
    try {
      let w = widget;
      if (w.visibility !== 'public' || !w.slug) {
        w = await widgetsApi.publish(widget.id, false);
        setWidget(w);
      }
      if (w.slug) {
        const url = `${WEB_BASE_URL}/share/widget/${w.slug}`;
        await Share.share({ url, message: url });
      }
    } catch {
      Alert.alert('Share failed', 'Could not publish this widget. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const onUnpublish = async () => {
    if (!widget) return;
    setBusy(true);
    try {
      const w = await widgetsApi.publish(widget.id, true);
      setWidget(w);
    } catch {} finally { setBusy(false); }
  };

  const onDelete = () => {
    if (!widget) return;
    Alert.alert('Delete widget', 'Delete this widget? This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          try { await widgetsApi.delete(widget.id); router.back(); } catch {}
        },
      },
    ]);
  };

  const onClone = async () => {
    if (!widget) return;
    setBusy(true);
    try {
      const w = await widgetsApi.clone(widget.id);
      router.replace(`/widgets/${w.id}` as any);
    } catch {
      Alert.alert('Clone failed', 'Could not clone this widget.');
    } finally { setBusy(false); }
  };

  if (notFound) {
    return (
      <View style={{ flex: 1, backgroundColor: '#fafaf9', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 }}>
        <Stack.Screen options={{ title: 'Widget' }} />
        <Text style={{ fontSize: 14, fontFamily: 'DMSans', color: '#6b7280' }}>This widget isn’t available.</Text>
      </View>
    );
  }

  if (!widget) {
    return (
      <View style={{ flex: 1, backgroundColor: '#fafaf9', alignItems: 'center', justifyContent: 'center' }}>
        <Stack.Screen options={{ title: 'Widget' }} />
        <ActivityIndicator color="#059669" />
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: '#fafaf9' }}
      contentContainerStyle={{ padding: 16, paddingBottom: insets.bottom + 32 }}
    >
      <Stack.Screen options={{ title: widget.title || 'Widget' }} />

      {/* Header */}
      <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 14 }}>
        <Text style={{ fontSize: 26 }}>{widget.emoji || '📊'}</Text>
        <View style={{ flex: 1, minWidth: 0 }}>
          <Text style={{ fontSize: 18, fontFamily: 'DMSans-Bold', color: '#111827' }}>{widget.title}</Text>
          {!!widget.description && (
            <Text style={{ fontSize: 13, fontFamily: 'DMSans', color: '#6b7280', marginTop: 2 }}>{widget.description}</Text>
          )}
          {widget.visibility === 'public' && (
            <Text style={{ fontSize: 11.5, fontFamily: 'DMSans', color: '#9ca3af', marginTop: 4 }}>
              Public · {widget.view_count} views · {widget.clone_count} clones
            </Text>
          )}
        </View>
      </View>

      {/* Actions */}
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 18, flexWrap: 'wrap' }}>
        {widget.is_owner ? (
          <>
            <ActionButton icon={<Share2 size={15} color="#fff" />} label={busy ? '…' : widget.visibility === 'public' ? 'Share link' : 'Share'} primary onPress={onShare} disabled={busy} />
            {widget.visibility === 'public' && (
              <ActionButton icon={<Lock size={15} color="#6b7280" />} label="Make private" onPress={onUnpublish} disabled={busy} />
            )}
            <ActionButton icon={<Trash2 size={15} color="#dc2626" />} label="Delete" onPress={onDelete} danger />
          </>
        ) : (
          <ActionButton icon={<Copy size={15} color="#fff" />} label={busy ? '…' : 'Clone to my widgets'} primary onPress={onClone} disabled={busy} />
        )}
      </View>

      <WidgetCanvas spec={widget.spec} data={data} />
    </ScrollView>
  );
}

function ActionButton({
  icon, label, onPress, primary, danger, disabled,
}: {
  icon: React.ReactNode; label: string; onPress: () => void; primary?: boolean; danger?: boolean; disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.8}
      style={{
        flexDirection: 'row', alignItems: 'center', gap: 6,
        paddingHorizontal: 14, paddingVertical: 9, borderRadius: 10,
        backgroundColor: primary ? '#059669' : '#fff',
        borderWidth: primary ? 0 : 1,
        borderColor: danger ? '#fecaca' : '#e5e7eb',
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {icon}
      <Text style={{ fontSize: 13.5, fontFamily: 'DMSans-Medium', color: primary ? '#fff' : danger ? '#dc2626' : '#374151' }}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}
