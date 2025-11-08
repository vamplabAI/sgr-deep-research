// Store-related types and interfaces
import type { ChatMessage, AgentStateResponse, AgentListItem } from '@/shared/api/types'

// ===== AUTH STORE TYPES =====
export interface User {
  id: string
  email: string
  name?: string
  picture?: string
}

// ===== AGENTS STORE TYPES =====
// Local Agent interface that combines static model data with dynamic API data
export interface Agent {
  id: string
  name: string
  value: string
  // Dynamic data from API (optional, populated when fetched)
  task?: string
  state?: string
  iteration?: number
  searches_used?: number
  clarifications_used?: number
  sources_count?: number
  current_step_reasoning?: Record<string, unknown> | null
}

export interface ModelOption {
  id: string
  name: string
  value: string
}

// Store state interface
export interface AgentsState {
  currentAgent: Agent | null
  agentsList: AgentListItem[]
  isLoading: boolean
  error: string | null
}

// ===== CHAT STORE TYPES =====
// Chat message interface extending the API type
export interface ChatMessageExtended extends ChatMessage {
  id: string
  timestamp: Date
  isStreaming?: boolean
  error?: string
  agentReasoning?: Record<string, any> | null
  toolHistory?: Array<{
    id: string
    role: string
    content: string | null
    tool_calls?: any
    tool_name?: string | null
    tool_call_id?: string | null
    sequence_number?: number
  }>
}

// Chat session interface
export interface ChatSession {
  id: string
  title: string
  messages: ChatMessageExtended[]
  agent: Agent | null
  agentId: string | null // Store the actual agent ID for API calls
  state?: string // Agent state: 'running', 'completed', 'waiting_for_clarification', etc.
  createdAt: Date
  updatedAt: Date
  isActive: boolean
}

// Streaming state interface
export interface StreamingState {
  isStreaming: boolean
  currentMessageId: string | null
  currentContent: string
  error: string | null
  retryCount: number
  isRetrying: boolean
}

// Agent state interface for detailed reasoning
export interface AgentReasoning {
  reasoning_steps: string[]
  current_situation: string
  plan_status: string
  enough_data: boolean
  remaining_steps: string[]
  task_completed: boolean
}

// Store state interface
export interface ChatState {
  currentSession: ChatSession | null
  sessions: ChatSession[]
  streamingState: StreamingState
  isLoading: boolean
  error: string | null
  // Agent state management
  currentAgentState: AgentStateResponse | null
  isLoadingAgentState: boolean
  agentStateError: string | null
  // Chat sessions list (from API)
  chatSessions: AgentListItem[]
  isLoadingChatSessions: boolean
  chatSessionsError: string | null
  lastUpdated: Date | null
}
