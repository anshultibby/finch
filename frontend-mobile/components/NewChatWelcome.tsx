import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView } from 'react-native';
import { DollarSign, PieChart, Search, Send } from 'lucide-react-native';
import InvestorPicker from './InvestorPicker';
import FinchLogo from './FinchLogo';
import { TLH_PROMPT, PORTFOLIO_REVIEW_PROMPT, RESEARCH_STOCK_PROMPT, InvestorPersona } from '@/lib/aiPrompts';

interface QuickAction {
  label: string;
  description: string;
  prompt: string;
  icon: React.ReactNode;
  bgColor: string;
  iconBgColor: string;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    label: 'Tax-loss harvesting',
    description: 'Find tax savings',
    prompt: TLH_PROMPT,
    icon: <DollarSign size={16} color="#059669" />,
    bgColor: 'bg-emerald-50',
    iconBgColor: 'bg-emerald-100',
  },
  {
    label: 'Portfolio review',
    description: 'Analyze holdings',
    prompt: PORTFOLIO_REVIEW_PROMPT,
    icon: <PieChart size={16} color="#7c3aed" />,
    bgColor: 'bg-violet-50',
    iconBgColor: 'bg-violet-100',
  },
  {
    label: 'Research stock',
    description: 'Deep dive any ticker',
    prompt: RESEARCH_STOCK_PROMPT,
    icon: <Search size={16} color="#64748b" />,
    bgColor: 'bg-slate-50',
    iconBgColor: 'bg-slate-100',
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
    onSendMessage(text, selectedPersona?.id);
    setMessage('');
    setSelectedPersona(null);
  };

  return (
    <ScrollView
      className="flex-1"
      contentContainerClassName="px-5 py-8"
      keyboardShouldPersistTaps="handled"
    >
      {/* Header */}
      <View className="items-center mb-8">
        <FinchLogo size={40} />
        <Text className="text-2xl font-body-bold text-slate-900 mt-3">How can I help?</Text>
        <Text className="text-sm font-body text-slate-400 mt-1">
          Pick a quick action or ask anything about your portfolio.
        </Text>
      </View>

      {/* Quick Actions */}
      <View className="gap-2 mb-6">
        {QUICK_ACTIONS.map((action) => (
          <TouchableOpacity
            key={action.label}
            onPress={() => {
              if (disabled) return;
              setMessage(action.prompt);
            }}
            disabled={disabled}
            className={`flex-row items-center gap-3 px-4 py-3 rounded-xl ${action.bgColor}`}
            activeOpacity={0.7}
          >
            <View className={`w-8 h-8 rounded-lg items-center justify-center ${action.iconBgColor}`}>
              {action.icon}
            </View>
            <View className="flex-1">
              <Text className="text-sm font-body-medium text-slate-900">{action.label}</Text>
              <Text className="text-xs font-body text-slate-500">{action.description}</Text>
            </View>
          </TouchableOpacity>
        ))}
      </View>

      {/* Investor Picker */}
      <View className="mb-6">
        <InvestorPicker
          selectedId={selectedPersona?.id ?? null}
          onSelect={setSelectedPersona}
          disabled={disabled}
        />
      </View>

      {/* Input */}
      <View className="bg-white rounded-2xl border border-black/5 overflow-hidden">
        <TextInput
          value={message}
          onChangeText={setMessage}
          placeholder={selectedPersona ? `Ask ${selectedPersona.name} anything...` : 'Ask anything...'}
          placeholderTextColor="#94a3b8"
          multiline
          className="px-4 py-3 text-[15px] font-body text-slate-900 min-h-[80px] max-h-[160px]"
          editable={!disabled}
        />
        <View className="flex-row items-center justify-between px-3 py-2 border-t border-black/5">
          <Text className="text-[10px] font-body text-slate-400">Press send when ready</Text>
          <TouchableOpacity
            onPress={handleSend}
            disabled={disabled || !message.trim()}
            className={`flex-row items-center gap-1.5 px-4 py-2 rounded-xl ${
              message.trim() ? 'bg-emerald-600' : 'bg-slate-200'
            }`}
            activeOpacity={0.8}
          >
            <Text className={`text-xs font-body-medium ${message.trim() ? 'text-white' : 'text-slate-400'}`}>
              Send
            </Text>
            <Send size={12} color={message.trim() ? '#ffffff' : '#94a3b8'} />
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
}
