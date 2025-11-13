<template>
  <div class="agent-reasoning-step">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">
          {{ step.reasoning || step.function?.reasoning || 'Tool Execution' }}
        </span>
        <span class="agent-reasoning-step__tool-name">
          {{ (step.tool_name_discriminator || step.function?.tool_name_discriminator || 'unknown').toUpperCase() }}
        </span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24
          :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }"
        />
      </div>
    </div>

    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <div class="agent-reasoning-step__details">
        <div class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Tool Data:</span>
          <pre class="agent-reasoning-step__json">{{ JSON.stringify(step, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIconChevronDown24 from '@/shared/ui/icons/AppIconChevronDown24.vue'

interface Props {
  step: any
}

defineProps<Props>()

const isCollapsed = ref(true)

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>
