import { View, Text, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginScreen() {
  const { signInWithGoogle } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const handleSignIn = async () => {
    setIsLoading(true);
    try {
      await signInWithGoogle();
    } catch (error) {
      console.error('Sign in error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <View className="flex-1 bg-finch-bg items-center justify-center px-8">
      <View className="items-center mb-16">
        <Text className="text-5xl font-body-bold text-slate-900 mb-2">Finch</Text>
        <Text className="text-lg font-body text-slate-500">AI-powered trading</Text>
      </View>

      <TouchableOpacity
        onPress={handleSignIn}
        disabled={isLoading}
        className="w-full bg-slate-900 rounded-2xl py-4 px-6 items-center flex-row justify-center"
        activeOpacity={0.8}
      >
        {isLoading ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text className="text-white font-body-medium text-base">
            Continue with Google
          </Text>
        )}
      </TouchableOpacity>

      <Text className="text-xs text-slate-400 mt-6 text-center font-body">
        By continuing, you agree to our Terms of Service and Privacy Policy
      </Text>
    </View>
  );
}
