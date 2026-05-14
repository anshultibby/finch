import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';

interface SegmentedControlProps<T extends string> {
  options: T[];
  selected: T;
  onChange: (value: T) => void;
  labels?: Record<T, string>;
}

export default function SegmentedControl<T extends string>({ options, selected, onChange, labels }: SegmentedControlProps<T>) {
  return (
    <View style={styles.container}>
      {options.map((opt) => {
        const isActive = selected === opt;
        return (
          <TouchableOpacity
            key={opt}
            onPress={() => { Haptics.selectionAsync(); onChange(opt); }}
            style={[styles.option, isActive && styles.activeOption]}
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
    padding: 3,
  },
  option: {
    flex: 1,
    paddingVertical: 7,
    borderRadius: 8,
    alignItems: 'center',
  },
  activeOption: {
    backgroundColor: '#ffffff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 3,
    elevation: 2,
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
