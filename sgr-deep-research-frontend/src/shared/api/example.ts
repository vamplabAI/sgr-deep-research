// Example usage of the API service
import { apiServices } from './services'
import type { ChatMessage } from './types'

// Example: Check API health
export const checkApiHealth = async () => {
  try {
    const health = await apiServices.health.checkHealth()
    console.log('API Health:', health)
    return health
  } catch (error) {
    console.error('Health check failed:', error)
    throw error
  }
}

// Example: Get agents list
export const getAgents = async () => {
  try {
    const agents = await apiServices.agents.getAgentsList()
    console.log('Agents:', agents)
    return agents
  } catch (error) {
    console.error('Failed to get agents:', error)
    throw error
  }
}

// Example: Get specific agent state
export const getAgentState = async (agentId: string) => {
  try {
    const state = await apiServices.agents.getAgentState(agentId)
    console.log('Agent State:', state)
    return state
  } catch (error) {
    console.error('Failed to get agent state:', error)
    throw error
  }
}

// Example: Create chat completion
export const createChatCompletion = async (messages: ChatMessage[]) => {
  try {
    const completion = apiServices.chat.createCompletion({
      messages: messages.map((msg) => ({
        role: 'user' as const,
        content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
      })),
      model: 'sgr_agent',
      stream: false,
    })
    console.log('Chat Completion:', completion)
    return completion
  } catch (error) {
    console.error('Chat completion failed:', error)
    throw error
  }
}

// Example: Streaming chat completion
export const createStreamingChat = async (messages: ChatMessage[]) => {
  try {
    await apiServices.chat.createStreamingCompletion(
      {
        messages: messages.map((msg) => ({
          role: 'user' as const,
          content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
        })),
        model: 'sgr_agent',
        stream: true,
      },
      (chunk: any) => {
        // Handle each chunk of the response
        console.log('Received chunk:', chunk)
      },
    )
  } catch (error) {
    console.error('Streaming chat failed:', error)
    throw error
  }
}
