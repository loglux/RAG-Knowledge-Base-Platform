import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiClient } from '../services/api'
import { useChat } from '../hooks/useChat'
import { MessageBubble } from '../components/chat/MessageBubble'
import { SourceCard } from '../components/chat/SourceCard'
import { ChatInput } from '../components/chat/ChatInput'
import { ChatSettings } from '../components/chat/ChatSettings'
import type { KnowledgeBase, ConversationSettings } from '../types/index'

export function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [kbLoading, setKbLoading] = useState(true)
  const [kbError, setKbError] = useState<string | null>(null)

  const [showSettings, setShowSettings] = useState(false)
  const [topK, setTopK] = useState(() => {
    return 5
  })
  const [temperature, setTemperature] = useState(() => {
    return 0.7
  })
  const [maxContextChars, setMaxContextChars] = useState(() => {
    return 0
  })
  const [scoreThreshold, setScoreThreshold] = useState(() => {
    return 0
  })
  const [llmModel, setLlmModel] = useState(() => {
    return 'gpt-4o'
  })
  const [llmProvider, setLlmProvider] = useState(() => {
    return 'openai'
  })
  const [useStructure, setUseStructure] = useState(() => {
    return false
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { messages, isLoading, error, sendMessage, clearMessages, conversationId } = useChat(id!)

  // No localStorage fallback: settings are loaded from server per conversation

  // Load conversation settings from server
  useEffect(() => {
    const loadConversationSettings = async () => {
      if (!conversationId) return
      try {
        const detail = await apiClient.getConversation(conversationId)
        const settings = detail.settings
        if (!settings) return

        if (settings.top_k !== undefined) setTopK(settings.top_k)
        if (settings.temperature !== undefined) setTemperature(settings.temperature)
        if (settings.max_context_chars !== undefined) setMaxContextChars(settings.max_context_chars)
        if (settings.score_threshold !== undefined) setScoreThreshold(settings.score_threshold)
        if (settings.llm_model) setLlmModel(settings.llm_model)
        if (settings.llm_provider) setLlmProvider(settings.llm_provider)
        if (settings.use_structure !== undefined) setUseStructure(settings.use_structure)
      } catch (err) {
        console.error('Failed to load conversation settings:', err)
      }
    }

    loadConversationSettings()
  }, [conversationId])

  // Persist conversation settings to server when they change
  useEffect(() => {
    if (!conversationId) return
    const payload: ConversationSettings = {
      top_k: topK,
      temperature,
      max_context_chars: maxContextChars,
      score_threshold: scoreThreshold,
      llm_model: llmModel,
      llm_provider: llmProvider,
      use_structure: useStructure,
    }

    apiClient.updateConversationSettings(conversationId, payload).catch((err) => {
      console.error('Failed to update conversation settings:', err)
    })
  }, [conversationId, topK, temperature, maxContextChars, scoreThreshold, llmModel, llmProvider, useStructure])

  useEffect(() => {
    const fetchKB = async () => {
      try {
        setKbLoading(true)
        setKbError(null)
        const data = await apiClient.getKnowledgeBase(id!)
        setKb(data)
      } catch (err) {
        setKbError(err instanceof Error ? err.message : 'Failed to load knowledge base')
      } finally {
        setKbLoading(false)
      }
    }

    if (id) {
      fetchKB()
    }
  }, [id])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = (question: string) => {
    sendMessage(question, topK, temperature, maxContextChars, scoreThreshold, llmModel, llmProvider, useStructure)
  }

  const handleLLMChange = (model: string, provider: string) => {
    setLlmModel(model)
    setLlmProvider(provider)
  }

  if (kbLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
          <p className="mt-4 text-gray-400">Loading knowledge base...</p>
        </div>
      </div>
    )
  }

  if (kbError || !kb) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="card max-w-md text-center">
          <div className="text-6xl mb-4">❌</div>
          <h2 className="text-xl font-semibold text-white mb-2">Error</h2>
          <p className="text-gray-400 mb-4">{kbError || 'Knowledge base not found'}</p>
          <button onClick={() => navigate('/')} className="btn-primary">
            Go Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(`/kb/${id}`)}
                className="text-gray-400 hover:text-white transition-colors"
                aria-label="Go back"
              >
                ← Back
              </button>
              <div>
                <h1 className="text-2xl font-bold text-white">💬 Chat with {kb.name}</h1>
                {kb.description && <p className="text-gray-400 text-sm mt-1">{kb.description}</p>}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="text-gray-400 hover:text-white transition-colors px-3 py-2"
                aria-label="Settings"
              >
                ⚙️
              </button>
              <button
                onClick={clearMessages}
                className="text-gray-400 hover:text-red-500 transition-colors px-3 py-2"
                aria-label="Clear chat"
              >
                🗑️
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-6 mt-4 text-sm text-gray-400">
            <span>{kb.document_count} documents</span>
            <span>•</span>
            <span>{kb.total_chunks} chunks</span>
          </div>
        </div>
      </header>

      {/* Settings Panel */}
      {showSettings && (
        <ChatSettings
          topK={topK}
          temperature={temperature}
          maxContextChars={maxContextChars}
          scoreThreshold={scoreThreshold}
          llmModel={llmModel}
          llmProvider={llmProvider}
          useStructure={useStructure}
          onTopKChange={setTopK}
          onTemperatureChange={setTemperature}
          onMaxContextCharsChange={setMaxContextChars}
          onScoreThresholdChange={setScoreThreshold}
          onLLMChange={handleLLMChange}
          onUseStructureChange={setUseStructure}
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-4xl mx-auto">
          {/* Error Display */}
          {error && (
            <div className="mb-4 p-4 bg-red-500 bg-opacity-10 border border-red-500 rounded-lg text-red-500">
              {error}
            </div>
          )}

          {/* Empty State */}
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">💭</div>
              <h3 className="text-xl font-semibold text-white mb-2">Start a conversation</h3>
              <p className="text-gray-400 mb-6">
                Ask questions about the documents in this knowledge base
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto text-left">
                <div className="card p-4">
                  <p className="text-sm text-gray-300">Example: "What is the main topic?"</p>
                </div>
                <div className="card p-4">
                  <p className="text-sm text-gray-300">Example: "Summarize the key points"</p>
                </div>
                <div className="card p-4">
                  <p className="text-sm text-gray-300">Example: "Explain in detail..."</p>
                </div>
                <div className="card p-4">
                  <p className="text-sm text-gray-300">Example: "Compare and contrast..."</p>
                </div>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="space-y-6">
            {messages.map((message, index) => (
              <div key={index}>
                <MessageBubble message={message} />
                {message.sources && message.sources.length > 0 && (
                  <details className="mt-4 space-y-2">
                    <summary className="text-xs text-gray-500 font-medium cursor-pointer select-none sources-summary">
                      <span>SOURCES ({message.sources.length})</span>
                      <span className="sources-caret ml-2">▸</span>
                    </summary>
                    <div className="grid grid-cols-1 gap-2 mt-2">
                      {message.sources.map((source, idx) => (
                        <SourceCard key={idx} source={source} />
                      ))}
                    </div>
                  </details>
                )}
              </div>
            ))}
          </div>

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex items-center space-x-3 text-gray-400 mt-6">
              <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-primary-500"></div>
              <span className="text-sm">Thinking...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Chat Input */}
      <div className="border-t border-gray-700 bg-gray-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
        </div>
      </div>
    </div>
  )
}
