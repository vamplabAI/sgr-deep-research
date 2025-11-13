<template>
  <!-- Check if this is extracted page content (should be collapsible) -->
  <div v-if="isExtractedPageContent" class="agent-reasoning-step">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">Extracted Page Content:</span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24
          :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }"
        />
      </div>
    </div>
    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <div class="agent-reasoning-step__string-content">
        <MarkdownRenderer :content="content" />
      </div>
    </div>
  </div>
  <!-- Check if this is search results (should be collapsible) -->
  <div v-else-if="isSearchResults" class="agent-reasoning-step">
    <div class="agent-reasoning-step__header" @click="toggleCollapsed">
      <div class="agent-reasoning-step__title">
        <span class="agent-reasoning-step__reasoning">Search Results:</span>
      </div>
      <div class="agent-reasoning-step__toggle">
        <AppIconChevronDown24
          :class="{ 'agent-reasoning-step__chevron--rotated': !isCollapsed }"
        />
      </div>
    </div>
    <div v-if="!isCollapsed" class="agent-reasoning-step__content">
      <div class="agent-reasoning-step__string-content">
        <MarkdownRenderer :content="content" />
      </div>
    </div>
  </div>
  <!-- Regular string content -->
  <div v-else class="agent-reasoning-step__string-content">
    <MarkdownRenderer :content="content" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIconChevronDown24 from '@/shared/ui/icons/AppIconChevronDown24.vue'
import { MarkdownRenderer } from '@/shared/ui'

interface Props {
  content: string
}

const props = defineProps<Props>()

const isCollapsed = ref(true)

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value
}

const isExtractedPageContent = computed(() => {
  return props.content.includes('Extracted Page Content:')
})

const isSearchResults = computed(() => {
  return props.content.includes('Search Query:') && props.content.includes('Search Results')
})

const formattedContent = computed(() => {
  return formatTextWithLinks(props.content)
})

/**
 * Convert URLs and Markdown links in text to clickable links
 */
const formatTextWithLinks = (text: string): string => {
  if (!text) return ''

  const processedLinks: string[] = []
  const PLACEHOLDER_PREFIX = '___LINK_PLACEHOLDER_'

  let result = text

  // 1. Process markdown links: [text](url)
  result = result.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, linkText, url) => {
    const trimmedUrl = url.trim()
    const href = trimmedUrl.startsWith('www.') ? `https://${trimmedUrl}` : trimmedUrl
    const linkHtml = `<a href="${href}" target="_blank" rel="noopener noreferrer" class="message-link">${linkText}</a>`
    const placeholder = `${PLACEHOLDER_PREFIX}${processedLinks.length}___`
    processedLinks.push(linkHtml)
    return placeholder
  })

  // 2. Process regular URLs (https:// or http://)
  result = result.replace(
    /(?<!href=["'])(https?:\/\/[^\s<>"{}|\\^`\[\]]+)/gi,
    (match) => {
      const linkHtml = `<a href="${match}" target="_blank" rel="noopener noreferrer" class="message-link">${match}</a>`
      const placeholder = `${PLACEHOLDER_PREFIX}${processedLinks.length}___`
      processedLinks.push(linkHtml)
      return placeholder
    }
  )

  // 3. Restore all placeholders
  processedLinks.forEach((linkHtml, index) => {
    const placeholder = `${PLACEHOLDER_PREFIX}${index}___`
    result = result.replace(placeholder, linkHtml)
  })

  return result
}
</script>
