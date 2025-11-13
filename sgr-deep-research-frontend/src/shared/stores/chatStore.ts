/**
 * Chat Store (New Architecture)
 * Clean, modular implementation with separated concerns
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type {
  ChatCompletionRequest,
  AgentListItem,
} from '@/shared/api/types'
import type {
  ChatMessageExtended,
  ChatSession,
  StreamingState,
  Agent,
} from '@/shared/types/store'
import { apiServices } from '@/shared/api/services'
import { generateChatSessionId, generateMessageId } from '@/shared/lib/index'
import { StreamProcessor } from './streaming/streamProcessor'
import { loadChatHistory, loadChatDetails } from './history/historyLoader'

export const useChatStore = defineStore('chat', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const currentSession = ref<ChatSession | null>(null)
  const streamingState = ref<StreamingState>({
    isStreaming: false,
    currentMessageId: null,
    currentContent: '',
    error: null,
    retryCount: 0,
    isRetrying: false,
  })
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Agent state
  const agentState = ref<string | null>(null)

  // Chat sessions list
  const chatSessions = ref<AgentListItem[]>([])
  const isLoadingChatSessions = ref(false)
  const chatSessionsError = ref<string | null>(null)

  // Stream processor instance
  const streamProcessor = new StreamProcessor()

  // ============================================================================
  // COMPUTED
  // ============================================================================

  const currentMessages = computed(() => currentSession.value?.messages || [])
  const isStreaming = computed(() => streamingState.value.isStreaming)
  const hasActiveSession = computed(() => !!currentSession.value)
  const hasChatSessions = computed(() => chatSessions.value.length > 0)
  const needsClarification = computed(() => agentState.value === 'waiting_for_clarification')

  const sortedChatSessions = computed(() => {
    return [...chatSessions.value].sort((a, b) => {
      const getStatePriority = (state: string) => {
        switch (state) {
          case 'waiting_for_clarification':
            return 0
          case 'inited':
            return 1
          case 'completed':
            return 2
          default:
            return 3
        }
      }

      const aPriority = getStatePriority(a.state)
      const bPriority = getStatePriority(b.state)

      if (aPriority !== bPriority) {
        return aPriority - bPriority
      }

      const aTime = new Date(a.creation_time).getTime()
      const bTime = new Date(b.creation_time).getTime()
      return bTime - aTime
    })
  })

  // ============================================================================
  // HELPERS
  // ============================================================================

  /**
   * Create new message
   */
  const prepareMessage = (
    message: Omit<ChatMessageExtended, 'id' | 'timestamp'>
  ): ChatMessageExtended => {
    return {
      ...message,
      id: generateMessageId(),
      timestamp: new Date(),
    }
  }

  /**
   * Update existing message
   */
  const updateMessage = (messageId: string, updates: Partial<ChatMessageExtended>) => {
    if (!currentSession.value) return

    const messageIndex = currentSession.value.messages.findIndex((msg) => msg.id === messageId)
    if (messageIndex !== -1) {
      currentSession.value.messages[messageIndex] = {
        ...currentSession.value.messages[messageIndex],
        ...updates,
      } as ChatMessageExtended
      currentSession.value.updatedAt = new Date()
    }
  }

  // ============================================================================
  // STREAMING LIFECYCLE
  // ============================================================================

  /**
   * Start streaming
   */
  const startStreaming = (messageId: string) => {
    streamingState.value = {
      isStreaming: true,
      currentMessageId: messageId,
      currentContent: '',
      error: null,
      retryCount: 0,
      isRetrying: false,
    }
    streamProcessor.reset()
  }

  /**
   * Finish streaming
   */
  const finishStreaming = async () => {
    console.log('🏁 finishStreaming called')

    if (streamingState.value.isStreaming && streamingState.value.currentMessageId) {
      // Find the message and remove _streaming flags from content
      const message = currentSession.value?.messages.find(
        (m) => m.id === streamingState.value.currentMessageId
      )

      if (message && Array.isArray(message.content)) {
        // Remove _streaming flag from all content items
        message.content.forEach((item: any) => {
          if (typeof item === 'object' && item !== null && '_streaming' in item) {
            delete item._streaming
            delete item._raw_content
            console.log('🧹 Removed _streaming flag from content item:', item.tool_name_discriminator)
          }
        })
      }

      updateMessage(streamingState.value.currentMessageId, {
        isStreaming: false,
      })
    }

    const agentId = currentSession.value?.agentId
    console.log('🔍 finishStreaming - agentId:', agentId, 'hasSession:', !!currentSession.value)

    streamingState.value = {
      isStreaming: false,
      currentMessageId: null,
      currentContent: '',
      error: null,
      retryCount: 0,
      isRetrying: false,
    }

    streamProcessor.reset()

    // Update agent state
    if (agentId && currentSession.value) {
      console.log('🔍 Requesting agent state for:', agentId)
      try {
        const agentStateResponse = await apiServices.agents.getAgentState(agentId)
        currentSession.value.state = agentStateResponse.state
        agentState.value = agentStateResponse.state
        console.log('🔍 Agent state updated:', agentStateResponse.state)
      } catch (err) {
        console.error('❌ Failed to get agent state:', err)
      }
    } else {
      console.warn('⚠️ Cannot update agent state - no agentId or session')
    }
  }

  /**
   * Set streaming error
   */
  const setStreamingError = (errorMessage: string) => {
    streamingState.value.error = errorMessage
    streamingState.value.isStreaming = false

    if (streamingState.value.currentMessageId) {
      updateMessage(streamingState.value.currentMessageId, {
        error: errorMessage,
        isStreaming: false,
      })
    }
  }

  // ============================================================================
  // SESSION MANAGEMENT
  // ============================================================================

  /**
   * Initialize new chat
   */
  const initializeChat = async (agent: Agent | null = null): Promise<void> => {
    console.log('🆕 Initializing new chat')

    currentSession.value = {
      id: generateChatSessionId(),
      title: 'New Chat',
      messages: [],
      agent,
      agentId: null,
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true,
    }
  }

  /**
   * Clear current session
   */
  const clearCurrentSession = () => {
    currentSession.value = null
    streamProcessor.reset()
  }

  /**
   * Create new session (compatibility)
   */
  const createNewSession = (agent: Agent | null = null) => {
    const sessionId = generateChatSessionId()
    currentSession.value = {
      id: sessionId,
      agentId: agent?.id || null,
      title: 'New Chat',
      messages: [],
      agent: agent,
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true,
    }
    console.log('📝 Created new session:', sessionId)
  }

  // ============================================================================
  // MESSAGING
  // ============================================================================

  /**
   * Send new message
   */
  const sendMessage = async (
    content: string,
    agent: Agent | null = null
  ): Promise<void> => {
    if (!content.trim()) return

    if (streamingState.value.isStreaming || streamingState.value.isRetrying) {
      console.warn('⚠️ Streaming already in progress')
      return
    }

    streamingState.value.isStreaming = true

    // Prepare messages
    const userMessage = prepareMessage({
      role: 'user',
      content: [content.trim()],
    })

    const assistantMessage = prepareMessage({
      role: 'assistant',
      content: [],
      isStreaming: true,
    })

    startStreaming(assistantMessage.id)

    // Initialize session if needed
    if (!currentSession.value) {
      await initializeChat(agent)
    }

    // Add messages
    if (currentSession.value) {
      currentSession.value.messages.push(userMessage)
      currentSession.value.messages.push(assistantMessage)
    }

    try {
      const request: ChatCompletionRequest = {
        model: agent?.value || null,
        messages: [{ role: 'user', content: content.trim() }],
        stream: true,
        user_id: null,
      }

      let receivedLength = 0

      await apiServices.chat.createStreamingCompletion(request, (progressEvent) => {
        const responseText = progressEvent.event.target.responseText || ''
        const newChunk = responseText.slice(receivedLength)
        receivedLength = responseText.length

        if (newChunk && currentSession.value) {
          streamProcessor.processRawChunk(
            currentSession.value,
            newChunk,
            agent?.value,
            finishStreaming
          )
        }
      })

      console.log('✅ Message sent successfully')
    } catch (err: any) {
      if (err.status === 429 || err.limitError) {
        const limitError = err.limitError || {}
        const errorMessage = limitError.message || 'Rate limit exceeded'
        setStreamingError(errorMessage)
        console.error('⚠️ Rate limit error:', limitError)
      } else {
        const errorMessage = err instanceof Error ? err.message : 'Failed to send message'
        setStreamingError(errorMessage)
        console.error('❌ Error sending message:', err)
      }
      throw err
    }
  }

  /**
   * Continue existing chat
   */
  const continueChatConversation = async (agentId: string, message: string): Promise<void> => {
    if (!message.trim()) return

    if (streamingState.value.isStreaming || streamingState.value.isRetrying) {
      console.warn('⚠️ Streaming already in progress')
      return
    }

    streamingState.value.isStreaming = true

    // Prepare messages
    const userMessage = prepareMessage({
      role: 'user',
      content: [message.trim()],
    })

    const assistantMessage = prepareMessage({
      role: 'assistant',
      content: [],
      isStreaming: true,
    })

    startStreaming(assistantMessage.id)

    // Add messages
    if (currentSession.value) {
      currentSession.value.messages.push(userMessage)
      currentSession.value.messages.push(assistantMessage)
    }

    try {
      // Use /v1/chat/completions with agentId as model to continue conversation
      const request: ChatCompletionRequest = {
        model: agentId,
        messages: [{ role: 'user', content: message.trim() }],
        stream: true,
        user_id: null,
      }

      let receivedLength = 0

      await apiServices.chat.createStreamingCompletion(request, (progressEvent) => {
        const responseText = progressEvent.event.target.responseText || ''
        const newChunk = responseText.slice(receivedLength)
        receivedLength = responseText.length

        if (newChunk && currentSession.value) {
          streamProcessor.processRawChunk(
            currentSession.value,
            newChunk,
            agentId,
            finishStreaming
          )
        }
      })

      console.log('✅ Chat continued successfully')
    } catch (err: any) {
      if (err.status === 429 || err.limitError) {
        const limitError = err.limitError || {}
        const errorMessage = limitError.message || 'Rate limit exceeded'
        setStreamingError(errorMessage)
        console.error('⚠️ Rate limit error:', limitError)
      } else {
        const errorMessage = err instanceof Error ? err.message : 'Failed to continue chat'
        setStreamingError(errorMessage)
        console.error('❌ Error continuing chat:', err)
      }
      throw err
    }
  }

  /**
   * Add user message to session
   */
  const addUserMessage = (content: string): void => {
    if (!currentSession.value) {
      console.error('❌ No current session to add message to')
      return
    }

    const userMessage = prepareMessage({
      role: 'user',
      content: [content.trim()],
    })

    currentSession.value.messages.push(userMessage)
    console.log('✅ User message added to session')
  }

  /**
   * Provide clarification with streaming
   */
  const provideClarificationWithStreaming = async (
    agentId: string,
    clarification: string
  ): Promise<void> => {
    if (!clarification.trim()) return

    if (streamingState.value.isStreaming || streamingState.value.isRetrying) {
      console.warn('⚠️ Streaming already in progress')
      return
    }

    // Mark previous message as not streaming
    if (currentSession.value && currentSession.value.messages.length > 0) {
      const lastMessage = currentSession.value.messages[currentSession.value.messages.length - 1]
      if (lastMessage && lastMessage.isStreaming) {
        console.log('🔄 Marking previous message as not streaming')
        lastMessage.isStreaming = false
      }
    }

    streamingState.value.isStreaming = true

    // Prepare assistant message
    const assistantMessage = prepareMessage({
      role: 'assistant',
      content: [],
      isStreaming: true,
    })

    startStreaming(assistantMessage.id)

    if (currentSession.value) {
      currentSession.value.messages.push(assistantMessage)
      console.log('📨 Added new assistant message for clarification response')
    }

    try {
      console.log('💬 Providing clarification to agent:', agentId)

      let receivedLength = 0

      await apiServices.agents.provideClarificationWithStreaming(
        agentId,
        clarification,
        (progressEvent) => {
          const responseText = progressEvent.event.target.responseText || ''
          const newChunk = responseText.slice(receivedLength)
          receivedLength = responseText.length

          if (newChunk && currentSession.value) {
            streamProcessor.processRawChunk(
              currentSession.value,
              newChunk,
              agentId,
              finishStreaming
            )
          }
        }
      )

      console.log('✅ Clarification sent and response received')
    } catch (err: any) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to provide clarification'
      setStreamingError(errorMessage)
      console.error('❌ Error providing clarification:', err)
      throw new Error(errorMessage)
    }
  }

  // ============================================================================
  // HISTORY MANAGEMENT
  // ============================================================================

  /**
   * Load chat history
   */
  const loadChatHistoryAction = async (agentId: string): Promise<void> => {
    try {
      const messages = await loadChatHistory(agentId)

      if (currentSession.value) {
        currentSession.value.messages = messages
        currentSession.value.updatedAt = new Date()
      }

      console.log(`✅ Loaded ${messages.length} messages`)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load chat history'
      console.error('❌ Error loading chat history:', err)
      throw err
    }
  }

  /**
   * Load chat with history
   */
  const loadChatWithHistory = async (agentId: string): Promise<void> => {
    isLoading.value = true
    error.value = null

    try {
      console.log('📥 Loading chat:', agentId)

      // Load chat details
      const details = await loadChatDetails(agentId)
      console.log('📄 Chat details loaded:', details.title)

      // Create session
      currentSession.value = {
        id: generateChatSessionId(),
        title: details.title,
        messages: [],
        agent: null,
        agentId: agentId,
        createdAt: details.createdAt,
        updatedAt: new Date(),
        isActive: true,
      }

      // Load history
      await loadChatHistoryAction(agentId)

      console.log('✅ Chat loaded successfully')
      console.log('📊 Messages in session:', currentSession.value?.messages.length)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load chat'
      console.error('❌ Error loading chat:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch chats list
   */
  const fetchChatsListFromAPI = async (page: number = 1, pageSize: number = 20): Promise<void> => {
    isLoadingChatSessions.value = true
    chatSessionsError.value = null

    try {
      const response = await apiServices.chatHistory.getChatsList(page, pageSize)

      chatSessions.value = response.chats.map((chat) => ({
        agent_id: chat.agent_id,
        task: chat.initial_task,
        state: chat.state,
        creation_time: chat.created_at,
      }))

      console.log(`✅ Loaded ${response.chats.length} chats from API`)
    } catch (err) {
      chatSessionsError.value = err instanceof Error ? err.message : 'Failed to fetch chats'
      console.error('❌ Error fetching chats:', err)
    } finally {
      isLoadingChatSessions.value = false
    }
  }

  /**
   * Delete chat
   */
  const deleteChat = async (agentId: string): Promise<boolean> => {
    try {
      console.log(`🗑️ Deleting chat: ${agentId}`)

      const response = await apiServices.chatHistory.deleteChat(agentId)

      if (response.success) {
        chatSessions.value = chatSessions.value.filter((chat) => chat.agent_id !== agentId)

        if (currentSession.value?.agentId === agentId) {
          currentSession.value = null
        }

        console.log(`✅ Chat deleted: ${agentId}`)
        return true
      }

      return false
    } catch (err) {
      console.error('❌ Error deleting chat:', err)
      error.value = err instanceof Error ? err.message : 'Failed to delete chat'
      throw err
    }
  }

  // ============================================================================
  // COMPATIBILITY
  // ============================================================================

  const clearAgentState = () => {
    // No-op for compatibility
  }

  const retryStreaming = async (messageId: string, agent: Agent | null = null) => {
    // TODO: Implement retry logic
    console.warn('⚠️ Retry not implemented yet')
  }

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    currentSession,
    streamingState,
    isLoading,
    error,
    chatSessions,
    isLoadingChatSessions,
    chatSessionsError,

    // Computed
    currentMessages,
    isStreaming,
    hasActiveSession,
    hasChatSessions,
    sortedChatSessions,

    // Compatibility aliases
    chatsList: chatSessions,

    // Clarification state
    needsClarification,

    // Actions
    initializeChat,
    sendMessage,
    addUserMessage,
    continueChatConversation,
    provideClarificationWithStreaming,
    loadChatHistory: loadChatHistoryAction,
    loadChatWithHistory,
    fetchChatsListFromAPI,
    fetchChatsList: fetchChatsListFromAPI,
    deleteChat,
    clearCurrentSession,
    clearAgentState,
    retryStreaming,
    createNewSession,
  }
})
