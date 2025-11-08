import axios, { type AxiosInstance } from 'axios'
import { TRANSCRIPTION_API_CONFIG, TRANSCRIPTION_ENDPOINTS } from './config'
import type {
  TranscriptionUploadResponse,
  TranscriptionStatusResponse,
  TranscriptionResultResponse,
} from './types'

/**
 * Create a separate axios instance for transcription API
 * (different base URL and auth)
 */
const createTranscriptionClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: TRANSCRIPTION_API_CONFIG.BASE_URL,
    headers: {
      'Authorization': `Bearer ${TRANSCRIPTION_API_CONFIG.BEARER_TOKEN}`,
      'accept': 'application/json',
    },
  })

  // Request interceptor for logging
  client.interceptors.request.use(
    (config) => {
      if (import.meta.env.DEV) {
        console.log(`🎤 Transcription API Request: ${config.method?.toUpperCase()} ${config.url}`)
      }
      return config
    },
    (error) => {
      console.error('Transcription request error:', error)
      return Promise.reject(error)
    },
  )

  // Response interceptor for logging
  client.interceptors.response.use(
    (response) => {
      if (import.meta.env.DEV) {
        console.log(`✅ Transcription API Response: ${response.config.url}`, response.data)
      }
      return response
    },
    (error) => {
      console.error('❌ Transcription API Error:', error.response?.data || error.message)
      return Promise.reject(error)
    },
  )

  return client
}

const transcriptionClient = createTranscriptionClient()

/**
 * Transcription Service
 * Handles audio file upload, status polling, and result retrieval
 */
export const transcriptionService = {
  /**
   * Upload audio file for transcription
   * @param audioBlob - Audio file as Blob
   * @param filename - Optional filename (defaults to 'recording.webm')
   * @returns Upload response with task_id
   */
  uploadAudio: async (
    audioBlob: Blob,
    filename: string = 'recording.webm',
  ): Promise<TranscriptionUploadResponse> => {
    const formData = new FormData()
    formData.append('file', audioBlob, filename)

    const response = await transcriptionClient.post<TranscriptionUploadResponse>(
      TRANSCRIPTION_ENDPOINTS.UPLOAD,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        params: {
          model: TRANSCRIPTION_API_CONFIG.MODEL,
          diarize: false,
        },
      },
    )

    return response.data
  },

  /**
   * Check transcription status
   * @param taskId - Task ID from upload response
   * @returns Status response
   */
  checkStatus: async (taskId: string): Promise<TranscriptionStatusResponse> => {
    const response = await transcriptionClient.get<TranscriptionStatusResponse>(
      TRANSCRIPTION_ENDPOINTS.STATUS(taskId),
    )

    return response.data
  },

  /**
   * Get transcription result
   * @param taskId - Task ID from upload response
   * @returns Full transcription result with segments
   */
  getResult: async (taskId: string): Promise<TranscriptionResultResponse> => {
    const response = await transcriptionClient.get<TranscriptionResultResponse>(
      TRANSCRIPTION_ENDPOINTS.RESULT(taskId),
    )

    return response.data
  },

  /**
   * Poll transcription status until completed or failed
   * @param taskId - Task ID from upload response
   * @param onProgress - Optional callback for progress updates
   * @returns Final status response
   */
  pollStatus: async (
    taskId: string,
    onProgress?: (status: TranscriptionStatusResponse) => void,
  ): Promise<TranscriptionStatusResponse> => {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await transcriptionService.checkStatus(taskId)

          // Call progress callback if provided
          if (onProgress) {
            onProgress(status)
          }

          // Check if completed or failed
          if (status.status === 'completed') {
            resolve(status)
            return
          }

          if (status.status === 'failed') {
            reject(new Error(status.error || 'Transcription failed'))
            return
          }

          // Continue polling
          setTimeout(poll, TRANSCRIPTION_API_CONFIG.POLL_INTERVAL)
        } catch (error) {
          reject(error)
        }
      }

      // Start polling
      poll()
    })
  },

  /**
   * Upload audio and wait for transcription to complete
   * @param audioBlob - Audio file as Blob
   * @param filename - Optional filename
   * @param onProgress - Optional callback for progress updates
   * @returns Transcription result with text
   */
  transcribeAudio: async (
    audioBlob: Blob,
    filename?: string,
    onProgress?: (status: TranscriptionStatusResponse) => void,
  ): Promise<string> => {
    // 1. Upload audio
    const uploadResponse = await transcriptionService.uploadAudio(audioBlob, filename)
    const taskId = uploadResponse.task_id

    // 2. Poll until completed
    await transcriptionService.pollStatus(taskId, onProgress)

    // 3. Get result
    const result = await transcriptionService.getResult(taskId)

    // 4. Extract plain text from segments
    const plainText = result.segments.map((segment) => segment.text.trim()).join(' ')

    return plainText
  },

  /**
   * Extract plain text from transcription segments
   * @param segments - Array of transcription segments
   * @returns Plain text
   */
  extractPlainText: (segments: TranscriptionResultResponse['segments']): string => {
    return segments.map((segment) => segment.text.trim()).join(' ')
  },
}
