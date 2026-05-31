import React, { useEffect, useState } from 'react';
import { View, StyleSheet, ViewStyle, DimensionValue } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';

/**
 * A single shimmering placeholder block. A light gradient sweeps across a
 * neutral base on a loop — used to build layout-matched loading states so
 * screens never flash blank.
 */
export function Skeleton({
  width = '100%',
  height = 14,
  radius = 8,
  style,
}: {
  width?: DimensionValue;
  height?: number;
  radius?: number;
  style?: ViewStyle;
}) {
  const [w, setW] = useState(0);
  const x = useSharedValue(0);

  useEffect(() => {
    x.value = withRepeat(withTiming(1, { duration: 1100, easing: Easing.linear }), -1, false);
  }, [x]);

  const sweep = useAnimatedStyle(() => ({
    transform: [{ translateX: -w + x.value * (2 * w) }],
  }));

  return (
    <View
      onLayout={(e) => setW(e.nativeEvent.layout.width)}
      style={[{ width, height, borderRadius: radius, backgroundColor: '#e9ecef', overflow: 'hidden' }, style]}
    >
      {w > 0 && (
        <Animated.View style={[StyleSheet.absoluteFill, sweep]}>
          <LinearGradient
            colors={['transparent', 'rgba(255,255,255,0.7)', 'transparent']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={{ flex: 1 }}
          />
        </Animated.View>
      )}
    </View>
  );
}

/** Convenience: a small horizontal group of skeleton mover cards. */
export function SkeletonMoverRow() {
  return (
    <View style={{ flexDirection: 'row', gap: 10, paddingHorizontal: 16 }}>
      {[0, 1, 2].map((i) => (
        <View key={i} style={styles.moverCard}>
          <Skeleton width={42} height={12} radius={4} />
          <Skeleton width={70} height={9} radius={4} style={{ marginTop: 8 }} />
          <Skeleton width={56} height={15} radius={4} style={{ marginTop: 14 }} />
          <Skeleton width={48} height={11} radius={4} style={{ marginTop: 6 }} />
        </View>
      ))}
    </View>
  );
}

/** A vertical stack of list-row skeletons (watchlist, holdings, search). */
export function SkeletonRows({ count = 6 }: { count?: number }) {
  return (
    <View style={{ paddingHorizontal: 16 }}>
      {Array.from({ length: count }).map((_, i) => (
        <View key={i} style={styles.row}>
          <View style={{ flex: 1 }}>
            <Skeleton width={64} height={14} radius={4} />
            <Skeleton width={120} height={10} radius={4} style={{ marginTop: 7 }} />
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Skeleton width={60} height={14} radius={4} />
            <Skeleton width={40} height={10} radius={4} style={{ marginTop: 7 }} />
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  moverCard: {
    width: 130,
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: '#f3f4f6',
  },
});
