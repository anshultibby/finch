import React from 'react';
import { View, Text } from 'react-native';
import Svg, { Rect } from 'react-native-svg';

interface FinchLogoProps {
  size?: number;
  showText?: boolean;
}

// Canonical Finch mark: bar-chart forming an "F" on an emerald rounded square
// (matches web `frontend/components/shared/FinchLogo.tsx` and the app icon).
export default function FinchLogo({ size = 28, showText = false }: FinchLogoProps) {
  return (
    <View className="flex-row items-center gap-2">
      <Svg width={size} height={size} viewBox="0 0 36 36" fill="none">
        <Rect width="36" height="36" rx="8" fill="#10b981" />
        <Rect x="8" y="8" width="5" height="20" rx="1.5" fill="white" />
        <Rect x="15" y="8" width="5" height="12" rx="1.5" fill="white" />
        <Rect x="22" y="14" width="5" height="6" rx="1.5" fill="white" />
      </Svg>
      {showText && (
        <Text className="text-base font-body-bold text-gray-900 tracking-tight">Finch</Text>
      )}
    </View>
  );
}
