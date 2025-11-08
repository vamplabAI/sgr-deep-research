<template>
  <div class="message-sender__wrapper">
    <div :class="[
      'message-sender',
      {
        'message-sender--focused': isFocused,
        'message-sender--disabled': props.disabled
      }
    ]">
      <!-- Audio Attachment Display -->
      <AudioAttachment
        v-if="audioAttachment"
        :duration="audioAttachment.duration"
        :size="audioAttachment.size"
        :audio-url="audioAttachment.url"
        @remove="removeAudioAttachment"
      />

      <!-- Transcription Progress -->
      <div v-if="isTranscribing" class="transcription-progress">
        <div class="transcription-progress__icon">
          <svg class="spinner" width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="50.265" stroke-dashoffset="12.566" />
          </svg>
        </div>
        <div class="transcription-progress__info">
          <div class="transcription-progress__title">Транскрибация аудио...</div>
          <div class="transcription-progress__status">
            {{ transcriptionProgress?.progression.description || 'Обработка' }}
            <span v-if="transcriptionProgress?.progression.progress_percent">
              ({{ transcriptionProgress.progression.progress_percent }}%)
            </span>
          </div>
        </div>
      </div>

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
          <!-- Audio Recorder -->
          <AudioRecorder
            ref="audioRecorderRef"
            :disabled="props.disabled || chatStore.isStreaming || !!audioAttachment"
            @recorded="handleAudioRecorded"
            @error="handleAudioError"
          />

          <!-- Send Button -->
          <div class="send-message-button-slot">
            <SendMessageButton :is-disabled="props.disabled || isDisabled" @send="sendMessage" />
          </div>
        </div>
      </div>
    </div>

    <!-- Disclaimer -->
    <div class="message-sender__disclaimer">
      ⚠️ AI может допускать ошибки. Проверяйте важную информацию.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { MessageInput, SendMessageButton, AudioRecorder, AudioAttachment } from '@/features/send-message'
import { useChatStore } from '@/shared/stores'
import { transcriptionService } from '@/shared/api/transcription.service'
import type { Agent } from '@/shared/stores'
import type { TranscriptionStatusResponse } from '@/shared/api/types'

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
const audioRecorderRef = ref<InstanceType<typeof AudioRecorder> | null>(null)

// Audio attachment state
interface AudioAttachmentData {
  blob: Blob
  duration: number
  size: number
  url: string
}

const audioAttachment = ref<AudioAttachmentData | null>(null)

// Transcription state
const isTranscribing = ref(false)
const transcriptionProgress = ref<TranscriptionStatusResponse | null>(null)

const isDisabled = computed(() => {
  // Allow sending if there's a message OR an audio attachment
  const hasContent = message.value?.trim() || audioAttachment.value
  return !hasContent || chatStore.isStreaming || !props.currentAssistant || isTranscribing.value || isSending.value
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

// Handle audio recording
function handleAudioRecorded(audioBlob: Blob, duration: number) {
  // Create a URL for the audio blob so it can be played
  const audioUrl = URL.createObjectURL(audioBlob)

  audioAttachment.value = {
    blob: audioBlob,
    duration,
    size: audioBlob.size,
    url: audioUrl,
  }
}

function handleAudioError(error: string) {
  emit('error', error)
}

function removeAudioAttachment() {
  // Revoke the object URL to free up memory
  if (audioAttachment.value?.url) {
    URL.revokeObjectURL(audioAttachment.value.url)
  }
  audioAttachment.value = null
}

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

  // Handle audio transcription
  if (audioAttachment.value) {
    try {
      isTranscribing.value = true
      transcriptionProgress.value = null

      console.log('🎤 Starting audio transcription...', {
        duration: audioAttachment.value.duration,
        size: audioAttachment.value.size,
        type: audioAttachment.value.blob.type,
      })

      // Transcribe audio
      const transcribedText = await transcriptionService.transcribeAudio(
        audioAttachment.value.blob,
        'recording.webm',
        (progress) => {
          transcriptionProgress.value = progress
          console.log('📊 Transcription progress:', progress.progression.progress_percent + '%')
        },
      )

      console.log('✅ Transcription completed:', transcribedText)

      // Combine transcribed text with user's text message if any
      let finalMessage = transcribedText
      if (messageContent) {
        finalMessage = `${messageContent}\n\n[Транскрибированное аудио]: ${transcribedText}`
      }

      // Send the transcribed message
      emit('send', finalMessage)

      // Clean up
      if (audioAttachment.value.url) {
        URL.revokeObjectURL(audioAttachment.value.url)
      }
      audioAttachment.value = null
      message.value = ''
      isTranscribing.value = false
      transcriptionProgress.value = null
    } catch (error) {
      console.error('❌ Transcription error:', error)
      const errorMessage = error instanceof Error ? error.message : 'Ошибка транскрибации'
      emit('error', `Не удалось транскрибировать аудио: ${errorMessage}`)
      isTranscribing.value = false
      transcriptionProgress.value = null
    }
  } else if (messageContent) {
    // Send text message only
    emit('send', messageContent)
    // ✅ Don't clear immediately - wait for streaming to start
    // message.value = ''
  }
}

// Cleanup on unmount
onUnmounted(() => {
  // Revoke object URL to prevent memory leaks
  if (audioAttachment.value?.url) {
    URL.revokeObjectURL(audioAttachment.value.url)
  }
})

// Expose methods for parent components if needed
defineExpose({
  focus: () => {
    messageInputRef.value?.$el?.querySelector('textarea')?.focus()
  },
  clear: () => {
    message.value = ''
    // Revoke URL before clearing
    if (audioAttachment.value?.url) {
      URL.revokeObjectURL(audioAttachment.value.url)
    }
    audioAttachment.value = null
  },
  insertText: (text: string) => {
    message.value = text
    // Focus on input after inserting text
    messageInputRef.value?.$el?.querySelector('textarea')?.focus()
  },
  getAudioAttachment: () => audioAttachment.value,
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

.transcription-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--bg-2-5-gray-2);
  border-radius: 12px;
  margin-bottom: 8px;

  &__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: var(--core-1-1-core);
    color: white;
    flex-shrink: 0;

    .spinner {
      animation: spin 1s linear infinite;
    }
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__title {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-3-1-dark);
    margin-bottom: 4px;
  }

  &__status {
    font-size: 12px;
    color: var(--text-3-5-white-gray);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
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
