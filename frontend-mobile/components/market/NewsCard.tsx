import React from 'react';
import { View, Text, TouchableOpacity, Linking, Image, StyleSheet } from 'react-native';

interface NewsCardProps {
  title: string;
  source: string;
  date: string;
  url?: string;
  compact?: boolean;
  image?: string;
}

export default function NewsCard({ title, source, date, url, compact, image }: NewsCardProps) {
  const handlePress = () => {
    if (url) Linking.openURL(url);
  };

  const formattedDate = (() => {
    try {
      const d = new Date(date);
      const now = new Date();
      const diffH = Math.floor((now.getTime() - d.getTime()) / 3600000);
      if (diffH < 1) return 'Just now';
      if (diffH < 24) return `${diffH}h ago`;
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return date;
    }
  })();

  if (compact) {
    return (
      <TouchableOpacity onPress={handlePress} className="py-2.5" activeOpacity={0.6}>
        <Text className="text-[13px] font-body-medium text-gray-900 leading-[18px]" numberOfLines={2}>{title}</Text>
        <Text className="text-[11px] font-body text-gray-400 mt-1">{source} · {formattedDate}</Text>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      onPress={handlePress}
      style={newsStyles.card}
      activeOpacity={0.7}
    >
      <View style={{ flex: 1 }}>
        <Text className="text-[13px] font-body-medium text-gray-900 leading-[18px]" numberOfLines={3}>{title}</Text>
        <Text className="text-[11px] font-body text-gray-400 mt-1.5">{source} · {formattedDate}</Text>
      </View>
      {image && (
        <Image source={{ uri: image }} style={newsStyles.thumbnail} />
      )}
    </TouchableOpacity>
  );
}

const newsStyles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: '#fff',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  thumbnail: {
    width: 64,
    height: 64,
    borderRadius: 8,
    backgroundColor: '#f3f4f6',
  },
});
