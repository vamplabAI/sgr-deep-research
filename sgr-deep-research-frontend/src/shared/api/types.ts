// API Types based on OpenAPI specification

export interface HealthResponse {
  status: 'healthy'
  service: string
}

export type AgentStatus = 'completed' | 'inited' | 'waiting_for_clarification' | 'failed'

export interface AgentListItem {
  agent_id: string
  task: string
  state: AgentStatus
  creation_time: string
}

export interface AgentListResponse {
  agents: AgentListItem[]
  total: number
}

export interface AgentStateResponse {
  agent_id: string
  task: string
  state: string
  iteration: number
  searches_used: number
  clarifications_used: number
  sources_count: number
  current_step_reasoning?: Record<string, any> | null
}

export type ChatMessageRole = 'system' | 'user' | 'assistant' | 'tool'

export interface ReasoningStep {
  reasoning: string
  title: string
  user_request_language_reference: string
  content: string
  confidence: string
  tool_name_discriminator: string
  status: string
  query: string
  urls: string[]
  completed_steps: string[]
  // New nested structure fields
  reasoning_steps?: string[]
  current_situation?: string
  plan_status?: string
  remaining_steps?: string[]
  questions?: string[]
  answer?: string
  _raw_content: string
  enough_data?: boolean
  task_completed?: boolean
  function?: {
    tool_name_discriminator: string
    reasoning: string
    query?: string
    max_results?: number
    scrape_content?: boolean
    title?: string
    user_request_language_reference?: string
    content?: string
    confidence?: string
    completed_steps?: string[]
    questions?: string[]
    status?: string
    urls?: string[]
    answer?: string
    research_goal?: string
    planned_steps?: string[]
    search_strategies?: string[]
  }
}

export interface ChatMessage {
  role: ChatMessageRole
  content: (ReasoningStep | string)[]
}

export interface ChatCompletionRequest {
  model?: string | null
  messages: { role: 'user'; content: string }[]
  stream?: boolean
  max_tokens?: number | null
  temperature?: number | null
  user_id?: string | null
}

export interface AvailableModelsResponse {
  data: AvailableModel[]
}

export interface AvailableModel {
  id: string
  object: 'model'
  created: number
  owned_by: 'sgr-deep-research'
}

export interface ValidationError {
  loc: (string | number)[]
  msg: string
  type: string
}

export interface HTTPValidationError {
  detail: ValidationError[]
}

// API Response wrapper
export interface ApiResponse<T> {
  data: T
  status: number
  statusText: string
}

// API Error
export interface ApiError {
  message: string
  status?: number
  details?: ValidationError[]
  limitError?: {
    error: string
    limit_type: string
    limit: number
    used: number
    reset_at: string
    message: string
  }
}

// ============================================================================
// Chat History API Types
// ============================================================================

export interface ChatListItem {
  id: string
  agent_id: string
  agent_type: string
  initial_task: string
  state: AgentStatus
  created_at: string
  last_message_at: string | null
  total_messages: number
  total_iterations: number
  searches_used: number
}

export interface ChatListResponse {
  chats: ChatListItem[]
  total: number
  page: number
  page_size: number
}

// ============================================================================
// New Structured Chat History Format (Turns & Iterations)
// ============================================================================

export interface ToolCall {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

export interface HistoryMessage {
  id: string
  content: string | null
  tool_calls?: ToolCall[]
  tool_call_id?: string
  tool_name?: string
  created_at: string
}

export interface ChatIteration {
  iteration: number
  reasoning_message: HistoryMessage
  reasoning_result: HistoryMessage
  action_message: HistoryMessage
  action_result: HistoryMessage
}

export interface ChatTurn {
  user_message: HistoryMessage
  iterations: ChatIteration[]
}

export interface ChatHistoryResponse {
  chat_id: string
  agent_id: string
  turns: ChatTurn[]
  total_turns: number
  total_iterations: number
  page: number
  page_size: number
}

// ============================================================================
// Legacy format (kept for backwards compatibility if needed)
// ============================================================================

export interface ChatHistoryMessage {
  id: string
  role: ChatMessageRole
  content: string | null
  tool_call_id?: string | null
  tool_name?: string | null
  iteration?: number | null
  sequence_number: number
  created_at: string
}

export interface ChatDetailResponse {
  id: string
  agent_id: string
  agent_type: string
  initial_task: string
  state: AgentStatus
  created_at: string
  updated_at: string
  last_message_at: string | null
  total_messages: number
  total_iterations: number
  searches_used: number
  is_archived: boolean
}

export interface DeleteChatResponse {
  success: boolean
  message: string
  agent_id: string
}
