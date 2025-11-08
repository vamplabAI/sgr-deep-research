import axios, { AxiosError } from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import { API_CONFIG } from './config'
import type { ApiError } from './types'

// Create axios instance with default configuration
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_CONFIG.BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // Request interceptor
  client.interceptors.request.use(
    (config) => {
      // Log request in development
      if (import.meta.env.DEV) {
        console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data)
      }

      return config
    },
    (error) => {
      console.error('Request interceptor error:', error)
      return Promise.reject(error)
    },
  )

  // Response interceptor
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      // Log response in development
      if (import.meta.env.DEV) {
        // console.log(`✅ API Response: ${response.status} ${response.config.url}`, response.data)
      }
      return response
    },
    (error: AxiosError) => {
      // Log error in development
      if (import.meta.env.DEV) {
        console.error(
          `❌ API Error: ${error.response?.status} ${error.config?.url}`,
          error.response?.data,
        )
      }

      // Handle different error types
      const apiError: ApiError = {
        message: error.message || 'An unexpected error occurred',
        status: error.response?.status,
      }

      // Handle validation errors
      if (error.response?.status === 422 && error.response.data) {
        const validationData = error.response.data as Record<string, unknown>
        if (validationData.detail) {
          apiError.details = validationData.detail as ApiError['details']
        }
      }

      // Handle authentication errors
      if (error.response?.status === 401) {
        console.warn('Authentication failed')
      }

      return Promise.reject(apiError)
    },
  )

  return client
}

// Export the configured axios instance
export const apiClient = createApiClient()

// Utility function for retrying requests
export const retryRequest = async <T>(
  requestFn: () => Promise<T>,
  attempts: number = API_CONFIG.RETRY_ATTEMPTS,
  delay: number = API_CONFIG.RETRY_DELAY,
): Promise<T> => {
  try {
    return await requestFn()
  } catch (error) {
    if (attempts > 1) {
      await new Promise((resolve) => setTimeout(resolve, delay))
      return retryRequest(requestFn, attempts - 1, delay * 2)
    }
    throw error
  }
}
