<template>
  <div class="message-sender__wrapper">
    <div :class="[
      'message-sender',
      {
        'message-sender--focused': isFocused,
        'message-sender--disabled': props.disabled
      }
    ]">
      <div class="message-sender__input-row">
        <MessageInput
          ref="messageInputRef"
          v-model="message"
          :disabled="props.disabled || chatStore.isStreaming || isSending"
          @send="sendMessage"
          @focus="handleFocus"
          @blur="handleBlur"
        />

        <div class="message-sender__actions">
          <!-- Send Button -->
          <div class="send-message-button-slot">
            <SendMessageButton :is-disabled="props.disabled || isDisabled" @send="sendMessage" />
          </div>
        </div>
      </div>
    </div>

    <!-- Disclaimer -->
    <div class="message-sender__disclaimer">
      ⚠️ AI may make mistakes. Verify important information.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { MessageInput, SendMessageButton } from '@/features/send-message'
import { useChatStore } from '@/shared/stores'
import type { Agent } from '@/shared/stores'

interface Props {
  chatId?: string | null
  currentAssistant?: Agent | null
  initialMessage?: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  chatId: null,
  disabled: false,
  currentAssistant: null,
  initialMessage: '',
})

const emit = defineEmits<{
  send: [message: string]
  error: [error: string]
  input: [value: string]
  focus: []
  blur: []
}>()

const chatStore = useChatStore()

const message = ref('')
const isFocused = ref(false)
const isSending = ref(false)
const messageInputRef = ref<InstanceType<typeof MessageInput> | null>(null)

const isDisabled = computed(() => {
  const hasContent = message.value?.trim()
  // Allow input when clarification is needed, even if streaming
  const isWaitingForClarification = chatStore.needsClarification
  const isActuallyStreaming = chatStore.isStreaming && !isWaitingForClarification
  return !hasContent || isActuallyStreaming || !props.currentAssistant || isSending.value
})

// Watch for initial message from parent (e.g., from EmptyState suggestions)
watch(
  () => props.initialMessage,
  (newMessage) => {
    if (newMessage) {
      message.value = newMessage
    }
  },
  { immediate: true }
)

// Emit input event when message changes
watch(
  () => message.value,
  (newValue) => {
    emit('input', newValue)
  }
)

// Watch for streaming state changes to provide user feedback
watch(
  () => chatStore.isStreaming,
  (isStreaming, wasStreaming) => {
    if (isStreaming && !wasStreaming) {
      // ✅ Clear input when streaming STARTS
      console.log('🔄 Streaming started, clearing input')
      message.value = ''
      isSending.value = false  // Reset sending state
    } else if (!isStreaming && messageInputRef.value) {
      // Focus back to input when streaming is complete
      messageInputRef.value.$el?.querySelector('textarea')?.focus()
    }
  },
)

function handleFocus() {
  isFocused.value = true
  emit('focus')
}

function handleBlur() {
  isFocused.value = false
  emit('blur')
}

async function sendMessage() {
  if (isDisabled.value) return

  const messageContent = message.value.trim()

  // ✅ Set sending state immediately
  isSending.value = true
  console.log('📤 Sending message, input disabled')

  // Send text message
  if (messageContent) {
    emit('send', messageContent)
    // ✅ Don't clear immediately - wait for streaming to start
    // message.value = ''
  }
}

// Expose methods for parent components if needed
defineExpose({
  focus: () => {
    messageInputRef.value?.$el?.querySelector('textarea')?.focus()
  },
  clear: () => {
    message.value = ''
  },
  insertText: (text: string) => {
    message.value = text
    // Focus on input after inserting text
    messageInputRef.value?.$el?.querySelector('textarea')?.focus()
  },
})
</script>
<style scoped lang="scss">
.message-sender__wrapper {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px;
}

.message-sender {
  background-color: var(--bg-2-5-gray-2);
  border-radius: var(--ui-border-radius-32);
  display: flex;
  flex-direction: column;
  max-height: 314px;
  padding: 16px 28px;
  position: relative;
  transition: var(--base-transition);
  width: 100%;

  &:hover {
    background-color: var(--bg-2-3-white);
  }
}

.message-sender--focused {
  background-color: var(--bg-2-3-white);
}

.message-sender--disabled {
  opacity: 0.6;
  pointer-events: none;
  background-color: #f9fafb;

  &:hover {
    background-color: #f9fafb;
  }
}

.message-sender__input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 24px;
}

.message-sender__actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.send-message-button-slot {
  display: flex;
  align-items: center;
}

.message-sender__disclaimer {
  text-align: center;
  font-size: 12px;
  color: var(--text-3-2-dark-gray);
  opacity: 0.7;
  margin-top: 8px;
  padding: 0 16px;
  user-select: none;

  @media (max-width: 768px) {
    font-size: 11px;
    margin-top: 6px;
  }
}
</style>
