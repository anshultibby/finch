import { Link, Stack } from 'expo-router';
import { View, Text } from 'react-native';

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: 'Not Found' }} />
      <View className="flex-1 items-center justify-center bg-white px-8">
        <Text className="text-xl font-body-bold text-gray-900">Page not found</Text>
        <Link href="/" className="mt-4">
          <Text className="text-emerald-600 font-body-medium">Go home</Text>
        </Link>
      </View>
    </>
  );
}
