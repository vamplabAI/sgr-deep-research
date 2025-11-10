<template>
  <div class="agent-reasoning-step agent-reasoning-step--reasoning">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <div class="agent-reasoning-step__title-main">
          <span class="agent-reasoning-step__icon">🧠</span>
          <span class="agent-reasoning-step__reasoning">Agent Analysis & Planning</span>
        </div>
        <div class="agent-reasoning-step__preview" v-if="isCollapsed && previewText">
          <span class="agent-reasoning-step__preview-text">{{ previewText }}</span>
        </div>
        <span class="agent-reasoning-step__tool-name">REASONINGTOOL</span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24 :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }" />
      </div>
    </div>

    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <div class="agent-reasoning-step__details">
        <!-- Current Situation -->
        <div v-if="data.current_situation" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Current Situation:</span>
          <div class="agent-reasoning-step__situation-text">{{ data.current_situation }}</div>
        </div>

        <!-- Plan Status -->
        <div v-if="data.plan_status" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Plan Status:</span>
          <div class="agent-reasoning-step__status-text">{{ data.plan_status }}</div>
        </div>

        <!-- Reasoning Steps -->
        <div
          v-if="data.reasoning_steps && data.reasoning_steps.length"
          class="agent-reasoning-step__field"
        >
          <span class="agent-reasoning-step__field-label">Analysis Steps:</span>
          <ul class="agent-reasoning-step__reasoning-list">
            <li
              v-for="(reasoningStep, index) in data.reasoning_steps"
              :key="index"
              class="agent-reasoning-step__reasoning-item"
            >
              {{ reasoningStep }}
            </li>
          </ul>
        </div>

        <!-- Remaining Steps -->
        <div
          v-if="data.remaining_steps && data.remaining_steps.length"
          class="agent-reasoning-step__field"
        >
          <span class="agent-reasoning-step__field-label">Next Steps:</span>
          <ul class="agent-reasoning-step__remaining-list">
            <li
              v-for="(remainingStep, index) in data.remaining_steps"
              :key="index"
              class="agent-reasoning-step__remaining-item"
            >
              {{ remainingStep }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIconChevronDown24 from '@/shared/ui/icons/AppIconChevronDown24.vue'

interface Props {
  data: {
    current_situation?: string
    plan_status?: string
    reasoning_steps?: string[]
    remaining_steps?: string[]
    enough_data?: boolean
    task_completed?: boolean
  }
}

const props = defineProps<Props>()

const isCollapsed = ref(true)

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value
}

// Generate preview text for collapsed state
const previewText = computed(() => {
  // Prefer current_situation if available
  if (props.data.current_situation) {
    return truncateText(props.data.current_situation, 100)
  }
  // Otherwise use first reasoning step
  if (props.data.reasoning_steps && props.data.reasoning_steps.length > 0) {
    return truncateText(props.data.reasoning_steps[0] || '', 100)
  }
  // Or plan status
  if (props.data.plan_status) {
    return truncateText(props.data.plan_status, 100)
  }
  return null
})

const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength).trim() + '...'
}
</script>
