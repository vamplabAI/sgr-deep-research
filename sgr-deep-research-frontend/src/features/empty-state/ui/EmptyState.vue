<template>
  <div class="empty-state">
    <div class="empty-state__content">
      <h2 class="empty-state__title">Welcome to SGR Memory Agent</h2>
      <p class="empty-state__subtitle">Personal AI assistant with long-term memory</p>

      <div class="empty-state__suggestions">
        <h3 class="suggestions__title">Where to start?</h3>

        <div class="suggestions__grid">
          <button
            v-for="suggestion in suggestions"
            :key="suggestion.id"
            class="suggestion-card"
            @click="handleSuggestionClick(suggestion.prompt)"
          >
            <div class="suggestion-card__content">
              <h4 class="suggestion-card__title">{{ suggestion.title }}</h4>
              <p class="suggestion-card__description">{{ suggestion.description }}</p>
            </div>
          </button>
        </div>

        <div class="empty-state__footer">
          <div class="footer__agent-info">
            <h4 class="agent-info__title">SGR Memory Agent</h4>
            <p class="agent-info__description">
              AI assistant with long-term memory that remembers everything about you and uses this knowledge for more personalized assistance.
            </p>
            <div class="agent-info__capabilities">
              <span class="capability">Infinite memory</span>
              <span class="capability">Deep search</span>
              <span class="capability">Contextual understanding</span>
              <span class="capability">Personalization</span>
            </div>
          </div>
          <p class="footer__tip">
            <strong>Tip:</strong> The more you tell me, the better I can help
          </p>
        </div>

        <div class="suggestions__divider">
          <span class="divider__text">or</span>
        </div>

        <button class="new-chat-button" @click="handleNewChatClick">
          <span class="new-chat-button__text">Start from scratch</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  startChat: [prompt: string]
  newChat: []
}>()

interface Suggestion {
  id: string
  icon: string
  title: string
  description: string
  prompt: string
}

const suggestions = ref<Suggestion[]>([
  {
    id: 'about-me',
    icon: '',
    title: 'Tell me about yourself',
    description: 'Let\'s get acquainted! Tell me about yourself, your interests and goals',
    prompt: 'Hello! My name is [Your name]. I work as [position/field]. I\'m interested in [interests]. I want you to help me with [tasks].'
  },
  {
    id: 'research',
    icon: '',
    title: 'Find information',
    description: 'Deep search and analysis of information on the internet',
    prompt: 'Find and analyze the latest news and trends on the topic: [your topic]'
  },
  {
    id: 'productivity',
    icon: '',
    title: 'Increase productivity',
    description: 'Tips on time management, planning and efficiency',
    prompt: 'Help me create a plan for the day/week taking into account my goals and priorities'
  },
  {
    id: 'learning',
    icon: '',
    title: 'Learn something new',
    description: 'I\'ll create a learning plan and help you understand complex topics',
    prompt: 'I want to learn [topic/skill]. Create a learning plan with resources for me'
  },
  {
    id: 'brainstorm',
    icon: '',
    title: 'Generate ideas',
    description: 'Brainstorming for projects, business or creativity',
    prompt: 'Let\'s brainstorm on the topic: [your idea/project]'
  },
  {
    id: 'analyze',
    icon: '',
    title: 'Analysis and conclusions',
    description: 'I\'ll help analyze data and draw conclusions',
    prompt: 'Help me analyze [data/situation] and give recommendations'
  }
])

const handleSuggestionClick = (prompt: string) => {
  emit('startChat', prompt)
}

const handleNewChatClick = () => {
  emit('newChat')
}
</script>

<style scoped lang="scss">
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 40px 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #f8f9fa 100%);
  overflow-y: auto;
  overflow-x: hidden;
}

.empty-state__content {
  max-width: 1100px; // Increased for better card placement
  width: 100%;
  text-align: center;
}

.empty-state__title {
  margin: 0 0 12px;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1.2;
}

.empty-state__subtitle {
  margin: 0 0 48px;
  font-size: 18px;
  color: #4a4a4a;
  line-height: 1.5;
}

.empty-state__suggestions {
  margin-bottom: 40px;
}

.suggestions__title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.suggestions__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr); // 3 columns on desktop
  gap: 20px;
  margin-bottom: 32px;

  @media (max-width: 1024px) {
    grid-template-columns: repeat(2, 1fr); // 2 columns on tablets
  }
}

.suggestion-card {
  display: flex;
  align-items: flex-start;
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease;
  min-height: 100px;

  &:hover {
    background: #f9fafb;
    border-color: #2563eb;
  }

  &:active {
    background: #f3f4f6;
  }
}

.suggestion-card__content {
  flex: 1;
  min-width: 0;
}

.suggestion-card__title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.suggestion-card__description {
  margin: 8px 0 0 0;
  font-size: 14px;
  color: #666666;
  line-height: 1.5;
}

.suggestions__divider {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 32px 0 24px;
  position: relative;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(
      to right,
      transparent,
      #e5e7eb 20%,
      #e5e7eb 80%,
      transparent
    );
  }

  &::before {
    margin-right: 16px;
  }

  &::after {
    margin-left: 16px;
  }
}

.divider__text {
  font-size: 14px;
  color: #9ca3af;
  font-weight: 500;
  text-transform: lowercase;
}

.new-chat-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
  padding: 14px 28px;
  background: #2563eb;
  border: none;
  border-radius: 8px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease;

  &:hover {
    background: #1d4ed8;
  }

  &:active {
    background: #1e40af;
  }
}

.new-chat-button__text {
  user-select: none;
}

.empty-state__footer {
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.footer__agent-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.agent-info__title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-info__description {
  margin: 0;
  font-size: 14px;
  color: #666666;
  line-height: 1.6;
}

.agent-info__capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.capability {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  background: #f0f7ff;
  border: 1px solid #bfdbfe;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  color: #1e40af;
  white-space: nowrap;
}

.footer__tip {
  margin: 0;
  font-size: 14px;
  color: #4a4a4a;
  line-height: 1.6;

  strong {
    color: #2563eb;
    font-weight: 600;
  }
}

@media (max-width: 768px) {
  .empty-state {
    padding: 20px 16px;
    align-items: flex-start;
  }

  .empty-state__content {
    padding-bottom: 40px; // Extra space at bottom for scrolling
  }

  .empty-state__title {
    font-size: 24px;
    margin-bottom: 8px;
  }

  .empty-state__subtitle {
    font-size: 16px;
    margin-bottom: 32px;
  }

  .suggestions__title {
    font-size: 18px;
    margin-bottom: 16px;
  }

  .suggestions__grid {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 24px;
  }

  .suggestion-card {
    padding: 16px;
    min-height: 90px;
  }

  .suggestion-card__title {
    font-size: 14px;
  }

  .suggestion-card__description {
    font-size: 13px;
  }

  .suggestions__divider {
    margin: 24px 0 20px;
  }

  .new-chat-button {
    max-width: 100%;
    padding: 12px 24px;
    font-size: 14px;
  }

  .empty-state__footer {
    padding: 16px;
    gap: 16px;
  }

  .footer__agent-info {
    gap: 10px;
    padding-bottom: 16px;
  }

  .agent-info__title {
    font-size: 16px;
  }

  .agent-info__description {
    font-size: 13px;
  }

  .agent-info__capabilities {
    gap: 6px;
  }

  .capability {
    font-size: 12px;
    padding: 5px 10px;
  }

  .footer__tip {
    font-size: 13px;
  }
}

// Extra small screens (< 400px)
@media (max-width: 400px) {
  .empty-state {
    padding: 20px 12px;
  }

  .empty-state__title {
    font-size: 20px;
  }

  .empty-state__subtitle {
    font-size: 14px;
  }

  .suggestion-card {
    padding: 14px;
  }

  .suggestion-card__title {
    font-size: 13px;
  }

  .suggestion-card__description {
    font-size: 12px;
  }

  .new-chat-button {
    padding: 12px 20px;
    font-size: 14px;
  }

  .agent-info__title {
    font-size: 15px;
  }

  .agent-info__description {
    font-size: 12px;
  }

  .capability {
    font-size: 11px;
    padding: 4px 8px;
  }
}
</style>
