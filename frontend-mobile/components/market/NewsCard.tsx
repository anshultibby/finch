import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Linking, Image, StyleSheet } from 'react-native';
import { ChevronDown, ExternalLink } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { COLORS, formatRelativeTime } from '@/lib/constants';

interface NewsCardProps {
  title: string;
  source: string;
  date: string;
  url?: string;
  compact?: boolean;
  image?: string;
  symbol?: string;
  onSymbolPress?: (symbol: string) => void;
}

export default function NewsCard({ title, source, date, url, compact, image, symbol, onSymbolPress }: NewsCardProps) {
  const [open, setOpen] = useState(false);

  const openUrl = () => { if (url) Linking.openURL(url); };
  const when = (() => { try { return formatRelativeTime(date); } catch { return date; } })();

  if (compact) {
    return (
      <TouchableOpacity onPress={openUrl} className="py-2.5" activeOpacity={0.6}>
        <Text className="text-[13px] font-body-medium text-gray-900 leading-[18px]" numberOfLines={2}>{title}</Text>
        <Text className="text-[11px] font-body text-gray-400 mt-1">{source} · {when}</Text>
      </TouchableOpacity>
    );
  }

  return (
    <View style={newsStyles.card}>
      {/* Collapsed row — tap to expand */}
      <TouchableOpacity
        onPress={() => { Haptics.selectionAsync(); setOpen(o => !o); }}
        style={newsStyles.row}
        activeOpacity={0.7}
      >
        <View style={{ flex: 1 }}>
          <Text className="text-[13px] font-body-medium text-gray-900 leading-[18px]" numberOfLines={open ? undefined : 2}>{title}</Text>
          <View style={newsStyles.metaRow}>
            {!!symbol && (
              <TouchableOpacity
                onPress={() => onSymbolPress?.(symbol)}
                style={newsStyles.ticker}
                activeOpacity={0.7}
                hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}
              >
                <Text style={newsStyles.tickerText}>{symbol}</Text>
              </TouchableOpacity>
            )}
            <Text className="text-[11px] font-body text-gray-400">{source} · {when}</Text>
          </View>
        </View>
        {image ? <Image source={{ uri: image }} style={newsStyles.thumbnail} /> : null}
        <ChevronDown
          size={16}
          color={COLORS.gray400}
          style={{ transform: [{ rotate: open ? '180deg' : '0deg' }] }}
        />
      </TouchableOpacity>

      {/* Expanded — read action */}
      {open && (
        <TouchableOpacity onPress={openUrl} style={newsStyles.readRow} activeOpacity={0.7}>
          <ExternalLink size={14} color={COLORS.emerald} />
          <Text style={newsStyles.readText}>Read full article on {source}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const newsStyles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#f3f4f6',
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 6,
  },
  ticker: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 6,
    backgroundColor: '#ecfdf5',
  },
  tickerText: {
    fontSize: 10,
    fontFamily: 'DMSans-Bold',
    color: COLORS.emerald,
    letterSpacing: 0.2,
  },
  thumbnail: {
    width: 60,
    height: 60,
    borderRadius: 8,
    backgroundColor: '#f3f4f6',
  },
  readRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 14,
    paddingBottom: 12,
    paddingTop: 2,
  },
  readText: {
    fontSize: 12,
    fontFamily: 'DMSans-Medium',
    color: COLORS.emerald,
  },
});
