import type { ChatMessageExtended } from '@/shared/types/store'

/**
 * Форматирует сообщение в markdown формат для копирования
 */
export function formatMessageToMarkdown(message: ChatMessageExtended): string {
  const lines: string[] = []

  // Заголовок сообщения
  if (message.role === 'user') {
    lines.push('## 👤 User\n')
  } else if (message.role === 'assistant') {
    lines.push('## 🤖 Assistant\n')
  } else {
    lines.push('## System\n')
  }

  // Основной контент
  if (message.content && message.content.length > 0) {
    message.content.forEach((content) => {
      // content может быть строкой или объектом ReasoningStep
      if (typeof content === 'string') {
        lines.push(content)
      } else if (content && typeof content === 'object') {
        // Если это объект (ReasoningStep), преобразуем в строку
        lines.push(JSON.stringify(content, null, 2))
      }
    })
  }

  // Agent Reasoning (если есть)
  if (message.agentReasoning) {
    lines.push('\n### 🧠 Reasoning\n')

    if (message.agentReasoning.reasoning) {
      lines.push('**Reasoning:**')
      lines.push(String(message.agentReasoning.reasoning))
      lines.push('')
    }

    if (message.agentReasoning.steps && Array.isArray(message.agentReasoning.steps)) {
      lines.push('**Steps:**\n')
      message.agentReasoning.steps.forEach((step: any, index: number) => {
        lines.push(`${index + 1}. **${step.action || step.title || 'Action'}**`)
        if (step.reasoning) {
          lines.push(`   - Reasoning: ${step.reasoning}`)
        }
        if (step.result || step.content) {
          lines.push(`   - Result: ${step.result || step.content}`)
        }
        lines.push('')
      })
    }
  }

  // Tool History (если есть)
  if (message.toolHistory && message.toolHistory.length > 0) {
    lines.push('\n### 🔧 Tool History\n')
    message.toolHistory.forEach((tool, index) => {
      lines.push(`#### Tool ${index + 1}: ${tool.tool_name || 'Unknown'}`)
      if (tool.tool_call_id) {
        lines.push(`- Call ID: \`${tool.tool_call_id}\``)
      }
      lines.push('- Content:')
      lines.push('```')
      lines.push(tool.content || '')
      lines.push('```')
      lines.push('')
    })
  }

  // Timestamp
  if (message.timestamp) {
    const date = new Date(message.timestamp)
    lines.push(`\n---`)
    lines.push(`*${date.toLocaleString()}*`)
  }

  return lines.join('\n')
}

/**
 * Копирует текст в буфер обмена
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    // Современный API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }

    // Fallback для старых браузеров
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()

    const successful = document.execCommand('copy')
    document.body.removeChild(textArea)

    return successful
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    return false
  }
}
