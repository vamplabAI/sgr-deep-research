import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ModelOption } from '@/shared/types/store'
import { apiServices } from '@/shared/api/services'

export const useAgentsStore = defineStore('agents', () => {
  // State
  const currentAgent = ref<ModelOption | null>(null)
  const availableModels = ref<ModelOption[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const isInitialized = ref(false)

  // Getters
  const isAgentSelected = computed(() => !!currentAgent.value)

  const currentAgentInfo = computed(() => {
    if (!currentAgent.value) return null

    return {
      ...currentAgent.value,
    }
  })

  // Actions
  const setCurrentAgent = (agent: ModelOption | null) => {
    currentAgent.value = agent
  }

  const fetchAgentsList = async (): Promise<void> => {
    isLoading.value = true
    error.value = null

    try {
      console.log('📡 Fetching models from API...')
      const response = await apiServices.models.getAvailableModels()
      console.log('✅ Received models:', response.data.length)

      // Map all models from API response (no filtering)
      const models = response.data
        .map((model) => ({
          id: model.id,
          name: model.id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), // Format name
          value: model.id,
        }))

      console.log('✅ Available models:', models)
      availableModels.value = models

      // Set first model as default if none selected
      if (!currentAgent.value && models.length > 0) {
        currentAgent.value = models[0] || null
        console.log('✅ Selected default model:', currentAgent.value?.name)
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch agents list'
      console.error('❌ Error fetching agents list:', err)
      availableModels.value = []
    } finally {
      isLoading.value = false
    }
  }

  const clearCurrentAgent = () => {
    currentAgent.value = null
  }

  const initializeAgents = async (): Promise<void> => {
    // Prevent multiple initializations
    if (isInitialized.value) {
      console.log('⚠️ Agents already initialized, skipping...')
      return
    }

    console.log('🔄 Initializing agents...')
    await fetchAgentsList()
    isInitialized.value = true
    console.log('✅ Agents initialization complete')
  }

  return {
    // State
    currentAgent,
    availableModels,
    isLoading,
    error,

    // Getters
    isAgentSelected,
    currentAgentInfo,

    // Actions
    setCurrentAgent,
    fetchAgentsList,
    clearCurrentAgent,
    initializeAgents,
  }
})
