import React, { useState } from 'react';
import { View, TextInput, TouchableOpacity, Image, ScrollView, StyleSheet } from 'react-native';
import { Send, Square, X, Plus } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import * as Haptics from 'expo-haptics';
import type { ImageAttachment } from '@/lib/types';
import { COLORS } from '@/lib/constants';

interface ChatInputProps {
  onSend: (text: string, images?: ImageAttachment[]) => void;
  onStop?: () => void;
  isStreaming: boolean;
  placeholder?: string;
}

export default function ChatInput({ onSend, onStop, isStreaming, placeholder }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [images, setImages] = useState<{ uri: string; base64: string; type: string }[]>([]);

  const handleSend = () => {
    const text = input.trim();
    if (!text && images.length === 0) return;
    if (isStreaming) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    const attachments: ImageAttachment[] | undefined = images.length > 0
      ? images.map(img => ({ data: img.base64, media_type: img.type }))
      : undefined;
    onSend(text, attachments);
    setInput('');
    setImages([]);
  };

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: false,
      base64: true,
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]?.base64) {
      const asset = result.assets[0];
      setImages(prev => [...prev, {
        uri: asset.uri,
        base64: asset.base64!,
        type: asset.mimeType || 'image/jpeg',
      }]);
    }
  };

  const hasContent = input.trim().length > 0 || images.length > 0;

  return (
    <View style={styles.container}>
      {images.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 6, marginHorizontal: 8 }} contentContainerStyle={{ gap: 6 }}>
          {images.map((img, i) => (
            <View key={i}>
              <Image source={{ uri: img.uri }} style={{ width: 40, height: 40, borderRadius: 8 }} />
              <TouchableOpacity
                onPress={() => setImages(prev => prev.filter((_, idx) => idx !== i))}
                style={styles.removeImage}
              >
                <X size={8} color="#fff" />
              </TouchableOpacity>
            </View>
          ))}
        </ScrollView>
      )}

      <View style={styles.row}>
        <TouchableOpacity onPress={pickImage} disabled={isStreaming} style={styles.attachBtn} activeOpacity={0.6}>
          <Plus size={18} color={COLORS.gray400} strokeWidth={2} />
        </TouchableOpacity>

        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder={placeholder || 'Message Finch...'}
          placeholderTextColor={COLORS.gray400}
          multiline
          maxLength={10000}
          style={styles.input}
          editable={!isStreaming}
          onSubmitEditing={handleSend}
          blurOnSubmit={false}
        />

        {isStreaming ? (
          <TouchableOpacity
            onPress={() => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium); onStop?.(); }}
            style={[styles.sendBtn, { backgroundColor: '#111827' }]}
            activeOpacity={0.8}
          >
            <Square size={11} color="#fff" fill="#fff" />
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            onPress={handleSend}
            disabled={!hasContent}
            style={[styles.sendBtn, { backgroundColor: hasContent ? '#059669' : '#e5e7eb' }]}
            activeOpacity={0.8}
          >
            <Send size={13} color={hasContent ? '#fff' : '#9ca3af'} />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 12,
    marginBottom: 8,
    backgroundColor: '#ffffff',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    paddingVertical: 6,
    paddingHorizontal: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 3,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  attachBtn: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 2,
  },
  input: {
    flex: 1,
    fontSize: 15,
    fontFamily: 'DMSans',
    color: '#111827',
    paddingHorizontal: 4,
    paddingTop: 6,
    paddingBottom: 6,
    maxHeight: 96,
    lineHeight: 20,
  },
  sendBtn: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 2,
  },
  removeImage: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: '#374151',
    borderRadius: 8,
    width: 16,
    height: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
