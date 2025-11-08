<template>
  <div class="audio-attachment">
    <!-- Play/Pause Button -->
    <button
      class="audio-attachment__play-button"
      @click="togglePlayback"
      :title="isPlaying ? 'Пауза' : 'Воспроизвести'"
    >
      <!-- Play Icon -->
      <svg v-if="!isPlaying" width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 4.5L15 10L6 15.5V4.5Z" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>

      <!-- Pause Icon -->
      <svg v-else width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="6" y="5" width="2.5" height="10" rx="1" fill="currentColor"/>
        <rect x="11.5" y="5" width="2.5" height="10" rx="1" fill="currentColor"/>
      </svg>
    </button>

    <div class="audio-attachment__info">
      <div class="audio-attachment__name">Аудиозапись</div>
      <div class="audio-attachment__meta">
        <span class="audio-attachment__time">{{ formattedCurrentTime }} / {{ formattedDuration }}</span>
        <span class="audio-attachment__separator">•</span>
        <span class="audio-attachment__size">{{ formattedSize }}</span>
      </div>

      <!-- Progress Bar -->
      <div class="audio-attachment__progress">
        <div
          class="audio-attachment__progress-bar"
          :style="{ width: progressPercent + '%' }"
        ></div>
      </div>
    </div>

    <button
      class="audio-attachment__remove"
      @click="handleRemove"
      title="Удалить аудио"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <!-- Hidden Audio Element -->
    <audio
      ref="audioRef"
      :src="audioUrl"
      @timeupdate="updateProgress"
      @ended="handleEnded"
      @loadedmetadata="handleLoadedMetadata"
    ></audio>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'

const props = defineProps({
  duration: {
    type: Number,
    required: true,
  },
  size: {
    type: Number,
    required: true,
  },
  audioUrl: {
    type: String,
    required: true,
  },
})

const emit = defineEmits<{
  remove: []
}>()

const audioRef = ref<HTMLAudioElement | null>(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const audioDuration = ref(props.duration)

const formattedDuration = computed(() => {
  const minutes = Math.floor(audioDuration.value / 60)
  const seconds = Math.floor(audioDuration.value % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
})

const formattedCurrentTime = computed(() => {
  const minutes = Math.floor(currentTime.value / 60)
  const seconds = Math.floor(currentTime.value % 60)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
})

const formattedSize = computed(() => {
  const kb = props.size / 1024
  if (kb < 1024) {
    return `${kb.toFixed(0)} KB`
  }
  const mb = kb / 1024
  return `${mb.toFixed(1)} MB`
})

const progressPercent = computed(() => {
  if (audioDuration.value === 0) return 0
  return (currentTime.value / audioDuration.value) * 100
})

function togglePlayback() {
  if (!audioRef.value) return

  if (isPlaying.value) {
    audioRef.value.pause()
    isPlaying.value = false
  } else {
    audioRef.value.play()
    isPlaying.value = true
  }
}

function updateProgress() {
  if (audioRef.value) {
    currentTime.value = audioRef.value.currentTime
  }
}

function handleEnded() {
  isPlaying.value = false
  currentTime.value = 0
  if (audioRef.value) {
    audioRef.value.currentTime = 0
  }
}

function handleLoadedMetadata() {
  if (audioRef.value) {
    audioDuration.value = audioRef.value.duration
  }
}

function handleRemove() {
  // Stop playback if playing
  if (audioRef.value && isPlaying.value) {
    audioRef.value.pause()
    isPlaying.value = false
  }
  emit('remove')
}

// Cleanup on unmount
onUnmounted(() => {
  if (audioRef.value && isPlaying.value) {
    audioRef.value.pause()
  }
})
</script>

<style scoped lang="scss">
.audio-attachment {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--bg-2-5-gray-2);
  border-radius: 12px;
  margin-bottom: 8px;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: var(--bg-2-4-gray);
  }

  &__play-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border: none;
    border-radius: 50%;
    background-color: var(--core-1-1-core);
    color: white;
    cursor: pointer;
    transition: all 0.2s ease;
    flex-shrink: 0;

    &:hover {
      background-color: var(--core-1-2-hover);
      transform: scale(1.05);
    }

    &:active {
      transform: scale(0.95);
    }

    svg {
      transition: transform 0.2s ease;
    }
  }

  &__info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  &__name {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-3-1-dark);
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-3-5-white-gray);
  }

  &__time {
    font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
  }

  &__separator {
    color: var(--text-3-5-white-gray);
  }

  &__progress {
    width: 100%;
    height: 4px;
    background-color: var(--bg-2-4-gray);
    border-radius: 2px;
    overflow: hidden;
    margin-top: 2px;
  }

  &__progress-bar {
    height: 100%;
    background-color: var(--core-1-1-core);
    border-radius: 2px;
    transition: width 0.1s linear;
  }

  &__remove {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
    color: var(--icon-5-2-dark-hover);
    cursor: pointer;
    transition: all 0.2s ease;
    flex-shrink: 0;

    &:hover {
      background-color: var(--system-7-2-error);
      color: white;
    }
  }
}
</style>
