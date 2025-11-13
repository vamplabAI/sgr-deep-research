<template>
  <div
    ref="dropdownRef"
    :class="[
      'dropdown-input',
      {
        'dropdown-input--disabled': disabled,
      },
    ]"
  >
    <div
      :class="[
        'dropdown-input__value-wrapper',
        {
          'dropdown-input__value-wrapper--white': theme === 'white',
          'dropdown-input__value-wrapper--active': optionsOpened,
          'dropdown-input__value-wrapper--selected': selectedValue,
        },
      ]"
      @click="dropdownClickHandler"
    >
      <span class="dropdown-input__placeholder">{{ placeholder }}</span>
      <input
        v-model="selectedValue"
        :class="[
          'dropdown-input__selected-value',
          {
            'dropdown-input__selected-value--white': theme === 'white',
          },
        ]"
        type="text"
        readonly
      />
      <div
        class="dropdown-input__arrow"
        :class="{ 'dropdown-input__arrow--rotated': optionsOpened }"
      >
        <AppIcon name="ChevronDown24" />
      </div>
    </div>
    <div
      v-if="optionsOpened"
      :class="[
        'dropdown-input__options',
        {
          'dropdown-input__options--black': theme === 'white',
        },
      ]"
    >
      <ul v-if="options" class="dropdown-input__options-list">
        <li v-for="(option, index) in options" :key="index" class="dropdown-input__options-item">
          <button
            :class="[
              'dropdown-input__options-button',
              {
                'dropdown-input__options-button--black': theme === 'white',
                'dropdown-input__options-button--with-description': (option as any).description,
              },
            ]"
            type="button"
            @click="dropdownOptionClickHandler(option as any)"
          >
            <span class="dropdown-input__options-title">{{ (option as any).name }}</span>
            <span v-if="(option as any).description" class="dropdown-input__options-description">
              {{ (option as any).description }}
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps({
  placeholder: {
    type: String,
    required: true,
  },
  options: {
    type: Array,
    required: true,
  },
  initValue: {
    type: String,
    required: false,
    default: '',
  },
  theme: {
    required: false,
    type: String,
    validator(value: string) {
      return ['white', 'black'].includes(value)
    },
    default: 'black',
  },
  disabled: {
    required: false,
    type: Boolean,
    default: false,
  },
})
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { AppIcon } from '@/shared/ui'

const emit = defineEmits(['change'])

const selectedValue = ref<string | null>(null)
const optionsOpened = ref(false)
const dropdownRef = ref(null)

function closeDropdownOnScroll() {
  optionsOpened.value = false
}

function dropdownClickHandler() {
  if (props.disabled) {
    return
  }

  if (!optionsOpened.value) {
    window.addEventListener('scroll', closeDropdownOnScroll, { capture: true, once: true })
  }

  optionsOpened.value = !optionsOpened.value
}

function dropdownOptionClickHandler(option: any) {
  selectedValue.value = option.name
  optionsOpened.value = !optionsOpened.value
  emit('change', option)
}

const clickOutside = (event: Event) => {
  if (dropdownRef.value && !(dropdownRef.value as HTMLElement).contains(event.target as Node)) {
    optionsOpened.value = false
  }
}

onMounted(() => {
  if (props.initValue) {
    selectedValue.value = props.initValue || null
  }
  window.addEventListener('click', clickOutside)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', clickOutside)
})

watch(
  () => props.initValue,
  (newValue) => {
    if (newValue) {
      const option = (props.options as any[]).find((opt: any) => opt.name === newValue)
      if (option) {
        selectedValue.value = option.name
      }
    }
  },
  { immediate: true },
)
</script>

<style lang="scss">
.dropdown-input {
  height: 40px;
  position: relative;
  width: 322px;

  &--disabled {
    opacity: 0.5;
  }

  &__value-wrapper {
    align-items: stretch;
    color: var(--text-3-1-dark);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;

    &::before {
      background: var(--divider-6-1-white);
      bottom: 0;
      content: '';
      display: block;
      height: 1px;
      left: 0;
      position: absolute;
      right: 0;
      width: 100%;
    }

    &--selected {
      &::before {
        background: var(--rm-grey);
      }
    }

    &--white {
      &::before {
        background: var(--bg-2-3-white);
      }
    }
  }

  &__selected-value {
    background: transparent;
    border: none;
    color: var(--text-3-1-dark);
    cursor: pointer;
    margin: 0;
    padding: 12px 104px 12px 0;
    width: 100%;

    @include typography.content-a4;

    &:focus {
      outline: none;
    }

    &::placeholder {
      opacity: 0;
    }
  }

  &__placeholder {
    background-color: var(--bg-2-3-white);
    color: var(--text-3-2-dark-gray);
    pointer-events: none;
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    transform-origin: left top;
    transition: all 0.2s ease-in-out;
    z-index: 1;
  }

  &__value-wrapper--active,
  &__value-wrapper--selected {
    .dropdown-input__placeholder {
      /* stylelint-disable-next-line declaration-no-important */
      display: block !important;
      transform: translateY(-26px) scale(0.8);
    }
  }

  &__arrow {
    color: var(--text-3-1-dark);
    pointer-events: none;
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-38%);
    transition: transform 0.2s ease;

    &--rotated {
      transform: translateY(-50%) rotate(180deg);
    }
  }
}

.dropdown-input__options {
  align-items: stretch;
  background: var(--bg-2-3-white);
  border-radius: var(--ui-border-radius-16);
  box-shadow: var(--ui-box-shadow);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  left: 0;
  max-height: 272px;
  padding: 0 0 16px;
  position: absolute;
  right: 0;
  top: calc(100% + 5px);
  transition: var(--base-transition);
  z-index: 1;

  &--with-description {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  &::after {
    bottom: 0;
    content: '';
    display: block;
    height: 1px;
    left: 0;
    position: absolute;
    right: 0;
    width: 100%;
  }

  &--black {
    background: var(--bg-2-1-dark);
  }
}

.dropdown-input__options-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  text-align: start;
  width: 100%;
}

.dropdown-input__options-title {
  color: var(--text-3-1-dark);
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
}

.dropdown-input__options-description {
  -webkit-box-orient: vertical;
  color: var(--text-3-2-dark-gray);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  max-width: 45ch;
  overflow: hidden;
  text-align: left;

  @include typography.subscript-a5;
}

.dropdown-input__options-list {
  align-items: stretch;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  list-style: none;
  margin: 0;
  overflow: auto;
  padding: 0;
}

.dropdown-input__options-item {
  align-items: stretch;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  margin: 0;
  padding: 8px 24px 0 8px;
}

.dropdown-input__options-button {
  background: none;
  border: 1px solid transparent;
  border-radius: var(--ui-border-radius-8);
  color: var(--text-3-1-dark);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  font-family: var(--font-rmr-smooth);
  font-size: 20px;
  font-weight: 400;
  gap: 4px;
  line-height: 20px;
  margin: 0;
  padding: 8px;
  text-align: start;
  width: 100%;

  &:hover {
    border-color: var(--divider-6-3-super-black);
    color: var(--text-3-1-dark);
  }

  &--black {
    color: var(--text-3-4-white);

    &:hover {
      background: var(--bg-2-1-dark);
      color: var(--text-3-4-white);
    }
  }
}
</style>
