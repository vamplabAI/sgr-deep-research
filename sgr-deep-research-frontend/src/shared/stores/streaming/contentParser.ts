/**
 * Content Parser
 * Handles parsing of streaming content (JSON, text, tool calls)
 */

import type { ParsedContent, ContentType } from './types'

/**
 * Check if string is valid JSON
 */
export function isValidJson(str: string): boolean {
  if (typeof str !== 'string' || str.trim().length === 0) {
    return false
  }
  try {
    const parsed = JSON.parse(str)
    return typeof parsed === 'object' && parsed !== null
  } catch {
    return false
  }
}

/**
 * Parse JSON string and add tool discriminator
 */
export function parseJsonWithTool(jsonString: string, toolName: string): any | null {
  try {
    const json = JSON.parse(jsonString)
    if (toolName) {
      json.tool_name_discriminator = toolName
    }
    return json
  } catch (e) {
    console.error('❌ Failed to parse JSON:', e)
    return null
  }
}

/**
 * Check if content should be ignored for specific tool
 */
export function shouldIgnoreContent(toolName: string): boolean {
  const toolsToIgnore = [
    'finalanswertool',
    'websearchtool',
    'extractpagecontenttool',
  ]
  return toolsToIgnore.includes(toolName)
}

/**
 * Determine content type
 */
export function getContentType(content: string, hasToolName: boolean): ContentType {
  if (!content || content.trim().length === 0) {
    return 'empty'
  }

  if (hasToolName) {
    return isValidJson(content) ? 'json' : 'tool_call'
  }

  return 'text'
}

/**
 * Parse content chunk
 */
export function parseContent(
  content: string,
  toolName: string,
  isFinishing: boolean
): ParsedContent {
  const contentType = getContentType(content, !!toolName)

  switch (contentType) {
    case 'json':
      return {
        type: 'json',
        toolName,
        data: parseJsonWithTool(content, toolName),
        isComplete: true,
      }

    case 'tool_call':
      return {
        type: 'tool_call',
        toolName,
        data: content,
        isComplete: isFinishing,
      }

    case 'text':
      return {
        type: 'text',
        data: content,
        isComplete: false,
      }

    case 'empty':
    default:
      return {
        type: 'empty',
        data: null,
        isComplete: isFinishing,
      }
  }
}
