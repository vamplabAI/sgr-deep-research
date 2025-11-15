<template>
  <div class="wrapper">
    <textarea
      ref="inputRef"
      class="textarea-input"
      name=""
      rows="1"
      placeholder="Ask agent"
      :value="modelValue"
      :maxlength="INPUT_MAX_LENGTH"
      :disabled="disabled"
      @input="changeInput"
      @focus="emit('focus')"
      @blur="emit('blur')"
      @keydown.enter.exact.prevent="$emit('send', modelValue)"
    />
    <button
      v-if="modelValue && modelValue.trim()"
      class="clear-button"
      type="button"
      title="Clear text"
      @click="clearInput"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { INPUT_MAX_LENGTH } from '../config/constants'

const emit = defineEmits(['send', 'focus', 'blur', 'update:modelValue'])

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const inputRef = ref(null)

watch(
  () => props.modelValue,
  () => {
    nextTick(() => {
      resizeTextarea()
    })
  },
)

onMounted(() => {
  resizeTextarea()
})

function changeInput(event) {
  if (props.disabled) return
  emit('update:modelValue', event.target.value)
  resizeTextarea()
}

function resizeTextarea() {
  const input = inputRef.value
  if (!input) return

  input.style.height = 'auto'

  const maxHeight = 200
  const minHeight = 18

  if (input.scrollHeight <= maxHeight) {
    input.style.height = `${Math.max(input.scrollHeight, minHeight)}px`
  } else {
    input.style.height = `${maxHeight}px`
    input.style.overflowY = 'auto'
  }
}

function clearInput() {
  emit('update:modelValue', '')
  nextTick(() => {
    resizeTextarea()
    inputRef.value?.focus()
  })
}
</script>

<style scoped lang="scss">
.wrapper {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 0;
  width: 100%;
  position: relative;
}

.textarea-input {
  background-color: transparent;
  border: none;
  box-sizing: border-box;
  caret-color: var(--core-1-1-core);
  outline: none;
  padding: 4px 0;
  resize: none;
  text-align: left;
  width: 100%;
  line-height: 1.5;
  vertical-align: top;
  overflow-y: hidden;
  max-height: 200px;
  font-family: 'Inter', sans-serif;

  @include typography.field-a4;

  &::placeholder {
    color: var(--text-3-2-dark-gray);
    opacity: 0.7;
    line-height: 1.5;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background-color: #f3f4f6;
    color: #9ca3af;

    &::placeholder {
      color: #9ca3af;
    }
  }

  // Scrollbar styles
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--divider-6-1-white);
    border-radius: 3px;

    &:hover {
      background: var(--text-3-2-dark-gray);
    }
  }
}

.clear-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  margin-top: 2px;
  background: transparent;
  border: none;
  border-radius: 50%;
  color: var(--text-3-2-dark-gray);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;

  &:hover {
    background: var(--bg-2-4-gray-1);
    color: var(--text-3-1-dark);
  }

  &:active {
    transform: scale(0.95);
  }

  svg {
    width: 16px;
    height: 16px;
  }
}
</style>
