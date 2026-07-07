import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { AlertTriangle, RefreshCw } from 'lucide-react-native';

/**
 * Inline error banner for data sections that failed to load. Companion to
 * EmptyState: empty = "nothing here yet", this = "we couldn't find out".
 * Sections should never silently render blank on a failed fetch.
 */
export default function DataError({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <View className="flex-row items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
      <View className="flex-row items-center gap-2.5 flex-1">
        <AlertTriangle size={16} color="#f59e0b" />
        <Text className="text-sm font-body text-gray-700 flex-shrink" numberOfLines={2}>{message}</Text>
      </View>
      {onRetry && (
        <TouchableOpacity onPress={onRetry} activeOpacity={0.7} className="flex-row items-center gap-1.5">
          <RefreshCw size={13} color="#111827" />
          <Text className="text-sm font-body-bold text-gray-900">Retry</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
