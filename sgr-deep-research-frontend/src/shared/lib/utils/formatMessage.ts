import type { ChatMessageExtended } from '@/shared/types/store'

/**
 * Formats message to markdown format for copying
 */
export function formatMessageToMarkdown(message: ChatMessageExtended): string {
  const lines: string[] = []

  // Message header
  if (message.role === 'user') {
    lines.push('## 👤 User\n')
  } else if (message.role === 'assistant') {
    lines.push('## 🤖 Assistant\n')
  } else {
    lines.push('## System\n')
  }

  // Main content
  if (message.content && message.content.length > 0) {
    message.content.forEach((content) => {
      // content can be a string or ReasoningStep object
      if (typeof content === 'string') {
        lines.push(content)
      } else if (content && typeof content === 'object') {
        // If it's an object (ReasoningStep), convert to string
        lines.push(JSON.stringify(content, null, 2))
      }
    })
  }

  // Agent Reasoning (if present)
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

  // Tool History (if present)
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
 * Copies text to clipboard
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    // Modern API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }

    // Fallback for older browsers
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
