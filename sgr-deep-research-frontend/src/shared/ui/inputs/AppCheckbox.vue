<template>
  <label :class="['checkbox-wrapper', { 'checkbox-wrapper--disabled': disabled }]">
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      class="checkbox-input"
      @change="handleChange"
    />
    <span class="checkbox-custom">
      <svg
        v-if="modelValue"
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M5 8L6.29289 9.29289C6.68342 9.68342 7.31658 9.68342 7.70711 9.29289L11 6"
          stroke="white"
          stroke-linecap="round"
        />
      </svg>
    </span>
    <span v-if="title" class="checkbox-label">{{ title }}</span>
  </label>
</template>
<script setup lang="ts">
defineProps({
  title: {
    type: String,
    default: '',
    required: false,
  },
  modelValue: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

function handleChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target) {
    emit('update:modelValue', target.checked)
  }
}
</script>

<style scoped lang="scss">
.checkbox-input {
  cursor: pointer;
  opacity: 0;
  width: 0;
}

.checkbox-custom {
  align-items: center;
  background: transparent;
  border: 1px solid var(--text-3-2-dark-gray);
  border-radius: 4px;
  color: var(--icon-5-7-core-white);
  display: flex;
  flex-shrink: 0;
  height: 16px;
  justify-content: center;
  transition: all 0.2s ease;
  width: 16px;

  & svg {
    flex-shrink: 0;
  }
}

.checkbox-label {
  margin-left: 8px;

  @include typography.content-a4;
}

.checkbox-wrapper {
  align-items: center;
  color: var(--text-3-1-dark);
  cursor: pointer;
  display: inline-flex;

  & .checkbox-custom {
    border-color: var(--divider-6-1-white);
  }

  &--disabled .checkbox-custom {
    border-color: var(--icon-5-3-dark-disable);
    cursor: default;
  }

  &:hover .checkbox-custom {
    border-color: var(--icon-5-1-dark);
  }

  & .checkbox-input:checked + .checkbox-custom {
    background: var(--core-1-1-core);
    border-color: var(--core-1-1-core);
  }

  &--disabled .checkbox-input:checked + .checkbox-custom {
    background: var(--icon-5-3-dark-disable);
    border-color: var(--icon-5-3-dark-disable);
    color: var(--icon-5-4-white);
    cursor: default;
  }

  &:hover:not(.checkbox-wrapper--disabled) .checkbox-input:checked + .checkbox-custom {
    background: var(--core-1-2-hover);
    border-color: var(--core-1-2-hover);
  }

  &--disabled {
    cursor: default;
  }
}
</style>
