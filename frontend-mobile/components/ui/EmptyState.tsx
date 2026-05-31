import React from 'react';
import { View, Text } from 'react-native';
import Animated, { FadeInDown, ZoomIn } from 'react-native-reanimated';
import { PressableScale } from './PressableScale';

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
      <Animated.View entering={ZoomIn.springify().damping(11).mass(0.6)}>
        {icon}
      </Animated.View>
      <Animated.View entering={FadeInDown.delay(90).springify().damping(15)} className="items-center">
        <Text className="text-base font-body-medium text-gray-400 mt-4 text-center">{title}</Text>
        {description && (
          <Text className="text-[13px] font-body text-gray-400 mt-1 text-center leading-5">{description}</Text>
        )}
      </Animated.View>
      {actionLabel && onAction && (
        <Animated.View entering={FadeInDown.delay(180).springify().damping(15)}>
          <PressableScale onPress={onAction} style={{ marginTop: 20, backgroundColor: '#111827', borderRadius: 12, paddingHorizontal: 20, paddingVertical: 10 }}>
            <Text className="text-white font-body-medium text-[13px]">{actionLabel}</Text>
          </PressableScale>
        </Animated.View>
      )}
    </View>
  );
}
