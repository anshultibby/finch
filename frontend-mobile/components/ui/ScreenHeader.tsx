import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { ChevronLeft } from 'lucide-react-native';
import { COLORS } from '@/lib/constants';

/**
 * Header for the card destinations (Screener, Trader, Calendar, …). Each of
 * those screens is one tap from home, so the only navigation it needs is a
 * back chevron — no drawer, no tabs.
 */
export default function ScreenHeader({ title, subtitle, right }: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}) {
  const router = useRouter();
  const goBack = () => (router.canGoBack() ? router.back() : router.replace('/(tabs)'));

  return (
    <View style={styles.header}>
      <TouchableOpacity onPress={goBack} style={styles.back} activeOpacity={0.7} accessibilityLabel="Back">
        <ChevronLeft size={24} color={COLORS.gray900} />
      </TouchableOpacity>
      <View style={styles.titles}>
        <Text style={styles.title} numberOfLines={1}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text> : null}
      </View>
      <View style={styles.right}>{right}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, paddingTop: 4, paddingBottom: 10 },
  back: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  titles: { flex: 1, marginLeft: 2 },
  title: { fontFamily: 'DMSans-Bold', fontSize: 20, color: COLORS.gray900, letterSpacing: -0.3 },
  subtitle: { fontFamily: 'DMSans', fontSize: 12.5, color: COLORS.gray500, marginTop: 1 },
  right: { minWidth: 40, alignItems: 'flex-end', paddingRight: 8 },
});
