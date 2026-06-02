import { useState } from 'react';
import { View, Text, TouchableOpacity, Modal, Pressable } from 'react-native';
import { ChevronDown, Check } from 'lucide-react-native';
import type { ModelOption } from '@/lib/types';
import { COLORS } from '@/lib/constants';

interface ModelPickerProps {
  models: ModelOption[];
  value?: string;            // selected model id (undefined = default)
  onChange: (id: string) => void;
  disabled?: boolean;
}

/** Compact model picker for the chat composer. Renders nothing until models load. */
export default function ModelPicker({ models, value, onChange, disabled }: ModelPickerProps) {
  const [open, setOpen] = useState(false);

  if (!models || models.length === 0) return null;

  const selected = models.find(m => m.id === value) ?? models[0];

  return (
    <>
      <TouchableOpacity
        disabled={disabled}
        onPress={() => setOpen(true)}
        className="flex-row items-center gap-1 px-2 py-1 rounded-lg"
        activeOpacity={0.7}
      >
        <Text className="text-[12px] font-body-medium text-gray-500" numberOfLines={1}>
          {selected?.label}
        </Text>
        <ChevronDown size={12} color={COLORS.gray400} />
      </TouchableOpacity>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable className="flex-1" onPress={() => setOpen(false)}>
          <View className="absolute bottom-28 left-4 right-4 bg-white rounded-2xl border border-gray-200 py-1 shadow-lg">
            {models.map(m => {
              const active = m.id === selected?.id;
              return (
                <TouchableOpacity
                  key={m.id}
                  onPress={() => { onChange(m.id); setOpen(false); }}
                  className="flex-row items-center justify-between px-4 py-2.5"
                  activeOpacity={0.7}
                >
                  <View>
                    <Text className="text-[14px] font-body-medium text-gray-900">{m.label}</Text>
                    {m.provider ? <Text className="text-[11px] font-body text-gray-400">{m.provider}</Text> : null}
                  </View>
                  {active ? <Check size={16} color={COLORS.gray900} /> : null}
                </TouchableOpacity>
              );
            })}
          </View>
        </Pressable>
      </Modal>
    </>
  );
}
