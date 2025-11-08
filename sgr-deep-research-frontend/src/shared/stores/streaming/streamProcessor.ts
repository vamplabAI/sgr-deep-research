/**
 * Stream Processor
 * Handles SSE streaming chunks and processes tool calls
 */

import type { ChatSession } from '@/shared/types/store'
import { isValidJson } from './contentParser'
import { addJsonToMessage } from './toolHandlers'

interface ToolCall {
  id: string
  name: string
  arguments: string
}

interface StreamChunk {
  model?: string
  choices?: Array<{
    delta?: {
      content?: string
      tool_calls?: Array<{
        index?: number
        id?: string
        function?: {
          name?: string
          arguments?: string
        }
      }>
    }
    finish_reason?: string
  }>
}

export class StreamProcessor {
  private toolCalls: Map<number, ToolCall> = new Map()
  private processedToolCallIds: Set<string> = new Set()
  private isProcessing: boolean = false
  private pendingChunks: Array<{
    session: ChatSession
    rawChunk: string
    agentId?: string
    onFinish?: () => void | Promise<void>
  }> = []

  /**
   * Reset processor state
   */
  reset(): void {
    this.toolCalls.clear()
    this.processedToolCallIds.clear()
    this.pendingChunks = []
    this.isProcessing = false
  }

  /**
   * Process raw SSE chunk (queued for sequential processing)
   */
  processRawChunk(
    session: ChatSession,
    rawChunk: string,
    agentId?: string,
    onFinish?: () => void | Promise<void>
  ): void {
    // Add to queue
    this.pendingChunks.push({ session, rawChunk, agentId, onFinish })

    // If already processing, return (will be processed from queue)
    if (this.isProcessing) {
      return
    }

    // Start processing queue (fire and forget - runs in background)
    void this.processQueue()
  }

  /**
   * Process queue sequentially
   */
  private async processQueue(): Promise<void> {
    console.log('📦 processQueue started, chunks:', this.pendingChunks.length)
    this.isProcessing = true

    while (this.pendingChunks.length > 0) {
      const { session, rawChunk, agentId, onFinish } = this.pendingChunks.shift()!
      console.log('📦 Processing chunk, hasOnFinish:', !!onFinish)
      const shouldStop = await this.processRawChunkInternal(session, rawChunk, agentId, onFinish)
      
      // If onFinish was called, stop processing queue and clear remaining chunks
      if (shouldStop) {
        console.log('🛑 Stopping queue processing after onFinish')
        this.pendingChunks = []
        break
      }
    }

    console.log('📦 processQueue finished')
    this.isProcessing = false
  }

  /**
   * Internal chunk processing logic
   * @returns true if onFinish was called (should stop processing queue)
   */
  private async processRawChunkInternal(
    session: ChatSession,
    rawChunk: string,
    agentId?: string,
    onFinish?: () => void | Promise<void>
  ): Promise<boolean> {
    const lines = rawChunk.split('\n')
    let shouldCallFinish = false
    let lastFinishReason: string | null = null

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue

      try {
        // Extract data segment
        const segment = trimmed.split('data: ')[1]
        if (!segment) continue

        // Check for end marker
        if (segment === '[DONE]') {
          console.log('✅ Stream finished with [DONE]')
          shouldCallFinish = true
          break
        }

        // Parse JSON chunk
        if (!isValidJson(segment)) {
          console.warn('⚠️ Invalid JSON segment:', segment.substring(0, 100))
          continue
        }

        const chunk: StreamChunk = JSON.parse(segment)

        // Process chunk
        const { shouldFinish, finishReason } = this.processChunk(session, chunk, agentId)

        // Mark for finish and STOP processing remaining lines immediately
        if (shouldFinish) {
          console.log('🏁 Finish reason detected:', finishReason)
          shouldCallFinish = true
          lastFinishReason = finishReason
          break // Stop processing lines immediately
        }
      } catch (e) {
        console.error('❌ Error processing line:', e)
      }
    }

    // Call onFinish after processing all lines
    if (shouldCallFinish && onFinish) {
      console.log('✅ Calling onFinish callback, reason:', lastFinishReason)
      await onFinish()
      return true // Signal to stop processing queue
    }
    
    return false // Continue processing queue
  }

  /**
   * Process parsed chunk
   */
  private processChunk(
    session: ChatSession,
    chunk: StreamChunk,
    agentId?: string
  ): { shouldFinish: boolean; finishReason: string | null } {
    const choice = chunk.choices?.[0]
    if (!choice) {
      return { shouldFinish: false, finishReason: null }
    }

    const delta = choice.delta
    const finishReason = choice.finish_reason

    // Extract agentId from chunk.model if not already set in session
    if (chunk.model && !session.agentId) {
      session.agentId = chunk.model
      console.log('🆔 Extracted agentId from stream:', chunk.model)
    }

    // Get last message
    const lastMessage = session.messages[session.messages.length - 1]
    if (!lastMessage) {
      return { shouldFinish: false, finishReason: null }
    }

    // Process tool calls
    if (delta?.tool_calls) {
      this.processToolCalls(delta, lastMessage)
    }

    // Process content
    if (delta?.content) {
      this.processContent(delta.content, lastMessage)
    }

    // Check finish reason
    if (finishReason) {
      // Finalize accumulated tool calls on any finish reason (tool_calls or stop)
      if (this.toolCalls.size > 0) {
        console.log(`🎯 Finalizing tool calls on finish_reason: ${finishReason}`)
        this.finalizeToolCalls(lastMessage)
      }
      
      // Only trigger stream finish on "stop" finish reason, not on "tool_calls"
      // This allows backend to send complete tool call data after finish_reason: "tool_calls"
      const shouldTriggerFinish = finishReason === 'stop'
      console.log(`🏁 Finish reason: ${finishReason}, shouldTriggerFinish: ${shouldTriggerFinish}`)
      return { shouldFinish: shouldTriggerFinish, finishReason }
    }

    return { shouldFinish: false, finishReason: null }
  }

  /**
   * Process tool calls from delta
   */
  private processToolCalls(delta: any, lastMessage: any): void {
    if (!delta?.tool_calls) return

    for (const toolCall of delta.tool_calls) {
      const index = toolCall.index ?? 0
      const toolName = toolCall.function?.name

      // Debug logging
      console.log(`🔍 Tool call chunk:`, {
        index,
        id: toolCall.id,
        name: toolName,
        argsLength: toolCall.function?.arguments?.length || 0,
        argsPreview: toolCall.function?.arguments?.substring(0, 50),
        currentAccumulated: this.toolCalls.get(index)?.arguments?.length || 0,
      })

      // Check if this is a duplicate (backend sends full JSON after streaming)
      if (toolCall.id && this.processedToolCallIds.has(toolCall.id)) {
        console.log('⏭️ Skipping duplicate tool_call with id:', toolCall.id)
        continue
      }

      // Initialize new tool call
      if (toolCall.id) {
        if (!toolName) continue

        // Check if this is a complete tool call from backend (ID like "1-action", "2-action")
        const isBackendComplete = toolCall.id && /^\d+-action$/.test(toolCall.id)
        
        // Skip backend complete tool calls - we already have them from streaming
        if (isBackendComplete) {
          console.log(`⏭️ Skipping backend complete tool call: ${toolName} (${toolCall.id})`)
          continue
        }

        // Check if we already have a finalized version of THIS SPECIFIC tool call (by ID)
        const alreadyFinalized = lastMessage.content.some(
          (item: any) =>
            !item?._streaming &&
            item?.tool_name_discriminator === toolName &&
            item?._tool_call_id === toolCall.id &&
            typeof item === 'object'
        )

        if (alreadyFinalized) {
          console.log(`⏭️ Skipping duplicate tool call (already finalized): ${toolName} (${toolCall.id})`)
          continue
        }

        // Check if we're already accumulating this tool at this index
        const existingToolCall = this.toolCalls.get(index)
        if (existingToolCall && existingToolCall.name === toolName) {
          // Already accumulating - skip duplicate
          console.log(`⏭️ Already accumulating ${toolName}, skipping duplicate init`)
          continue
        }

        console.log(`🔧 New tool call [${index}]:`, toolName, 'id:', toolCall.id)

        this.toolCalls.set(index, {
          id: toolCall.id,
          name: toolName,
          arguments: '',
        })

        // Add streaming indicator to message
        this.updateStreamingProgress(lastMessage, index, toolName, '', toolCall.id)
      }

      // Accumulate arguments (only if we have an active tool call)
      const args = toolCall.function?.arguments
      if (args) {
        if (!this.toolCalls.has(index)) {
          console.log(`⏭️ Skipping args for index ${index} - no active tool call (likely stale chunks)`)
          continue
        }

        const current = this.toolCalls.get(index)!

        // If toolName is provided, verify it matches the current tool call
        if (toolName && current.name !== toolName) {
          console.warn(`⚠️ Tool name mismatch at index ${index}: expected ${current.name}, got ${toolName}`)
          continue
        }

        // Check if this is a complete JSON (duplicate from backend)
        if (this.isCompleteJson(args) && current.arguments.length > 0) {
          console.log(`⏭️ Skipping complete JSON duplicate, already have ${current.arguments.length} chars`)
          continue
        }

        current.arguments += args
        console.log(`➕ Accumulating args [${index}] for ${current.name}:`, args.substring(0, 30))

        // Update streaming progress with accumulated args
        this.updateStreamingProgress(lastMessage, index, current.name, current.arguments, current.id)
      }
    }
  }

  /**
   * Process content delta
   */
  private processContent(content: string, lastMessage: any): void {
    if (!content) return

    // Skip content that looks like JSON object (backend sends tool calls as content)
    const trimmed = content.trim()
    // Check if it's a JSON object with typical tool call fields
    if (trimmed.startsWith('{') && (
      trimmed.includes('"reasoning"') || 
      trimmed.includes('"answer"') || 
      trimmed.includes('"completed_steps"')
    )) {
      console.log('⏭️ Skipping JSON tool call in content:', trimmed.substring(0, 50))
      return
    }

    // Find last string content or add new
    const lastContentItem = lastMessage.content[lastMessage.content.length - 1]
    if (typeof lastContentItem === 'string') {
      lastMessage.content[lastMessage.content.length - 1] = lastContentItem + content
    } else {
      lastMessage.content.push(content)
    }
  }

  /**
   * Check if string is complete JSON
   */
  private isCompleteJson(str: string): boolean {
    const trimmed = str.trim()
    return trimmed.startsWith('{') && trimmed.endsWith('}') && trimmed.length > 10
  }

  /**
   * Update streaming progress in message content
   */
  private updateStreamingProgress(
    message: any,
    index: number,
    toolName: string,
    accumulatedArgs: string,
    toolCallId: string
  ): void {
    // Create streaming placeholder object
    const streamingItem = {
      tool_name_discriminator: toolName,
      _streaming: true,
      _raw_content: accumulatedArgs || '...',
      _tool_call_id: toolCallId, // Store ID to identify specific tool call
    }

    // Find existing streaming placeholder for this specific tool call (by ID)
    const streamingIndex = message.content.findIndex(
      (item: any) =>
        item?._streaming &&
        item?.tool_name_discriminator === toolName &&
        item?._tool_call_id === toolCallId
    )

    if (streamingIndex >= 0) {
      // Update existing streaming item
      message.content[streamingIndex] = streamingItem
    } else {
      // Add new streaming item
      message.content.push(streamingItem)
    }
  }

  /**
   * Finalize tool calls - parse and add to message
   */
  private finalizeToolCalls(lastMessage: any): void {
    if (this.toolCalls.size === 0) return

    console.log('🏁 Finalizing', this.toolCalls.size, 'tool call(s)')

    for (const [index, toolCall] of this.toolCalls) {
      console.log(`📋 Finalizing tool [${index}]:`, toolCall.name)
      console.log(`📝 Arguments (${toolCall.arguments.length} chars)`)

      try {
        const json = JSON.parse(toolCall.arguments)
        json.tool_name_discriminator = toolCall.name

        console.log('🔍 Looking for streaming placeholder:', {
          toolName: toolCall.name,
          toolCallId: toolCall.id,
          contentLength: lastMessage.content.length,
          content: lastMessage.content.map((item: any, idx: number) => ({
            index: idx,
            isStreaming: item?._streaming,
            discriminator: item?.tool_name_discriminator,
            toolCallId: item?._tool_call_id,
          })),
        })

        // Find streaming placeholder by ID (each tool call has unique ID)
        const streamingIndex = lastMessage.content.findIndex(
          (item: any) =>
            item?._streaming &&
            item?.tool_name_discriminator === toolCall.name &&
            item?._tool_call_id === toolCall.id
        )

        console.log('🔍 Found streaming index:', streamingIndex)

        if (streamingIndex >= 0) {
          // Keep streaming block, add finalized JSON after it
          // Preserve tool call ID to prevent duplicates
          json._tool_call_id = toolCall.id
          lastMessage.content.splice(streamingIndex + 1, 0, json)
          console.log(`✅ Added finalized JSON after streaming block at index ${streamingIndex}`)
        } else {
          // No streaming placeholder, add to end (shouldn't happen but just in case)
          console.warn('⚠️ No streaming placeholder found, adding to end')
          addJsonToMessage(lastMessage, json, toolCall.name)
        }

        // Mark as processed to prevent duplicates
        this.processedToolCallIds.add(toolCall.id)
      } catch (e) {
        console.warn(`⚠️ Failed to parse JSON for ${toolCall.name} (likely incomplete):`, e)
        // Don't show error to user - just skip this tool call
      }
    }

    // Clear for next batch
    this.toolCalls.clear()
  }
}
