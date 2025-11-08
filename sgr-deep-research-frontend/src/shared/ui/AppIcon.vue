<template>
  <span v-if="NamedIcon" class="icon-container">
    <component :is="NamedIcon" />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import * as Icons from './icons'

const props = defineProps({
  name: {
    type: String,
    required: true,
  },
})

const NamedIcon = computed(() => {
  const iconName = `AppIcon${props.name}` as keyof typeof Icons
  return Icons[iconName]
})
</script>

<style scoped lang="scss">
.icon-container {
  align-items: center;
  display: inline-flex;
  flex-grow: 0;
  flex-shrink: 0;
  font-size: 0;
  justify-content: center;
}
</style>
