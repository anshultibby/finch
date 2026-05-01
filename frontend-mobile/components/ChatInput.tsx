import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Image, ScrollView, ActivityIndicator, Platform } from 'react-native';
import { Send, Square, Paperclip, X, ImageIcon } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import type { ImageAttachment } from '@/lib/types';

interface ChatInputProps {
  onSend: (text: string, images?: ImageAttachment[]) => void;
  onStop?: () => void;
  isStreaming: boolean;
  placeholder?: string;
}

export default function ChatInput({ onSend, onStop, isStreaming, placeholder }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [images, setImages] = useState<{ uri: string; base64: string; type: string }[]>([]);
  const [uploading, setUploading] = useState(false);

  const handleSend = () => {
    const text = input.trim();
    if (!text && images.length === 0) return;
    if (isStreaming) return;

    const imageAttachments: ImageAttachment[] | undefined = images.length > 0
      ? images.map(img => ({ data: img.base64, media_type: img.type }))
      : undefined;

    onSend(text, imageAttachments);
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

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      if (asset.base64) {
        setImages(prev => [...prev, {
          uri: asset.uri,
          base64: asset.base64!,
          type: asset.mimeType || 'image/jpeg',
        }]);
      }
    }
  };

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <View className="px-4 py-3 border-t border-black/5 bg-finch-bg">
      {/* Image previews */}
      {images.length > 0 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          className="mb-2"
          contentContainerClassName="gap-2"
        >
          {images.map((img, i) => (
            <View key={i} className="relative">
              <Image source={{ uri: img.uri }} className="w-16 h-16 rounded-xl" />
              <TouchableOpacity
                onPress={() => removeImage(i)}
                className="absolute -top-1.5 -right-1.5 bg-slate-900 rounded-full w-5 h-5 items-center justify-center"
              >
                <X size={10} color="#ffffff" />
              </TouchableOpacity>
            </View>
          ))}
        </ScrollView>
      )}

      <View className="flex-row items-end gap-2">
        {/* Attachment button */}
        <TouchableOpacity
          onPress={pickImage}
          disabled={isStreaming}
          className="w-10 h-10 items-center justify-center rounded-full bg-white border border-black/5"
          activeOpacity={0.7}
        >
          <ImageIcon size={18} color="#94a3b8" />
        </TouchableOpacity>

        {/* Text input */}
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder={placeholder || 'Message...'}
          placeholderTextColor="#94a3b8"
          multiline
          maxLength={10000}
          className="flex-1 bg-white rounded-2xl px-4 py-3 text-[15px] font-body text-slate-900 border border-black/5 max-h-32"
          editable={!isStreaming}
          onSubmitEditing={handleSend}
          blurOnSubmit={false}
        />

        {/* Send / Stop button */}
        {isStreaming ? (
          <TouchableOpacity
            onPress={onStop}
            className="bg-red-500 rounded-full w-10 h-10 items-center justify-center"
            activeOpacity={0.8}
          >
            <Square size={16} color="#ffffff" fill="#ffffff" />
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            onPress={handleSend}
            disabled={!input.trim() && images.length === 0}
            className={`rounded-full w-10 h-10 items-center justify-center ${
              input.trim() || images.length > 0 ? 'bg-emerald-600' : 'bg-slate-200'
            }`}
            activeOpacity={0.8}
          >
            <Send size={16} color={input.trim() || images.length > 0 ? '#ffffff' : '#94a3b8'} />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}
