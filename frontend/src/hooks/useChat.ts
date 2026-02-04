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
            id: msg.id,
            role: msg.role,
            content: msg.content,
            sources: msg.sources,
            timestamp: msg.timestamp,
            message_index: msg.message_index,
            model: msg.model,
            use_self_check: msg.use_self_check,
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
          id: msg.id,
          role: msg.role,
          content: msg.content,
          sources: msg.sources,
          timestamp: msg.timestamp,
          message_index: msg.message_index,
          model: msg.model,
          use_self_check: msg.use_self_check,
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
      bm25MatchMode?: string | null,
      bm25MinShouldMatch?: number | null,
      bm25UsePhrase?: boolean | null,
      bm25Analyzer?: string | null,
      maxContextChars?: number,
      scoreThreshold?: number,
      llmModel?: string,
      llmProvider?: string,
      useStructure = false,
      useMmr = false,
      mmrDiversity = 0.5,
      useSelfCheck = false,
      useConversationHistory = true,
      conversationHistoryLimit = 10
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
          bm25_match_mode: bm25MatchMode ?? undefined,
          bm25_min_should_match: bm25MinShouldMatch ?? undefined,
          bm25_use_phrase: bm25UsePhrase ?? undefined,
          bm25_analyzer: bm25Analyzer ?? undefined,
          max_context_chars: maxContextChars,
          score_threshold: scoreThreshold,
          llm_model: llmModel,
          llm_provider: llmProvider,
          use_structure: useStructure,
          use_mmr: useMmr,
          mmr_diversity: mmrDiversity,
          use_self_check: useSelfCheck,
          use_conversation_history: useConversationHistory,
          conversation_history_limit: conversationHistoryLimit,
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
          id: response.assistant_message_id,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          timestamp: new Date().toISOString(),
          model: response.model,
          use_mmr: response.use_mmr,
          mmr_diversity: response.mmr_diversity,
          use_self_check: response.use_self_check,
        }

        setMessages((prev) => {
          const next = [...prev]
          if (response.user_message_id) {
            for (let i = next.length - 1; i >= 0; i -= 1) {
              if (next[i].role === 'user' && !next[i].id) {
                next[i] = { ...next[i], id: response.user_message_id }
                break
              }
            }
          }
          next.push(assistantMessage)
          return next
        })
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

  const deleteMessagePair = useCallback(async (messageId: string, pair = true) => {
    if (!conversationId) return
    try {
      const response = await apiClient.deleteConversationMessage(conversationId, messageId, pair)
      const deletedSet = new Set(response.deleted_ids)
      setMessages((prev) => prev.filter((msg) => !msg.id || !deletedSet.has(msg.id)))
    } catch (e) {
      console.error('Failed to delete chat message:', e)
    }
  }, [conversationId])

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
    deleteMessagePair,
    clearMessages,
    conversationId,
  }
}
