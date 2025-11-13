<template>
  <div class="agent-reasoning-step__streaming">
    <div class="agent-reasoning-step__header">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">🔄 Streaming...</span>
        <span class="agent-reasoning-step__tool-name">{{ toolName?.toUpperCase() }}</span>
      </div>
    </div>
    <div class="agent-reasoning-step__content">
      <pre class="agent-reasoning-step__raw-content">{{ rawContent }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  toolName?: string
  rawContent: string
}

defineProps<Props>()
</script>
