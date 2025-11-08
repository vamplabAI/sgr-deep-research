/**
 * Tool Handlers
 * Manages tool-specific content handling
 */

import type { ChatMessageExtended } from '@/shared/types/store'
import { isValidJson, parseJsonWithTool } from './contentParser'

/**
 * Check if JSON already exists in message content
 */
export function isDuplicateJson(
  message: ChatMessageExtended,
  json: any,
  toolName: string
): boolean {
  return message.content.some((item: any) => {
    return (
      typeof item === 'object' &&
      item !== null &&
      item.tool_name_discriminator === toolName &&
      JSON.stringify(item) === JSON.stringify(json)
    )
  })
}

/**
 * Add JSON object to message content
 */
export function addJsonToMessage(
  message: ChatMessageExtended,
  json: any,
  toolName: string
): boolean {
  // Add discriminator
  if (toolName) {
    json.tool_name_discriminator = toolName
  }

  // Check for duplicates
  if (isDuplicateJson(message, json, toolName)) {
    console.log('⏭️ Skipping duplicate JSON for tool:', toolName)
    return false
  }

  // Get last content item
  const lastIndex = message.content.length - 1
  const lastContent = message.content[lastIndex]

  // Replace empty string or add new item
  if (lastContent === '' || lastContent === undefined) {
    message.content[lastIndex] = json
  } else {
    message.content.push(json)
  }

  // Add empty string for next content
  message.content.push('')

  console.log('✅ Added JSON for tool:', toolName)
  return true
}

/**
 * Append text chunk to message content
 */
export function appendTextToMessage(
  message: ChatMessageExtended,
  text: string
): void {
  const lastIndex = message.content.length - 1
  const lastContent = message.content[lastIndex]

  // Ensure we have a string to append to
  if (typeof lastContent === 'string') {
    message.content[lastIndex] = lastContent + text
  } else {
    message.content.push(text)
  }
}

/**
 * Parse accumulated content as JSON
 */
export function parseAccumulatedContent(
  message: ChatMessageExtended,
  toolName: string
): boolean {
  const lastIndex = message.content.length - 1
  const lastContent = message.content[lastIndex]

  // Only parse if last content is a non-empty string
  if (typeof lastContent !== 'string' || lastContent.trim().length === 0) {
    return false
  }

  // Try to parse as JSON
  if (!isValidJson(lastContent)) {
    console.warn('⚠️ Content is not valid JSON, keeping as text')
    return false
  }

  const json = parseJsonWithTool(lastContent, toolName)
  if (!json) {
    return false
  }

  // Check for duplicates
  if (isDuplicateJson(message, json, toolName)) {
    console.log('⏭️ Skipping duplicate parsed JSON for tool:', toolName)
    // Remove the accumulated string since it's a duplicate
    message.content[lastIndex] = ''
    return false
  }

  // Replace string with parsed JSON
  message.content[lastIndex] = json
  message.content.push('')

  console.log('✅ Parsed accumulated content for tool:', toolName)
  return true
}
