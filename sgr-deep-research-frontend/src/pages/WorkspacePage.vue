<template>
  <div class="workspace-page">
    <!-- Header with model selector -->
    <div class="workspace-page__header">
      <button
        :class="[
          'workspace-page__new-chat-btn',
          { 'workspace-page__new-chat-btn--highlighted': isAgentCompleted },
        ]"
        @click="handleNewChat"
        :disabled="isStreaming"
      >
        New Chat
      </button>

      <h1 class="workspace-page__title">SGR Agent Core</h1>

      <div class="workspace-page__model-selector">
        <SelectAgent />
      </div>
    </div>

    <!-- Show chat if we have messages -->
    <div v-if="hasMessages" class="workspace-page__chat">
      <ChatContainer
        :messages="currentMessages"
        :is-streaming="isStreaming"
        :current-agent="currentAgent"
        :is-agent-completed="isAgentCompleted"
        @send="handleContinueChat"
        @retry="handleRetryMessage"
      />
    </div>

    <!-- Show welcome screen if no messages -->
    <div v-else class="workspace-page__welcome">
      <div class="welcome-content">
        <div class="welcome-icon">🤖</div>
        <h2 class="welcome-title">Start a conversation</h2>
        <p class="welcome-subtitle">Select a model above and start chatting with AI</p>
      </div>
    </div>

    <!-- Message Input (only when no messages) -->
    <div v-if="!hasMessages" class="workspace-page__input">
      <MessageSender
        ref="messageSenderRef"
        :current-assistant="currentAgent"
        :is-streaming="false"
        :disabled="!currentAgent"
        @send="handleSendMessage"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { MessageSender } from '@/widgets/MessageSender'
import { ChatContainer } from '@/widgets/ChatContainer'
import { SelectAgent } from '@/features/select-agent'
import { useChatStore, useAgentsStore } from '@/shared/stores'
import type { ChatMessageExtended } from '@/shared/stores'

const chatStore = useChatStore()
const agentsStore = useAgentsStore()

const messageSenderRef = ref<InstanceType<typeof MessageSender> | null>(null)

// Computed
const currentAgent = computed(() => agentsStore.currentAgent)
const currentMessages = computed(() => chatStore.currentMessages)
const isStreaming = computed(() => chatStore.isStreaming)
const hasMessages = computed(() => currentMessages.value.length > 0)
const agentId = computed(() => chatStore.currentSession?.agentId)
const agentState = computed(() => chatStore.currentSession?.state)
const isAgentCompleted = computed(() => agentState.value === 'completed')
const canContinueChat = computed(() => {
  // Can continue if we have an agentId, not streaming, and agent is not completed
  return !!agentId.value && !isStreaming.value && !isAgentCompleted.value
})

// Handlers
const handleSendMessage = async (message: string) => {
  if (!currentAgent.value) {
    console.error('No agent selected')
    return
  }

  try {
    console.log('📤 Starting new chat')

    // Initialize chat
    await chatStore.initializeChat(currentAgent.value)

    // Send message
    await chatStore.sendMessage(message, currentAgent.value)

    console.log('✅ Message sent')
  } catch (error) {
    console.error('❌ Error starting chat:', error)
  }
}

const handleContinueChat = async (message: string) => {
  try {
    const agentId = chatStore.currentSession?.agentId
    if (!agentId) {
      console.error('No agentId found')
      return
    }

    // Check if agent needs clarification
    console.log('🔍 Checking clarification status:', {
      needsClarification: chatStore.needsClarification,
      agentId,
    })

    if (chatStore.needsClarification) {
      console.log('💬 Providing clarification to agent:', agentId)

      // Add user message to chat first
      chatStore.addUserMessage(message)

      // Send clarification and receive streaming response
      await chatStore.provideClarificationWithStreaming(agentId, message)
    } else {
      console.log('📤 Continuing chat:', agentId)
      await chatStore.continueChatConversation(agentId, message)
    }
  } catch (error) {
    console.error('❌ Error continuing chat:', error)
  }
}

const handleRetryMessage = async (message: ChatMessageExtended) => {
  try {
    console.log('🔄 Retrying message:', message.id)
    await chatStore.retryStreaming(message.id, currentAgent.value)
  } catch (error) {
    console.error('❌ Error retrying message:', error)
  }
}

const handleNewChat = async () => {
  console.log('🆕 Starting new chat')

  // Clear current session and start fresh
  chatStore.clearCurrentSession()
  await chatStore.initializeChat(currentAgent.value)

  console.log('✅ New chat initialized')
}

// Initialize
onMounted(async () => {
  console.log('📍 WorkspacePage mounted')

  // Clear any existing session
  chatStore.clearCurrentSession()

  // Initialize agents
  await agentsStore.initializeAgents()
  console.log('✅ Agents initialized')
})
</script>

<style scoped lang="scss">
.workspace-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-1-1-white);
}

.workspace-page__header {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 20px;
  padding: 20px 32px;
  border-bottom: 1px solid var(--border-1-1-light);
  background: var(--bg-1-1-white);
}

.workspace-page__new-chat-btn {
  justify-self: start;
  padding: 10px 20px;
  background: #ffffff;
  color: #1a1a1a;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;

  &:hover:not(:disabled) {
    background: #f9fafb;
    border-color: #d1d5db;
  }

  &:active:not(:disabled) {
    background: #f3f4f6;
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  // Highlighted state when agent is completed
  &--highlighted {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: #ffffff;
    border-color: #2563eb;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    animation: pulse 2s ease-in-out infinite;

    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
      border-color: #1d4ed8;
      box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
    }

    &:active:not(:disabled) {
      background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    }
  }
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }
  50% {
    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5);
  }
}

.workspace-page__title {
  font-family: 'Inter', sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-3-1-dark);
  margin: 0;
  text-align: center;
  white-space: nowrap;
}

.workspace-page__model-selector {
  justify-self: end;
}

// Responsive
@media (max-width: 768px) {
  .workspace-page__header {
    grid-template-columns: auto 1fr auto;
    gap: 12px;
    padding: 16px 20px;
  }

  .workspace-page__title {
    font-size: 18px;
  }

  .workspace-page__new-chat-btn {
    padding: 8px 12px;
    font-size: 13px;
  }
}

.workspace-page__chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workspace-page__welcome {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.welcome-content {
  text-align: center;
  max-width: 500px;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 24px;
}

.welcome-title {
  font-family: 'Inter', sans-serif;
  font-size: 32px;
  font-weight: 600;
  color: var(--text-3-1-dark);
  margin: 0 0 12px 0;
}

.welcome-subtitle {
  font-family: 'Inter', sans-serif;
  font-size: 16px;
  color: var(--text-3-2-dark-gray);
  margin: 0;
  line-height: 1.5;
}

.workspace-page__input {
  flex-shrink: 0;
  background: var(--bg-1-1-white);
  border-top: 1px solid var(--border-1-1-light);
  padding: 16px 24px;
}

@media (max-width: 768px) {
  .workspace-page__header {
    padding: 16px;
  }

  .workspace-page__title {
    font-size: 24px;
    margin-bottom: 16px;
  }

  .welcome-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .welcome-title {
    font-size: 24px;
  }

  .welcome-subtitle {
    font-size: 14px;
  }

  .workspace-page__input {
    padding: 12px 16px;
  }
}
</style>
