<template v-if="message.role === 'user'">
  <div class="chat-message__content-wrapper">
    <div class="chat-message__content">
      <div class="chat-message__text">
        <div v-if="message.error" class="chat-message__error">
          <span class="error-icon">⚠️</span>
          <span>{{ message.error }}</span>
          <button class="retry-button" @click="$emit('retry')">Retry</button>
        </div>

        <div v-else-if="message.isStreaming" class="chat-message__streaming">
          <span class="streaming-content">{{ message.content }}</span>
          <span class="streaming-cursor">|</span>
        </div>

        <div v-else-if="message.agentReasoning" class="chat-message__agent-reasoning">
          <AgentReasoningDisplay :reasoning="message.agentReasoning" />
        </div>

        <div v-else class="chat-message__static">
          {{ message.content[0] }}
        </div>
      </div>
    </div>

    <!-- Copy Button and Timestamp (bottom right) -->
    <div class="chat-message__footer">
      <div v-if="!message.isStreaming && !message.error" class="chat-message__copy-button">
        <CopyButton @copy="$emit('copy')" />
      </div>
      <div class="chat-message__timestamp">
        {{ formattedTimestamp }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AppIcon, CopyButton, type ChatMessageExtended } from '@/shared'
import AgentReasoningDisplay from './AgentReasoningDisplay.vue'

const props = defineProps<{
  message: ChatMessageExtended
}>()

defineEmits<{
  copy: []
  retry: []
}>()

const userPicture = computed(() => undefined)
const userName = computed(() => 'User')

const formattedTimestamp = computed(() => {
  if (!props.message.timestamp) return ''

  const date = new Date(props.message.timestamp)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  // If less than a minute - "just now"
  if (diffInSeconds < 60) {
    return 'just now'
  }

  // If less than an hour - "N minutes ago"
  if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60)
    return `${minutes} min ago`
  }

  // If today - show time
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  // If yesterday
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (date.toDateString() === yesterday.toDateString()) {
    return `yesterday at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`
  }

  // Otherwise full date
  return date.toLocaleString('en-US', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
})
</script>
<style scoped lang="scss">
.chat-message__content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 800px;
}

.chat-message__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end; // Right
  gap: 12px;
  padding-right: 8px;
  margin-top: 4px;
}

.chat-message__copy-button {
  display: flex;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.chat-message__timestamp {
  font-size: 11px;
  color: var(--text-3-2-dark-gray); // Gray color (same as assistant)
  opacity: 0.7;
  user-select: none;
}

.chat-message__content-wrapper:hover .chat-message__copy-button {
  opacity: 1;
}

.chat-message__content {
  padding: 12px 16px;
  min-width: 0;
  word-wrap: break-word;
  background-color: var(--core-1-1-core); // Blue background
  color: var(--text-3-4-white); // White text
  border-radius: 18px;
}

.chat-message__text {
  line-height: 1.5;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.chat-message__error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  color: var(--system-7-2-error);
  font-size: 14px;

  .error-icon {
    font-size: 16px;
  }

  .retry-button {
    margin-left: auto;
    padding: 4px 8px;
    background-color: var(--system-7-2-error);
    color: var(--text-3-4-white);
    border: none;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    transition: background-color 0.2s ease;

    &:hover {
      background-color: var(--system-7-2-error);
      opacity: 0.8;
    }
  }
}

.chat-message__streaming {
  display: flex;
  align-items: center;
  gap: 2px;
  position: relative;

  .streaming-content {
    flex: 1;
  }

  .streaming-cursor {
    display: inline-block;
    width: 2px;
    height: 1.2em;
    background-color: currentColor;
    animation: blink 1.2s infinite;
    margin-left: 2px;
    border-radius: 1px;
  }
}

@media (max-width: 768px) {
  .chat-message.chat-message--user {
    .chat-message__content {
      margin-right: 0;
      margin-bottom: 8px;
      max-width: 85%;
    }

    .chat-message__content-wrapper {
      margin-right: 0;
      max-width: 85%;
    }

    .chat-message__copy-button {
      opacity: 1; // Always show on mobile
    }
  }
}
</style>
