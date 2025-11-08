<template>
  <div class="agent-reasoning-step">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">{{ step.reasoning }}</span>
        <span class="agent-reasoning-step__tool-name">{{
          getToolDisplayName(step.tool_name_discriminator)
        }}</span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24 :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }" />
      </div>
    </div>

    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <!-- Web Search Tool -->
      <div
        v-if="step.tool_name_discriminator === 'websearchtool'"
        class="agent-reasoning-step__details"
      >
        <div v-if="step.query" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Query:</span>
          <span class="agent-reasoning-step__field-value">{{ step.query }}</span>
        </div>
      </div>

      <!-- Extract Page Content Tool -->
      <div
        v-else-if="step.tool_name_discriminator === 'extractpagecontenttool'"
        class="agent-reasoning-step__details"
      >
        <div v-if="step.urls && step.urls.length" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">URLs:</span>
          <div class="agent-reasoning-step__urls">
            <a
              v-for="(url, index) in step.urls"
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

      <!-- Create Report Tool -->
      <div
        v-else-if="step.tool_name_discriminator === 'createreporttool'"
        class="agent-reasoning-step__details"
      >
        <div v-if="step.title" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Title:</span>
          <span class="agent-reasoning-step__field-value">{{ step.title }}</span>
        </div>
        <div v-if="step.user_request_language_reference" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">User Request:</span>
          <span class="agent-reasoning-step__field-value">{{
            step.user_request_language_reference
          }}</span>
        </div>
        <div v-if="step.content" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Content:</span>
          <div class="agent-reasoning-step__content-text">{{ step.content }}</div>
        </div>
      </div>

      <!-- Agent Completion Tool -->
      <div
        v-else-if="step.tool_name_discriminator === 'agentcompletiontool'"
        class="agent-reasoning-step__details"
      >
        <div
          v-if="step.completed_steps && step.completed_steps.length"
          class="agent-reasoning-step__field"
        >
          <span class="agent-reasoning-step__field-label">Completed Steps:</span>
          <ul class="agent-reasoning-step__steps-list">
            <li v-for="(completedStep, index) in step.completed_steps" :key="index">
              {{ completedStep }}
            </li>
          </ul>
        </div>
        <div v-if="step.status" class="agent-reasoning-step__field">
          <span class="agent-reasoning-step__field-label">Status:</span>
          <span class="agent-reasoning-step__field-value agent-reasoning-step__status--completed">{{
            step.status
          }}</span>
        </div>
      </div>

      <!-- Generic fallback for unknown tools -->
      <div v-else class="agent-reasoning-step__details">
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

interface ReasoningStep {
  tool_name_discriminator: string
  reasoning: string
  query?: string
  urls?: string[]
  title?: string
  user_request_language_reference?: string
  content?: string
  completed_steps?: string[]
  status?: string
}

defineProps<{
  step: ReasoningStep
}>()

const isCollapsed = ref(true)

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value
}

const getToolDisplayName = (toolName: string): string => {
  const toolNames: Record<string, string> = {
    websearchtool: 'Web Search',
    extractpagecontenttool: 'Extract Content',
    createreporttool: 'Create Report',
    agentcompletiontool: 'Agent Completion',
  }
  return toolNames[toolName] || toolName
}
</script>

<style scoped>
.agent-reasoning-step {
  width: 100%;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  margin-bottom: 8px;
  background: #fafbfc;
  overflow: hidden;
}

.agent-reasoning-step__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.agent-reasoning-step__header:hover {
  background-color: #f1f3f4;
}

.agent-reasoning-step__title {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-reasoning-step__reasoning {
  font-size: 14px;
  line-height: 1.4;
  color: #1a1a1a;
  font-weight: 500;
}

.agent-reasoning-step__tool-name {
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.agent-reasoning-step__toggle {
  margin-left: 12px;
  transition: transform 0.2s ease;
}

.agent-reasoning-step__chevron--rotated {
  transform: rotate(180deg);
}

.agent-reasoning-step__content {
  border-top: 1px solid #e1e5e9;
  background: #ffffff;
}

.agent-reasoning-step__details {
  padding: 16px;
}

.agent-reasoning-step__field {
  margin-bottom: 12px;
}

.agent-reasoning-step__field:last-child {
  margin-bottom: 0;
}

.agent-reasoning-step__field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.agent-reasoning-step__field-value {
  font-size: 14px;
  color: #1a1a1a;
  line-height: 1.4;
}

.agent-reasoning-step__urls {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-reasoning-step__url {
  font-size: 13px;
  color: #2563eb;
  text-decoration: none;
  word-break: break-all;
  line-height: 1.3;
}

.agent-reasoning-step__url:hover {
  text-decoration: underline;
}

.agent-reasoning-step__content-text {
  font-size: 14px;
  color: #1a1a1a;
  line-height: 1.5;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #e1e5e9;
}

.agent-reasoning-step__steps-list {
  margin: 0;
  padding-left: 16px;
  font-size: 14px;
  color: #1a1a1a;
  line-height: 1.4;
}

.agent-reasoning-step__steps-list li {
  margin-bottom: 4px;
}

.agent-reasoning-step__status--completed {
  color: #059669;
  font-weight: 600;
}

.agent-reasoning-step__json {
  font-size: 12px;
  color: #6b7280;
  background: #f8f9fa;
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #e1e5e9;
  overflow-x: auto;
  margin: 0;
}
</style>
