import { useState, useCallback, useEffect } from 'react'
import { apiClient } from '../services/api'
import type { ChatMessage, ChatRequest } from '../types/index'

const STORAGE_KEY_PREFIX = 'chat_history_'

export function useChat(kbId: string) {
  const storageKey = `${STORAGE_KEY_PREFIX}${kbId}`

  // Load initial messages from localStorage
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const stored = localStorage.getItem(storageKey)
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Save messages to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(messages))
    } catch (e) {
      console.error('Failed to save chat history:', e)
    }
  }, [messages, storageKey])

  const sendMessage = useCallback(
    async (
      question: string,
      topK = 5,
      temperature = 0.7,
      llmModel?: string,
      llmProvider?: string,
      useStructure = false
    ) => {
      if (!question.trim()) return

      const userMessage: ChatMessage = {
        role: 'user',
        content: question,
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, userMessage])
      setIsLoading(true)
      setError(null)

      try {
        // Prepare conversation history (last 10 messages, excluding current question)
        const history = messages.slice(-10).map(msg => ({
          role: msg.role,
          content: msg.content
        }))

        const request: ChatRequest = {
          question,
          knowledge_base_id: kbId,
          conversation_history: history.length > 0 ? history : undefined,
          top_k: topK,
          temperature,
          llm_model: llmModel,
          llm_provider: llmProvider,
          use_structure: useStructure,
        }

        const response = await apiClient.chat(request)

        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          timestamp: new Date().toISOString(),
        }

        setMessages((prev) => [...prev, assistantMessage])
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to send message'
        setError(errorMessage)

        // Add error message to chat
        const errorChatMessage: ChatMessage = {
          role: 'assistant',
          content: `Error: ${errorMessage}`,
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, errorChatMessage])
      } finally {
        setIsLoading(false)
      }
    },
    [kbId]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    try {
      localStorage.removeItem(storageKey)
    } catch (e) {
      console.error('Failed to clear chat history:', e)
    }
  }, [storageKey])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  }
}
