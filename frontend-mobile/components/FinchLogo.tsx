import React from 'react';
import { View, Text } from 'react-native';
import Svg, { Rect, Path, Circle } from 'react-native-svg';

interface FinchLogoProps {
  size?: number;
  showText?: boolean;
}

export default function FinchLogo({ size = 28, showText = false }: FinchLogoProps) {
  return (
    <View className="flex-row items-center gap-2">
      <Svg width={size} height={size} viewBox="0 0 36 36" fill="none">
        <Rect width="36" height="36" rx="8" fill="#10b981" />
        <Path
          d="M10 22C10 22 9 18 11 15C13 12 16 11 18 10L22 8"
          stroke="white"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M22 8L24 13L26 10L28 12"
          stroke="white"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M12 19C14 17 16 16 18 16"
          stroke="rgba(255,255,255,0.5)"
          strokeWidth={2}
          strokeLinecap="round"
        />
        <Circle cx="19" cy="11.5" r="1.5" fill="white" />
        <Circle cx="24" cy="13" r="1" fill="rgba(255,255,255,0.6)" />
        <Circle cx="28" cy="12" r="1" fill="rgba(255,255,255,0.6)" />
      </Svg>
      {showText && (
        <Text className="text-base font-body-bold text-gray-900 tracking-tight">Finch</Text>
      )}
    </View>
  );
}
