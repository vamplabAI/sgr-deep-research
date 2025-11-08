<template>
  <div class="audio-recorder">
    <!-- Record Button with Dropdown (shown when not recording) -->
    <div v-if="!isRecording" class="audio-recorder__controls">
      <button
        class="audio-recorder__button audio-recorder__button--record"
        :disabled="disabled"
        @click="startRecording"
        title="Записать аудио"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M10 13C11.6569 13 13 11.6569 13 10V5C13 3.34315 11.6569 2 10 2C8.34315 2 7 3.34315 7 5V10C7 11.6569 8.34315 13 10 13Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M16 10C16 13.3137 13.3137 16 10 16C6.68629 16 4 13.3137 4 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M10 16V18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <!-- Microphone Selection Dropdown -->
      <div ref="deviceSelectorRef" class="audio-recorder__device-selector" v-if="audioDevices.length > 1">
        <button
          class="audio-recorder__device-button"
          @click="toggleDeviceList"
          :disabled="disabled"
          title="Выбрать микрофон"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>

        <!-- Device List Dropdown -->
        <div v-if="showDeviceList" class="audio-recorder__device-list">
          <div
            v-for="device in audioDevices"
            :key="device.deviceId"
            class="audio-recorder__device-item"
            :class="{ 'audio-recorder__device-item--active': device.deviceId === selectedDeviceId }"
            @click="selectDevice(device.deviceId)"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M8 10C9.10457 10 10 9.10457 10 8V4C10 2.89543 9.10457 2 8 2C6.89543 2 6 2.89543 6 4V8C6 9.10457 6.89543 10 8 10Z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M12 8C12 10.2091 10.2091 12 8 12C5.79086 12 4 10.2091 4 8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="audio-recorder__device-name">{{ device.label || `Микрофон ${device.deviceId.slice(0, 8)}` }}</span>
            <svg v-if="device.deviceId === selectedDeviceId" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M13 4L6 11L3 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Recording State (shown while recording) -->
    <div v-else class="audio-recorder__recording">
      <!-- Recording Time -->
      <span class="audio-recorder__time" :class="{ 'audio-recorder__time--warning': isNearLimit }">
        {{ formattedTime }}
      </span>

      <!-- Stop Button with Pulsing Circle -->
      <div class="audio-recorder__stop-wrapper">
        <!-- Пульсирующая окружность -->
        <div
          class="audio-recorder__pulse-ring"
          :style="{
            transform: `translate(-50%, -50%) scale(${audioLevel})`,
            opacity: Math.min(0.8, audioLevel * 0.35)
          }"
        ></div>

        <button
          class="audio-recorder__button audio-recorder__button--stop"
          @click="stopRecording"
          title="Остановить запись"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="4" width="8" height="8" rx="1" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="audio-recorder__error">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { MAX_AUDIO_DURATION_SECONDS } from '../config/constants'

const emit = defineEmits<{
  recorded: [audioBlob: Blob, duration: number]
  error: [error: string]
}>()

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
})

const isRecording = ref(false)
const recordingTime = ref(0)
const error = ref<string | null>(null)
const audioDevices = ref<MediaDeviceInfo[]>([])
const selectedDeviceId = ref<string | null>(null)
const showDeviceList = ref(false)
const audioLevel = ref(0.1) // Уровень звука от 0 до 1
const deviceSelectorRef = ref<HTMLElement | null>(null)

let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let recordingInterval: number | null = null
let permissionGranted = false // Track if permission was already granted
let audioContext: AudioContext | null = null
let analyser: AnalyserNode | null = null
let animationFrameId: number | null = null

const STORAGE_KEY = 'selected_audio_device_id'

const formattedTime = computed(() => {
  const time = recordingTime.value || 0
  const minutes = Math.floor(time / 60)
  const seconds = time % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
})

const remainingTime = computed(() => {
  const time = recordingTime.value || 0
  return MAX_AUDIO_DURATION_SECONDS - time
})

const isNearLimit = computed(() => {
  return remainingTime.value <= 60 // Последняя минута
})

// Load audio devices
async function loadAudioDevices() {
  try {
    // Сначала пробуем получить устройства БЕЗ запроса разрешения
    const devices = await navigator.mediaDevices.enumerateDevices()
    const audioInputs = devices.filter(device => device.kind === 'audioinput')

    // Если есть устройства с labels, значит разрешение уже было дано
    if (audioInputs.length > 0 && audioInputs[0]?.label) {
      permissionGranted = true
      audioDevices.value = audioInputs
      console.log('🎤 Microphone permission already granted')
    } else {
      // Если labels пустые, просто показываем устройства без имен
      // Разрешение запросим только при начале записи
      audioDevices.value = audioInputs
      console.log('🎤 Audio devices found, but permission not granted yet')
    }

    // Load saved device or use default
    const savedDeviceId = localStorage.getItem(STORAGE_KEY)
    if (savedDeviceId && audioDevices.value.some(d => d.deviceId === savedDeviceId)) {
      selectedDeviceId.value = savedDeviceId
    } else if (audioDevices.value.length > 0) {
      const firstDevice = audioDevices.value[0]
      if (firstDevice) {
        selectedDeviceId.value = firstDevice.deviceId
      }
    }

    console.log('🎤 Available audio devices:', audioDevices.value.length)
  } catch (err) {
    console.error('Error loading audio devices:', err)
  }
}

function toggleDeviceList() {
  showDeviceList.value = !showDeviceList.value
}

function selectDevice(deviceId: string) {
  selectedDeviceId.value = deviceId
  localStorage.setItem(STORAGE_KEY, deviceId)
  showDeviceList.value = false
  console.log('🎤 Selected device:', deviceId)
}

// Close device list when clicking outside
function handleClickOutside(event: MouseEvent) {
  if (deviceSelectorRef.value && !deviceSelectorRef.value.contains(event.target as Node)) {
    showDeviceList.value = false
  }
}

// Add/remove click outside listener when device list opens/closes
function setupClickOutsideListener() {
  if (showDeviceList.value) {
    document.addEventListener('click', handleClickOutside)
  } else {
    document.removeEventListener('click', handleClickOutside)
  }
}

// Счетчик кадров для логирования
let frameCount = 0

// Анализ уровня звука в реальном времени
function analyzeAudioLevel() {
  if (!analyser) {
    console.warn('⚠️ Analyser is null')
    return
  }

  const dataArray = new Uint8Array(analyser.frequencyBinCount)
  analyser.getByteFrequencyData(dataArray) // Используем частотные данные

  // Вычисляем средний уровень звука
  let sum = 0
  let max = 0
  for (let i = 0; i < dataArray.length; i++) {
    const value = dataArray[i] || 0
    sum += value
    if (value > max) max = value
  }
  const average = sum / dataArray.length

  // Нормализуем значение от 0 до 1 с усилением чувствительности
  // Используем степенную функцию для усиления малых изменений
  const normalized = average / 255 // Нормализуем к 0-1
  const amplified = Math.pow(normalized, 0.3) // Усиливаем еще больше (кубический корень)
  const scaled = amplified * 5 // Увеличиваем в 5 раз
  const newLevel = Math.max(0.5, Math.min(2.5, scaled)) // Минимум 0.5, максимум 2.5
  audioLevel.value = newLevel

  // Логируем каждые 60 фреймов (~1 секунда)
  frameCount++
  if (frameCount % 60 === 0) {
    console.log('🎵 Audio level:', {
      average: average.toFixed(2),
      max: max,
      normalized: normalized.toFixed(3),
      amplified: amplified.toFixed(3),
      scaled: scaled.toFixed(3),
      final: newLevel.toFixed(3),
      audioLevel: audioLevel.value.toFixed(3),
      sampleData: Array.from(dataArray.slice(0, 10))
    })
  }

  // Продолжаем анализ
  if (isRecording.value) {
    animationFrameId = requestAnimationFrame(analyzeAudioLevel)
  } else {
    console.log('🛑 Stopping audio analysis')
  }
}

async function startRecording() {
  try {
    error.value = null

    // Request microphone access with specific device if selected
    const constraints: MediaStreamConstraints = {
      audio: selectedDeviceId.value
        ? { deviceId: { exact: selectedDeviceId.value } }
        : true
    }

    console.log('🎤 Requesting microphone access with constraints:', constraints)
    const stream = await navigator.mediaDevices.getUserMedia(constraints)

    // Создаем AudioContext для анализа уровня звука
    audioContext = new AudioContext()
    const source = audioContext.createMediaStreamSource(stream)
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 512 // Увеличиваем для более точного анализа
    analyser.smoothingTimeConstant = 0.3 // Меньше сглаживания для быстрого отклика
    analyser.minDecibels = -70 // Повышаем чувствительность
    analyser.maxDecibels = -20 // Расширяем диапазон
    source.connect(analyser)

    console.log('🎵 Audio analyser created:', {
      fftSize: analyser.fftSize,
      frequencyBinCount: analyser.frequencyBinCount,
      smoothingTimeConstant: analyser.smoothingTimeConstant,
      minDecibels: analyser.minDecibels,
      maxDecibels: analyser.maxDecibels
    })

    // Create MediaRecorder
    mediaRecorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
    })

    audioChunks = []

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
      emit('recorded', audioBlob, recordingTime.value)

      // Stop all tracks
      stream.getTracks().forEach(track => track.stop())

      // Reset state
      recordingTime.value = 0
      if (recordingInterval) {
        clearInterval(recordingInterval)
        recordingInterval = null
      }
    }

    // Start recording
    mediaRecorder.start()
    isRecording.value = true
    recordingTime.value = 0

    // Запускаем анализ уровня звука ПОСЛЕ установки isRecording
    console.log('🎵 Starting audio level analysis..., isRecording:', isRecording.value)
    analyzeAudioLevel()

    // Start timer
    recordingInterval = window.setInterval(() => {
      recordingTime.value++

      // Автоматически останавливаем запись при достижении максимальной длительности
      if (recordingTime.value >= MAX_AUDIO_DURATION_SECONDS) {
        console.log(`⏱️ Достигнут лимит записи: ${MAX_AUDIO_DURATION_SECONDS} секунд`)
        stopRecording()
      }
    }, 1000)

  } catch (err) {
    let errorMessage = 'Не удалось получить доступ к микрофону'

    if (err instanceof Error) {
      // Handle specific error types
      if (err.name === 'NotReadableError') {
        errorMessage = 'Микрофон занят другим приложением. Закройте другие приложения, использующие микрофон, и попробуйте снова.'
      } else if (err.name === 'NotAllowedError') {
        errorMessage = 'Доступ к микрофону запрещен. Разрешите доступ в настройках браузера.'
      } else if (err.name === 'NotFoundError') {
        errorMessage = 'Микрофон не найден. Подключите микрофон и попробуйте снова.'
      } else if (err.name === 'OverconstrainedError') {
        errorMessage = 'Выбранный микрофон недоступен. Попробуйте выбрать другой.'
        // Reset to default device
        selectedDeviceId.value = null
        localStorage.removeItem(STORAGE_KEY)
        await loadAudioDevices()
      } else {
        errorMessage = err.message
      }
    }

    error.value = errorMessage
    emit('error', errorMessage)
    console.error('Error accessing microphone:', err)
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.stop()
    isRecording.value = false
  }

  // Останавливаем анализ звука
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }

  // Закрываем AudioContext
  if (audioContext) {
    audioContext.close()
    audioContext = null
  }

  analyser = null
  audioLevel.value = 0.1
}

// Watch for device list changes to add/remove click outside listener
watch(showDeviceList, () => {
  setupClickOutsideListener()
})

// Initialize on mount
onMounted(() => {
  loadAudioDevices()

  // Listen for device changes
  navigator.mediaDevices.addEventListener('devicechange', loadAudioDevices)
})

// Cleanup on unmount
onUnmounted(() => {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.stop()
  }
  if (recordingInterval) {
    clearInterval(recordingInterval)
  }

  // Останавливаем анализ звука
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }

  // Закрываем AudioContext
  if (audioContext) {
    audioContext.close()
  }

  // Remove event listeners
  navigator.mediaDevices.removeEventListener('devicechange', loadAudioDevices)
  document.removeEventListener('click', handleClickOutside)
})

// Expose methods
defineExpose({
  startRecording,
  stopRecording,
  isRecording: computed(() => isRecording.value),
  refreshDevices: loadAudioDevices,
})
</script>

<style scoped lang="scss">
.audio-recorder {
  display: flex;
  align-items: center;
  gap: 8px;

  &__controls {
    display: flex;
    align-items: center;
    gap: 4px;
    position: relative;
  }

  &__button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s ease;
    background-color: transparent;
    color: var(--icon-5-2-dark-hover);

    &:hover:not(:disabled) {
      background-color: var(--bg-2-5-gray-2);
      color: var(--core-1-1-core);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    &--record {
      &:hover:not(:disabled) {
        transform: scale(1.05);
      }
    }

    &--stop {
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      color: white;
      width: 32px;
      height: 32px;
      position: relative;
      z-index: 1;
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);

      &:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        transform: scale(1.05);
      }
    }
  }

  &__device-selector {
    position: relative;
  }

  &__device-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
    background-color: transparent;
    color: var(--icon-5-2-dark-hover);

    &:hover:not(:disabled) {
      background-color: var(--bg-2-5-gray-2);
      color: var(--core-1-1-core);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }

  &__device-list {
    position: absolute;
    bottom: calc(100% + 8px); // Открываем вверх
    right: 0;
    min-width: 250px;
    max-width: 350px;
    background-color: var(--bg-2-3-white);
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: 4px;
    z-index: 1000;
    max-height: min(400px, 60vh); // Адаптивная высота
    overflow-y: auto;
    overflow-x: hidden;

    // Улучшенная прокрутка
    scrollbar-width: thin;
    scrollbar-color: var(--bg-2-5-gray-2) transparent;

    &::-webkit-scrollbar {
      width: 6px;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }

    &::-webkit-scrollbar-thumb {
      background-color: var(--bg-2-5-gray-2);
      border-radius: 3px;

      &:hover {
        background-color: var(--icon-5-2-dark-hover);
      }
    }

    // Плавное появление
    animation: slideUp 0.2s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  &__device-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background-color 0.2s ease;
    color: var(--text-3-1-dark);

    &:hover {
      background-color: var(--bg-2-5-gray-2);
    }

    &--active {
      background-color: var(--bg-2-5-gray-2);
      color: var(--core-1-1-core);
    }

    svg {
      flex-shrink: 0;
      color: var(--icon-5-2-dark-hover);
    }

    &--active svg {
      color: var(--core-1-1-core);
    }
  }

  &__device-name {
    flex: 1;
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__recording {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 4px 8px;
    background-color: var(--bg-2-5-gray-2);
    border-radius: 20px;
  }

  &__stop-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
  }

  &__pulse-ring {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: radial-gradient(
      circle,
      rgba(59, 130, 246, 0.5) 0%,    /* Blue-500 */
      rgba(96, 165, 250, 0.3) 40%,   /* Blue-400 */
      rgba(147, 197, 253, 0.15) 70%, /* Blue-300 */
      transparent 100%
    );
    box-shadow:
      0 0 20px rgba(59, 130, 246, 0.4),
      0 0 40px rgba(59, 130, 246, 0.2),
      inset 0 0 20px rgba(59, 130, 246, 0.1);
    border: 2px solid rgba(59, 130, 246, 0.6);
    transform: translate(-50%, -50%) scale(1);
    transform-origin: center;
    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    will-change: transform, opacity;
    pointer-events: none;
    z-index: 0;
  }

  &__time {
    font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-3-1-dark);
    min-width: 40px;
    transition: color 0.3s ease;

    &--warning {
      color: var(--system-7-2-error);
      animation: pulse-warning 1s ease-in-out infinite;
    }
  }

  @keyframes pulse-warning {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: 0.6;
    }
  }

  &__error {
    font-size: 12px;
    color: var(--system-7-2-error);
    margin-left: 8px;
  }
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.1;
  }
  100% {
    transform: scale(1);
    opacity: 0.3;
  }
}
</style>
