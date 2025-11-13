import type { AxiosProgressEvent, AxiosResponse } from 'axios'
import { apiClient, retryRequest } from './client'
import { API_ENDPOINTS } from './config'
import type {
  HealthResponse,
  AgentListResponse,
  AgentStateResponse,
  ChatCompletionRequest,
  AvailableModelsResponse,
  ChatListResponse,
  ChatDetailResponse,
  ChatHistoryResponse,
  DeleteChatResponse,
} from './types'

// Health Service
export const healthService = {
  /**
   * Check API health status
   */
  checkHealth: async (): Promise<HealthResponse> => {
    const response: AxiosResponse<HealthResponse> = await retryRequest(() =>
      apiClient.get(API_ENDPOINTS.HEALTH),
    )
    return response.data
  },
}

// Agents Service
export const agentsService = {
  /**
   * Get list of all agents
   */
  getAgentsList: async (): Promise<AgentListResponse> => {
    const response: AxiosResponse<AgentListResponse> = await retryRequest(() =>
      apiClient.get(API_ENDPOINTS.AGENTS),
    )
    return response.data
  },

  /**
   * Get specific agent state
   */
  getAgentState: async (agentId: string): Promise<AgentStateResponse> => {
    const response: AxiosResponse<AgentStateResponse> = await retryRequest(() =>
      apiClient.get(API_ENDPOINTS.AGENT_STATE(agentId)),
    )
    return response.data
  },

  /**
   * Provide clarification to an agent with streaming response
   */
  provideClarificationWithStreaming: async (
    agentId: string,
    clarifications: string,
    onProgress: (event: AxiosProgressEvent) => void,
  ): Promise<void> => {
    return apiClient.post(
      API_ENDPOINTS.AGENT_CLARIFICATION(agentId),
      { clarifications },
      {
        responseType: 'text',
        headers: {
          Accept: 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        onDownloadProgress: onProgress,
      },
    )
  },
}

// Models Service
export const modelsService = {
  /**
   * Get available models
   */
  getAvailableModels: async (): Promise<AvailableModelsResponse> => {
    const response: AxiosResponse<AvailableModelsResponse> = await retryRequest(() =>
      apiClient.get(API_ENDPOINTS.MODELS),
    )
    return response.data
  },
}

// Chat Service
export const chatService = {
  /**
   * Create chat completion
   */
  createCompletion: async (request: ChatCompletionRequest): Promise<unknown> => {
    const response: AxiosResponse<unknown> = await retryRequest(() =>
      apiClient.post(API_ENDPOINTS.CHAT_COMPLETIONS, request),
    )
    return response.data
  },

  /**
   * Create streaming chat completion
   * Note: user_id should be provided in the request object
   */
  createStreamingCompletion: async (
    request: ChatCompletionRequest,
    onProgress: (event: AxiosProgressEvent) => void,
  ): Promise<void> => {
    return apiClient.post(
      API_ENDPOINTS.CHAT_COMPLETIONS,
      { ...request, stream: true },
      {
        responseType: 'text',
        headers: {
          Accept: 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        onDownloadProgress: onProgress,
      },
    )
  },
}

// Chat History Service
export const chatHistoryService = {
  /**
   * Get list of all chats with pagination
   */
  getChatsList: async (page: number = 1, pageSize: number = 20): Promise<ChatListResponse> => {
    const response: AxiosResponse<ChatListResponse> = await retryRequest(() =>
      apiClient.get(API_ENDPOINTS.CHATS_LIST, {
        params: { page, page_size: pageSize },
      }),
    )
    return response.data
  },

  /**
   * Get detailed information about a specific chat
   */
  getChatDetail: async (agentId: string): Promise<ChatDetailResponse> => {
    const response: AxiosResponse<ChatDetailResponse> = await retryRequest(() =>
      apiClient.get(API_ENDPOINTS.CHAT_DETAIL(agentId)),
    )
    return response.data
  },

  /**
   * Get message history for a specific chat
   */
  getChatHistory: async (
    agentId: string,
    page: number = 1,
    pageSize: number = 50,
  ): Promise<ChatHistoryResponse> => {
    const response: AxiosResponse<ChatHistoryResponse> = await retryRequest(() =>
      apiClient.get(API_ENDPOINTS.CHAT_HISTORY(agentId), {
        params: { page, page_size: pageSize },
      }),
    )
    return response.data
  },

  /**
   * Delete a chat and all associated data
   */
  deleteChat: async (agentId: string): Promise<DeleteChatResponse> => {
    const response: AxiosResponse<DeleteChatResponse> = await retryRequest(() =>
      apiClient.delete(API_ENDPOINTS.CHAT_DELETE(agentId)),
    )
    return response.data
  },
}

// Export all services
export const apiServices = {
  health: healthService,
  agents: agentsService,
  models: modelsService,
  chat: chatService,
  chatHistory: chatHistoryService,
}
