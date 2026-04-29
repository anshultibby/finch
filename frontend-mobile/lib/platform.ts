import { Platform } from 'react-native';

export const isNative = () => Platform.OS !== 'web';
export const isIOS = () => Platform.OS === 'ios';
export const isAndroid = () => Platform.OS === 'android';
export const isWeb = () => Platform.OS === 'web';
