import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
  SafeAreaView,
  StatusBar,
  Platform,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { BarChart3, X, ExternalLink } from 'lucide-react-native';
import { visualizationsApi } from '@/lib/api';
import type { Visualization } from '@/lib/types';

interface VisualizationChipProps {
  filename: string;
}

export function VisualizationChip({ filename }: VisualizationChipProps) {
  const [modalVisible, setModalVisible] = useState(false);
  const displayName = filename
    .replace(/^visualizations\//, '')
    .replace(/\.html$/i, '')
    .replace(/[_-]/g, ' ');

  return (
    <>
      <TouchableOpacity
        onPress={() => setModalVisible(true)}
        activeOpacity={0.7}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 6,
          paddingHorizontal: 12,
          paddingVertical: 8,
          marginVertical: 4,
          backgroundColor: '#eef2ff',
          borderRadius: 10,
          borderWidth: 1,
          borderColor: '#c7d2fe',
        }}
      >
        <BarChart3 size={14} color="#6366f1" />
        <Text style={{ fontSize: 13, fontFamily: 'DMSans-Medium', color: '#4338ca' }}>
          {displayName}
        </Text>
        <ExternalLink size={11} color="#818cf8" />
      </TouchableOpacity>

      <VisualizationModal
        visible={modalVisible}
        filename={filename}
        title={displayName}
        onClose={() => setModalVisible(false)}
      />
    </>
  );
}

interface VisualizationModalProps {
  visible: boolean;
  filename: string;
  title: string;
  onClose: () => void;
}

function VisualizationModal({ visible, filename, title, onClose }: VisualizationModalProps) {
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadVisualization = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { visualizations } = await visualizationsApi.list();
      const normalizedTarget = filename.startsWith('visualizations/')
        ? filename
        : `visualizations/${filename}`;
      const viz = visualizations.find(
        (v: Visualization) => v.filename === normalizedTarget || v.filename === filename
      );
      if (!viz) {
        setError('Visualization not found');
        return;
      }
      const htmlContent = await visualizationsApi.getRenderHtml(viz.id);
      const viewport = `<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">`;
      const patched = htmlContent.includes('<head>')
        ? htmlContent.replace('<head>', `<head>${viewport}`)
        : `<html><head>${viewport}</head><body>${htmlContent}</body></html>`;
      setHtml(patched);
    } catch (e: any) {
      setError(e.message || 'Failed to load visualization');
    } finally {
      setLoading(false);
    }
  }, [filename]);

  const handleShow = useCallback(() => {
    setHtml(null);
    setError(null);
    loadVisualization();
  }, [loadVisualization]);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="fullScreen"
      onShow={handleShow}
      onRequestClose={onClose}
    >
      <SafeAreaView style={{ flex: 1, backgroundColor: '#fff' }}>
        <StatusBar barStyle="dark-content" />
        {/* Header */}
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingHorizontal: 16,
            paddingVertical: 12,
            borderBottomWidth: 1,
            borderBottomColor: '#e5e7eb',
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 }}>
            <BarChart3 size={18} color="#6366f1" />
            <Text
              style={{
                fontSize: 15,
                fontFamily: 'DMSans-Medium',
                color: '#111827',
                flex: 1,
              }}
              numberOfLines={1}
            >
              {title}
            </Text>
          </View>
          <TouchableOpacity
            onPress={onClose}
            activeOpacity={0.6}
            style={{
              padding: 6,
              borderRadius: 8,
              backgroundColor: '#f3f4f6',
            }}
          >
            <X size={18} color="#6b7280" />
          </TouchableOpacity>
        </View>

        {/* Content */}
        <View style={{ flex: 1 }}>
          {loading && (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
              <ActivityIndicator size="large" color="#6366f1" />
              <Text style={{ marginTop: 12, fontSize: 13, color: '#9ca3af', fontFamily: 'DMSans' }}>
                Loading visualization...
              </Text>
            </View>
          )}
          {error && (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 32 }}>
              <Text style={{ fontSize: 14, color: '#ef4444', fontFamily: 'DMSans', textAlign: 'center' }}>
                {error}
              </Text>
              <TouchableOpacity
                onPress={loadVisualization}
                activeOpacity={0.7}
                style={{
                  marginTop: 16,
                  paddingHorizontal: 20,
                  paddingVertical: 10,
                  borderRadius: 8,
                  backgroundColor: '#eef2ff',
                }}
              >
                <Text style={{ fontSize: 13, color: '#4338ca', fontFamily: 'DMSans-Medium' }}>
                  Retry
                </Text>
              </TouchableOpacity>
            </View>
          )}
          {html && !loading && (
            <WebView
              source={{ html }}
              style={{ flex: 1 }}
              javaScriptEnabled
              domStorageEnabled
              scalesPageToFit={Platform.OS === 'android'}
              originWhitelist={['*']}
              scrollEnabled
            />
          )}
        </View>
      </SafeAreaView>
    </Modal>
  );
}
