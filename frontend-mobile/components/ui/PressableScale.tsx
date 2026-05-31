import React from 'react';
import { Pressable, PressableProps, StyleProp, ViewStyle, GestureResponderEvent } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';
import { SPRING_BOUNCY, PRESS_SCALE } from '@/lib/animations';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/**
 * A Pressable that springs down on press and bounces back on release, with a
 * light haptic on tap. Drop-in replacement for TouchableOpacity where you want
 * a more tactile, lively feel.
 */
export function PressableScale({
  children,
  onPress,
  haptic = true,
  scale = PRESS_SCALE,
  style,
  ...rest
}: {
  children: React.ReactNode;
  onPress?: (e: GestureResponderEvent) => void;
  haptic?: boolean;
  scale?: number;
  style?: StyleProp<ViewStyle>;
} & Omit<PressableProps, 'style' | 'onPress'>) {
  const s = useSharedValue(1);
  const animStyle = useAnimatedStyle(() => ({ transform: [{ scale: s.value }] }));

  return (
    <AnimatedPressable
      onPressIn={() => {
        s.value = withTiming(scale, { duration: 90 });
      }}
      onPressOut={() => {
        s.value = withSpring(1, SPRING_BOUNCY);
      }}
      onPress={(e) => {
        if (haptic) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        onPress?.(e);
      }}
      style={[style, animStyle]}
      {...rest}
    >
      {children}
    </AnimatedPressable>
  );
}
