import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { Check } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { INVESTOR_PERSONAS, InvestorPersona } from '@/lib/aiPrompts';

const COLORS_MAP: Record<string, string> = {
  buffett: '#4f46e5',
  munger: '#ea580c',
  marks: '#0d9488',
  lynch: '#7c3aed',
  soros: '#e11d48',
  cathie_wood: '#d946ef',
  damodaran: '#374151',
};

interface InvestorPickerProps {
  selectedId: string | null;
  onSelect: (persona: InvestorPersona | null) => void;
  disabled?: boolean;
}

export default function InvestorPicker({ selectedId, onSelect, disabled }: InvestorPickerProps) {
  return (
    <View>
      <Text className="text-[10px] font-body-bold text-gray-400 uppercase tracking-widest mb-2">
        Invest like a legend
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingBottom: 2 }}>
        {INVESTOR_PERSONAS.map((persona) => {
          const isSelected = selectedId === persona.id;
          const color = COLORS_MAP[persona.id] || '#6b7280';
          return (
            <TouchableOpacity
              key={persona.id}
              onPress={() => {
                if (disabled) return;
                Haptics.selectionAsync();
                onSelect(isSelected ? null : persona);
              }}
              disabled={disabled}
              style={[styles.card, isSelected && styles.cardSelected]}
              activeOpacity={0.7}
            >
              <View style={[styles.header, { backgroundColor: color }]}>
                <Text className="text-white font-body-bold text-[11px]">{persona.initial}</Text>
                {isSelected && <Check size={11} color="#fff" />}
              </View>
              <View className="bg-white px-2.5 py-2">
                <Text className="text-[11px] font-body-medium text-gray-900" numberOfLines={1}>{persona.shortName}</Text>
                <Text className="text-[10px] font-body text-gray-400 mt-px" numberOfLines={1}>{persona.tagline}</Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
      {selectedId && (
        <TouchableOpacity onPress={() => onSelect(null)} className="mt-1.5" activeOpacity={0.7}>
          <Text className="text-[11px] font-body text-gray-400">Clear selection</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: 110,
    borderRadius: 10,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  cardSelected: {
    borderColor: '#111827',
  },
  header: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
});
