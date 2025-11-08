/**
 * Streaming-related types and interfaces
 */

export interface StreamChunk {
  id: string
  model?: string
  choices?: Array<{
    delta?: {
      role?: string
      content?: string | null
      tool_calls?: Array<{
        index: number
        id?: string
        type?: string
        function?: {
          name?: string
          arguments?: string
        }
      }>
    }
    finish_reason?: string | null
    index: number
  }>
  created?: number
  object?: string
}

export interface ToolCallData {
  toolName: string
  arguments: string
  isComplete: boolean
}

export interface ContentParserState {
  currentToolName: string
  accumulatedContent: string
  lastParsedJson: any | null
}

export type ContentType = 'tool_call' | 'text' | 'json' | 'empty'

export interface ParsedContent {
  type: ContentType
  toolName?: string
  data: any
  isComplete: boolean
}
