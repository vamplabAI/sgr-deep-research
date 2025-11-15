<template>
  <button
    :class="['copy-button', { 'copy-button--copied': isCopied }]"
    :disabled="disabled || isCopied"
    :title="isCopied ? 'Copied!' : 'Copy message'"
    @click="handleCopy"
  >
    <AppIcon v-if="!isCopied" name="Copy24" />
    <AppIcon v-else name="Check24" />
    <span v-if="showLabel" class="copy-button__label">
      {{ isCopied ? 'Copied!' : 'Copy' }}
    </span>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AppIcon } from '@/shared/ui'

interface Props {
  disabled?: boolean
  showLabel?: boolean
}

withDefaults(defineProps<Props>(), {
  disabled: false,
  showLabel: false,
})

const emit = defineEmits<{
  copy: []
}>()

const isCopied = ref(false)
let timeoutId: number | null = null

const handleCopy = () => {
  if (isCopied.value) return

  emit('copy')

  isCopied.value = true

  // Reset state after 2 seconds
  if (timeoutId) {
    clearTimeout(timeoutId)
  }

  timeoutId = window.setTimeout(() => {
    isCopied.value = false
    timeoutId = null
  }, 2000)
}
</script>

<style scoped lang="scss">
.copy-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background-color: transparent;
  border: 1px solid var(--divider-6-1-white);
  border-radius: 8px;
  color: var(--text-3-2-dark-gray);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;

  &:hover:not(:disabled) {
    background-color: var(--bg-2-3-white);
    border-color: var(--text-3-2-dark-gray);
    color: var(--text-3-1-dark);
  }

  &:active:not(:disabled) {
    transform: scale(0.95);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  &--copied {
    background-color: var(--system-7-1-success);
    border-color: var(--system-7-1-success);
    color: var(--text-3-4-white);

    &:hover {
      background-color: var(--system-7-1-success);
      border-color: var(--system-7-1-success);
      color: var(--text-3-4-white);
    }
  }

  svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }
}

.copy-button__label {
  user-select: none;
}

@media (max-width: 768px) {
  .copy-button {
    padding: 8px 12px;
    font-size: 14px;

    svg {
      width: 18px;
      height: 18px;
    }
  }
}
</style>
