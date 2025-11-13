// API Configuration
export const API_CONFIG = {
  // Use empty string for development (Vite proxy will handle it)
  // Set VITE_API_BASE_URL in production
  BASE_URL: import.meta.env.VITE_API_BASE_URL || '',
  TIMEOUT: 10000, // 10 seconds
  RETRY_ATTEMPTS: 1, // Only 1 retry to avoid spam
  RETRY_DELAY: 500, // 0.5 second
} as const

export const API_ENDPOINTS = {
  HEALTH: '/health',
  AGENTS: '/agents',
  AGENT_STATE: (agentId: string) => `/agents/${agentId}/state`,
  AGENT_CLARIFICATION: (agentId: string) => `/agents/${agentId}/provide_clarification`,
  MODELS: '/v1/models',
  CHAT_COMPLETIONS: '/v1/chat/completions',
  // Chat history endpoints (still used by chatStore)
  CHATS_LIST: '/v1/chats',
  CHAT_DETAIL: (agentId: string) => `/v1/chats/${agentId}`,
  CHAT_HISTORY: (agentId: string) => `/v1/chats/${agentId}/history`,
  CHAT_DELETE: (agentId: string) => `/v1/chats/${agentId}`,
} as const
