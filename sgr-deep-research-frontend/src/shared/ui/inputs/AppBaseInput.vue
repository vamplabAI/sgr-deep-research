<template>
  <div class="input">
    <input
      :id="id"
      ref="inputRef"
      v-model="inputValue"
      class="input__field"
      :type="type"
      :name="name"
      placeholder=" "
      :required="required"
      :disabled="disabled"
      :readonly="readonly"
      :maxlength="maxLength"
      @input="inputChangeHandler"
    />
    <span class="input__placeholder">{{ placeholder }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps({
  label: {
    required: true,
    type: String,
  },
  type: {
    required: true,
    type: String,
    validator(value: string) {
      return ['text', 'email', 'password'].includes(value)
    },
  },
  id: {
    required: true,
    type: String,
  },
  name: {
    required: true,
    type: String,
  },
  placeholder: {
    required: false,
    default: '',
    type: String,
  },
  required: {
    required: false,
    type: Boolean,
  },
  disabled: {
    required: false,
    type: Boolean,
  },
  initValue: {
    type: String,
    required: true,
  },
  readonly: {
    required: false,
    type: Boolean,
  },
  maxLength: {
    required: false,
    default: null,
    type: Number,
  },
})

const emit = defineEmits(['change'])

const inputValue = ref(props.initValue)
const inputRef = ref(null)

function inputChangeHandler() {
  emit('change', inputValue.value)
}

watch(
  () => props.initValue,
  (newValue) => {
    if (newValue !== undefined && newValue !== null) {
      inputValue.value = newValue
    }
  },
  { immediate: true },
)
</script>

<style scoped lang="scss">
.input {
  align-items: stretch;
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 40px;
  justify-content: flex-start;
  margin: 0;
  padding: 0;
  position: relative;

  @include typography.content-a4;
}

.input__field {
  background: transparent;
  border: 1px solid transparent;
  border-bottom-color: var(--divider-6-1-white);
  box-sizing: border-box;
  color: var(--text-3-1-dark);
  cursor: pointer;
  line-height: 20px;
  margin: 0;
  padding: 14px 0 4px;
  transition: var(--base-transition);
}

.input__field:not(:placeholder-shown) {
  border-bottom-color: var(--divider-6-3-super-black);
  border-radius: 0;
}

.input__field::placeholder {
  opacity: 0;
}

.input__field::hover {
  opacity: 0;
}

.input__field:focus,
.input__field:focus-visible,
.input__field:active,
.input__field:focus-within {
  border-bottom-color: var(--divider-6-3-super-black);
}

.input__field--error {
  border-color: var(--system-7-2-error);
  color: var(--system-7-2-error);
}

.input__field:hover,
.input__field:focus {
  outline: none;
}

.input__placeholder {
  color: var(--text-3-2-dark-gray);
  pointer-events: none;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  transform-origin: left top;
  transition: all 0.2s ease-in-out;
}

.input__field:focus + .input__placeholder,
.input__field:not(:placeholder-shown) + .input__placeholder {
  padding: 0 4px;
  transform: translateY(-23px) scale(0.8) translateX(-4px);
}

.input:hover .input__field {
  border-bottom-color: var(--divider-6-3-super-black);
}
</style>
