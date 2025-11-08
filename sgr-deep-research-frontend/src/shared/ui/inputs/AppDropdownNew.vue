<template>
  <div ref="dropdownRef" :class="{ 'dropdown--opened': optionsOpened }" class="dropdown">
    <div class="dropdown__input-wrapper" @click="dropdownInputClickHandler">
      <input
        class="dropdown__input"
        type="text"
        readonly
        :disabled="readonly || loading"
        :placeholder="placeholder"
        :value="modelValue ? modelValue[optionLabel] : null"
      />
      <app-icon :class="[optionsOpened ? 'dropdown__icon--active' : '']" name="ChevronDown24" />
    </div>
    <div v-if="optionsOpened" class="dropdown__wrapper">
      <ul class="dropdown__options">
        <li
          v-for="(option, index) in options"
          :key="index"
          class="dropdown__option"
          :class="[
            modelValue && (modelValue as any).value === (option as any)?.value
              ? 'dropdown__option--selected'
              : '',
          ]"
          @click="dropdownUpdateHandler(option)"
        >
          <span class="dropdown__option-name">{{ (option as any).name }}</span>
          <span v-if="(option as any).description" class="dropdown__option-description">{{
            (option as any)?.description
          }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import AppIcon from '../AppIcon.vue'

const emit = defineEmits(['update:modelValue', 'select'])
const props = defineProps({
  label: {
    required: true,
    type: String,
  },
  options: {
    required: true,
    type: [Array, null],
  },
  optionLabel: {
    required: true,
    type: [Number, String],
  },
  placeholder: {
    required: true,
    type: String,
  },
  modelValue: {
    type: Object,
    default: null,
  },
  loading: {
    required: false,
    type: Boolean,
  },
  readonly: {
    required: false,
    type: Boolean,
  },
})

const optionsOpened = ref(false)
const dropdownRef = ref(null)

function dropdownInputClickHandler() {
  if (props.loading || props.readonly) return

  optionsOpened.value = !optionsOpened.value
}

function dropdownUpdateHandler(option: any) {
  emit('select', option)
  emit('update:modelValue', option)

  setTimeout(() => {
    optionsOpened.value = false
  }, 150)
}

function handleClickOutside(event: Event) {
  if (dropdownRef.value && !(dropdownRef.value as HTMLElement).contains(event.target as Node)) {
    optionsOpened.value = false
  }
}

onMounted(() => {
  if (optionsOpened.value) {
    document.addEventListener('click', handleClickOutside)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(optionsOpened, (newVal) => {
  if (newVal) {
    document.addEventListener('click', handleClickOutside)
  } else {
    document.removeEventListener('click', handleClickOutside)
  }
})
</script>

<style scoped lang="scss">
.dropdown {
  align-items: stretch;
  background: var(--bg-2-3-white);
  border-radius: var(--ui-border-radius-20);
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: flex-start;
  margin: 0;
  padding: 0;
  position: relative;

  &--opened {
    background-color: var(--bg-2-5-gray-2);
  }
}

.dropdown__input-wrapper {
  align-items: center;
  cursor: pointer;
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  margin: 0;
  padding: 8px 16px;
  position: relative;
}

.dropdown__input {
  background: transparent;
  border: none;
  border-radius: 4px;
  box-sizing: border-box;
  color: var(--text-3-1-dark);
  cursor: pointer;
  margin: 0;
  max-width: calc(100% - 24px);
  padding: 0;
  text-align: left;
  text-overflow: ellipsis;

  @include typography.but-a3;
}

.dropdown__input[disabled] {
  color: var(--text-3-3-dark-disable);
  cursor: default;
}

.dropdown__icon--active {
  transform: rotate(180deg);
}

.dropdown__input:hover,
.dropdown__input:focus,
.dropdown__input:active {
  border: none;
  outline: none;
}

.dropdown__clear-button,
.dropdown__open-button {
  align-items: center;
  background: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  height: 46px;
  justify-content: center;
  margin: 0;
  padding: 0;
  position: absolute;
  right: 0;
  top: 0;
  width: 46px;
}

.dropdown__open-button path {
  transition: var(--base-transition);
}

.dropdown__open-button:hover path,
.dropdown__open-button:focus path {
  fill: #fff;
}

.dropdown__wrapper {
  background: var(--bg-2-3-white);
  border-radius: var(--ui-border-radius-16);
  box-shadow: var(--ui-box-shadow);
  left: 0;
  margin-top: 4px;
  max-height: 404px;
  overflow: hidden;
  padding: 8px;
  position: absolute;
  right: 0;
  top: 100%;
  z-index: 100;
}

.dropdown__options {
  align-items: stretch;
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100%;
  justify-content: flex-start;
  list-style: none;
  margin: 0;
  max-height: 388px;
  overflow: hidden;
  overflow-y: auto;
  padding: 0;
  scrollbar-color: var(--bg-2-10-hover);
}

.dropdown__option {
  border: 1px solid transparent;
  border-radius: var(--ui-border-radius-8);
  box-sizing: border-box;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  justify-content: flex-start;
  margin: 0;
  padding: 8px;
  transition: var(--base-transition);

  &:hover,
  &:focus {
    background: var(--bg-2-10-hover);
  }

  &--selected {
    border: 1px solid var(--bg-2-2-dark-gray);
  }
}

.dropdown__option-name {
  color: var(--text-3-1-dark);
  text-align: left;

  @include typography.but-a3;
}

.dropdown__option-description {
  -webkit-box-orient: vertical;
  color: var(--text-3-2-dark-gray);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;

  @include typography.subscript-a5;
}
</style>
