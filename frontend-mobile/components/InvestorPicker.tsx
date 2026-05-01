import React from 'react';
import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import { Check } from 'lucide-react-native';
import { INVESTOR_PERSONAS, InvestorPersona } from '@/lib/aiPrompts';

const GRADIENT_COLORS: Record<string, string> = {
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
      <Text className="text-[10px] font-body-bold text-slate-400 uppercase tracking-widest mb-2">
        Invest like a legend
      </Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerClassName="gap-2 pb-1"
      >
        {INVESTOR_PERSONAS.map((persona) => {
          const isSelected = selectedId === persona.id;
          const color = GRADIENT_COLORS[persona.id] || '#64748b';

          return (
            <TouchableOpacity
              key={persona.id}
              onPress={() => {
                if (disabled) return;
                onSelect(isSelected ? null : persona);
              }}
              disabled={disabled}
              className={`w-[120px] rounded-xl overflow-hidden border ${
                isSelected ? 'border-slate-900' : 'border-black/5'
              }`}
              activeOpacity={0.7}
            >
              <View style={{ backgroundColor: color }} className="px-3 py-2 flex-row items-center justify-between">
                <Text className="text-white font-body-bold text-xs">{persona.initial}</Text>
                {isSelected && <Check size={12} color="#ffffff" />}
              </View>
              <View className="bg-white px-3 py-2">
                <Text className="text-xs font-body-medium text-slate-900" numberOfLines={1}>
                  {persona.shortName}
                </Text>
                <Text className="text-[10px] font-body text-slate-400 mt-0.5" numberOfLines={1}>
                  {persona.tagline}
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {selectedId && (
        <TouchableOpacity onPress={() => onSelect(null)} className="mt-2" activeOpacity={0.7}>
          <Text className="text-xs font-body text-slate-400">Clear selection</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
