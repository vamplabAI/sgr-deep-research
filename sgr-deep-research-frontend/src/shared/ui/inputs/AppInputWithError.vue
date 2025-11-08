<template>
  <div class="input-wrapper">
    <div
      class="input"
      :class="{
        'input--error': errorText,
        'input--disabled': disabled,
        'input--solid': isLabelFocused || (modelValue?.length && !errorText),
        'input--with-slot': $slots.default,
      }"
    >
      <label
        class="input__label"
        :class="{
          'input__label--focused': isLabelFocused,
          'input__label--with-value': modelValue?.length,
        }"
        :for="name"
      >
        {{ label }}
      </label>
      <input
        :id="name"
        class="input__field"
        :type="type"
        :name="name"
        :placeholder="placeholder"
        :required="required"
        :disabled="disabled"
        :value="modelValue"
        :autocomplete="autocomplete"
        :maxlength="maxLength"
        @input="inputChangeHandler"
        @focus="inputFocusHandler"
        @blur="inputBlurHandler"
      />
    </div>
    <slot />
    <span class="input-error-text" :class="{ 'input-error-text--visible': error }">{{
      errorText
    }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const emit = defineEmits(['blur', 'update:modelValue', 'change'])

const props = defineProps({
  placeholder: {
    type: String,
    required: false,
    default: '',
  },
  name: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  disabled: {
    required: false,
    type: Boolean,
    default: false,
  },
  modelValue: {
    type: String,
    default: '',
  },
  required: {
    required: false,
    type: Boolean,
    default: false,
  },
  type: {
    type: String,
    default: 'text',
  },
  errorText: {
    type: String,
    required: false,
    default: '',
  },
  error: {
    type: Boolean,
    required: false,
    default: false,
  },
  maxLength: {
    type: Number,
    required: false,
    default: null,
  },
  autocomplete: {
    type: String,
    required: false,
    default: 'off',
  },
})

const isFocused = ref(false)

function inputChangeHandler(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
  emit('change', props.name)
}

function inputFocusHandler() {
  isFocused.value = true
}

function inputBlurHandler() {
  isFocused.value = false
  emit('blur', props.name)
}

const isLabelFocused = computed(() => isFocused.value)
</script>

<style lang="scss" scoped>
.input-wrapper {
  width: 100%;
}

.input__label {
  color: var(--text-3-2-dark-gray);
  left: 0;
  position: absolute;
  top: 9px;
  transition:
    top 0.2s ease,
    font-size 0.2s ease,
    color 0.2s ease;
  user-select: none;

  @include typography.content-a4;

  &--with-value {
    top: 0;

    @include typography.subscript-a5;
  }

  &--focused {
    top: 0;

    @include typography.subscript-a5;
  }
}

.input {
  align-items: stretch;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding: 15px 0 5px;
  position: relative;
  transition: var(--base-transition);

  &--disabled .input__label {
    color: var(--text-3-3-dark-disable);
  }

  &:has(.input__field:is(:-webkit-autofill, :autofill)) .input__label {
    top: 0;

    @include typography.subscript-a5;
  }

  &::before {
    background: var(--divider-6-1-white);
    bottom: 0;
    content: '';
    display: block;
    height: 1px;
    left: 0;
    position: absolute;
    right: 0;
    transition: var(--base-transition);
    width: 100%;
  }

  &--error::before {
    background: var(--system-7-2-error);
  }

  &--disabled {
    color: var(--text-3-3-dark-disable);
  }

  &--disabled::before {
    background: var(--divider-6-1-white);
  }

  &--solid::before {
    background: var(--text-3-3-dark-disable);
  }

  &--with-slot {
    padding-right: 26px;
  }
}

.input:focus,
.input:focus-visible,
.input:active,
.input:focus-within {
  &::before {
    background: var(--divider-6-3-super-black);
  }
}

.input-wrapper:hover .input::before {
  background-color: var(--divider-6-3-super-black);
}

.input__field {
  background: transparent;
  border: none;
  color: var(--text-3-1-dark);
  margin: 0;
  padding: 0;

  @include typography.content-a4;

  &:hover,
  &:focus-visible {
    outline: none;
  }

  &--error {
    color: var(--system-7-2-error);
  }

  &:disabled {
    color: var(--text-3-3-dark-disable);
  }
}

.input-error-text {
  color: var(--system-7-2-error);
  display: block;
  height: 24px;
  opacity: 0;
  padding: 4px 0;

  @include typography.subscript-a5;

  &--visible {
    opacity: 1;
  }
}
</style>
