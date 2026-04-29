import { Link, Stack } from 'expo-router';
import { View, Text } from 'react-native';

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: 'Oops!' }} />
      <View className="flex-1 items-center justify-center bg-finch-bg p-5">
        <Text className="text-xl font-body-bold text-slate-900 mb-4">
          This screen doesn't exist.
        </Text>
        <Link href="/">
          <Text className="text-sm font-body text-blue-600">Go to home screen</Text>
        </Link>
      </View>
    </>
  );
}
