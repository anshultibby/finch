import { Easing } from 'react-native-reanimated';

/**
 * Motion tokens — "playful & lively": bouncy springs with a little overshoot,
 * quick-but-visible timings. Keep durations short so the app still feels fast.
 */

// Bouncy spring for pops (button press release, star toggle, badges).
export const SPRING_BOUNCY = { damping: 10, stiffness: 180, mass: 0.7 } as const;

// Softer spring for entrances / layout (cards sliding in, indicators).
export const SPRING_SOFT = { damping: 16, stiffness: 150, mass: 0.9 } as const;

export const DUR = { fast: 160, base: 320, slow: 700 } as const;

// Expressive ease-out (decelerate hard) for draw-ins and fades.
export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);

// Press feedback scale.
export const PRESS_SCALE = 0.94;

// Stagger helper for list entrances.
export const enterDelay = (index: number, step = 55) => index * step;
