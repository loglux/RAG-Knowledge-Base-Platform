import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiClient } from '../services/api'
import { useChat } from '../hooks/useChat'
import { MessageBubble } from '../components/chat/MessageBubble'
import { SourceCard } from '../components/chat/SourceCard'
import { ChatInput } from '../components/chat/ChatInput'
import { ChatSettings } from '../components/chat/ChatSettings'
import { ConversationList } from '../components/chat/ConversationList'
import { Panel } from '../components/common/Panel'
import { PanelHeader } from '../components/common/PanelHeader'
import { Button } from '../components/common/Button'
import type { KnowledgeBase, ConversationSettings, Document } from '../types/index'

export function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { logout } = useAuth()

  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [kbLoading, setKbLoading] = useState(true)
  const [kbError, setKbError] = useState<string | null>(null)
  const [headerHeight, setHeaderHeight] = useState(0)
  const [chatListCollapsed, setChatListCollapsed] = useState(() => {
    try {
      return localStorage.getItem('chat_list_collapsed') === '1'
    } catch {
      return false
    }
  })
  const [mobileChatListOpen, setMobileChatListOpen] = useState(false)
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
  const [retrievalMode, setRetrievalMode] = useState<'dense' | 'hybrid'>(() => {
    return 'dense'
  })
  const [lexicalTopK, setLexicalTopK] = useState(() => {
    return 20
  })
  const [hybridDenseWeight, setHybridDenseWeight] = useState(() => {
    return 0.6
  })
  const [hybridLexicalWeight, setHybridLexicalWeight] = useState(() => {
    return 0.4
  })
  const [bm25MatchMode, setBm25MatchMode] = useState(() => {
    return 'balanced'
  })
  const [bm25MinShouldMatch, setBm25MinShouldMatch] = useState(() => {
    return 50
  })
  const [bm25UsePhrase, setBm25UsePhrase] = useState(() => {
    return true
  })
  const [bm25Analyzer, setBm25Analyzer] = useState(() => {
    return 'mixed'
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
  const [useMmr, setUseMmr] = useState(() => {
    return false
  })
  const [mmrDiversity, setMmrDiversity] = useState(() => {
    return 0.5
  })
  const [useSelfCheck, setUseSelfCheck] = useState(() => {
    return false
  })
  const [useConversationHistory, setUseConversationHistory] = useState(() => {
    return true
  })
  const [conversationHistoryLimit, setConversationHistoryLimit] = useState(() => {
    return 10
  })
  const [useDocumentFilter, setUseDocumentFilter] = useState(() => {
    return false
  })
  const [contextExpansion, setContextExpansion] = useState<string[]>([])
  const [contextWindow, setContextWindow] = useState(() => {
    return 1
  })
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [opensearchAvailable, setOpensearchAvailable] = useState<boolean | null>(null)
  const [settingsLoaded, setSettingsLoaded] = useState(false)
  const [kbDefaultsApplied, setKbDefaultsApplied] = useState(false)
  const [bm25MatchModes, setBm25MatchModes] = useState<string[] | null>(null)
  const [bm25Analyzers, setBm25Analyzers] = useState<string[] | null>(null)
  const [showPromptVersions, setShowPromptVersions] = useState(false)

  const messagesScrollRef = useRef<HTMLDivElement>(null)
  const headerRef = useRef<HTMLElement>(null)
  const restoredConversationRef = useRef<string | null>(null)
  const restoringScrollRef = useRef(false)

  const {
    conversations,
    conversationsLoading,
    messages,
    isLoading,
    error,
    setError,
    sendMessage,
    deleteMessagePair,
    startNewChat,
    deleteConversation,
    renameConversation,
    selectConversation,
    conversationId,
  } = useChat(id!)

  const activeConversation = useMemo(() => {
    return conversations.find((conversation) => conversation.id === conversationId) ?? null
  }, [conversations, conversationId])
  const activeConversationTitle = (activeConversation?.title ?? '').trim() || 'Untitled chat'
  const scrollStateKey = useMemo(() => {
    return conversationId ? `chat_scroll_${conversationId}` : null
  }, [conversationId])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const settingsDraftKey = `chat_settings_draft_${id}`

  // Load conversation settings from server
  useEffect(() => {
    const loadConversationSettings = async () => {
      if (!conversationId) return
      try {
        const detail = await apiClient.getConversation(conversationId)
        const settings = detail.settings
        if (!settings) {
          setSettingsLoaded(true)
          return
        }

        if (settings.top_k !== undefined) setTopK(settings.top_k)
        if (settings.temperature !== undefined) setTemperature(settings.temperature)
        if (settings.max_context_chars !== undefined) setMaxContextChars(settings.max_context_chars)
        if (settings.score_threshold !== undefined) setScoreThreshold(settings.score_threshold)
        if (settings.retrieval_mode) setRetrievalMode(settings.retrieval_mode)
        if (settings.lexical_top_k !== undefined && settings.lexical_top_k !== null) {
          setLexicalTopK(settings.lexical_top_k)
        }
        if (settings.hybrid_dense_weight !== undefined && settings.hybrid_dense_weight !== null) {
          setHybridDenseWeight(settings.hybrid_dense_weight)
        }
        if (settings.hybrid_lexical_weight !== undefined && settings.hybrid_lexical_weight !== null) {
          setHybridLexicalWeight(settings.hybrid_lexical_weight)
        }
        if (settings.bm25_match_mode) setBm25MatchMode(settings.bm25_match_mode)
        if (settings.bm25_min_should_match !== undefined && settings.bm25_min_should_match !== null) {
          setBm25MinShouldMatch(settings.bm25_min_should_match)
        }
        if (settings.bm25_use_phrase !== undefined && settings.bm25_use_phrase !== null) {
          setBm25UsePhrase(settings.bm25_use_phrase)
        }
        if (settings.bm25_analyzer) setBm25Analyzer(settings.bm25_analyzer)
        if (settings.llm_model) setLlmModel(settings.llm_model)
        if (settings.llm_provider) setLlmProvider(settings.llm_provider)
        if (settings.use_structure !== undefined) setUseStructure(settings.use_structure)
        if (settings.use_mmr !== undefined) setUseMmr(settings.use_mmr)
        if (settings.mmr_diversity !== undefined && settings.mmr_diversity !== null) {
          setMmrDiversity(settings.mmr_diversity)
        }
        if (settings.use_self_check !== undefined) setUseSelfCheck(settings.use_self_check)
        if (typeof settings.use_conversation_history === 'boolean') {
          setUseConversationHistory(settings.use_conversation_history)
        }
        if (typeof settings.conversation_history_limit === 'number') {
          setConversationHistoryLimit(settings.conversation_history_limit)
        }
        if (typeof settings.use_document_filter === 'boolean') {
          setUseDocumentFilter(settings.use_document_filter)
        }
        if (Array.isArray(settings.document_ids)) {
          setSelectedDocumentIds(settings.document_ids)
        }
        if (Array.isArray(settings.context_expansion)) {
          setContextExpansion(settings.context_expansion)
        }
        if (typeof settings.context_window === 'number') {
          setContextWindow(settings.context_window)
        }
        setSettingsLoaded(true)
      } catch (err) {
        console.error('Failed to load conversation settings:', err)
        setSettingsLoaded(true)
      }
    }

    loadConversationSettings()
  }, [conversationId])

  useEffect(() => {
    const loadGlobalSettings = async () => {
      if (conversationId) return
      try {
        const draftRaw = localStorage.getItem(settingsDraftKey)
        if (draftRaw) {
          return
        }
      } catch (err) {
        console.error('Failed to read draft chat settings:', err)
      }
      try {
        const data = await apiClient.getAppSettings()
        if (data.top_k !== null) setTopK(data.top_k)
        if (data.temperature !== null) setTemperature(data.temperature)
        if (data.max_context_chars !== null) setMaxContextChars(data.max_context_chars)
        if (data.score_threshold !== null) setScoreThreshold(data.score_threshold)
        if (data.retrieval_mode) setRetrievalMode(data.retrieval_mode)
        if (data.lexical_top_k !== null) setLexicalTopK(data.lexical_top_k)
        if (data.hybrid_dense_weight !== null) setHybridDenseWeight(data.hybrid_dense_weight)
        if (data.hybrid_lexical_weight !== null) setHybridLexicalWeight(data.hybrid_lexical_weight)
        if (data.bm25_match_mode) setBm25MatchMode(data.bm25_match_mode)
        if (data.bm25_min_should_match !== null) setBm25MinShouldMatch(data.bm25_min_should_match)
        if (data.bm25_use_phrase !== null) setBm25UsePhrase(data.bm25_use_phrase)
        if (data.bm25_analyzer) setBm25Analyzer(data.bm25_analyzer)
        if (data.llm_model) setLlmModel(data.llm_model)
        if (data.llm_provider) setLlmProvider(data.llm_provider)
        if (data.use_structure !== null) setUseStructure(data.use_structure)
        setSettingsLoaded(true)
      } catch (err) {
        console.error('Failed to load global settings:', err)
        setSettingsLoaded(true)
      }
    }

    loadGlobalSettings()
  }, [conversationId])

  useEffect(() => {
    const loadPromptDisplaySettings = async () => {
      try {
        const data = await apiClient.getAppSettings()
        if (data.show_prompt_versions !== null) {
          setShowPromptVersions(data.show_prompt_versions)
        }
      } catch (err) {
        console.error('Failed to load prompt display settings:', err)
      }
    }

    loadPromptDisplaySettings()
  }, [])

  useEffect(() => {
    if (conversationId) return
    try {
      const raw = localStorage.getItem(settingsDraftKey)
      if (!raw) return
      const draft = JSON.parse(raw)
      if (draft.top_k !== undefined) setTopK(draft.top_k)
      if (draft.temperature !== undefined) setTemperature(draft.temperature)
      if (draft.max_context_chars !== undefined) setMaxContextChars(draft.max_context_chars)
      if (draft.score_threshold !== undefined) setScoreThreshold(draft.score_threshold)
      if (draft.retrieval_mode) setRetrievalMode(draft.retrieval_mode)
      if (draft.lexical_top_k !== undefined && draft.lexical_top_k !== null) {
        setLexicalTopK(draft.lexical_top_k)
      }
      if (draft.hybrid_dense_weight !== undefined && draft.hybrid_dense_weight !== null) {
        setHybridDenseWeight(draft.hybrid_dense_weight)
      }
      if (draft.hybrid_lexical_weight !== undefined && draft.hybrid_lexical_weight !== null) {
        setHybridLexicalWeight(draft.hybrid_lexical_weight)
      }
      if (draft.bm25_match_mode) setBm25MatchMode(draft.bm25_match_mode)
      if (draft.bm25_min_should_match !== undefined && draft.bm25_min_should_match !== null) {
        setBm25MinShouldMatch(draft.bm25_min_should_match)
      }
      if (draft.bm25_use_phrase !== undefined && draft.bm25_use_phrase !== null) {
        setBm25UsePhrase(draft.bm25_use_phrase)
      }
      if (draft.bm25_analyzer) setBm25Analyzer(draft.bm25_analyzer)
      if (draft.llm_model) setLlmModel(draft.llm_model)
      if (draft.llm_provider) setLlmProvider(draft.llm_provider)
      if (draft.use_structure !== undefined) setUseStructure(draft.use_structure)
      if (draft.use_mmr !== undefined) setUseMmr(draft.use_mmr)
      if (draft.mmr_diversity !== undefined && draft.mmr_diversity !== null) setMmrDiversity(draft.mmr_diversity)
      if (draft.use_self_check !== undefined) setUseSelfCheck(draft.use_self_check)
      if (typeof draft.use_conversation_history === 'boolean') {
        setUseConversationHistory(draft.use_conversation_history)
      }
      if (typeof draft.conversation_history_limit === 'number') {
        setConversationHistoryLimit(draft.conversation_history_limit)
      }
      if (typeof draft.use_document_filter === 'boolean') {
        setUseDocumentFilter(draft.use_document_filter)
      }
      if (Array.isArray(draft.document_ids)) {
        setSelectedDocumentIds(draft.document_ids)
      }
      if (Array.isArray(draft.context_expansion)) {
        setContextExpansion(draft.context_expansion)
      }
      if (typeof draft.context_window === 'number') {
        setContextWindow(draft.context_window)
      }
    } catch (err) {
      console.error('Failed to load draft chat settings:', err)
    }
  }, [conversationId, settingsDraftKey])

  useEffect(() => {
    const loadSettingsMetadata = async () => {
      try {
        const metadata = await apiClient.getSettingsMetadata()
        setBm25MatchModes(metadata.bm25_match_modes || null)
        setBm25Analyzers(metadata.bm25_analyzers || null)
      } catch {
        setBm25MatchModes(null)
        setBm25Analyzers(null)
      }
    }

    loadSettingsMetadata()
  }, [])

  useEffect(() => {
    const loadInfo = async () => {
      try {
        const info = await apiClient.getApiInfo()
        setOpensearchAvailable(info.integrations?.opensearch_available ?? null)
      } catch {
        setOpensearchAvailable(null)
      }
    }

    loadInfo()
  }, [])

  useEffect(() => {
    const loadDocuments = async () => {
      if (!id) return
      setDocumentsLoading(true)
      try {
        const response = await apiClient.getDocuments(id, 1, 100)
        const items = response.items.filter((doc) => !doc.is_deleted)
        setDocuments(items)
      } catch (err) {
        console.error('Failed to load documents:', err)
        setDocuments([])
      } finally {
        setDocumentsLoading(false)
      }
    }

    loadDocuments()
  }, [id])

  // Persist conversation settings to server when they change
  useEffect(() => {
    if (!conversationId || !settingsLoaded) return
    const safeHistoryLimit = Number.isFinite(conversationHistoryLimit)
      ? conversationHistoryLimit
      : 10
    const payload: ConversationSettings = {
      top_k: topK,
      temperature,
      max_context_chars: maxContextChars,
      score_threshold: scoreThreshold,
      retrieval_mode: retrievalMode,
      lexical_top_k: lexicalTopK,
      hybrid_dense_weight: hybridDenseWeight,
      hybrid_lexical_weight: hybridLexicalWeight,
      bm25_match_mode: bm25MatchMode,
      bm25_min_should_match: bm25MinShouldMatch,
      bm25_use_phrase: bm25UsePhrase,
      bm25_analyzer: bm25Analyzer,
      llm_model: llmModel,
      llm_provider: llmProvider,
      use_structure: useStructure,
      use_mmr: useMmr,
      mmr_diversity: mmrDiversity,
      use_self_check: useSelfCheck,
      use_conversation_history: Boolean(useConversationHistory),
      conversation_history_limit: safeHistoryLimit,
      use_document_filter: Boolean(useDocumentFilter),
      document_ids: useDocumentFilter ? selectedDocumentIds : [],
      context_expansion: contextExpansion,
      context_window: contextExpansion.includes('window') ? contextWindow : 0,
    }

    apiClient.updateConversationSettings(conversationId, payload).catch((err) => {
      console.error('Failed to update conversation settings:', err)
    })
  }, [conversationId, settingsLoaded, topK, temperature, maxContextChars, scoreThreshold, retrievalMode, lexicalTopK, hybridDenseWeight, hybridLexicalWeight, bm25MatchMode, bm25MinShouldMatch, bm25UsePhrase, bm25Analyzer, llmModel, llmProvider, useStructure, useMmr, mmrDiversity, useSelfCheck, useConversationHistory, conversationHistoryLimit, useDocumentFilter, selectedDocumentIds, contextExpansion, contextWindow])

  useEffect(() => {
    if (conversationId || !settingsLoaded) return
    const safeHistoryLimit = Number.isFinite(conversationHistoryLimit)
      ? conversationHistoryLimit
      : 10
    const payload: ConversationSettings = {
      top_k: topK,
      temperature,
      max_context_chars: maxContextChars,
      score_threshold: scoreThreshold,
      retrieval_mode: retrievalMode,
      lexical_top_k: lexicalTopK,
      hybrid_dense_weight: hybridDenseWeight,
      hybrid_lexical_weight: hybridLexicalWeight,
      bm25_match_mode: bm25MatchMode,
      bm25_min_should_match: bm25MinShouldMatch,
      bm25_use_phrase: bm25UsePhrase,
      bm25_analyzer: bm25Analyzer,
      llm_model: llmModel,
      llm_provider: llmProvider,
      use_structure: useStructure,
      use_mmr: useMmr,
      mmr_diversity: mmrDiversity,
      use_self_check: useSelfCheck,
      use_conversation_history: Boolean(useConversationHistory),
      conversation_history_limit: safeHistoryLimit,
      use_document_filter: Boolean(useDocumentFilter),
      document_ids: useDocumentFilter ? selectedDocumentIds : [],
      context_expansion: contextExpansion,
      context_window: contextExpansion.includes('window') ? contextWindow : 0,
    }
    try {
      localStorage.setItem(settingsDraftKey, JSON.stringify(payload))
    } catch (err) {
      console.error('Failed to persist draft chat settings:', err)
    }
  }, [conversationId, settingsLoaded, topK, temperature, maxContextChars, scoreThreshold, retrievalMode, lexicalTopK, hybridDenseWeight, hybridLexicalWeight, bm25MatchMode, bm25MinShouldMatch, bm25UsePhrase, bm25Analyzer, llmModel, llmProvider, useStructure, useMmr, mmrDiversity, useSelfCheck, useConversationHistory, conversationHistoryLimit, useDocumentFilter, selectedDocumentIds, contextExpansion, contextWindow, settingsDraftKey])

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

  useLayoutEffect(() => {
    const headerEl = headerRef.current
    if (!headerEl) return

    const updateHeight = () => {
      setHeaderHeight(headerEl.getBoundingClientRect().height)
    }

    updateHeight()

    let observer: ResizeObserver | null = null
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(() => updateHeight())
      observer.observe(headerEl)
    } else {
      window.addEventListener('resize', updateHeight)
    }

    return () => {
      if (observer) {
        observer.disconnect()
      } else {
        window.removeEventListener('resize', updateHeight)
      }
    }
  }, [])

  useEffect(() => {
    if (!kb || conversationId || kbDefaultsApplied) return
    if (kb.bm25_match_mode !== undefined && kb.bm25_match_mode !== null) {
      setBm25MatchMode(kb.bm25_match_mode)
    }
    if (kb.bm25_min_should_match !== undefined && kb.bm25_min_should_match !== null) {
      setBm25MinShouldMatch(kb.bm25_min_should_match)
    }
    if (kb.bm25_use_phrase !== undefined && kb.bm25_use_phrase !== null) {
      setBm25UsePhrase(kb.bm25_use_phrase)
    }
    if (kb.bm25_analyzer !== undefined && kb.bm25_analyzer !== null) {
      setBm25Analyzer(kb.bm25_analyzer)
    }
    setKbDefaultsApplied(true)
  }, [kb, conversationId, kbDefaultsApplied])

  // Auto-scroll to bottom when new messages arrive without jumping the window.
  useEffect(() => {
    const container = messagesScrollRef.current
    if (!container) return
    if (restoringScrollRef.current) return

    const nearBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 120
    if (!nearBottom && messages.length > 0) return

    requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight
    })
  }, [messages])

  // Restore scroll position per conversation once messages are ready.
  useEffect(() => {
    if (!conversationId || messages.length === 0) return
    if (restoredConversationRef.current === conversationId) return

    const container = messagesScrollRef.current
    if (!container || !scrollStateKey) return

    let saved: string | null = null
    try {
      saved = sessionStorage.getItem(scrollStateKey)
    } catch {
      saved = null
    }

    if (saved !== null) {
      const next = Number(saved)
      if (Number.isFinite(next)) {
        restoringScrollRef.current = true
        requestAnimationFrame(() => {
          container.scrollTop = next
          requestAnimationFrame(() => {
            restoringScrollRef.current = false
          })
        })
      }
    }

    restoredConversationRef.current = conversationId
  }, [conversationId, messages.length, scrollStateKey])

  // Persist scroll position for the active conversation.
  useEffect(() => {
    const container = messagesScrollRef.current
    if (!container || !scrollStateKey) return

    let ticking = false
    const handleScroll = () => {
      if (ticking) return
      ticking = true
      requestAnimationFrame(() => {
        try {
          sessionStorage.setItem(scrollStateKey, String(container.scrollTop))
        } catch {
          // ignore storage errors
        }
        ticking = false
      })
    }

    container.addEventListener('scroll', handleScroll)
    return () => {
      container.removeEventListener('scroll', handleScroll)
    }
  }, [scrollStateKey])

  const handleSendMessage = (question: string) => {
    const safeHistoryLimit = Number.isFinite(conversationHistoryLimit)
      ? conversationHistoryLimit
      : 10
    if (useDocumentFilter && selectedDocumentIds.length === 0) {
      setError('Select at least one document or disable the document filter.')
      return
    }
    const effectiveWindow = contextExpansion.includes('window') ? contextWindow : 0
    sendMessage(
      question,
      topK,
      temperature,
      retrievalMode,
      lexicalTopK,
      hybridDenseWeight,
      hybridLexicalWeight,
      bm25MatchMode,
      bm25MinShouldMatch,
      bm25UsePhrase,
      bm25Analyzer,
      maxContextChars,
      scoreThreshold,
      llmModel,
      llmProvider,
      useStructure,
      useMmr,
      mmrDiversity,
      useSelfCheck,
      Boolean(useConversationHistory),
      safeHistoryLimit,
      Boolean(useDocumentFilter),
      selectedDocumentIds,
      contextExpansion,
      effectiveWindow
    )
  }

  useEffect(() => {
    if (!conversationId) return
    try {
      localStorage.removeItem(settingsDraftKey)
    } catch (err) {
      console.error('Failed to clear draft chat settings:', err)
    }
  }, [conversationId, settingsDraftKey])

  const handleLLMChange = (model: string, provider: string) => {
    setLlmModel(model)
    setLlmProvider(provider)
  }

  const handleResetDefaults = async () => {
    try {
      const data = await apiClient.getAppSettings()
      if (data.top_k !== null) setTopK(data.top_k)
      if (data.temperature !== null) setTemperature(data.temperature)
      if (data.max_context_chars !== null) setMaxContextChars(data.max_context_chars)
      if (data.score_threshold !== null) setScoreThreshold(data.score_threshold)
      if (data.retrieval_mode) setRetrievalMode(data.retrieval_mode)
      if (data.lexical_top_k !== null) setLexicalTopK(data.lexical_top_k)
      if (data.hybrid_dense_weight !== null) setHybridDenseWeight(data.hybrid_dense_weight)
      if (data.hybrid_lexical_weight !== null) setHybridLexicalWeight(data.hybrid_lexical_weight)
      if (data.bm25_match_mode) setBm25MatchMode(data.bm25_match_mode)
      if (data.bm25_min_should_match !== null) setBm25MinShouldMatch(data.bm25_min_should_match)
      if (data.bm25_use_phrase !== null) setBm25UsePhrase(data.bm25_use_phrase)
      if (data.bm25_analyzer) setBm25Analyzer(data.bm25_analyzer)
      if (data.llm_model) setLlmModel(data.llm_model)
      if (data.llm_provider) setLlmProvider(data.llm_provider)
      if (data.use_structure !== null) setUseStructure(data.use_structure)

      // Reset toggles to default values
      setUseMmr(false)
      setMmrDiversity(0.5)
      setUseSelfCheck(false)
      setUseConversationHistory(true)
      setConversationHistoryLimit(10)
      setUseDocumentFilter(false)
      setSelectedDocumentIds([])
      setContextExpansion([])
      setContextWindow(1)

      if (kb) {
        if (kb.bm25_match_mode !== null && kb.bm25_match_mode !== undefined) setBm25MatchMode(kb.bm25_match_mode)
        if (kb.bm25_min_should_match !== null && kb.bm25_min_should_match !== undefined) {
          setBm25MinShouldMatch(kb.bm25_min_should_match)
        }
        if (kb.bm25_use_phrase !== null && kb.bm25_use_phrase !== undefined) setBm25UsePhrase(kb.bm25_use_phrase)
        if (kb.bm25_analyzer !== null && kb.bm25_analyzer !== undefined) setBm25Analyzer(kb.bm25_analyzer)
      }
    } catch (err) {
      console.error('Failed to reset chat defaults:', err)
    }
  }

  const toggleChatListCollapsed = () => {
    setChatListCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem('chat_list_collapsed', next ? '1' : '0')
      } catch {
        // ignore storage errors
      }
      return next
    })
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
          <Button variant="primary" onClick={() => navigate('/')}>
            Go Home
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen overflow-hidden bg-gray-900 flex flex-col">
      {/* Header */}
      <header ref={headerRef} className="sticky top-0 z-30 bg-gray-800/95 backdrop-blur border-b border-gray-700 shadow-sm">
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
                <p className="text-sm text-gray-300 mt-1">
                  {activeConversationTitle}
                </p>
                {kb.description && <p className="text-gray-400 text-sm mt-1">{kb.description}</p>}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Button onClick={handleLogout} size="sm">
                Logout
              </Button>
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="text-gray-400 hover:text-white transition-colors px-3 py-2"
                aria-label="Settings"
              >
                ⚙️
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
        <div
          className="sticky z-20 bg-gray-800/95 backdrop-blur border-b border-gray-700 shadow-sm"
          style={{ top: headerHeight }}
        >
          <div className="max-h-[60vh] overflow-y-auto">
            <ChatSettings
              topK={topK}
              temperature={temperature}
              maxContextChars={maxContextChars}
              scoreThreshold={scoreThreshold}
              retrievalMode={retrievalMode}
              lexicalTopK={lexicalTopK}
              hybridDenseWeight={hybridDenseWeight}
              hybridLexicalWeight={hybridLexicalWeight}
              bm25MatchMode={bm25MatchMode}
              bm25MinShouldMatch={bm25MinShouldMatch}
              bm25UsePhrase={bm25UsePhrase}
              bm25Analyzer={bm25Analyzer}
              bm25MatchModes={bm25MatchModes ?? undefined}
              bm25Analyzers={bm25Analyzers ?? undefined}
              opensearchAvailable={opensearchAvailable ?? undefined}
              llmModel={llmModel}
              llmProvider={llmProvider}
              useStructure={useStructure}
              useMmr={useMmr}
              mmrDiversity={mmrDiversity}
              useSelfCheck={useSelfCheck}
              useConversationHistory={useConversationHistory}
              conversationHistoryLimit={conversationHistoryLimit}
              useDocumentFilter={useDocumentFilter}
              contextExpansion={contextExpansion}
              contextWindow={contextWindow}
              selectedDocumentIds={selectedDocumentIds}
              documents={documents}
              documentsLoading={documentsLoading}
              onTopKChange={setTopK}
              onTemperatureChange={setTemperature}
              onMaxContextCharsChange={setMaxContextChars}
              onScoreThresholdChange={setScoreThreshold}
              onRetrievalModeChange={setRetrievalMode}
              onLexicalTopKChange={setLexicalTopK}
              onHybridDenseWeightChange={setHybridDenseWeight}
              onHybridLexicalWeightChange={setHybridLexicalWeight}
              onBm25MatchModeChange={setBm25MatchMode}
              onBm25MinShouldMatchChange={setBm25MinShouldMatch}
              onBm25UsePhraseChange={setBm25UsePhrase}
              onBm25AnalyzerChange={setBm25Analyzer}
              onLLMChange={handleLLMChange}
              onUseStructureChange={setUseStructure}
              onUseMmrChange={setUseMmr}
              onMmrDiversityChange={setMmrDiversity}
              onUseSelfCheckChange={setUseSelfCheck}
              onUseConversationHistoryChange={setUseConversationHistory}
              onConversationHistoryLimitChange={(value) => {
                setConversationHistoryLimit(Number.isFinite(value) ? value : 0)
              }}
              onUseDocumentFilterChange={setUseDocumentFilter}
              onContextExpansionChange={setContextExpansion}
              onContextWindowChange={setContextWindow}
              onSelectedDocumentIdsChange={setSelectedDocumentIds}
              onResetDefaults={handleResetDefaults}
              onClose={() => setShowSettings(false)}
            />
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 min-h-0 px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-7xl mx-auto h-full min-h-0">
          <div
            className={`grid grid-cols-1 gap-6 h-full min-h-0 ${
              chatListCollapsed ? 'lg:grid-cols-[56px,1fr]' : 'lg:grid-cols-[280px,1fr]'
            }`}
          >
            <aside className="hidden lg:block h-full min-h-0 relative">
              <ConversationList
                conversations={conversations}
                conversationsLoading={conversationsLoading}
                activeConversationId={conversationId}
                onStartNewChat={startNewChat}
                onSelectConversation={selectConversation}
                onDeleteConversation={deleteConversation}
                onRenameConversation={renameConversation}
                collapsed={chatListCollapsed}
                onToggleCollapsed={toggleChatListCollapsed}
              />
              <button
                type="button"
                onClick={toggleChatListCollapsed}
                className="absolute top-1/2 -right-3 -translate-y-1/2 w-6 h-10 rounded-r-lg bg-gray-800 border border-gray-700 text-gray-300 hover:text-white transition-colors"
                aria-label={chatListCollapsed ? 'Expand chat list' : 'Collapse chat list'}
                title={chatListCollapsed ? 'Expand chat list' : 'Collapse chat list'}
              >
                {chatListCollapsed ? '▸' : '▾'}
              </button>
            </aside>

            <section className="min-w-0 h-full min-h-0 flex flex-col">
              <div className="lg:hidden mb-4">
                <Panel className="p-3">
                  <PanelHeader
                    title={(
                      <div className="min-w-0">
                        <div className="text-xs text-gray-400">Chats</div>
                        <div className="text-sm text-white truncate">{activeConversationTitle}</div>
                      </div>
                    )}
                    actions={(
                      <>
                        <Button type="button" onClick={() => startNewChat()} size="xs">
                          New
                        </Button>
                        <Button
                          type="button"
                          onClick={() => setMobileChatListOpen((prev) => !prev)}
                          size="xs"
                        >
                          {mobileChatListOpen ? 'Hide' : 'Show'}
                        </Button>
                      </>
                    )}
                  />
                </Panel>

                {mobileChatListOpen && (
                  <div className="mt-3">
                    <ConversationList
                      conversations={conversations}
                      conversationsLoading={conversationsLoading}
                      activeConversationId={conversationId}
                      onStartNewChat={() => {
                        startNewChat()
                        setMobileChatListOpen(false)
                      }}
                      onSelectConversation={(cid) => {
                        selectConversation(cid)
                        setMobileChatListOpen(false)
                      }}
                      onDeleteConversation={deleteConversation}
                      onRenameConversation={renameConversation}
                      collapsed={false}
                      onToggleCollapsed={toggleChatListCollapsed}
                    />
                  </div>
                )}
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto" ref={messagesScrollRef}>
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
                        <p className="text-sm text-gray-300">Example: &quot;What is the main topic?&quot;</p>
                      </div>
                      <div className="card p-4">
                        <p className="text-sm text-gray-300">Example: &quot;Summarize the key points&quot;</p>
                      </div>
                      <div className="card p-4">
                        <p className="text-sm text-gray-300">Example: &quot;Explain in detail...&quot;</p>
                      </div>
                      <div className="card p-4">
                        <p className="text-sm text-gray-300">Example: &quot;Compare and contrast...&quot;</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Messages */}
                <div className="space-y-6">
                  {messages.map((message, index) => {
                    const previous = messages[index - 1]
                    const canDeletePair = (
                      message.role === 'assistant' &&
                      previous?.role === 'user' &&
                      message.id &&
                      previous.id
                    )
                    const handleDelete = canDeletePair
                      ? () => {
                          if (!message.id) return
                          const ok = window.confirm('Delete this Q&A pair from the chat history?')
                          if (ok) {
                            deleteMessagePair(message.id, true)
                          }
                        }
                      : undefined
                    return (
                      <div key={message.id ?? index}>
                        <MessageBubble
                          message={message}
                          onDelete={handleDelete}
                          showPromptVersion={showPromptVersions}
                        />
                      {message.sources && message.sources.length > 0 && (
                        <details className="mt-4 space-y-2">
                          <summary className="text-xs text-gray-500 font-medium cursor-pointer select-none sources-summary">
                            <span>SOURCES ({message.sources.length})</span>
                            {message.use_mmr && (
                              <span className="ml-2 px-2 py-0.5 text-[10px] bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded">
                                MMR {message.mmr_diversity?.toFixed(1)}
                              </span>
                            )}
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
                    )
                  })}
                </div>

                {/* Loading Indicator */}
                {isLoading && (
                  <div className="flex items-center space-x-3 text-gray-400 mt-6">
                    <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-primary-500"></div>
                    <span className="text-sm">Thinking...</span>
                  </div>
                )}

                <div />
                </div>
              </div>

              {/* Chat Input */}
              <div className="border-t border-gray-700 bg-gray-800">
                <div className="max-w-4xl mx-auto py-4">
                  <ChatInput onSend={handleSendMessage} disabled={isLoading} />
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
