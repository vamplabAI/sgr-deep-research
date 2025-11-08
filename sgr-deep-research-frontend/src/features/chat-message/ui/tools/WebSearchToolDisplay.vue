<template>
  <div class="agent-reasoning-step">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">{{ data.reasoning }}</span>
        <span class="agent-reasoning-step__tool-name">WEBSEARCHTOOL</span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24
          :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }"
        />
      </div>
    </div>

    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <div class="agent-reasoning-step__details">
        <!-- Query -->
        <div v-if="data.query" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Search Query:</span>
          <span class="agent-reasoning-step__field-value">{{ data.query }}</span>
        </div>

        <!-- Max Results -->
        <div v-if="data.max_results" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Max Results:</span>
          <span class="agent-reasoning-step__field-value">{{ data.max_results }}</span>
        </div>

        <!-- Scrape Content -->
        <div v-if="data.scrape_content !== undefined" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Scrape Content:</span>
          <span class="agent-reasoning-step__field-value">{{ data.scrape_content ? 'Yes' : 'No' }}</span>
        </div>

        <!-- Search Results -->
        <div v-if="data.results && data.results.length" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Search Results:</span>
          <div class="agent-reasoning-step__search-results">
            <div
              v-for="(result, index) in data.results"
              :key="index"
              class="search-result-item"
            >
              <div class="search-result-title">
                [{{ index + 1 }}]
                <a
                  v-if="result.link"
                  :href="result.link"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ result.title }}
                </a>
                <span v-else>{{ result.title }}</span>
              </div>
              <div v-if="result.snippet" class="search-result-snippet">
                {{ result.snippet }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIconChevronDown24 from '@/shared/ui/icons/AppIconChevronDown24.vue'

interface SearchResult {
  title: string
  link?: string
  snippet?: string
}

interface Props {
  data: {
    reasoning: string
    query?: string
    max_results?: number
    scrape_content?: boolean
    results?: SearchResult[]
  }
}

defineProps<Props>()

const isCollapsed = ref(true)

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>
