<template>
  <div class="select-agent">
    <div v-if="isLoading" class="select-agent__loading">
      Loading...
    </div>
    <select
      v-else
      v-model="selectedModel"
      class="select-agent__dropdown"
      @change="handleModelChange"
    >
      <option v-if="availableModels.length === 0" disabled value="">No models available</option>
      <option
        v-for="model in availableModels"
        :key="model.id"
        :value="model.id"
      >
        {{ model.name }}
      </option>
    </select>
    <div v-if="error" class="select-agent__error">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAgentsStore } from '@/shared/stores'

const agentsStore = useAgentsStore()

// Local state for dropdown
const selectedModel = ref<string>('')

// Computed properties from the store
const isLoading = computed(() => agentsStore.isLoading)
const error = computed(() => agentsStore.error)
const currentAgent = computed(() => agentsStore.currentAgent)
const availableModels = computed(() => agentsStore.availableModels)

// Watch for current agent changes
watch(currentAgent, (newAgent) => {
  if (newAgent) {
    selectedModel.value = newAgent.id
  }
}, { immediate: true })

// Handle model selection
const handleModelChange = () => {
  const selected = availableModels.value.find(m => m.id === selectedModel.value)
  if (selected) {
    agentsStore.setCurrentAgent(selected)
  }
}
</script>

<style scoped lang="scss">
.select-agent {
  position: relative;

  &__loading {
    padding: 10px 20px;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    color: var(--text-3-2-dark-gray);
  }

  &__dropdown {
    min-width: 200px;
    padding: 10px 16px;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    font-weight: 500;
    color: #1a1a1a;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23666' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 36px;

    &:hover {
      background-color: #f9fafb;
      border-color: #d1d5db;
    }

    &:focus {
      outline: none;
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }

    option {
      padding: 8px;
      font-family: 'Inter', sans-serif;
      background: #ffffff;
      color: #1a1a1a;
    }
  }

  &__error {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 4px;
    padding: 4px 8px;
    font-family: 'Inter', sans-serif;
    background: var(--system-7-2-error);
    color: white;
    font-size: 12px;
    border-radius: 12px;
    white-space: nowrap;
  }
}
</style>
