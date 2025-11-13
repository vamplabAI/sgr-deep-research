<template>
  <button
    :class="['button-icon', props.disabled ? 'button-icon--disabled' : '']"
    type="button"
    :disabled="disabled"
    @click="buttonClickHandler"
  >
    <app-icon :name="icon" />
  </button>
</template>

<script setup lang="ts">
import AppIcon from '../AppIcon.vue'
const emit = defineEmits(['click'])

const props = defineProps({
  icon: {
    required: true,
    type: String,
  },
  disabled: {
    required: false,
    type: Boolean,
    default: false,
  },
})

function buttonClickHandler(event: MouseEvent) {
  event.stopPropagation()
  emit('click', event)
}
</script>

<style lang="scss" scoped>
.button-icon {
  align-items: center;
  background: transparent;
  border: none;
  border-radius: var(--ui-border-radius-20);
  box-sizing: border-box;
  cursor: pointer;
  display: flex;
  flex-shrink: 0;
  font-size: 0;
  gap: 8px;
  height: min-content;
  justify-content: center;
  overflow: hidden;
  padding: 0;
  transition: var(--base-transition);
  width: min-content;

  &:disabled {
    cursor: default;
  }

  &:hover:not(:disabled) {
    opacity: 0.8;
  }

  &--disabled {
    background-color: var(--but-4-3-dark-disable);
    color: var(--icon-5-3-dark-disable);
  }
}
</style>
