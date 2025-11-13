<template>
  <button :class="buttonClasses()" :type="type" :disabled="disabled" @click="buttonClickHandler">
    <span :class="['button__content', icon && 'button__content--with-icon']">
      <AppCircleLoader v-if="loading" />
      <app-icon v-else-if="icon" :name="icon" />
      {{ text }}
    </span>
  </button>
</template>

<script setup lang="ts">
import AppCircleLoader from '../misc/AppCircleLoader.vue'
import AppIcon from '../AppIcon.vue'
const emit = defineEmits(['click'])

const props = defineProps({
  text: {
    required: false,
    type: String,
    default: null,
  },
  icon: {
    required: false,
    type: String,
    default: null,
  },
  theme: {
    required: true,
    type: String,
    validator(value: string) {
      return [
        'outlined',
        'primary',
        'white',
        'gray',
        'black',
        'danger',
        'success',
        'secondary',
        'text',
      ].includes(value)
    },
  },
  loading: {
    type: Boolean,
    default: false,
    required: false,
  },
  disabled: {
    required: false,
    type: Boolean,
    default: false,
  },
  type: {
    required: false,
    default: 'button',
    type: String as () => 'button' | 'reset' | 'submit',
    validator(value: string) {
      return ['button', 'reset', 'submit'].includes(value)
    },
  },
})

function buttonClickHandler() {
  if (props.disabled || props.loading) return

  emit('click')
}

const buttonClasses = () => {
  return [
    'button-new',
    themeClass(props.theme),
    props.icon && !props.text ? 'button-new--icon-centered' : '',
    props.disabled ? 'button-new--disabled' : '',
  ].filter(Boolean) // Remove any empty strings
}

// Helper function to get theme class
const themeClass = (theme: string) => {
  if (theme === 'gray') return 'button-new--gray'
  if (theme === 'white') return 'button-new--white'
  if (theme === 'black') return 'button-new--black'
  if (theme === 'danger') return 'button-new--danger'
  if (theme === 'success') return 'button-new--success'
  if (theme === 'primary') return 'button-new--primary'
  if (theme === 'outlined') return 'button-new--outlined'
  if (theme === 'secondary') return 'button-new--secondary'
  return ''
}
</script>

<style lang="scss" scoped>
.button-new {
  align-items: center;
  background: var(--bg-2-1-dark);
  border: none;
  border-radius: var(--ui-border-radius-20);
  box-sizing: border-box;
  color: var(--text-3-7-core-white);
  cursor: pointer;
  display: flex;
  height: 40px;
  justify-content: center;
  padding: 11px 18px;
  width: 100%;

  &--primary {
    background: var(--core-1-1-core);
    color: var(--text-3-7-core-white);

    &:hover:not(:disabled) {
      background-color: var(--core-1-2-hover);
    }
  }

  &--secondary {
    background-color: var(--bg-2-4-gray-1);
    color: var(--text-3-1-dark);
  }

  &--white {
    background-color: var(--bg-2-3-white);
    color: var(--text-3-1-dark);
  }

  &--black {
    background-color: var(--bg-2-1-dark);
    color: var(--text-3-4-white);
  }

  &--danger {
    background-color: var(--system-7-2-error);
    color: var(--text-3-4-white);
  }

  &--gray {
    background-color: var(--but-4-2-dark-gray);
    color: var(--text-3-8-core-black);
  }

  &--outlined {
    background: transparent;
    border: 1px solid var(--but-4-2-dark-gray);
    color: var(--text-3-8-core-black);
  }

  &--icon-centered {
    padding: 0;

    &::before {
      left: calc(50% - 12px);
    }
  }

  &--disabled {
    background-color: var(--but-4-3-dark-disable);
    color: var(--text-3-3-dark-disable);
  }

  &:disabled {
    cursor: default;
  }
}

.button__content {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: center;
  overflow: hidden;
  padding: 0 8px;
  text-overflow: ellipsis;
  white-space: nowrap;

  @include typography.but-a3;

  &--with-icon {
    padding: 0;
  }
}
</style>
