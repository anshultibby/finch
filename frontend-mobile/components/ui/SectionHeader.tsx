import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { ChevronRight } from 'lucide-react-native';

interface SectionHeaderProps {
  title: string;
  action?: string;
  onAction?: () => void;
  count?: number;
}

export default function SectionHeader({ title, action, onAction, count }: SectionHeaderProps) {
  return (
    <View className="flex-row items-center justify-between mb-2.5">
      <View className="flex-row items-center gap-1.5">
        <Text className="text-[13px] font-body-bold text-gray-900 uppercase tracking-wide">{title}</Text>
        {count !== undefined && (
          <View className="bg-gray-100 rounded-full px-1.5 py-px">
            <Text className="text-[11px] font-body-medium text-gray-500">{count}</Text>
          </View>
        )}
      </View>
      {action && onAction && (
        <TouchableOpacity onPress={onAction} className="flex-row items-center gap-0.5" activeOpacity={0.7}>
          <Text className="text-[13px] font-body-medium text-gray-400">{action}</Text>
          <ChevronRight size={13} color="#9ca3af" />
        </TouchableOpacity>
      )}
    </View>
  );
}
