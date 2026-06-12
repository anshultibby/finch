import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { Lock } from 'lucide-react-native';

/**
 * Inline gate for account-based features (watchlist, portfolio, chat, …).
 * Guests can browse markets freely (App Store guideline 5.1.1); anything that
 * needs a server-side account renders this instead of hard-redirecting.
 */
export default function SignInPrompt({
  title = 'Sign in to continue',
  description,
}: {
  title?: string;
  description: string;
}) {
  const router = useRouter();

  return (
    <View style={styles.wrap}>
      <View style={styles.iconCircle}>
        <Lock size={24} color="#059669" />
      </View>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.desc}>{description}</Text>
      <TouchableOpacity
        style={styles.btn}
        onPress={() => router.push('/(auth)/login')}
        activeOpacity={0.85}
      >
        <Text style={styles.btnText}>Sign in or create account</Text>
      </TouchableOpacity>
      <Text style={styles.hint}>Free to sign up · No credit card required</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 36,
    paddingBottom: 40,
    // Keep the prompt readable on wide layouts (iPad landscape).
    alignSelf: 'center',
    width: '100%',
    maxWidth: 440,
  },
  iconCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#ecfdf5',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontFamily: 'DMSans-Bold',
    color: '#111827',
    marginBottom: 8,
    textAlign: 'center',
  },
  desc: {
    fontSize: 14,
    fontFamily: 'DMSans',
    color: '#9ca3af',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  btn: {
    backgroundColor: '#059669',
    paddingHorizontal: 24,
    paddingVertical: 13,
    borderRadius: 12,
    alignSelf: 'stretch',
    alignItems: 'center',
  },
  btnText: {
    fontSize: 15,
    fontFamily: 'DMSans-Medium',
    color: '#ffffff',
  },
  hint: {
    fontSize: 12,
    fontFamily: 'DMSans',
    color: '#d1d5db',
    marginTop: 12,
  },
});
