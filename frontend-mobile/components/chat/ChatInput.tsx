import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Image, ScrollView, StyleSheet, ActivityIndicator, ActionSheetIOS, Alert, Platform } from 'react-native';
import { Send, Square, X, Plus, FileText } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import * as Haptics from 'expo-haptics';
import { chatFilesApi } from '@/lib/api';
import type { ImageAttachment } from '@/lib/types';
import { COLORS } from '@/lib/constants';

interface PendingDoc {
  uri: string;
  name: string;
  mimeType: string;
}

interface ChatInputProps {
  onSend: (text: string, images?: ImageAttachment[]) => void;
  onStop?: () => void;
  isStreaming: boolean;
  placeholder?: string;
  /** Required for document uploads — docs are staged in the chat's sandbox. */
  chatId?: string;
}

export default function ChatInput({ onSend, onStop, isStreaming, placeholder, chatId }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [images, setImages] = useState<{ uri: string; base64: string; type: string }[]>([]);
  const [docs, setDocs] = useState<PendingDoc[]>([]);
  const [uploading, setUploading] = useState(false);

  const handleSend = async () => {
    const text = input.trim();
    if (!text && images.length === 0 && docs.length === 0) return;
    if (isStreaming || uploading) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

    let message = text;
    if (docs.length > 0 && chatId) {
      setUploading(true);
      try {
        const uploaded = await Promise.all(docs.map(d => chatFilesApi.uploadFile(chatId, d)));
        // Same convention as web: the agent finds the files at these sandbox paths.
        message = `[Uploaded files]\n${uploaded.map(f => f.path).join('\n')}\n\n${text}`;
      } catch {
        Alert.alert('Upload failed', 'Could not upload the attached files. Please try again.');
        setUploading(false);
        return;
      }
      setUploading(false);
    }

    const attachments: ImageAttachment[] | undefined = images.length > 0
      ? images.map(img => ({ data: img.base64, media_type: img.type }))
      : undefined;
    onSend(message, attachments);
    setInput('');
    setImages([]);
    setDocs([]);
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

  const pickDocument = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: ['application/pdf', 'text/csv', 'text/comma-separated-values', 'text/plain',
             'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
      copyToCacheDirectory: true,
      multiple: true,
    });
    if (result.canceled) return;
    setDocs(prev => [
      ...prev,
      ...result.assets.map(a => ({
        uri: a.uri,
        name: a.name,
        mimeType: a.mimeType || 'application/octet-stream',
      })),
    ]);
  };

  const handleAttach = () => {
    // Documents need a chat sandbox to upload into; without one, images only.
    if (!chatId) {
      pickImage();
      return;
    }
    if (Platform.OS === 'ios') {
      ActionSheetIOS.showActionSheetWithOptions(
        { options: ['Cancel', 'Photo', 'Document (PDF, CSV…)'], cancelButtonIndex: 0 },
        (index) => {
          if (index === 1) pickImage();
          if (index === 2) pickDocument();
        }
      );
    } else if (Platform.OS === 'android') {
      Alert.alert('Attach', undefined, [
        { text: 'Photo', onPress: pickImage },
        { text: 'Document (PDF, CSV…)', onPress: pickDocument },
        { text: 'Cancel', style: 'cancel' },
      ]);
    } else {
      pickImage();
    }
  };

  const hasContent = input.trim().length > 0 || images.length > 0 || docs.length > 0;
  const busy = isStreaming || uploading;

  return (
    <View style={styles.container}>
      {(images.length > 0 || docs.length > 0) && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 6, marginHorizontal: 8 }} contentContainerStyle={{ gap: 6 }}>
          {images.map((img, i) => (
            <View key={`img-${i}`}>
              <Image source={{ uri: img.uri }} style={{ width: 40, height: 40, borderRadius: 8 }} />
              <TouchableOpacity
                onPress={() => setImages(prev => prev.filter((_, idx) => idx !== i))}
                style={styles.removeImage}
              >
                <X size={8} color="#fff" />
              </TouchableOpacity>
            </View>
          ))}
          {docs.map((doc, i) => (
            <View key={`doc-${i}`} style={styles.docChip}>
              <FileText size={13} color={COLORS.gray500} />
              <Text style={styles.docName} numberOfLines={1}>{doc.name}</Text>
              <TouchableOpacity
                onPress={() => setDocs(prev => prev.filter((_, idx) => idx !== i))}
                style={styles.removeImage}
              >
                <X size={8} color="#fff" />
              </TouchableOpacity>
            </View>
          ))}
        </ScrollView>
      )}

      <View style={styles.row}>
        <TouchableOpacity onPress={handleAttach} disabled={busy} style={styles.attachBtn} activeOpacity={0.6}>
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
          editable={!busy}
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
            disabled={!hasContent || uploading}
            style={[styles.sendBtn, { backgroundColor: hasContent ? '#059669' : '#e5e7eb' }]}
            activeOpacity={0.8}
          >
            {uploading
              ? <ActivityIndicator size="small" color="#fff" />
              : <Send size={13} color={hasContent ? '#fff' : '#9ca3af'} />}
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
  docChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    height: 40,
    maxWidth: 160,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: '#f9fafb',
    borderWidth: 1,
    borderColor: '#f3f4f6',
  },
  docName: {
    flexShrink: 1,
    fontSize: 11,
    fontFamily: 'DMSans-Medium',
    color: '#374151',
  },
});
