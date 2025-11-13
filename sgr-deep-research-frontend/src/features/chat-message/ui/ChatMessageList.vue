<template>
  <div class="chat-message-list">
    <div v-if="messages.length === 0 && !isStreaming" class="chat-message-list__empty">
      <div class="empty-state">
        <div class="empty-state__icon">💬</div>
        <h3 class="empty-state__title">Start a conversation</h3>
        <p class="empty-state__description">Send a message to begin chatting with the assistant.</p>
      </div>
    </div>

    <div v-else class="chat-message-list__messages" ref="messagesContainer">
      <ChatMessage
        v-for="message in messages"
        :key="message.id"
        :message="message"
        @retry="handleRetry(message)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import ChatMessage from './ChatMessage.vue'
import type { ChatMessageExtended } from '@/shared/stores'

interface Props {
  messages: ChatMessageExtended[]
  isStreaming?: boolean
  autoScroll?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isStreaming: false,
  autoScroll: true,
})

const emit = defineEmits<{
  retry: [message: ChatMessageExtended]
  scrollToBottom: []
}>()

const messagesContainer = ref<HTMLElement | null>(null)
const isScrolling = ref(false)

// Auto-scroll to bottom when new messages arrive or streaming updates
watch(
  () => props.messages.length,
  () => {
    if (props.autoScroll) {
      scrollToBottom()
    }
  },
  { flush: 'post' },
)

// Watch for changes in message content (e.g., new steps added during streaming)
watch(
  () => props.messages,
  () => {
    if (props.autoScroll && props.isStreaming) {
      scrollToBottom()
    }
  },
  { deep: true, flush: 'post' },
)

watch(
  () => props.isStreaming,
  (isStreaming) => {
    if (isStreaming && props.autoScroll) {
      scrollToBottom()
    }
  },
)

// Scroll to bottom function
const scrollToBottom = () => {
  if (!messagesContainer.value) return

  nextTick(() => {
    const container = messagesContainer.value
    if (container) {
      container.scrollTop = container.scrollHeight
      emit('scrollToBottom')
    }
  })
}

// Handle retry for failed messages
const handleRetry = (message: ChatMessageExtended) => {
  emit('retry', message)
}

// Handle scroll events to detect user scrolling
const handleScroll = () => {
  if (!messagesContainer.value) return

  const container = messagesContainer.value
  const threshold = 100 // pixels from bottom
  const isNearBottom =
    container.scrollTop + container.clientHeight >= container.scrollHeight - threshold

  isScrolling.value = !isNearBottom
}

// Expose scroll methods for parent components
const scrollToTop = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = 0
  }
}

const scrollToMessage = (messageId: string) => {
  if (!messagesContainer.value) return

  const messageElement = messagesContainer.value.querySelector(`[data-message-id="${messageId}"]`)
  if (messageElement) {
    messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

onMounted(() => {
  if (messagesContainer.value) {
    messagesContainer.value.addEventListener('scroll', handleScroll)
  }
})

onUnmounted(() => {
  if (messagesContainer.value) {
    messagesContainer.value.removeEventListener('scroll', handleScroll)
  }
})

defineExpose({
  scrollToBottom,
  scrollToTop,
  scrollToMessage,
})
</script>

<style scoped lang="scss">
.chat-message-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;

  @include responsive.content-width;
}

.chat-message-list__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px 20px;
}

.empty-state {
  text-align: center;
  max-width: 400px;

  &__icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  &__title {
    margin: 0 0 8px 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--text-3-1-dark);
  }

  &__description {
    margin: 0;
    font-size: 14px;
    color: var(--text-3-2-dark-gray);
    line-height: 1.5;
  }
}

.chat-message-list__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
  scroll-behavior: smooth;
  scrollbar-width: thin;
  scrollbar-color: var(--divider-6-1-white) transparent;

  // Custom scrollbar styling for Webkit browsers (Chrome, Safari, Edge)
  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
    margin: 8px 0;
  }

  &::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.15);
    border-radius: 4px;
    border: 2px solid transparent;
    background-clip: padding-box;

    &:hover {
      background-color: rgba(0, 0, 0, 0.25);
    }

    &:active {
      background-color: rgba(0, 0, 0, 0.35);
    }
  }
}

.chat-message-list__typing {
  padding: 0 20px 16px 20px;
  animation: typingSlideIn 0.3s ease-out;
}

.typing-indicator {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 70%;
}

.typing-avatar {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-top: 2px;
  background-color: var(--bg-2-4-gray-1);
  border-radius: 50%;
  flex-shrink: 0;

  .avatar-placeholder {
    font-size: 14px;
    line-height: 1;
  }
}

.typing-bubble {
  background-color: var(--bg-2-4-gray-1);
  border-radius: 18px 18px 18px 4px;
  padding: 12px 16px;
  min-width: 60px;
}

@keyframes typingSlideIn {
  0% {
    opacity: 0;
    transform: translateY(10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

// Responsive adjustments
@media (max-width: 768px) {
  .chat-message-list__messages {
    padding: 16px 0;
  }

  .empty-state {
    padding: 20px;

    &__icon {
      font-size: 36px;
    }

    &__title {
      font-size: 18px;
    }
  }
}
</style>
