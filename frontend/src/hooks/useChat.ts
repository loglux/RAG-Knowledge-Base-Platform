import { useState, useCallback, useEffect } from 'react'
import { apiClient } from '../services/api'
import type { ChatMessage, ChatRequest } from '../types/index'

const CONVERSATION_KEY_PREFIX = 'chat_conversation_'

export function useChat(kbId: string) {
  const conversationKey = `${CONVERSATION_KEY_PREFIX}${kbId}`

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [conversationId, setConversationId] = useState<string | null>(() => {
    try {
      return localStorage.getItem(conversationKey)
    } catch {
      return null
    }
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    const loadConversation = async () => {
      try {
        if (conversationId) {
          const history = await apiClient.getConversationMessages(conversationId)
          if (!isMounted) return
          setMessages(history.map(msg => ({
            role: msg.role,
            content: msg.content,
            sources: msg.sources,
            timestamp: msg.timestamp,
            model: msg.model,
          })))
          return
        }

        const conversations = await apiClient.listConversations(kbId)
        if (!isMounted) return
        if (conversations.length === 0) {
          setMessages([])
          return
        }

        const latest = conversations[0]
        setConversationId(latest.id)
        try {
          localStorage.setItem(conversationKey, latest.id)
        } catch (e) {
          console.error('Failed to persist conversation id:', e)
        }

        const history = await apiClient.getConversationMessages(latest.id)
        if (!isMounted) return
        setMessages(history.map(msg => ({
          role: msg.role,
          content: msg.content,
          sources: msg.sources,
          timestamp: msg.timestamp,
          model: msg.model,
        })))
      } catch (e) {
        console.error('Failed to load conversation history:', e)
        if (conversationId) {
          setConversationId(null)
          try {
            localStorage.removeItem(conversationKey)
          } catch (removeError) {
            console.error('Failed to clear conversation id:', removeError)
          }
        }
      }
    }

    if (kbId) {
      loadConversation()
    }

    return () => {
      isMounted = false
    }
  }, [kbId, conversationId, conversationKey])

  const sendMessage = useCallback(
    async (
      question: string,
      topK = 5,
      temperature = 0.7,
      retrievalMode: 'dense' | 'hybrid' = 'dense',
      lexicalTopK?: number,
      hybridDenseWeight?: number,
      hybridLexicalWeight?: number,
      maxContextChars?: number,
      scoreThreshold?: number,
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
        const request: ChatRequest = {
          question,
          knowledge_base_id: kbId,
          conversation_id: conversationId || undefined,
          top_k: topK,
          temperature,
          retrieval_mode: retrievalMode,
          lexical_top_k: lexicalTopK,
          hybrid_dense_weight: hybridDenseWeight,
          hybrid_lexical_weight: hybridLexicalWeight,
          max_context_chars: maxContextChars,
          score_threshold: scoreThreshold,
          llm_model: llmModel,
          llm_provider: llmProvider,
          use_structure: useStructure,
        }

        const response = await apiClient.chat(request)

        if (response.conversation_id && response.conversation_id !== conversationId) {
          setConversationId(response.conversation_id)
          try {
            localStorage.setItem(conversationKey, response.conversation_id)
          } catch (e) {
            console.error('Failed to persist conversation id:', e)
          }
        }

        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          timestamp: new Date().toISOString(),
          model: response.model,
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
    [kbId, conversationId, conversationKey]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    try {
      if (conversationId) {
        apiClient.deleteConversation(conversationId).catch((e) => {
          console.error('Failed to delete conversation:', e)
        })
      }
      localStorage.removeItem(conversationKey)
      setConversationId(null)
    } catch (e) {
      console.error('Failed to clear chat history:', e)
    }
  }, [conversationId, conversationKey])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    conversationId,
  }
}
