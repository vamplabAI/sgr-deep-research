<template>
  <div class="agent-reasoning-step" v-if="step && !isEmptyString">
    <!-- Streaming content -->
    <StreamingContentDisplay
      v-if="isStreaming"
      :tool-name="(step as any).tool_name_discriminator"
      :raw-content="(step as any)._raw_content"
    />

    <!-- String content -->
    <StringContentDisplay
      v-else-if="isString"
      :content="step as string"
    />

    <!-- Reasoning Tool -->
    <ReasoningToolDisplay
      v-else-if="isReasoningTool"
      :data="getToolData(step)"
    />

    <!-- Clarification Tool -->
    <ClarificationToolDisplay
      v-else-if="isClarificationTool"
      :data="getToolData(step)"
    />

    <!-- Web Search Tool -->
    <WebSearchToolDisplay
      v-else-if="isWebSearchTool"
      :data="getToolData(step)"
    />

    <!-- Extract Page Content Tool -->
    <ExtractPageContentToolDisplay
      v-else-if="isExtractPageContentTool"
      :data="getToolData(step)"
    />

    <!-- Final Answer Tool -->
    <FinalAnswerToolDisplay
      v-else-if="isFinalAnswerTool"
      :data="getToolData(step)"
    />

    <!-- Generic Tool (fallback for other tools) -->
    <GenericToolDisplay
      v-else
      :step="step"
    />
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

const isString = computed(() => {
  return typeof props.step === 'string'
})

const isEmptyString = computed(() => {
  return typeof props.step === 'string' && props.step.trim() === ''
})

const getToolName = (step: any): string | null => {
  return step.tool_name_discriminator || step.function?.tool_name_discriminator || null
}

const isReasoningTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
    return toolName?.toLowerCase() === 'reasoningtool'
})

const isClarificationTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName === 'clarificationtool'
})

const isWebSearchTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName?.toLowerCase() === 'websearchtool'
})

const isExtractPageContentTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName?.toLowerCase() === 'extractpagecontenttool'
})

const isFinalAnswerTool = computed(() => {
  if (typeof props.step === 'string') return false
  const toolName = getToolName(props.step)
  return toolName?.toLowerCase() === 'finalanswertool'
})

/**
 * Extract tool data from step (handles both direct and function-wrapped data)
 */
const getToolData = (step: any) => {
  // If data is in function property, use that, otherwise use step directly
  return step.function || step
}
</script>

<style src="./tools/tool-display-styles.css"></style>
