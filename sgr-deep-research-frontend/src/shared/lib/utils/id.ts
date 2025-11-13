/**
 * Generates a unique ID using timestamp and random string
 * @param prefix - Optional prefix for the ID
 * @returns Unique ID string
 */
export function generateUniqueId(prefix: string = ''): string {
  const timestamp = Date.now()
  const randomString = Math.random().toString(36).substr(2, 9)
  return prefix ? `${prefix}_${timestamp}_${randomString}` : `${timestamp}_${randomString}`
}

/**
 * Generates a unique chat session ID
 * @returns Unique chat session ID
 */
export function generateChatSessionId(): string {
  return generateUniqueId('chat')
}

/**
 * Generates a unique message ID
 * @returns Unique message ID
 */
export function generateMessageId(): string {
  return generateUniqueId('msg')
}
