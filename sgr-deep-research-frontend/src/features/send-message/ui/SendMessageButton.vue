<template>
  <app-button-icon
    class="send-message-button"
    icon="ArrowUp16"
    :disabled="isDisabled"
    @click="$emit('send')"
  />
</template>

<script setup>
import { AppButtonIcon } from '@/shared/ui'

defineProps({
  isDisabled: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['send'])
</script>

<style scoped lang="scss">
.send-message-button {
  background-color: var(--icon-5-2-dark-hover);
  color: var(--text-3-4-white);
  padding: 8px;
  transition: background-color 0.2s ease;

  &:disabled {
    opacity: 0.5;
  }

  &:not(:disabled) {
    background-color: var(--core-1-1-core);

    &:hover {
      background-color: var(--core-1-2-hover);
    }
  }
}
</style>
