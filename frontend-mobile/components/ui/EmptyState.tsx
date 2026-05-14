import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function EmptyState({ icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <View className="flex-1 items-center justify-center px-8 py-20">
      {icon}
      <Text className="text-base font-body-medium text-gray-400 mt-4 text-center">{title}</Text>
      {description && (
        <Text className="text-[13px] font-body text-gray-400 mt-1 text-center leading-5">{description}</Text>
      )}
      {actionLabel && onAction && (
        <TouchableOpacity
          onPress={onAction}
          className="mt-5 bg-gray-900 rounded-xl px-5 py-2.5"
          activeOpacity={0.8}
        >
          <Text className="text-white font-body-medium text-[13px]">{actionLabel}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
