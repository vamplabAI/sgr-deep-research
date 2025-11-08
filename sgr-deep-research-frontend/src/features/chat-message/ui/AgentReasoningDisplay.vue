<template>
  <div class="agent-reasoning-display">
    <!-- Reasoning Steps -->
    <div v-if="reasoning.reasoning_steps?.length" class="reasoning-section">
      <div class="reasoning-header" @click="toggleSection('reasoning_steps')">
        <span class="reasoning-title">Reasoning Steps</span>
        <span class="reasoning-toggle">{{ isExpanded.reasoning_steps ? '−' : '+' }}</span>
      </div>
      <div v-if="isExpanded.reasoning_steps" class="reasoning-content">
        <ul class="reasoning-list">
          <li
            v-for="(step, index) in reasoning.reasoning_steps"
            :key="index"
            class="reasoning-item"
          >
            {{ step }}
          </li>
        </ul>
      </div>
    </div>

    <!-- Current Situation -->
    <div v-if="reasoning.current_situation" class="reasoning-section">
      <div class="reasoning-header" @click="toggleSection('current_situation')">
        <span class="reasoning-title">Current Situation</span>
        <span class="reasoning-toggle">{{ isExpanded.current_situation ? '−' : '+' }}</span>
      </div>
      <div v-if="isExpanded.current_situation" class="reasoning-content">
        <p class="reasoning-text">{{ reasoning.current_situation }}</p>
      </div>
    </div>

    <!-- Plan Status -->
    <div v-if="reasoning.plan_status" class="reasoning-section">
      <div class="reasoning-header" @click="toggleSection('plan_status')">
        <span class="reasoning-title">Plan Status</span>
        <span class="reasoning-toggle">{{ isExpanded.plan_status ? '−' : '+' }}</span>
      </div>
      <div v-if="isExpanded.plan_status" class="reasoning-content">
        <p class="reasoning-text">{{ reasoning.plan_status }}</p>
      </div>
    </div>

    <!-- Remaining Steps -->
    <div v-if="reasoning.remaining_steps?.length" class="reasoning-section">
      <div class="reasoning-header" @click="toggleSection('remaining_steps')">
        <span class="reasoning-title">Remaining Steps</span>
        <span class="reasoning-toggle">{{ isExpanded.remaining_steps ? '−' : '+' }}</span>
      </div>
      <div v-if="isExpanded.remaining_steps" class="reasoning-content">
        <ul class="reasoning-list">
          <li
            v-for="(step, index) in reasoning.remaining_steps"
            :key="index"
            class="reasoning-item"
          >
            {{ step }}
          </li>
        </ul>
      </div>
    </div>

    <!-- Task Status -->
    <div class="reasoning-section">
      <div class="reasoning-header" @click="toggleSection('task_status')">
        <span class="reasoning-title">Task Status</span>
        <span class="reasoning-toggle">{{ isExpanded.task_status ? '−' : '+' }}</span>
      </div>
      <div v-if="isExpanded.task_status" class="reasoning-content">
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">Task Completed:</span>
            <span
              :class="[
                'status-value',
                reasoning.task_completed ? 'status-completed' : 'status-pending',
              ]"
            >
              {{ reasoning.task_completed ? 'Yes' : 'No' }}
            </span>
          </div>
          <div class="status-item">
            <span class="status-label">Enough Data:</span>
            <span
              :class="[
                'status-value',
                reasoning.enough_data ? 'status-completed' : 'status-pending',
              ]"
            >
              {{ reasoning.enough_data ? 'Yes' : 'No' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

interface Props {
  reasoning: Record<string, any>
}

const props = defineProps<Props>()

// Track which sections are expanded
const isExpanded = reactive({
  reasoning_steps: true,
  current_situation: true,
  plan_status: true,
  remaining_steps: true,
  task_status: false,
})

const toggleSection = (section: keyof typeof isExpanded) => {
  isExpanded[section] = !isExpanded[section]
}
</script>

<style scoped lang="scss">
.agent-reasoning-display {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reasoning-section {
  border: 1px solid var(--divider-6-1-white);
  border-radius: 8px;
  overflow: hidden;
}

.reasoning-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background-color: var(--bg-2-4-gray-1);
  cursor: pointer;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: var(--bg-2-5-gray-2);
  }
}

.reasoning-title {
  font-weight: 600;
  color: var(--text-3-1-dark);
  font-size: 14px;
}

.reasoning-toggle {
  font-weight: bold;
  color: var(--text-3-2-dark-gray);
  font-size: 16px;
  user-select: none;
}

.reasoning-content {
  padding: 16px;
  background-color: var(--bg-2-3-white);
}

.reasoning-text {
  margin: 0;
  color: var(--text-3-1-dark);
  line-height: 1.5;
  font-size: 14px;
}

.reasoning-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.reasoning-item {
  padding: 8px 0;
  color: var(--text-3-1-dark);
  line-height: 1.5;
  font-size: 14px;
  border-bottom: 1px solid var(--divider-6-1-white);

  &:last-child {
    border-bottom: none;
  }

  &:before {
    content: '•';
    color: var(--core-1-1-core);
    font-weight: bold;
    margin-right: 8px;
  }
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-label {
  font-weight: 500;
  color: var(--text-3-2-dark-gray);
  font-size: 14px;
}

.status-value {
  font-weight: 600;
  font-size: 14px;
  padding: 2px 8px;
  border-radius: 4px;

  &.status-completed {
    background-color: var(--system-7-1-success);
    color: var(--text-3-1-dark);
  }

  &.status-pending {
    background-color: var(--system-7-3-attention);
    color: var(--text-3-1-dark);
  }
}
</style>
