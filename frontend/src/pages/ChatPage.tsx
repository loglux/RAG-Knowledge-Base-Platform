import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiClient } from '../services/api'
import { useChat } from '../hooks/useChat'
import { MessageBubble } from '../components/chat/MessageBubble'
import { SourceCard } from '../components/chat/SourceCard'
import { ChatInput } from '../components/chat/ChatInput'
import { ChatSettings } from '../components/chat/ChatSettings'
import type { KnowledgeBase } from '../types/index'

export function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [kbLoading, setKbLoading] = useState(true)
  const [kbError, setKbError] = useState<string | null>(null)

  const [showSettings, setShowSettings] = useState(false)
  const [topK, setTopK] = useState(() => {
    const saved = localStorage.getItem('chat_topK')
    return saved ? Number(saved) : 5
  })
  const [temperature, setTemperature] = useState(() => {
    const saved = localStorage.getItem('chat_temperature')
    return saved ? Number(saved) : 0.7
  })
  const [llmModel, setLlmModel] = useState(() => {
    return localStorage.getItem('chat_llmModel') || 'gpt-4o'
  })
  const [llmProvider, setLlmProvider] = useState(() => {
    return localStorage.getItem('chat_llmProvider') || 'openai'
  })
  const [useStructure, setUseStructure] = useState(() => {
    const saved = localStorage.getItem('chat_useStructure')
    return saved === 'true'
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { messages, isLoading, error, sendMessage, clearMessages } = useChat(id!)

  // Save settings to localStorage when they change
  useEffect(() => {
    localStorage.setItem('chat_topK', String(topK))
  }, [topK])

  useEffect(() => {
    localStorage.setItem('chat_temperature', String(temperature))
  }, [temperature])

  useEffect(() => {
    localStorage.setItem('chat_llmModel', llmModel)
  }, [llmModel])

  useEffect(() => {
    localStorage.setItem('chat_llmProvider', llmProvider)
  }, [llmProvider])

  useEffect(() => {
    localStorage.setItem('chat_useStructure', String(useStructure))
  }, [useStructure])

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
    sendMessage(question, topK, temperature, llmModel, llmProvider, useStructure)
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
          llmModel={llmModel}
          llmProvider={llmProvider}
          useStructure={useStructure}
          onTopKChange={setTopK}
          onTemperatureChange={setTemperature}
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
