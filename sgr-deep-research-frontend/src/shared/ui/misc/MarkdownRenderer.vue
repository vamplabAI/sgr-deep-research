<template>
  <div class="markdown-renderer" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import 'highlight.js/styles/github-dark.css'

// Import commonly used languages
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import sql from 'highlight.js/lib/languages/sql'
import yaml from 'highlight.js/lib/languages/yaml'
import markdown from 'highlight.js/lib/languages/markdown'

// Register languages
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('css', css)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('markdown', markdown)

interface Props {
  content: string
}

const props = defineProps<Props>()

// Configure marked with syntax highlighting
marked.setOptions({
  breaks: true, // Convert \n to <br>
  gfm: true, // GitHub Flavored Markdown
})

// Use custom renderer for code blocks with syntax highlighting
marked.use({
  renderer: {
    code(token) {
      const code = token.text
      const lang = token.lang
      let highlighted = code
      if (lang && hljs.getLanguage(lang)) {
        try {
          highlighted = hljs.highlight(code, { language: lang }).value
        } catch (err) {
          console.error('Highlight error:', err)
        }
      } else {
        try {
          highlighted = hljs.highlightAuto(code).value
        } catch (err) {
          console.error('Auto-highlight error:', err)
        }
      }
      const langClass = lang ? ` class="language-${lang}"` : ''
      return `<pre><code${langClass}>${highlighted}</code></pre>`
    },
  },
})

const renderedHtml = computed(() => {
  try {
    return marked.parse(props.content)
  } catch (error) {
    console.error('Markdown parsing error:', error)
    return props.content
  }
})
</script>

<style scoped>
.markdown-renderer {
  line-height: 1.6;
  color: var(--color-text);
}

/* Headings */
.markdown-renderer :deep(h1),
.markdown-renderer :deep(h2),
.markdown-renderer :deep(h3),
.markdown-renderer :deep(h4),
.markdown-renderer :deep(h5),
.markdown-renderer :deep(h6) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-renderer :deep(h1) {
  font-size: 2em;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.3em;
}

.markdown-renderer :deep(h2) {
  font-size: 1.5em;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.3em;
}

.markdown-renderer :deep(h3) {
  font-size: 1.25em;
}

.markdown-renderer :deep(h4) {
  font-size: 1em;
}

.markdown-renderer :deep(h5) {
  font-size: 0.875em;
}

.markdown-renderer :deep(h6) {
  font-size: 0.85em;
  color: var(--color-text-secondary);
}

/* Paragraphs */
.markdown-renderer :deep(p) {
  margin-top: 0;
  margin-bottom: 16px;
}

/* Lists */
.markdown-renderer :deep(ul),
.markdown-renderer :deep(ol) {
  margin-top: 0;
  margin-bottom: 16px;
  padding-left: 2em;
}

.markdown-renderer :deep(li) {
  margin-bottom: 4px;
}

.markdown-renderer :deep(li > p) {
  margin-bottom: 8px;
}

/* Code blocks */
.markdown-renderer :deep(pre) {
  background-color: var(--color-background-soft);
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  margin-bottom: 16px;
  border: 1px solid var(--color-border);
}

.markdown-renderer :deep(code) {
  background-color: var(--color-background-soft);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
}

.markdown-renderer :deep(pre code) {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
}

/* Blockquotes */
.markdown-renderer :deep(blockquote) {
  margin: 0 0 16px 0;
  padding: 0 1em;
  color: var(--color-text-secondary);
  border-left: 4px solid var(--color-border);
}

.markdown-renderer :deep(blockquote > :first-child) {
  margin-top: 0;
}

.markdown-renderer :deep(blockquote > :last-child) {
  margin-bottom: 0;
}

/* Tables */
.markdown-renderer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 16px;
}

.markdown-renderer :deep(table th),
.markdown-renderer :deep(table td) {
  padding: 8px 12px;
  border: 1px solid var(--color-border);
}

.markdown-renderer :deep(table th) {
  background-color: var(--color-background-soft);
  font-weight: 600;
}

.markdown-renderer :deep(table tr:nth-child(even)) {
  background-color: var(--color-background-mute);
}

/* Links */
.markdown-renderer :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}

.markdown-renderer :deep(a:hover) {
  text-decoration: underline;
}

/* Horizontal rule */
.markdown-renderer :deep(hr) {
  height: 0;
  margin: 24px 0;
  border: 0;
  border-top: 1px solid var(--color-border);
}

/* Images */
.markdown-renderer :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}

/* Strong and emphasis */
.markdown-renderer :deep(strong) {
  font-weight: 600;
}

.markdown-renderer :deep(em) {
  font-style: italic;
}

/* Task lists */
.markdown-renderer :deep(input[type='checkbox']) {
  margin-right: 8px;
}
</style>
