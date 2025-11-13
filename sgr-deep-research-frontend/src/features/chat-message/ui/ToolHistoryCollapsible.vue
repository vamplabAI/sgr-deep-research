<template>
  <div class="tool-history-collapsible">
    <button class="tool-history-toggle" @click="toggleExpanded">
      <span class="toggle-icon" :class="{ expanded: isExpanded }">▶</span>
      <span class="toggle-text">
        {{ isExpanded ? 'Hide' : 'Show' }} agent work history ({{ toolHistory.length }} steps)
      </span>
    </button>

    <div v-if="isExpanded" class="tool-history-content">
      <div
        v-for="(tool, index) in toolHistory"
        :key="tool.id"
        class="tool-history-item"
      >
        <div class="tool-header" :class="{ 'tool-header--reasoning': tool.tool_name === 'reasoningtool' }">
          <span class="tool-number">#{{ index + 1 }}</span>
          <span v-if="tool.tool_name === 'reasoningtool'" class="tool-icon">🧠</span>
          <span v-else-if="tool.tool_name" class="tool-icon">🔧</span>
          <span v-if="tool.tool_name" class="tool-type tool-name">{{ tool.tool_name }}</span>
          <span v-else-if="tool.role === 'assistant'" class="tool-type">Tool Call</span>
        </div>

        <div class="tool-body">
          <!-- Assistant tool call with tool_calls -->
          <div v-if="tool.role === 'assistant' && tool.tool_calls" class="tool-call">
            <div v-for="(call, callKey) in tool.tool_calls" :key="callKey" class="tool-call-item">
              <div class="tool-call-function">
                <strong>{{ call.function?.name || 'unknown' }}</strong>
              </div>
              <div v-if="call.function?.arguments" class="tool-call-args">
                <pre>{{ formatJSON(call.function.arguments) }}</pre>
              </div>
            </div>
          </div>

          <!-- Assistant reasoning (without tool_calls) -->
          <div v-else-if="tool.role === 'assistant' && tool.content" class="tool-reasoning">
            <div class="tool-reasoning-content">
              <pre>{{ tool.content }}</pre>
            </div>
          </div>

          <!-- Tool response -->
          <div v-else-if="tool.role === 'tool'" class="tool-response">
            <div class="tool-response-content">
              <pre>{{ tool.content || 'No response' }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  toolHistory: Array<{
    id: string
    role: string
    content: string | null
    tool_calls?: any
    tool_name?: string | null
    tool_call_id?: string | null
    sequence_number?: number
  }>
}

const props = defineProps<Props>()

const isExpanded = ref(false)

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

const formatJSON = (jsonString: string) => {
  try {
    const parsed = JSON.parse(jsonString)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return jsonString
  }
}
</script>

<style scoped lang="scss">
.tool-history-collapsible {
  margin-top: 12px;
  border-top: 1px solid var(--divider-6-1-white);
  padding-top: 12px;
}

.tool-history-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-2-4-gray-1);
  border: 1px solid var(--divider-6-1-white);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  text-align: left;

  &:hover {
    background: var(--bg-2-3-white);
    border-color: var(--core-1-1-core);
  }

  .toggle-icon {
    font-size: 10px;
    transition: transform 0.2s ease;
    color: var(--text-3-2-dark-gray);

    &.expanded {
      transform: rotate(90deg);
    }
  }

  .toggle-text {
    @include typography.content-a4;
    color: var(--text-3-2-dark-gray);
    font-weight: 500;
  }
}

.tool-history-content {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-history-item {
  background: var(--bg-2-4-gray-1);
  border: 1px solid var(--divider-6-1-white);
  border-radius: 8px;
  overflow: hidden;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-2-3-white);
  border-bottom: 1px solid var(--divider-6-1-white);
  transition: background 0.2s ease;

  &.tool-header--reasoning {
    background: linear-gradient(90deg, rgba(99, 102, 241, 0.05) 0%, var(--bg-2-3-white) 100%);
    border-left: 3px solid rgba(99, 102, 241, 0.4);
  }

  .tool-number {
    @include typography.subscript-bold-a5;
    color: var(--text-3-2-dark-gray);
    background: var(--bg-2-4-gray-1);
    padding: 2px 6px;
    border-radius: 4px;
    min-width: 24px;
    text-align: center;
  }

  .tool-icon {
    font-size: 16px;
    line-height: 1;
  }

  .tool-type {
    @include typography.subscript-a5;
    color: var(--text-3-2-dark-gray);
    font-weight: 600;
  }

  .tool-name {
    color: var(--core-1-1-core);
    font-family: monospace;
    font-size: 12px;
  }
}

.tool-body {
  padding: 12px;
}

.tool-call-item {
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }
}

.tool-call-function {
  @include typography.content-a4;
  color: var(--text-3-1-dark);
  margin-bottom: 6px;
  font-family: monospace;

  strong {
    color: var(--core-1-1-core);
  }
}

.tool-call-args {
  pre {
    @include typography.subscript-a5;
    font-family: monospace;
    color: var(--text-3-2-dark-gray);
    background: var(--bg-2-3-white);
    padding: 8px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.tool-reasoning {
  .tool-reasoning-content {
    pre {
      @include typography.subscript-a5;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: var(--text-3-1-dark);
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.03) 0%, rgba(139, 92, 246, 0.02) 100%);
      border-left: 2px solid rgba(99, 102, 241, 0.2);
      padding: 12px;
      border-radius: 4px;
      overflow-x: auto;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.7;
      font-size: 13px;
    }
  }
}

.tool-response {
  .tool-response-content {
    pre {
      @include typography.subscript-a5;
      font-family: monospace;
      color: var(--text-3-1-dark);
      background: var(--bg-2-3-white);
      padding: 8px;
      border-radius: 4px;
      overflow-x: auto;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
    }
  }
}
</style>
