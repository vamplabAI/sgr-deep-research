<template>
  <div class="agent-reasoning-step agent-reasoning-step--final-answer">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">✅ Final Answer</span>
        <span class="agent-reasoning-step__tool-name">FINALANSWERTOOL</span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24
          :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }"
        />
      </div>
    </div>

    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <div class="agent-reasoning-step__details">
        <!-- Completed Steps -->
        <div v-if="data.completed_steps && data.completed_steps.length" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Completed Steps:</span>
          <ul class="agent-reasoning-step__steps-list">
            <li
              v-for="(completedStep, index) in data.completed_steps"
              :key="index"
            >
              {{ completedStep }}
            </li>
          </ul>
        </div>

        <!-- Final Answer -->
        <div v-if="data.answer" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Final Answer:</span>
          <div class="agent-reasoning-step__answer-text">
            <MarkdownRenderer :content="data.answer" />
          </div>
        </div>

        <!-- Status -->
        <div v-if="data.status" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Status:</span>
          <span class="agent-reasoning-step__field-value agent-reasoning-step__status--completed">
            {{ data.status }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIconChevronDown24 from '@/shared/ui/icons/AppIconChevronDown24.vue'
import { MarkdownRenderer } from '@/shared/ui'

interface Props {
  data: {
    reasoning: string
    completed_steps?: string[]
    answer?: string
    status?: string
  }
}

defineProps<Props>()

const isCollapsed = ref(false) // Start expanded to show final answer immediately

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>
