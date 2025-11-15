<template>
  <div class="chat-container">
    <div class="chat-container__content">
      <ChatMessageList
        :messages="currentMessages"
        :is-streaming="isStreaming"
        @retry="handleRetryMessage"
        ref="messageListRef"
      />
    </div>

    <div class="chat-container__footer">
      <MessageSender
        :current-assistant="currentAgent"
        :disabled="isAgentCompleted"
        @send="handleSendMessage"
        @error="handleSendError"
        ref="messageSenderRef"
      />

      <!-- Message when agent is completed -->
      <div v-if="isAgentCompleted && showCompletedMessage" class="chat-container__completed-message">
        <span class="chat-container__completed-message-text">
          ✅ Task completed. Click "New Chat" to start a new conversation.
        </span>
        <button
          class="chat-container__completed-message-close"
          @click="showCompletedMessage = false"
          aria-label="Close"
        >
          ✕
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ChatMessageList } from '@/features/chat-message'
import { MessageSender } from '@/widgets/MessageSender'
import { useChatStore, useAgentsStore } from '@/shared/stores'
import type { ChatMessageExtended } from '@/shared/stores'

interface Props {
  isAgentCompleted?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isAgentCompleted: false,
})

const emit = defineEmits<{
  newChat: []
  error: [error: string]
}>()

const chatStore = useChatStore()
const agentsStore = useAgentsStore()

const messageListRef = ref<InstanceType<typeof ChatMessageList> | null>(null)
const messageSenderRef = ref<InstanceType<typeof MessageSender> | null>(null)
const showCompletedMessage = ref(true)

// Computed properties
const currentSession = computed(() => chatStore.currentSession)
const currentMessages = computed(() => chatStore.currentMessages)
const isStreaming = computed(() => chatStore.isStreaming)
const currentAgent = computed(() => agentsStore.currentAgent)
const hasActiveSession = computed(() => chatStore.hasActiveSession)
const needsClarification = computed(() => chatStore.needsClarification)

// Watch for streaming state changes
watch(
  () => isStreaming.value,
  (streaming) => {
    if (!streaming) {
      // Focus back to input when streaming completes
      nextTick(() => {
        messageSenderRef.value?.focus()
      })
    }
  },
)

// Handle sending messages
const handleSendMessage = async (message: string) => {
  try {
    const agentId = currentSession.value?.agentId

    if (agentId) {
      // Check if agent needs clarification
      console.log('🔍 Checking clarification status:', {
        needsClarification: needsClarification.value,
        agentId,
      })

      if (needsClarification.value) {
        console.log('💬 Providing clarification to agent:', agentId)

        // Add user message to chat first
        chatStore.addUserMessage(message)

        // Send clarification and receive streaming response
        await chatStore.provideClarificationWithStreaming(agentId, message)
      } else {
        // Continue existing chat conversation
        console.log('📤 Continuing chat with agent:', agentId)
        await chatStore.continueChatConversation(agentId, message)
      }
    } else {
      // Create new chat
      console.log('📤 Starting new chat')

      // Initialize chat if no active session
      if (!hasActiveSession.value) {
        await chatStore.initializeChat(currentAgent.value)
      }

      // Send message through chat store
      await chatStore.sendMessage(message, currentAgent.value)
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to send message'
    emit('error', errorMessage)
    console.error('❌ Error sending message:', error)
  }
}

// Handle send errors
const handleSendError = (error: string) => {
  emit('error', error)
}

// Handle retry for failed messages
const handleRetryMessage = async (message: ChatMessageExtended) => {
  try {
    // Use the new retry functionality from chat store
    await chatStore.retryStreaming(message.id, currentAgent.value)
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to retry message'
    emit('error', errorMessage)
  }
}

// These methods are removed - navigation handled by pages now
// cancelStreaming() - not needed
// startNewChat() - handled by WorkspacePage
// initializeChat() - handled by WorkspacePage and ChatPage

// Expose methods for parent components
defineExpose({
  focusInput: () => messageSenderRef.value?.focus(),
  scrollToBottom: () => messageListRef.value?.scrollToBottom(),
  scrollToTop: () => messageListRef.value?.scrollToTop(),
})
</script>

<style scoped lang="scss">
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-1-1-white);
}

.chat-container__header {
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-1-1-light);
  background-color: var(--bg-2-3-white);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__title {
    margin: 0 0 4px 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--text-1-1-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__agent {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    color: var(--text-2-2-secondary);

    .agent-label {
      font-weight: 500;
    }

    .agent-name {
      font-weight: 600;
      color: var(--core-1-1-core);
    }
  }

  &__actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.new-chat-button,
.cancel-streaming-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background-color: var(--bg-2-4-gray);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background-color: var(--bg-2-5-gray-2);
  }

  &:active {
    transform: scale(0.95);
  }

  svg {
    width: 18px;
    height: 18px;
    color: var(--text-2-2-secondary);
  }
}

.cancel-streaming-button {
  background-color: var(--bg-error-light);

  &:hover {
    background-color: var(--bg-error);
  }

  svg {
    color: var(--text-error);
  }
}

.chat-container__content {
  flex: 1;
  overflow: hidden;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.chat-container__footer {
  flex-shrink: 0;
  border-top: 1px solid var(--border-1-1-light);
  position: relative;
}

.chat-container__completed-message {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 12px;
  padding: 12px 24px 12px 24px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #ffffff;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 500;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  white-space: nowrap;
  animation: slideUp 0.3s ease-out;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat-container__completed-message-text {
  flex: 1;
}

.chat-container__completed-message-close {
  background: none;
  border: none;
  color: #ffffff;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
  opacity: 0.8;

  &:hover {
    opacity: 1;
    background-color: rgba(255, 255, 255, 0.2);
  }

  &:active {
    transform: scale(0.9);
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

// Responsive adjustments
@media (max-width: 768px) {
  .chat-header {
    padding: 12px 16px;

    &__title {
      font-size: 16px;
    }

    &__agent {
      font-size: 13px;
    }
  }

  .new-chat-button {
    width: 32px;
    height: 32px;

    svg {
      width: 16px;
      height: 16px;
    }
  }
}
</style>
