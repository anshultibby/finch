import React from 'react';
import { View, Text } from 'react-native';
import { Terminal, Search, Globe, FileText, CheckCircle, Zap, TrendingUp, AlertCircle, Loader } from 'lucide-react-native';
import type { ToolCallStatus } from '@/lib/types';

function getToolIcon(name: string) {
  switch (name) {
    case 'execute_code':
    case 'run_python':
    case 'bash':
      return <Terminal size={14} color="#64748b" />;
    case 'web_search':
    case 'news_search':
    case 'search':
      return <Search size={14} color="#64748b" />;
    case 'scrape_url':
      return <Globe size={14} color="#64748b" />;
    case 'write_chat_file':
    case 'create_file':
    case 'write_file':
    case 'edit_file':
    case 'read_chat_file':
      return <FileText size={14} color="#64748b" />;
    case 'place_trade':
    case 'place_order':
      return <TrendingUp size={14} color="#059669" />;
    case 'finish_execution':
      return <CheckCircle size={14} color="#059669" />;
    default:
      return <Zap size={14} color="#64748b" />;
  }
}

function getToolLabel(name: string): string {
  const labels: Record<string, string> = {
    execute_code: 'Running code',
    run_python: 'Running Python',
    bash: 'Running command',
    web_search: 'Searching web',
    news_search: 'Searching news',
    scrape_url: 'Reading page',
    write_chat_file: 'Writing file',
    create_file: 'Creating file',
    write_file: 'Writing file',
    edit_file: 'Editing file',
    read_chat_file: 'Reading file',
    place_trade: 'Placing trade',
    place_order: 'Placing order',
    finish_execution: 'Finishing',
    fetch_portfolio: 'Fetching portfolio',
    get_positions: 'Getting positions',
    search_stocks: 'Searching stocks',
    get_stock_quote: 'Getting quote',
    create_agent: 'Creating agent',
  };
  return labels[name] || name.replace(/_/g, ' ');
}

function getStatusInfo(status: string) {
  switch (status) {
    case 'completed':
      return { color: 'bg-emerald-500', icon: <CheckCircle size={10} color="#ffffff" /> };
    case 'error':
      return { color: 'bg-red-500', icon: <AlertCircle size={10} color="#ffffff" /> };
    case 'calling':
      return { color: 'bg-amber-500', icon: <Loader size={10} color="#ffffff" /> };
    case 'detected':
      return { color: 'bg-slate-300', icon: null };
    default:
      return { color: 'bg-slate-300', icon: null };
  }
}

interface ToolCallCardProps {
  toolCall: ToolCallStatus;
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const statusInfo = getStatusInfo(toolCall.status);
  const isActive = toolCall.status === 'calling' || toolCall.status === 'detected';

  const searchQuery = toolCall.arguments?.query;
  const scrapeUrl = toolCall.arguments?.url;

  return (
    <View className={`flex-row items-center gap-2.5 py-2 px-3 mb-1.5 rounded-xl ${isActive ? 'bg-amber-50 border border-amber-100' : 'bg-slate-50 border border-slate-100'}`}>
      <View className={`w-5 h-5 rounded-full items-center justify-center ${statusInfo.color}`}>
        {statusInfo.icon || <View className="w-1.5 h-1.5 rounded-full bg-white" />}
      </View>
      <View className="flex-row items-center gap-1.5 flex-1">
        {getToolIcon(toolCall.tool_name)}
        <Text className="text-xs font-body-medium text-slate-700 flex-1" numberOfLines={1}>
          {getToolLabel(toolCall.tool_name)}
          {searchQuery && <Text className="text-slate-400"> &middot; {searchQuery}</Text>}
          {scrapeUrl && <Text className="text-slate-400"> &middot; {scrapeUrl}</Text>}
        </Text>
      </View>
      {toolCall.result_summary && (
        <Text className="text-[10px] font-body text-slate-400 max-w-[100px]" numberOfLines={1}>
          {toolCall.result_summary}
        </Text>
      )}
    </View>
  );
}
