<template>
  <label :class="['radio', { 'radio--supressed': supressed }]">
    <input
      :id="id"
      type="radio"
      :name="name"
      :value="value"
      :checked="isChecked"
      :disabled="disabled"
      @change="$emit('update:modelValue', value)"
    />
    <span class="radio-checkmark" />
    <span v-if="label" class="radio-label">{{ label }}</span>
  </label>
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineEmits(['update:modelValue'])

const props = defineProps({
  id: {
    type: String,
    required: true,
  },
  name: {
    type: String,
    required: true,
  },
  value: {
    type: [String, Number],
    required: true,
  },
  label: {
    type: String,
    default: '',
  },
  modelValue: {
    type: [String, Number, null],
    required: true,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  supressed: {
    type: Boolean,
    default: false,
    required: false,
  },
})

const isChecked = computed(() => {
  return props.modelValue === props.value
})
</script>

<style scoped lang="scss">
input[type='radio'] {
  display: none;
}

.radio-checkmark {
  border: 1px solid var(--text-3-2-dark-gray);
  border-radius: 50%;
  flex-shrink: 0;
  height: 16px;
  position: relative;
  transition: border-color 0.15s ease-in-out;
  width: 16px;
}

.radio-label {
  margin-left: 8px;
}

.radio {
  align-items: center;
  cursor: pointer;
  display: flex;
  text-align: left;

  @include typography.content-a4;

  &--supressed {
    cursor: default;
  }

  &--supressed .radio-checkmark {
    background-color: var(--icon-5-4-white);
    border: 5px solid var(--icon-5-1-dark);
  }

  &--supressed:hover .radio-checkmark {
    background-color: var(--icon-5-4-white);
    border: 5px solid var(--icon-5-1-dark);
  }

  &:hover .radio-checkmark {
    border: 1px solid var(--icon-5-1-dark);
  }
}

.radio:has(input[type='radio']:disabled) {
  cursor: default;
}

input[type='radio']:checked + .radio-checkmark {
  background-color: var(--icon-5-4-white);
  border: 5px solid var(--core-1-1-core);
}

input[type='radio']:disabled + .radio-checkmark {
  border-color: var(--icon-5-3-dark-disable);
}

input[type='radio']:disabled ~ .radio-label {
  color: var(--text-3-2-dark-gray);
}

input[type='radio']:checked:disabled + .radio-checkmark {
  background-color: var(--icon-5-4-white);
  border: 5px solid var(--icon-5-3-dark-disable);
}

.radio:hover input[type='radio']:checked:not(:disabled) + .radio-checkmark {
  border-color: var(--core-1-2-hover);
}
</style>
