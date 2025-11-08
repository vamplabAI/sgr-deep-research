<template>
  <div class="agent-reasoning-step">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">{{ data.reasoning }}</span>
        <span class="agent-reasoning-step__tool-name">EXTRACTPAGECONTENTTOOL</span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24
          :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }"
        />
      </div>
    </div>

    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <div class="agent-reasoning-step__details">
        <!-- URLs -->
        <div v-if="data.urls && data.urls.length" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">URLs:</span>
          <div class="agent-reasoning-step__urls">
            <a
              v-for="(url, index) in data.urls"
              :key="index"
              :href="url"
              target="_blank"
              rel="noopener noreferrer"
              class="agent-reasoning-step__url"
            >
              {{ url }}
            </a>
          </div>
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
    urls?: string[]
  }
}

defineProps<Props>()

const isCollapsed = ref(true)

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>
