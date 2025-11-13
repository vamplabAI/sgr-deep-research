<template>
  <div class="agent-reasoning-step" v-if="step">
    <!-- Streaming content -->
    <StreamingContentDisplay
      v-if="isReasoningStep && isStreaming"
      :tool-name="(step as ReasoningStep).tool_name_discriminator"
      :raw-content="(step as ReasoningStep)._raw_content"
    />

    <!-- String content -->
    <StringContentDisplay v-else-if="isString" :content="step as string" />

    <!-- Reasoning Tool -->
    <ReasoningToolDisplay v-else-if="isReasoningTool" :data="getToolData(step)" />

    <!-- Clarification Tool -->
    <ClarificationToolDisplay v-else-if="isClarificationTool" :data="getToolData(step)" />

    <!-- Web Search Tool -->
    <WebSearchToolDisplay v-else-if="isWebSearchTool" :data="getToolData(step)" />

    <!-- Extract Page Content Tool -->
    <ExtractPageContentToolDisplay v-else-if="isExtractPageContentTool" :data="getToolData(step)" />

    <!-- Final Answer Tool -->
    <FinalAnswerToolDisplay v-else-if="isFinalAnswerTool" :data="getToolData(step)" />

    <!-- Generic Tool (fallback for other tools) -->
    <GenericToolDisplay v-else :step="step" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ReasoningStep } from '@/shared/api/types'
import StreamingContentDisplay from './tools/StreamingContentDisplay.vue'
import StringContentDisplay from './tools/StringContentDisplay.vue'
import ReasoningToolDisplay from './tools/ReasoningToolDisplay.vue'
import ClarificationToolDisplay from './tools/ClarificationToolDisplay.vue'
import WebSearchToolDisplay from './tools/WebSearchToolDisplay.vue'
import ExtractPageContentToolDisplay from './tools/ExtractPageContentToolDisplay.vue'
import FinalAnswerToolDisplay from './tools/FinalAnswerToolDisplay.vue'
import GenericToolDisplay from './tools/GenericToolDisplay.vue'

interface Props {
  step: ReasoningStep | string
}

const props = defineProps<Props>()

// Type guards
const isStreaming = computed(() => {
  return typeof props.step === 'object' && '_streaming' in props.step && props.step._streaming
})

const isReasoningStep = computed(() => {
  return typeof props.step === 'object' && props.step !== null
})

const isString = computed(() => {
  return typeof props.step === 'string'
})

const getToolName = (step: any): string | null => {
  return step.tool_name_discriminator || step.function?.tool_name_discriminator || null
}

const isReasoningTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName === 'reasoningtool'
})

const isClarificationTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName === 'clarificationtool'
})

const isWebSearchTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName === 'websearchtool'
})

const isExtractPageContentTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName === 'extractpagecontenttool'
})

const isFinalAnswerTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName === 'finalanswertool'
})

/**
 * Extract tool data from step (handles both direct and function-wrapped data)
 */
const getToolData = (step: any) => {
  // If data is in function property, use that, otherwise use step directly
  return step.function || step
}
</script>

<style scoped>
.agent-reasoning-step {
  width: 100%;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  margin-bottom: 20px;
  background: #fafbfc;
  overflow: hidden;
}
</style>
