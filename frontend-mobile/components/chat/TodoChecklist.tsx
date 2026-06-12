import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { Check } from 'lucide-react-native';
import type { TodoItem } from '@/lib/types';

/**
 * Live task-phase checklist shown while the agent works on a long task.
 * Fed by `todo_update` SSE events (the update_todos tool) — each event
 * replaces the whole list. Ephemeral: rendered only during streaming.
 */
export default function TodoChecklist({ items }: { items: TodoItem[] }) {
  if (items.length === 0) return null;
  const done = items.filter(i => i.status === 'completed').length;

  return (
    <View style={styles.card}>
      <Text style={styles.header}>TASKS · {done}/{items.length}</Text>
      {items.map((item, i) => (
        <View key={i} style={styles.row}>
          <View style={styles.iconSlot}>
            {item.status === 'completed' ? (
              <Check size={12} color="#10b981" strokeWidth={3} />
            ) : item.status === 'in_progress' ? (
              <PulsingDot />
            ) : (
              <View style={styles.pendingCircle} />
            )}
          </View>
          <Text
            style={[
              styles.text,
              item.status === 'completed' && styles.textDone,
              item.status === 'in_progress' && styles.textActive,
            ]}
          >
            {item.text}
          </Text>
        </View>
      ))}
    </View>
  );
}

function PulsingDot() {
  const halo = useSharedValue(0);
  useEffect(() => {
    halo.value = withRepeat(
      withTiming(1, { duration: 1100, easing: Easing.out(Easing.ease) }),
      -1,
      false
    );
  }, [halo]);

  const haloStyle = useAnimatedStyle(() => ({
    opacity: 0.5 * (1 - halo.value),
    transform: [{ scale: 0.6 + halo.value * 0.9 }],
  }));

  return (
    <View style={styles.dotWrap}>
      <Animated.View style={[styles.dotHalo, haloStyle]} />
      <View style={styles.dotCore} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    alignSelf: 'flex-start',
    minWidth: 200,
    maxWidth: '100%',
    backgroundColor: 'rgba(250,250,249,0.6)',
    borderWidth: 1,
    borderColor: '#f5f5f4',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 8,
    gap: 4,
  },
  header: {
    fontSize: 10,
    fontFamily: 'DMSans-Medium',
    letterSpacing: 0.6,
    color: '#a8a29e',
    marginBottom: 2,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  iconSlot: {
    width: 14,
    height: 14,
    marginTop: 3,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pendingCircle: {
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 1.5,
    borderColor: '#d6d3d1',
  },
  dotWrap: {
    width: 12,
    height: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dotHalo: {
    position: 'absolute',
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#34d399',
  },
  dotCore: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#10b981',
  },
  text: {
    flex: 1,
    fontSize: 12,
    lineHeight: 18,
    fontFamily: 'DMSans',
    color: '#a8a29e',
  },
  textDone: {
    textDecorationLine: 'line-through',
    textDecorationColor: '#d6d3d1',
  },
  textActive: {
    color: '#44403c',
    fontFamily: 'DMSans-Medium',
  },
});
