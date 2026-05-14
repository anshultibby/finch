import React, { useState } from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { Terminal, Search, Globe, FileText, CheckCircle, Zap, TrendingUp, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react-native';
import type { ToolCallStatus } from '@/lib/types';

const TOOL_ICONS: Record<string, (color: string) => React.ReactNode> = {
  execute_code: (c) => <Terminal size={12} color={c} />,
  run_python: (c) => <Terminal size={12} color={c} />,
  bash: (c) => <Terminal size={12} color={c} />,
  web_search: (c) => <Search size={12} color={c} />,
  news_search: (c) => <Search size={12} color={c} />,
  search: (c) => <Search size={12} color={c} />,
  scrape_url: (c) => <Globe size={12} color={c} />,
  write_chat_file: (c) => <FileText size={12} color={c} />,
  create_file: (c) => <FileText size={12} color={c} />,
  write_file: (c) => <FileText size={12} color={c} />,
  edit_file: (c) => <FileText size={12} color={c} />,
  read_chat_file: (c) => <FileText size={12} color={c} />,
  place_trade: (c) => <TrendingUp size={12} color={c} />,
  place_order: (c) => <TrendingUp size={12} color={c} />,
  finish_execution: (c) => <CheckCircle size={12} color={c} />,
};

const TOOL_LABELS: Record<string, string> = {
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

function getToolOutput(toolCall: ToolCallStatus): string | null {
  if (toolCall.code_output) {
    const parts: string[] = [];
    if (toolCall.code_output.stdout) parts.push(toolCall.code_output.stdout);
    if (toolCall.code_output.stderr) parts.push(`stderr: ${toolCall.code_output.stderr}`);
    return parts.join('\n') || null;
  }
  if (toolCall.search_results) {
    return toolCall.search_results.results
      ?.map((r: any) => `${r.title}\n${r.snippet || r.description || ''}`)
      .join('\n\n') || JSON.stringify(toolCall.search_results, null, 2);
  }
  if (toolCall.scraped_content) {
    return toolCall.scraped_content.content || toolCall.scraped_content.title || null;
  }
  if (toolCall.file_content) {
    return toolCall.file_content.content || null;
  }
  if (toolCall.result_summary) return toolCall.result_summary;
  if (toolCall.error) return `Error: ${toolCall.error}`;
  return null;
}

export default function ToolCallCard({ toolCall }: { toolCall: ToolCallStatus }) {
  const [expanded, setExpanded] = useState(false);
  const isActive = toolCall.status === 'calling' || toolCall.status === 'detected';
  const isDone = toolCall.status === 'completed';
  const isError = toolCall.status === 'error';
  const iconFn = TOOL_ICONS[toolCall.tool_name];
  const label = TOOL_LABELS[toolCall.tool_name] || toolCall.tool_name.replace(/_/g, ' ');
  const detail = toolCall.arguments?.query || toolCall.arguments?.url;
  const iconColor = isActive ? '#d97706' : isDone ? '#059669' : isError ? '#dc2626' : '#9ca3af';
  const output = getToolOutput(toolCall);
  const hasExpandableContent = isDone && (output || toolCall.arguments);

  return (
    <View className="mb-0.5">
      <TouchableOpacity
        onPress={hasExpandableContent ? () => setExpanded(!expanded) : undefined}
        className="flex-row items-center gap-1.5 py-1"
        activeOpacity={hasExpandableContent ? 0.6 : 1}
      >
        {isDone ? (
          <CheckCircle size={12} color="#059669" />
        ) : isError ? (
          <AlertCircle size={12} color="#dc2626" />
        ) : (
          iconFn ? iconFn(iconColor) : <Zap size={12} color={iconColor} />
        )}
        <Text className={`text-[11px] font-body-medium flex-1 ${isActive ? 'text-amber-600' : isDone ? 'text-gray-400' : isError ? 'text-red-500' : 'text-gray-400'}`} numberOfLines={1}>
          {label}
          {detail ? <Text className="text-gray-300"> · {typeof detail === 'string' ? detail.slice(0, 40) : ''}</Text> : null}
        </Text>
        {hasExpandableContent && (
          expanded ? <ChevronDown size={12} color="#d1d5db" /> : <ChevronRight size={12} color="#d1d5db" />
        )}
      </TouchableOpacity>

      {expanded && hasExpandableContent && (
        <View style={tcStyles.expandedBox}>
          {toolCall.arguments && Object.keys(toolCall.arguments).length > 0 && (
            <View style={tcStyles.section}>
              <Text style={tcStyles.sectionLabel}>Input</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator>
                <Text style={tcStyles.codeText} selectable>
                  {typeof toolCall.arguments === 'string'
                    ? toolCall.arguments
                    : JSON.stringify(toolCall.arguments, null, 2)}
                </Text>
              </ScrollView>
            </View>
          )}
          {output && (
            <View style={tcStyles.section}>
              <Text style={tcStyles.sectionLabel}>Output</Text>
              <ScrollView style={{ maxHeight: 200 }} nestedScrollEnabled>
                <ScrollView horizontal showsHorizontalScrollIndicator nestedScrollEnabled>
                  <Text style={tcStyles.codeText} selectable numberOfLines={50}>
                    {output.length > 2000 ? output.slice(0, 2000) + '\n...(truncated)' : output}
                  </Text>
                </ScrollView>
              </ScrollView>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

const tcStyles = StyleSheet.create({
  expandedBox: {
    backgroundColor: '#1f2937',
    borderRadius: 8,
    padding: 10,
    marginTop: 2,
    marginBottom: 4,
    marginLeft: 18,
  },
  section: {
    marginBottom: 6,
  },
  sectionLabel: {
    fontSize: 9,
    fontFamily: 'DMSans-Bold',
    color: '#9ca3af',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  codeText: {
    fontSize: 11,
    fontFamily: 'SpaceMono',
    color: '#e5e7eb',
    lineHeight: 16,
  },
});
