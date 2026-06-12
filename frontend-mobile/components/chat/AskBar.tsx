import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native';
import { ArrowUp, Sparkles } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/contexts/AuthContext';
import { chatApi } from '@/lib/api';
import { COLORS } from '@/lib/constants';
import * as Haptics from 'expo-haptics';

/**
 * A persistent "Ask anything about …" composer docked at the bottom of a
 * content screen (markets, a stock). Submitting spins up a fresh chat seeded
 * with the typed question (optionally prefixed with context) and jumps into it
 * — fusing the dashboard with the AI chat, Perplexity-Finance style.
 */
export default function AskBar({ placeholder = 'Ask anything…', prefix }: { placeholder?: string; prefix?: string }) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const { user } = useAuth();

  const hasContent = text.trim().length > 0;

  // Guests can't chat (account-based, costs credits) — the whole bar becomes a
  // sign-in affordance instead of an editable input.
  if (!user) {
    return (
      <View style={styles.wrap}>
        <TouchableOpacity
          style={styles.bar}
          onPress={() => router.push('/(auth)/login')}
          activeOpacity={0.8}
        >
          <Sparkles size={16} color={COLORS.emerald} />
          <Text style={[styles.input, styles.guestPlaceholder]} numberOfLines={1}>
            Sign in to ask Finch anything
          </Text>
          <View style={[styles.send, { backgroundColor: '#e5e7eb' }]}>
            <ArrowUp size={16} color="#9ca3af" strokeWidth={2.6} />
          </View>
        </TouchableOpacity>
      </View>
    );
  }

  const submit = async () => {
    const q = text.trim();
    if (!q || busy) return;
    setBusy(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    try {
      const chatId = await chatApi.createChat(user.id);
      const seed = prefix ? `${prefix}${q}` : q;
      setText('');
      router.push(`/(tabs)/chat/${chatId}?seed=${encodeURIComponent(seed)}`);
    } catch {
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        <Sparkles size={16} color={COLORS.emerald} />
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder={placeholder}
          placeholderTextColor={COLORS.gray400}
          style={styles.input}
          multiline
          onSubmitEditing={submit}
          blurOnSubmit
          returnKeyType="send"
        />
        <TouchableOpacity
          onPress={submit}
          disabled={!hasContent || busy}
          style={[styles.send, { backgroundColor: hasContent ? COLORS.emerald : '#e5e7eb' }]}
          activeOpacity={0.85}
        >
          <ArrowUp size={16} color={hasContent ? '#fff' : '#9ca3af'} strokeWidth={2.6} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 10,
    backgroundColor: 'transparent',
  },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    backgroundColor: '#ffffff',
    borderRadius: 22,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.07)',
    paddingLeft: 14,
    paddingRight: 6,
    minHeight: 48,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 14,
    elevation: 4,
  },
  input: {
    flex: 1,
    fontSize: 15,
    fontFamily: 'DMSans',
    color: '#0f172a',
    paddingVertical: 10,
    maxHeight: 96,
  },
  guestPlaceholder: {
    color: '#9ca3af',
  },
  send: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
