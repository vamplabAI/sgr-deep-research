<template>
  <div :class="['chat-message', `chat-message--${message.role}`]">
    <!-- User messages: Avatar on right, content on left -->
    <ChatMessageUser
      v-if="message.role === 'user'"
      :message="message"
      @copy="handleCopy"
    />

    <!-- Assistant messages: No avatar, centered -->
    <template v-else>
      <div class="chat-message__content-wrapper">
        <div class="chat-message__content">
          <div class="chat-message__text">
            <div v-if="message.error" class="chat-message__error">
              <span class="error-icon">⚠️</span>
              <span>{{ message.error }}</span>
              <button class="retry-button" @click="$emit('retry')">Retry</button>
            </div>

            <div v-else-if="message.isStreaming" class="chat-message__streaming">
              <AppCircleLoader
                v-if="!message.content.length"
                size="sm"
                class="chat-message__loading-indicator"
              />
              <span v-if="!message.content.length" class="streaming-content">{{
                'Looking for information...'
              }}</span>
              <template v-else>
                <ChatMessageStep v-for="(step, index) in message.content" :key="index" :step="step" />
              </template>
            </div>

            <div v-else-if="message.agentReasoning" class="chat-message__agent-reasoning">
              <AgentReasoningDisplay :reasoning="message.agentReasoning" />
            </div>

            <template v-else>
              <ChatMessageStep v-for="(step, index) in message.content" :key="index" :step="step" />
            </template>

            <!-- Final Answer - displayed separately after all steps -->
            <div v-if="finalAnswer" class="chat-message__final-answer">
              <div class="chat-message__final-answer-text">
                <MarkdownRenderer :content="finalAnswer" />
              </div>
            </div>

            <!-- Clarification Questions - displayed prominently -->
            <div v-if="clarificationQuestions && clarificationQuestions.length" class="chat-message__clarification">
              <div class="chat-message__clarification-header">
                <span class="clarification-icon">❓</span>
                <span class="clarification-title">Clarification needed</span>
              </div>
              <div class="chat-message__clarification-questions">
                <div
                  v-for="(question, index) in clarificationQuestions"
                  :key="index"
                  class="clarification-question"
                >
                  {{ question }}
                </div>
              </div>
            </div>

            <!-- Tool History (collapsible) -->
            <ToolHistoryCollapsible
              v-if="message.toolHistory && message.toolHistory.length > 0"
              :tool-history="message.toolHistory"
            />
          </div>
        </div>

        <!-- Copy Button and Timestamp (bottom right) -->
        <div class="chat-message__footer">
          <div v-if="!message.isStreaming && !message.error" class="chat-message__copy-button">
            <CopyButton @copy="handleCopy" />
          </div>
          <div class="chat-message__timestamp">
            {{ formattedTimestamp }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AppCircleLoader, CopyButton, MarkdownRenderer } from '@/shared/ui'
import AgentReasoningDisplay from './AgentReasoningDisplay.vue'
import type { ChatMessageExtended } from '@/shared/stores'
import ChatMessageUser from './ChatMessageUser.vue'
import ChatMessageStep from './ChatMessageStep.vue'
import ToolHistoryCollapsible from './ToolHistoryCollapsible.vue'
import { formatMessageToMarkdown, copyToClipboard } from '@/shared/lib'

interface Props {
  message: ChatMessageExtended
}

const props = defineProps<Props>()

defineEmits<{
  retry: []
}>()

// Extract final answer from message content
const finalAnswer = computed(() => {
  if (!props.message.content || props.message.isStreaming) return null

  // Find finalanswertool in content
  for (const step of props.message.content) {
    if (typeof step === 'object' && step !== null) {
      const toolName = step.tool_name_discriminator || step.function?.tool_name_discriminator
      if (toolName === 'finalanswertool') {
        return step.answer || step.function?.answer || null
      }
    }
  }
  return null
})

// Extract clarification questions from message content
const clarificationQuestions = computed(() => {
  if (!props.message.content || props.message.isStreaming) return null

  // Find clarificationtool in content
  for (const step of props.message.content) {
    if (typeof step === 'object' && step !== null) {
      const toolName = step.tool_name_discriminator || step.function?.tool_name_discriminator
      if (toolName === 'clarificationtool') {
        return step.questions || step.function?.questions || null
      }
    }
  }
  return null
})

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

const handleCopy = async () => {
  const markdown = formatMessageToMarkdown(props.message)
  const success = await copyToClipboard(markdown)

  if (!success) {
    console.error('Failed to copy message to clipboard')
  }
}
</script>

<style scoped lang="scss">
.chat-message {
  display: flex;
  justify-content: center; // All messages centered
  margin-bottom: 24px;
  padding: 0 20px;
  animation: messageSlideIn 0.3s ease-out;

  // User messages: Centered with blue background
  &--user {
    .chat-message__content {
      background-color: var(--core-1-1-core);
      color: var(--text-3-4-white);
      border-radius: 18px;
      max-width: 800px; // Wider
      width: 100%;
    }
  }

  // Assistant messages: Centered with white background
  &--assistant {
    .chat-message__content {
      background-color: var(--bg-2-3-white);
      color: var(--text-3-1-dark);
      border-radius: 18px;
      width: 100%;
      max-width: 800px; // Wider
    }

    .chat-message__content-wrapper {
      display: flex;
      flex-direction: column;
      gap: 8px;
      width: 100%;
      max-width: 800px; // Wider
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
      color: var(--text-3-2-dark-gray);
      opacity: 0.7;
      user-select: none;
    }

    &:hover .chat-message__copy-button {
      opacity: 1;
    }
  }

  // System messages: Centered
  &--system {
    .chat-message__content {
      background-color: var(--bg-2-3-white);
      border: 1px solid var(--divider-6-1-white);
      border-radius: 18px;
      max-width: 800px;
    }
  }
}

@media (max-width: 768px) {
  .chat-message {
    padding: 12px;

    .chat-message__content-wrapper {
      max-width: 100%;
    }

    .chat-message__content {
      max-width: 100%;
    }

    .chat-message__copy-button {
      opacity: 1; // Always show on mobile
    }
  }
}

.chat-message__loading-indicator {
  display: inline-block;
  margin-right: 8px;
}

.chat-message__content {
  padding: 12px 16px;
  min-width: 0;
  word-wrap: break-word;
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

.chat-message__steps {
  width: 100%;
  text-align: start;
  margin: 0;
  margin-bottom: 10px;
}

.chat-message__streaming {
  display: flex;
  flex-direction: column;
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

@keyframes blink {
  0%,
  50% {
    opacity: 1;
  }
  51%,
  100% {
    opacity: 0;
  }
}

@keyframes messageSlideIn {
  0% {
    opacity: 0;
    transform: translateY(10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

// Smooth transitions for content changes
.chat-message__content {
  transition: all 0.2s ease;
}

.chat-message__streaming {
  transition: all 0.2s ease;
}

.chat-message__agent-reasoning {
  transition: all 0.2s ease;
}

// Final Answer styles - displayed prominently after all steps
.chat-message__final-answer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 2px solid #e5e7eb;
}

.chat-message__final-answer-text {
  font-size: 18px;
  color: #1a1a1a;
  line-height: 1.7;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  padding: 20px 24px;
  border-radius: 16px;
  border-left: 5px solid #2563eb;
  font-weight: 500;
  white-space: pre-wrap;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// Clarification Questions styles - displayed prominently
.chat-message__clarification {
  margin-top: 24px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-radius: 16px;
  border-left: 5px solid #f59e0b;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);
  animation: fadeInUp 0.3s ease-out;
}

.chat-message__clarification-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid rgba(245, 158, 11, 0.3);
}

.clarification-icon {
  font-size: 24px;
}

.clarification-title {
  font-size: 18px;
  font-weight: 600;
  color: #92400e;
}

.chat-message__clarification-questions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.clarification-question {
  padding: 14px 18px;
  background: #ffffff;
  border-radius: 12px;
  border-left: 3px solid #f59e0b;
  font-size: 16px;
  color: #1a1a1a;
  line-height: 1.6;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateX(4px);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  }
}
</style>
