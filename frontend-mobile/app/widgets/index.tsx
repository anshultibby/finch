import React, { useCallback, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LogIn } from 'lucide-react-native';
import { widgetsApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import type { WidgetSummary } from '@/lib/types';

export default function WidgetsListScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const [widgets, setWidgets] = useState<WidgetSummary[] | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!user) { setWidgets([]); return; }
    try {
      const list = await widgetsApi.list();
      setWidgets(list);
    } catch {
      setWidgets([]);
    }
  }, [user]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  if (!user) {
    return (
      <View style={{ flex: 1, backgroundColor: '#fafaf9', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 }}>
        <Text style={{ fontSize: 40, marginBottom: 12 }}>📊</Text>
        <Text style={{ fontSize: 17, fontFamily: 'DMSans-Bold', color: '#111827', marginBottom: 6 }}>Live widgets</Text>
        <Text style={{ fontSize: 13.5, fontFamily: 'DMSans', color: '#6b7280', textAlign: 'center', marginBottom: 20, lineHeight: 19 }}>
          Sign in to build and view agent-made dashboards — trackers for any theme, event, or your portfolio.
        </Text>
        <TouchableOpacity
          onPress={() => router.push('/(auth)/login')}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#059669', paddingHorizontal: 20, paddingVertical: 11, borderRadius: 12 }}
          activeOpacity={0.85}
        >
          <LogIn size={16} color="#fff" />
          <Text style={{ fontSize: 14, fontFamily: 'DMSans-Medium', color: '#fff' }}>Sign in</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (widgets === null) {
    return (
      <View style={{ flex: 1, backgroundColor: '#fafaf9', alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color="#059669" />
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: '#fafaf9' }}
      contentContainerStyle={{ padding: 16, paddingBottom: insets.bottom + 24 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#059669" />}
    >
      {widgets.length === 0 ? (
        <View style={{ alignItems: 'center', justifyContent: 'center', paddingTop: 96, paddingHorizontal: 24 }}>
          <Text style={{ fontSize: 40, marginBottom: 12 }}>📊</Text>
          <Text style={{ fontSize: 17, fontFamily: 'DMSans-Bold', color: '#111827', marginBottom: 6 }}>No widgets yet</Text>
          <Text style={{ fontSize: 13.5, fontFamily: 'DMSans', color: '#6b7280', textAlign: 'center', lineHeight: 19 }}>
            Ask the agent to build one — “make me a tracker for oil and the Strait of Hormuz”, or “a widget for my portfolio”.
          </Text>
        </View>
      ) : (
        <View style={{ gap: 10 }}>
          {widgets.map((w) => (
            <TouchableOpacity
              key={w.id}
              activeOpacity={0.7}
              onPress={() => router.push(`/widgets/${w.id}` as any)}
              style={{ flexDirection: 'row', gap: 12, backgroundColor: '#fff', borderRadius: 14, borderWidth: 1, borderColor: '#e5e7eb', padding: 14 }}
            >
              <Text style={{ fontSize: 24 }}>{w.emoji || '📊'}</Text>
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={{ fontSize: 15, fontFamily: 'DMSans-Bold', color: '#111827' }} numberOfLines={1}>{w.title}</Text>
                {!!w.description && (
                  <Text style={{ fontSize: 12.5, fontFamily: 'DMSans', color: '#6b7280', marginTop: 2 }} numberOfLines={2}>{w.description}</Text>
                )}
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  {w.visibility === 'public' && (
                    <View style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 5, backgroundColor: '#ecfdf5', borderWidth: 1, borderColor: '#a7f3d0' }}>
                      <Text style={{ fontSize: 10, fontFamily: 'DMSans-Medium', color: '#047857' }}>Public</Text>
                    </View>
                  )}
                  {(w.tags || []).slice(0, 2).map((t) => (
                    <View key={t} style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 5, backgroundColor: '#f9fafb', borderWidth: 1, borderColor: '#e5e7eb' }}>
                      <Text style={{ fontSize: 10, fontFamily: 'DMSans', color: '#6b7280' }}>{t}</Text>
                    </View>
                  ))}
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </ScrollView>
  );
}
