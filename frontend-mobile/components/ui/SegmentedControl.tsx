import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withSpring } from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';
import { SPRING_SOFT } from '@/lib/animations';

interface SegmentedControlProps<T extends string> {
  options: T[];
  selected: T;
  onChange: (value: T) => void;
  labels?: Record<T, string>;
}

const PAD = 3;

export default function SegmentedControl<T extends string>({ options, selected, onChange, labels }: SegmentedControlProps<T>) {
  const [w, setW] = useState(0);
  const idx = Math.max(0, options.indexOf(selected));
  const segW = w > 0 ? (w - PAD * 2) / options.length : 0;
  const tx = useSharedValue(0);

  useEffect(() => {
    tx.value = withSpring(idx * segW, SPRING_SOFT);
  }, [idx, segW, tx]);

  const indicatorStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: tx.value }],
    width: segW,
  }));

  return (
    <View style={styles.container} onLayout={(e) => setW(e.nativeEvent.layout.width)}>
      {segW > 0 && <Animated.View style={[styles.indicator, indicatorStyle]} />}
      {options.map((opt) => {
        const isActive = selected === opt;
        return (
          <TouchableOpacity
            key={opt}
            onPress={() => { Haptics.selectionAsync(); onChange(opt); }}
            style={styles.option}
            activeOpacity={0.7}
          >
            <Text style={[styles.label, isActive && styles.activeLabel]}>
              {labels?.[opt] ?? opt.charAt(0).toUpperCase() + opt.slice(1)}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: '#f3f4f6',
    borderRadius: 10,
    padding: PAD,
  },
  indicator: {
    position: 'absolute',
    top: PAD,
    bottom: PAD,
    left: PAD,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 3,
    elevation: 2,
  },
  option: {
    flex: 1,
    paddingVertical: 7,
    borderRadius: 8,
    alignItems: 'center',
  },
  label: {
    fontSize: 13,
    fontFamily: 'DMSans-Medium',
    color: '#6b7280',
  },
  activeLabel: {
    color: '#111827',
  },
});
