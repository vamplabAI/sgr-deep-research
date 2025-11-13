<template>
  <div class="agent-reasoning-step">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">{{ data.reasoning }}</span>
        <span class="agent-reasoning-step__tool-name">CLARIFICATIONTOOL</span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24
          :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }"
        />
      </div>
    </div>

    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <div class="agent-reasoning-step__details">
        <!-- Questions -->
        <div v-if="data.questions && data.questions.length" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Questions:</span>
          <ul class="agent-reasoning-step__questions-list">
            <li
              v-for="(question, index) in data.questions"
              :key="index"
              class="agent-reasoning-step__question-item"
            >
              {{ question }}
            </li>
          </ul>
        </div>

        <!-- Unclear Terms -->
        <div v-if="data.unclear_terms && data.unclear_terms.length" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Unclear Terms:</span>
          <ul class="agent-reasoning-step__terms-list">
            <li
              v-for="(term, index) in data.unclear_terms"
              :key="index"
              class="agent-reasoning-step__term-item"
            >
              {{ term }}
            </li>
          </ul>
        </div>

        <!-- Assumptions -->
        <div v-if="data.assumptions && data.assumptions.length" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Assumptions:</span>
          <ul class="agent-reasoning-step__assumptions-list">
            <li
              v-for="(assumption, index) in data.assumptions"
              :key="index"
              class="agent-reasoning-step__assumption-item"
            >
              {{ assumption }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIconChevronDown24 from '@/shared/ui/icons/AppIconChevronDown24.vue'

interface Props {
  data: {
    reasoning: string
    questions?: string[]
    unclear_terms?: string[]
    assumptions?: string[]
  }
}

defineProps<Props>()

const isCollapsed = ref(true)

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>
