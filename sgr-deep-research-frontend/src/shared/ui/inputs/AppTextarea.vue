<template>
  <div class="textarea-input">
    <label
      class="textarea-input__label"
      for="text"
      :class="{
        'textarea-input__label--focused': isLabelFocused,
        'textarea-input__label--with-value': text?.length,
      }"
      >{{ label }}</label
    >
    <textarea
      id="text"
      v-model="text"
      class="textarea-input__field"
      :readonly="readonly"
      maxlength="330"
      @focus="textareaFocusHandler"
      @input="textareaInputHandler"
      @blur="textareaBlurHandler"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps({
  initValue: {
    required: true,
    type: [String, null],
  },
  label: {
    required: false,
    type: String,
    default: 'Description:',
  },
  readonly: {
    required: false,
    type: Boolean,
  },
})

const emit = defineEmits(['change'])

const text = ref(props.initValue)

function textareaInputHandler() {
  emit('change', text.value)
}

const isFocused = ref(false)

function textareaFocusHandler() {
  isFocused.value = true
}

function textareaBlurHandler() {
  isFocused.value = false
}

const isLabelFocused = computed(() => isFocused.value)
</script>

<style scoped lang="scss">
.textarea-input {
  align-items: stretch;
  display: flex;
  flex-direction: column;
  gap: 4px;
  justify-content: flex-start;
  padding: 0;
  position: relative;
}

.textarea-input__label {
  color: var(--text-3-2-dark-gray);
  cursor: pointer;
  font-family: var(--rm-font-family);
  left: 16px;
  position: absolute;
  top: 12px;
  transition:
    top 0.2s ease,
    font-size 0.2s ease,
    color 0.2s ease;
  user-select: none;

  @include typography.content-a4;

  &--with-value {
    top: 9px;

    @include typography.subscript-a5;
  }

  &--focused {
    color: var(--text-3-1-dark);
    top: 9px;

    @include typography.subscript-a5;
  }
}

.textarea-input__field {
  background: transparent;
  border: 1px solid var(--divider-6-1-white);
  border-radius: 10px;
  box-sizing: border-box;
  color: var(--text-3-1-dark);
  cursor: pointer;
  flex-grow: 1;
  font-family: var(--rm-font-family);
  margin: 0;
  min-height: 230px;
  padding: 28px 16px 16px;
  resize: none;
  transition: var(--base-transition);

  @include typography.content-a4;
}

.textarea-input__field:hover,
.textarea-input__field:focus,
.textarea-input__field:active {
  outline: none;
}
</style>
