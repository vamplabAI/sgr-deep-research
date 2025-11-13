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
  private finishCalled: boolean = false
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
    this.finishCalled = false
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
      await this.processRawChunkInternal(session, rawChunk, agentId, onFinish)
    }

    console.log('📦 processQueue finished')
    this.isProcessing = false
  }

  /**
   * Internal chunk processing logic
   */
  private async processRawChunkInternal(
    session: ChatSession,
    rawChunk: string,
    agentId?: string,
    onFinish?: () => void | Promise<void>
  ): Promise<void> {
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

        // Mark for finish but DON'T stop processing remaining lines
        // (we need to process tool calls that come after finish_reason)
        if (shouldFinish) {
          console.log('🏁 Finish reason detected:', finishReason)
          shouldCallFinish = true
          lastFinishReason = finishReason
          // Don't break - continue processing remaining chunks
        }
      } catch (e) {
        console.error('❌ Error processing line:', e)
      }
    }

    // Call onFinish after processing all lines (only once per session)
    if (shouldCallFinish && onFinish && !this.finishCalled) {
      console.log('✅ Calling onFinish callback, reason:', lastFinishReason)
      this.finishCalled = true
      await onFinish()
    }
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

      // Trigger stream finish on both "stop" and "tool_calls" to update agent state
      const shouldTriggerFinish = finishReason === 'stop' || finishReason === 'tool_calls'
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
      const args = toolCall.function?.arguments

      console.log(`🔍 Tool call:`, {
        index,
        id: toolCall.id,
        name: toolName,
        argsLength: args?.length || 0,
      })

      if (!toolName) continue

      // Initialize tool call if needed, or replace if ID changed (new iteration)
      if (toolCall.id) {
        const existing = this.toolCalls.get(index)

        // If this is a new tool call (different ID at same index), replace the old one
        if (!existing || existing.id !== toolCall.id) {
          console.log(`🔧 ${existing ? 'Replacing' : 'New'} tool call [${index}]:`, toolName, 'id:', toolCall.id)

          // If replacing, finalize the old tool call first (if it has arguments)
          if (existing && existing.arguments && existing.arguments.trim() !== '') {
            console.log(`🔨 Finalizing old tool call before replacement: ${existing.name}`)
            try {
              const oldJson = JSON.parse(existing.arguments)
              oldJson.tool_name_discriminator = existing.name

              // Find and replace streaming placeholder with finalized JSON
              const oldPlaceholderIndex = lastMessage.content.findIndex(
                (item: any) =>
                  item?._streaming &&
                  item?.tool_name_discriminator === existing.name &&
                  item?._tool_call_id === existing.id
              )

              if (oldPlaceholderIndex !== -1) {
                oldJson._tool_call_id = existing.id
                lastMessage.content[oldPlaceholderIndex] = oldJson
                console.log(`✅ Finalized and replaced old tool call at index ${oldPlaceholderIndex}`)
              } else {
                // No streaming placeholder, add finalized JSON
                lastMessage.content.push(oldJson)
                console.log(`✅ Added finalized old tool call to end`)
              }

              // Mark as processed to prevent duplicate finalization
              this.processedToolCallIds.add(existing.id)
            } catch (e) {
              console.warn(`⚠️ Failed to finalize old tool call ${existing.name}:`, e)
              // Remove streaming placeholder anyway
              const oldPlaceholderIndex = lastMessage.content.findIndex(
                (item: any) =>
                  item?._streaming &&
                  item?.tool_name_discriminator === existing.name &&
                  item?._tool_call_id === existing.id
              )
              if (oldPlaceholderIndex !== -1) {
                lastMessage.content.splice(oldPlaceholderIndex, 1)
              }
            }
          } else if (existing) {
            // Old tool call has no arguments, just remove streaming placeholder
            const oldPlaceholderIndex = lastMessage.content.findIndex(
              (item: any) =>
                item?._streaming &&
                item?.tool_name_discriminator === existing.name &&
                item?._tool_call_id === existing.id
            )
            if (oldPlaceholderIndex !== -1) {
              console.log(`🗑️ Removing old streaming placeholder for ${existing.name} (id: ${existing.id})`)
              lastMessage.content.splice(oldPlaceholderIndex, 1)
            }
          }

          this.toolCalls.set(index, {
            id: toolCall.id,
            name: toolName,
            arguments: '',
          })
        }
      }

      // Accumulate arguments
      if (args && this.toolCalls.has(index)) {
        const current = this.toolCalls.get(index)!

        // Only accumulate if this is the same tool call (same ID)
        if (current.id === toolCall.id) {
          const wasEmpty = current.arguments === ''
          current.arguments += args
          console.log(`➕ Accumulating args [${index}] for ${current.name}: ${args.length} chars`)

          // Add streaming placeholder on first chunk of arguments
          if (wasEmpty) {
            this.updateStreamingProgress(lastMessage, index, current.name, current.arguments, current.id)
          } else {
            // Update existing streaming progress
            this.updateStreamingProgress(lastMessage, index, current.name, current.arguments, current.id)
          }
        }
      }
    }
  }

  /**
   * Process content delta
   */
  private processContent(content: string, lastMessage: any): void {
    if (!content) return

    console.log('📝 Processing content:', content.substring(0, 100))

    // Check if content looks like a complete JSON
    const trimmed = content.trim()
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      try {
        const json = JSON.parse(trimmed)

        // If we have any tool calls being accumulated, this JSON is likely a duplicate
        // (result of tool execution that returns the same JSON as tool arguments)
        if (this.toolCalls.size > 0) {
          console.log('⏭️ Skipping JSON from content - tool calls are being processed')
          return
        }

        // If it has tool_name_discriminator, add it as a tool object
        if (json.tool_name_discriminator) {
          console.log('🔧 Found JSON tool in content:', json.tool_name_discriminator)
          lastMessage.content.push(json)
          console.log('✅ Added JSON tool from content')
          return
        }

        // Otherwise, treat as regular JSON text
        console.log('📄 Found JSON without discriminator, treating as text')
      } catch (e) {
        // Not valid JSON, continue as text
      }
    }

    // Find last string content or add new
    const lastContentItem = lastMessage.content[lastMessage.content.length - 1]
    if (typeof lastContentItem === 'string') {
      lastMessage.content[lastMessage.content.length - 1] = lastContentItem + content
      console.log('✅ Appended to existing content, total length:', lastMessage.content[lastMessage.content.length - 1].length)
    } else {
      lastMessage.content.push(content)
      console.log('✅ Added new content item, total items:', lastMessage.content.length)
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
      // Skip if already processed (finalized during replacement)
      if (this.processedToolCallIds.has(toolCall.id)) {
        console.log(`⏭️ Skipping ${toolCall.name} (id: ${toolCall.id}) - already processed`)
        continue
      }

      console.log(`📋 Finalizing tool [${index}]:`, toolCall.name)
      console.log(`📝 Arguments (${toolCall.arguments.length} chars)`)

      // Skip if arguments are empty
      if (!toolCall.arguments || toolCall.arguments.trim() === '') {
        console.log(`⏭️ Skipping ${toolCall.name} - empty arguments`)

        // For clarificationtool, we still need to remove the streaming placeholder
        if (toolCall.name.toLowerCase() === 'clarificationtool') {
          console.log('🔍 Removing streaming placeholder for clarificationtool with empty args')
          const streamingIndex = lastMessage.content.findIndex(
            (item: any) =>
              item?._streaming &&
              item?.tool_name_discriminator === toolCall.name &&
              item?._tool_call_id === toolCall.id
          )
          if (streamingIndex >= 0) {
            lastMessage.content.splice(streamingIndex, 1)
            console.log(`✅ Removed streaming placeholder at index ${streamingIndex}`)
          }
        }
        continue
      }

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
          // Replace streaming placeholder with finalized JSON
          json._tool_call_id = toolCall.id
          lastMessage.content[streamingIndex] = json
          console.log(`✅ Replaced streaming placeholder at index ${streamingIndex} with finalized JSON`)
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
