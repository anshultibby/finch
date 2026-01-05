// ═══════════════════════════════════════════════════════════════════════════
// Shared Types for Finch Frontend
// ═══════════════════════════════════════════════════════════════════════════

// ─────────────────────────────────────────────────────────────────────────────
// Core Chat Types
// ─────────────────────────────────────────────────────────────────────────────

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  toolCalls?: ToolCallStatus[];
}

export interface ImageAttachment {
  data: string;  // Base64-encoded image data (without data: prefix)
  media_type: string;  // MIME type (image/png, image/jpeg, etc.)
}

// ─────────────────────────────────────────────────────────────────────────────
// Tool Types
// ─────────────────────────────────────────────────────────────────────────────

export interface CodeOutput {
  stdout?: string;
  stderr?: string;
}

export interface FileContent {
  filename: string;
  content: string;
  file_type: string;
  is_complete: boolean;
}

export interface SearchResult {
  title: string;
  link: string;
  snippet: string;
  date?: string;
  source?: string;
  imageUrl?: string;
  position?: number;
}

export interface SearchResults {
  query: string;
  results: SearchResult[];
  answerBox?: {
    title?: string;
    answer?: string;
    snippet?: string;
  };
  knowledgeGraph?: {
    title?: string;
    type?: string;
    description?: string;
    imageUrl?: string;
  };
  is_complete: boolean;
}

export interface ToolCallStatus {
  tool_call_id: string;
  tool_name: string;
  status: 'calling' | 'completed' | 'error';
  resource_id?: string;
  error?: string;
  result_summary?: string;
  statusMessage?: string;
  arguments?: Record<string, any>;
  code_output?: CodeOutput;
  file_content?: FileContent;
  search_results?: SearchResults;
  agent_id?: string;
  parent_agent_id?: string;
  _insertionOrder?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// SSE Event Types
// ─────────────────────────────────────────────────────────────────────────────

export interface SSEToolCallStartEvent {
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  user_description?: string;
  agent_id: string;
  parent_agent_id?: string;
  timestamp: string;
}

export interface SSEToolCallCompleteEvent {
  tool_call_id: string;
  tool_name: string;
  status: 'completed' | 'error';
  resource_id?: string;
  error?: string;
  result_summary?: string;
  code_output?: CodeOutput;
  search_results?: SearchResults;
  agent_id: string;
  parent_agent_id?: string;
  timestamp: string;
}

export interface SSEAssistantMessageDeltaEvent {
  delta: string;
}

export interface SSEMessageEndEvent {
  role: string;
  content: string;
  timestamp: string;
  tool_calls?: Array<{
    id: string;
    type: string;
    function: {
      name: string;
      arguments: string;
    };
  }>;
}

export interface SSEDoneEvent {
  message: string;
  timestamp: string;
}

export interface SSEErrorEvent {
  error: string;
  details?: string;
  timestamp: string;
}

export interface SSECodeOutputEvent {
  stream: 'stdout' | 'stderr';
  content: string;
}

export interface SSEFileContentEvent {
  tool_call_id: string;
  filename: string;
  content: string;
  file_type: string;
  is_complete: boolean;
}

export interface SSEToolCallStreamingEvent {
  tool_call_id: string;
  tool_name: string;
  arguments_delta: string;
  filename?: string;
  file_content_delta?: string;
  timestamp: string;
}

export interface SSEOptionsEvent {
  type: string;
  question: string;
  options: OptionButton[];
  timestamp: string;
}

export interface SSEToolStatusEvent {
  tool_call_id?: string;
  tool_name?: string;
  status: string;
  message?: string;
  timestamp: string;
}

export interface SSEToolProgressEvent {
  tool_call_id?: string;
  tool_name?: string;
  percent: number;
  message?: string;
  timestamp: string;
}

export interface SSEToolLogEvent {
  tool_call_id?: string;
  tool_name?: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
}

export interface SSEDelegationStartEvent {
  direction: string;
  agent_id: string;
  parent_agent_id: string;
}

export interface SSEDelegationEndEvent {
  success: boolean;
  summary: string;
  files_created: string[];
  error?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// UI Types
// ─────────────────────────────────────────────────────────────────────────────

export interface OptionButton {
  id: string;
  label: string;
  value: string;
  description?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Resource Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ResourceMetadata {
  parameters?: Record<string, any>;
  tool_call_id?: string;
  execution_time_ms?: number;
  total_count?: number;
}

export interface Resource {
  id: string;
  chat_id: string;
  user_id: string;
  tool_name: string;
  resource_type: string;
  title: string;
  data: Record<string, any>;
  metadata?: ResourceMetadata;
  created_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// API Response Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ChatResponse {
  response: string;
  user_id: string;
  timestamp: string;
  needs_auth?: boolean;
  tool_calls?: ToolCallStatus[];
}

export interface ChatHistory {
  user_id: string;
  messages: Message[];
}

export interface UserChatsResponse {
  user_id: string;
  chats: Array<{
    chat_id: string;
    title: string | null;
    icon: string | null;
    created_at: string;
    updated_at: string;
    last_message?: string;
  }>;
}

export interface GenerateTitleResponse {
  title: string;
  icon: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// SnapTrade Types
// ─────────────────────────────────────────────────────────────────────────────

export interface SnapTradeConnectionResponse {
  success: boolean;
  message: string;
  redirect_uri?: string;
}

export interface SnapTradeStatusResponse {
  success: boolean;
  message: string;
  is_connected: boolean;
  account_count?: number;
  brokerages?: string[];
}

export interface BrokerageAccount {
  id: string;
  account_id: string;
  broker_id: string;
  broker_name: string;
  name: string;
  number: string;
  type: string;
  balance: number;
  connected_at: string;
  last_synced_at: string | null;
}

export interface Brokerage {
  id: string;
  name: string;
  logo: string;
}

export interface BrokerageAccountsResponse {
  success: boolean;
  accounts: BrokerageAccount[];
  message: string;
}

export interface BrokeragesResponse {
  success: boolean;
  brokerages: Brokerage[];
  message: string;
}

