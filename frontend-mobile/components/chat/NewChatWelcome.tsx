import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { DollarSign, PieChart, Search, Send, Sparkles } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import InvestorPicker from '@/components/InvestorPicker';
import { TLH_PROMPT, PORTFOLIO_REVIEW_PROMPT, RESEARCH_STOCK_PROMPT, InvestorPersona } from '@/lib/aiPrompts';
import { COLORS } from '@/lib/constants';

const QUICK_ACTIONS = [
  {
    label: 'Tax-loss harvesting',
    description: 'Find tax savings in your portfolio',
    prompt: TLH_PROMPT,
    icon: <DollarSign size={16} color={COLORS.emerald} />,
    bg: '#ecfdf5',
  },
  {
    label: 'Portfolio review',
    description: 'Comprehensive analysis of holdings',
    prompt: PORTFOLIO_REVIEW_PROMPT,
    icon: <PieChart size={16} color="#7c3aed" />,
    bg: '#f5f3ff',
  },
  {
    label: 'Research a stock',
    description: 'Deep-dive into any ticker',
    prompt: RESEARCH_STOCK_PROMPT,
    icon: <Search size={16} color={COLORS.gray500} />,
    bg: '#f9fafb',
  },
];

interface NewChatWelcomeProps {
  onSendMessage: (message: string, investorPersona?: string) => void;
  disabled?: boolean;
}

export default function NewChatWelcome({ onSendMessage, disabled }: NewChatWelcomeProps) {
  const [message, setMessage] = useState('');
  const [selectedPersona, setSelectedPersona] = useState<InvestorPersona | null>(null);

  const handleSend = () => {
    const text = message.trim();
    if (!text || disabled) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onSendMessage(text, selectedPersona?.id);
    setMessage('');
    setSelectedPersona(null);
  };

  const handleQuickAction = (prompt: string) => {
    Haptics.selectionAsync();
    setMessage(prompt);
  };

  const hasContent = message.trim().length > 0;

  return (
    <ScrollView className="flex-1" contentContainerClassName="px-4 py-6" keyboardShouldPersistTaps="handled">
      <View className="items-center mb-6">
        <View className="w-12 h-12 rounded-2xl bg-gray-50 items-center justify-center mb-2.5">
          <Sparkles size={22} color={COLORS.gray400} />
        </View>
        <Text className="text-xl font-body-bold text-gray-900">How can I help?</Text>
        <Text className="text-[13px] font-body text-gray-400 mt-1 text-center">
          Ask anything about your portfolio, markets, or trading.
        </Text>
      </View>

      <View className="gap-2 mb-5">
        {QUICK_ACTIONS.map((action) => (
          <TouchableOpacity
            key={action.label}
            onPress={() => handleQuickAction(action.prompt)}
            disabled={disabled}
            style={[styles.actionCard, { backgroundColor: action.bg }]}
            activeOpacity={0.7}
          >
            {action.icon}
            <View className="flex-1 ml-2.5">
              <Text className="text-[13px] font-body-medium text-gray-900">{action.label}</Text>
              <Text className="text-[11px] font-body text-gray-500 mt-px">{action.description}</Text>
            </View>
          </TouchableOpacity>
        ))}
      </View>

      <View className="mb-5">
        <InvestorPicker
          selectedId={selectedPersona?.id ?? null}
          onSelect={setSelectedPersona}
          disabled={disabled}
        />
      </View>

      <View style={styles.inputCard}>
        <TextInput
          value={message}
          onChangeText={setMessage}
          placeholder={selectedPersona ? `Ask ${selectedPersona.name} anything...` : 'Ask anything about your portfolio...'}
          placeholderTextColor={COLORS.gray400}
          multiline
          className="px-3.5 py-2.5 text-[14px] font-body text-gray-900 min-h-[70px] max-h-[140px]"
          editable={!disabled}
        />
        <View className="flex-row items-center justify-end px-3 py-2 border-t border-gray-100">
          <TouchableOpacity
            onPress={handleSend}
            disabled={disabled || !hasContent}
            style={[styles.sendBtn, { backgroundColor: hasContent ? '#111827' : '#e5e7eb' }]}
            activeOpacity={0.8}
          >
            <Send size={13} color={hasContent ? '#fff' : '#9ca3af'} />
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  actionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 12,
  },
  inputCard: {
    backgroundColor: '#fff',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    overflow: 'hidden',
  },
  sendBtn: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
