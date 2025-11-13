<template>
  <div class="circle-loader">
    <div
      :class="[
        'circle-loader__circle',
        `circle-loader__circle--${size}`,
        `circle-loader__circle--${theme}`,
      ]"
    />
    <p v-if="text" class="circle-loader__text">
      {{ text }}
    </p>
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    default: '',
    required: false,
  },
  size: {
    type: String,
    default: 'sm',
    validator(value) {
      return ['sm', 'md', 'lg'].includes(value)
    },
  },
  theme: {
    required: false,
    default: 'blue',
    validator(value) {
      return ['black', 'blue', 'white'].includes(value)
    },
  },
})
</script>

<style>
.circle-loader {
  display: flex;
  flex-direction: row;
  gap: 12px;
  justify-content: center;
  padding: 0;
}

.circle-loader__circle {
  flex-shrink: 0;
  animation: rotate 1s linear infinite;
  border-radius: 50%;
  position: relative;
}

.circle-loader__circle--sm {
  height: 18px;
  width: 18px;
}

.circle-loader__circle--md {
  height: 30px;
  width: 30px;
}

.circle-loader__circle--lg {
  height: 54px;
  width: 54px;
}

.circle-loader__circle::before {
  animation: prix-clip-fix 2s linear infinite;
  border: 1px solid;
  border-radius: 50%;
  box-sizing: border-box;
  content: '';
  inset: 0;
  position: absolute;
}

.circle-loader__circle--white::before {
  border-color: var(--text-3-4-white);
}

.circle-loader__circle--black::before {
  border-color: var(--text-3-1-dark);
}

.circle-loader__circle--blue::before {
  border-color: var(--core-1-1-core);
}

.circle-loader__text {
  margin: 0;
  padding: 0;
}

@keyframes rotate {
  100% {
    transform: rotate(360deg);
  }
}

@keyframes prix-clip-fix {
  0% {
    clip-path: polygon(50% 50%, 0 0, 0 0, 0 0, 0 0, 0 0);
  }

  25% {
    clip-path: polygon(50% 50%, 0 0, 100% 0, 100% 0, 100% 0, 100% 0);
  }

  50% {
    clip-path: polygon(50% 50%, 0 0, 100% 0, 100% 100%, 100% 100%, 100% 100%);
  }

  75% {
    clip-path: polygon(50% 50%, 0 0, 100% 0, 100% 100%, 0 100%, 0 100%);
  }

  100% {
    clip-path: polygon(50% 50%, 0 0, 100% 0, 100% 100%, 0 100%, 0 0);
  }
}
</style>
