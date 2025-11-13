/**
 * History Loader
 * Handles loading and formatting chat history from API
 */

import type { ChatMessageExtended } from '@/shared/types/store'
import { apiServices } from '@/shared/api/services'

/**
 * Format reasoning content
 */
function formatReasoningContent(content: string): string {
  try {
    const data = JSON.parse(content)
    const steps = data.reasoning_steps || []

    if (steps.length > 0) {
      return steps.map((step: string) => `• ${step}`).join('\n')
    }

    return content
  } catch {
    return content
  }
}

/**
 * Load chat history from API
 */
export async function loadChatHistory(agentId: string): Promise<ChatMessageExtended[]> {
  const historyResponse = await apiServices.chatHistory.getChatHistory(agentId, 1, 50)

  console.log('📥 Loading chat history:', {
    chat_id: historyResponse.chat_id,
    agent_id: historyResponse.agent_id,
    turns: historyResponse.turns?.length || 0,
  })

  const messages: ChatMessageExtended[] = []

  if (!historyResponse.turns || historyResponse.turns.length === 0) {
    console.log('⚠️ No turns found in chat history')
    return messages
  }

  // Process each turn
  for (const turn of historyResponse.turns) {
    console.log('\n👤 Processing user message:', turn.user_message.content?.substring(0, 50))

    // Add user message
    messages.push({
      id: turn.user_message.id,
      role: 'user',
      content: [turn.user_message.content || ''],
      timestamp: new Date(turn.user_message.created_at),
    })

    // Process iterations
    const toolHistory: Array<{
      id: string
      role: string
      content: string | null
      tool_name?: string
      tool_call_id?: string
      iteration?: number
    }> = []

    let finalResponse = ''
    let finalResponseTimestamp = new Date()
    let finalResponseId = ''

    if (!turn.iterations || turn.iterations.length === 0) {
      console.log('  ⚠️ No iterations found')
      continue
    }

    for (const iteration of turn.iterations) {
      console.log(`  🔄 Iteration ${iteration.iteration}`)

      // Add reasoning
      if (iteration.reasoning_result?.content) {
        const formattedReasoning = formatReasoningContent(iteration.reasoning_result.content)

        toolHistory.push({
          id: iteration.reasoning_result.id,
          role: 'assistant',
          content: formattedReasoning,
          tool_name: 'reasoningtool',
          tool_call_id: iteration.reasoning_result.tool_call_id,
          iteration: iteration.iteration,
        })

        console.log('    🧠 Reasoning added to history')
      }

      // Check for final response
      if (iteration.action_result.tool_name === 'responsetool') {
        try {
          const parsed = JSON.parse(iteration.action_result.content || '{}')
          finalResponse = parsed.response || iteration.action_result.content || ''
        } catch {
          finalResponse = iteration.action_result.content || ''
        }
        finalResponseTimestamp = new Date(iteration.action_result.created_at)
        finalResponseId = iteration.action_result.id
        console.log(`    ✅ Final response found: ${finalResponse.substring(0, 100)}`)
      } else {
        // Tool call
        const toolName = iteration.action_result.tool_name || 'unknown'
        console.log(`    🔧 Tool: ${toolName}`)

        toolHistory.push({
          id: iteration.action_result.id,
          role: 'tool',
          content: iteration.action_result.content,
          tool_name: toolName,
          tool_call_id: iteration.action_result.tool_call_id,
          iteration: iteration.iteration,
        })
      }
    }

    // Add assistant message
    if (finalResponse) {
      console.log(`🤖 Adding assistant message with ${toolHistory.length} tool calls`)
      messages.push({
        id: finalResponseId,
        role: 'assistant',
        content: [finalResponse],
        timestamp: finalResponseTimestamp,
        toolHistory: toolHistory.length > 0 ? toolHistory : undefined,
      })
    }
  }

  console.log(`✅ Loaded ${messages.length} messages from ${historyResponse.turns.length} turns`)
  return messages
}

/**
 * Load chat details
 */
export async function loadChatDetails(agentId: string): Promise<{
  title: string
  createdAt: Date
}> {
  const chatDetail = await apiServices.chatHistory.getChatDetail(agentId)

  return {
    title: chatDetail.initial_task,
    createdAt: new Date(chatDetail.created_at || Date.now()),
  }
}
