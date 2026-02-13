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

export interface ScrapedContent {
  url: string;
  title: string;
  content: string;
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
  scraped_content?: ScrapedContent;
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
  scraped_content?: ScrapedContent;
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

export interface Position {
  symbol: string;
  quantity: number;
  price: number;
  value: number;
  average_purchase_price?: number;
  total_cost?: number;
  gain_loss?: number;
  gain_loss_percent?: number;
}

export interface AccountDetail {
  id: string;
  name: string;
  number: string;
  type: string;
  institution: string;
  balance: number;
  positions: Position[];
  total_value: number;
  position_count: number;
  status?: string;
}

export interface PortfolioResponse {
  success: boolean;
  accounts: AccountDetail[];
  holdings_csv?: string;
  total_value: number;
  total_positions: number;
  account_count: number;
  message: string;
  syncing?: boolean;
  needs_auth?: boolean;
}

export interface PortfolioPerformance {
  success: boolean;
  total_value: number;
  total_cost: number;
  total_gain_loss: number;
  total_gain_loss_percent: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// API Keys Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ApiKeyInfo {
  service: string;
  api_key_id: string;
  api_key_id_masked: string;
  has_private_key: boolean;
  created_at: string | null;
}

export interface ApiKeysResponse {
  success: boolean;
  keys: ApiKeyInfo[];
  message: string;
}

export interface ApiKeyResponse {
  success: boolean;
  message: string;
  key?: ApiKeyInfo;
}

export interface TestApiKeyResponse {
  success: boolean;
  message: string;
  balance?: number;
}

// ============================================================================
// Strategies
// ============================================================================

export interface RiskLimits {
  max_order_usd?: number;
  max_daily_usd?: number;
  max_position_usd?: number;
  allowed_services?: string[];
}

export interface CapitalAllocation {
  total_capital?: number;
  capital_per_trade?: number;
  max_positions?: number;
  max_position_size?: number;
  max_daily_loss?: number;
  max_total_drawdown?: number;
  sizing_method?: 'fixed' | 'kelly' | 'percent_capital';
  deployed?: number;
}

export interface StrategyConfig {
  description?: string;
  source_chat_id?: string;
  file_ids?: string[];
  entrypoint?: string;
  schedule?: string;
  schedule_description?: string;
  risk_limits?: RiskLimits;
  approved_at?: string;
  thesis?: string;
  platform?: 'polymarket' | 'kalshi' | 'alpaca';
  execution_frequency?: number;
  capital?: CapitalAllocation;
  entry_script?: string;
  exit_script?: string;
  entry_description?: string;
  exit_description?: string;
  parameters?: Record<string, any>;
}

export interface StrategyStats {
  total_runs?: number;
  successful_runs?: number;
  failed_runs?: number;
  last_run_at?: string;
  last_run_status?: string;
  last_run_summary?: string;
  total_spent_usd?: number;
  total_profit_usd?: number;
  
  // Mode tracking
  mode?: 'backtest' | 'paper' | 'live';
  
  // Track record
  total_trades?: number;
  winning_trades?: number;
  losing_trades?: number;
  win_rate?: number;
  total_pnl?: number;
  total_volume?: number;
  avg_trade_pnl?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  
  // Per-mode stats
  backtest_trades?: number;
  backtest_win_rate?: number;
  backtest_pnl?: number;
  backtest_start?: string;
  backtest_end?: string;
  
  paper_trades?: number;
  paper_win_rate?: number;
  paper_pnl?: number;
  paper_start?: string;
  paper_end?: string;
  
  live_trades?: number;
  live_win_rate?: number;
  live_pnl?: number;
  live_start?: string;
  
  // Additional stats
  avg_win?: number;
  avg_loss?: number;
  largest_win?: number;
  largest_loss?: number;
  current_positions?: number;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  approved: boolean;
  schedule_description?: string;
  schedule?: string;
  risk_limits?: RiskLimits;
  stats?: StrategyStats;
  config?: StrategyConfig;
  created_at: string;
  updated_at: string;
  file_ids?: string[];
  entrypoint?: string;
  source_chat_id?: string;
}

export interface StrategyExecution {
  id: string;
  strategy_id: string;
  status: 'running' | 'success' | 'failed';
  started_at: string;
  completed_at?: string;
  trigger: string;
  summary?: string;
  error?: string;
  actions_count?: number;
  data?: {
    mode?: 'backtest' | 'paper' | 'live';
    trigger: string;
    completed_at?: string;
    duration_ms?: number;
    result?: any;
    error?: string;
    logs?: string[];
    summary?: string;
    signals?: Array<{
      market_id: string;
      market_name: string;
      side: string;
      reason: string;
      confidence: number;
      metadata?: any;
    }>;
    actions?: Array<{
      type: string;
      timestamp: string;
      dry_run: boolean;
      details: any;
    }>;
  };
}

export interface StrategyCodeResponse {
  strategy_id: string;
  name: string;
  entrypoint: string;
  files: Record<string, string>;
  config: StrategyConfig;
  stats?: StrategyStats;
}

