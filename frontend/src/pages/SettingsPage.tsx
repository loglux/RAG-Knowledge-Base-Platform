import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiClient } from '../services/api'
import { LLMSelector } from '../components/chat/LLMSelector'
import { Button } from '../components/common/Button'
import type {
  AppSettings,
  KnowledgeBase,
  PromptVersionDetail,
  PromptVersionSummary,
  SelfCheckPromptVersionDetail,
  SelfCheckPromptVersionSummary,
  MCPToken,
  MCPRefreshToken,
  MCPOAuthEvent,
  OAuthTokenResponse
} from '../types/index'

const MCP_TOOL_OPTIONS = [
  { id: 'rag_query', label: 'rag_query', description: 'Answer a question with RAG + sources.' },
  { id: 'list_knowledge_bases', label: 'list_knowledge_bases', description: 'List available knowledge bases.' },
  { id: 'list_documents', label: 'list_documents', description: 'List documents for a knowledge base.' },
  { id: 'retrieve_chunks', label: 'retrieve_chunks', description: 'Retrieve relevant chunks without generation.' },
  { id: 'get_kb_retrieval_settings', label: 'get_kb_retrieval_settings', description: 'Read KB retrieval settings.' },
  { id: 'set_kb_retrieval_settings', label: 'set_kb_retrieval_settings', description: 'Update KB retrieval settings.' },
  { id: 'clear_kb_retrieval_settings', label: 'clear_kb_retrieval_settings', description: 'Clear KB retrieval settings.' },
]

type TabType = 'query' | 'kb-defaults' | 'ai-providers' | 'databases' | 'prompts' | 'kb-transfer' | 'mcp'

export function SettingsPage() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('query')

  // Loading states
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Query Defaults (AppSettings)
  const [llmModel, setLlmModel] = useState('gpt-4o')
  const [llmProvider, setLlmProvider] = useState('openai')
  const [temperature, setTemperature] = useState(0.7)
  const [topK, setTopK] = useState(5)
  const [maxContextChars, setMaxContextChars] = useState(0)
  const [scoreThreshold, setScoreThreshold] = useState(0)
  const [retrievalMode, setRetrievalMode] = useState<'dense' | 'hybrid'>('dense')
  const [lexicalTopK, setLexicalTopK] = useState(20)
  const [hybridDenseWeight, setHybridDenseWeight] = useState(0.6)
  const [hybridLexicalWeight, setHybridLexicalWeight] = useState(0.4)
  const [linkHybridWeights, setLinkHybridWeights] = useState(true)
  const [bm25MatchMode, setBm25MatchMode] = useState('balanced')
  const [bm25MinShouldMatch, setBm25MinShouldMatch] = useState(50)
  const [bm25UsePhrase, setBm25UsePhrase] = useState(true)
  const [bm25Analyzer, setBm25Analyzer] = useState('mixed')
  const [useStructure, setUseStructure] = useState(false)
  const [structureRequestsPerMinute, setStructureRequestsPerMinute] = useState(10)
  const [useLlmChatTitles, setUseLlmChatTitles] = useState(true)
  const [opensearchAvailable, setOpensearchAvailable] = useState<boolean | null>(null)
  const clamp01 = (value: number) => Math.min(1, Math.max(0, value))
  const handleDenseWeightChange = (value: number) => {
    const nextDense = clamp01(value)
    setHybridDenseWeight(nextDense)
    if (linkHybridWeights) {
      setHybridLexicalWeight(Number((1 - nextDense).toFixed(2)))
    }
  }

  const handleLexicalWeightChange = (value: number) => {
    const nextLexical = clamp01(value)
    setHybridLexicalWeight(nextLexical)
    if (linkHybridWeights) {
      setHybridDenseWeight(Number((1 - nextLexical).toFixed(2)))
    }
  }

  // KB Defaults
  const [kbChunkSize, setKbChunkSize] = useState(1000)
  const [kbChunkOverlap, setKbChunkOverlap] = useState(200)
  const [kbUpsertBatchSize, setKbUpsertBatchSize] = useState(256)

  // Prompt Versions
  const [promptVersions, setPromptVersions] = useState<PromptVersionSummary[]>([])
  const [promptDraftName, setPromptDraftName] = useState('')
  const [promptDraftSystemContent, setPromptDraftSystemContent] = useState('')
  const [promptSelected, setPromptSelected] = useState<PromptVersionDetail | null>(null)
  const [activePromptVersionId, setActivePromptVersionId] = useState<string | null>(null)
  const [showPromptVersions, setShowPromptVersions] = useState(false)
  const [promptsLoading, setPromptsLoading] = useState(false)

  // Self-Check Prompt Versions
  const [selfCheckPromptVersions, setSelfCheckPromptVersions] = useState<SelfCheckPromptVersionSummary[]>([])
  const [selfCheckPromptDraftName, setSelfCheckPromptDraftName] = useState('')
  const [selfCheckPromptDraftSystemContent, setSelfCheckPromptDraftSystemContent] = useState('')
  const [selfCheckPromptSelected, setSelfCheckPromptSelected] = useState<SelfCheckPromptVersionDetail | null>(null)
  const [activeSelfCheckPromptVersionId, setActiveSelfCheckPromptVersionId] = useState<string | null>(null)
  const [selfCheckPromptsLoading, setSelfCheckPromptsLoading] = useState(false)

  // System Settings (AI Providers)
  const [openaiApiKey, setOpenaiApiKey] = useState('')
  const [voyageApiKey, setVoyageApiKey] = useState('')
  const [anthropicApiKey, setAnthropicApiKey] = useState('')
  const [deepseekApiKey, setDeepseekApiKey] = useState('')
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState('')
  const [showOpenaiKey, setShowOpenaiKey] = useState(false)
  const [showVoyageKey, setShowVoyageKey] = useState(false)
  const [showAnthropicKey, setShowAnthropicKey] = useState(false)
  const [showDeepseekKey, setShowDeepseekKey] = useState(false)


  // System Settings (Databases)
  const [qdrantUrl, setQdrantUrl] = useState('')
  const [qdrantApiKey, setQdrantApiKey] = useState('')
  const [opensearchUrl, setOpensearchUrl] = useState('')
  const [opensearchUsername, setOpensearchUsername] = useState('')
  const [opensearchPassword, setOpensearchPassword] = useState('')
  const [postgresUsername, setPostgresUsername] = useState('kb_user')
  const [postgresNewPassword, setPostgresNewPassword] = useState('')
  const [showQdrantKey, setShowQdrantKey] = useState(false)
  const [showOpensearchPassword, setShowOpensearchPassword] = useState(false)

  // System Settings
  const [systemName, setSystemName] = useState('')
  const [maxFileSizeMb, setMaxFileSizeMb] = useState(50)

  // MCP Settings
  const [mcpEnabled, setMcpEnabled] = useState(false)
  const [mcpPath, setMcpPath] = useState('/mcp')
  const [mcpPublicBaseUrl, setMcpPublicBaseUrl] = useState('')
  const [mcpDefaultKbId, setMcpDefaultKbId] = useState('')
  const [mcpToolsEnabled, setMcpToolsEnabled] = useState<string[]>(MCP_TOOL_OPTIONS.map((t) => t.id))
  const [mcpAuthMode, setMcpAuthMode] = useState<'bearer' | 'refresh' | 'oauth2'>('bearer')
  const [mcpTokens, setMcpTokens] = useState<MCPToken[]>([])
  const [mcpTokenName, setMcpTokenName] = useState('')
  const [mcpTokenTTL, setMcpTokenTTL] = useState<number | ''>('')
  const [mcpCreatedToken, setMcpCreatedToken] = useState<string | null>(null)
  const [mcpAccessTokenTtlMinutes, setMcpAccessTokenTtlMinutes] = useState<number | ''>('')
  const [mcpRefreshTokenTtlDays, setMcpRefreshTokenTtlDays] = useState<number | ''>('')
  const [mcpRefreshTokens, setMcpRefreshTokens] = useState<MCPRefreshToken[]>([])
  const [mcpOAuthUsername, setMcpOAuthUsername] = useState('')
  const [mcpOAuthPassword, setMcpOAuthPassword] = useState('')
  const [mcpOAuthIssued, setMcpOAuthIssued] = useState<OAuthTokenResponse | null>(null)
  const [mcpOAuthLoading, setMcpOAuthLoading] = useState(false)
  const [mcpOAuthEvents, setMcpOAuthEvents] = useState<MCPOAuthEvent[]>([])
  const [mcpOAuthEventsLimit, setMcpOAuthEventsLimit] = useState(20)
  const [mcpOAuthEventsFilter, setMcpOAuthEventsFilter] = useState('all')

  // KB Transfer
  const [kbList, setKbList] = useState<KnowledgeBase[]>([])
  const [kbTransferLoading, setKbTransferLoading] = useState(false)
  const [kbSelection, setKbSelection] = useState<string[]>([])
  const [exportInclude, setExportInclude] = useState({
    documents: true,
    vectors: true,
    bm25: true,
    uploads: false,
    chats: false,
  })
  const [importInclude, setImportInclude] = useState({
    documents: true,
    vectors: true,
    bm25: true,
    uploads: false,
    chats: false,
  })
  const [importMode, setImportMode] = useState<'create' | 'merge'>('create')
  const [remapIds, setRemapIds] = useState(true)
  const [targetKbId, setTargetKbId] = useState('')
  const [importFile, setImportFile] = useState<File | null>(null)
  const [exportingKbArchive, setExportingKbArchive] = useState(false)
  const [exportingChatsMd, setExportingChatsMd] = useState(false)
  const [importingKbArchive, setImportingKbArchive] = useState(false)

  useEffect(() => {
    loadAllSettings()
  }, [])

  useEffect(() => {
    if (activeTab !== 'kb-transfer') return
    loadKbList()
  }, [activeTab])

  useEffect(() => {
    if (activeTab !== 'mcp') return
    loadMcpTokens()
    loadMcpRefreshTokens()
    loadMcpOAuthEvents()
  }, [activeTab, mcpOAuthEventsLimit])

  const loadAllSettings = async () => {
    try {
      setLoading(true)

      // Load app settings (query defaults, KB defaults)
      const appSettings: AppSettings = await apiClient.getAppSettings()
      if (appSettings.llm_model) setLlmModel(appSettings.llm_model)
      if (appSettings.llm_provider) setLlmProvider(appSettings.llm_provider)
      if (appSettings.temperature !== null) setTemperature(appSettings.temperature)
      if (appSettings.top_k !== null) setTopK(appSettings.top_k)
      if (appSettings.max_context_chars !== null) setMaxContextChars(appSettings.max_context_chars)
      if (appSettings.score_threshold !== null) setScoreThreshold(appSettings.score_threshold)
      if (appSettings.use_structure !== null) setUseStructure(appSettings.use_structure)
      if (appSettings.retrieval_mode) setRetrievalMode(appSettings.retrieval_mode)
      if (appSettings.lexical_top_k !== null) setLexicalTopK(appSettings.lexical_top_k)
      if (appSettings.hybrid_dense_weight !== null) setHybridDenseWeight(appSettings.hybrid_dense_weight)
      if (appSettings.hybrid_lexical_weight !== null) setHybridLexicalWeight(appSettings.hybrid_lexical_weight)
      if (appSettings.bm25_match_mode) setBm25MatchMode(appSettings.bm25_match_mode)
      if (appSettings.bm25_min_should_match !== null) setBm25MinShouldMatch(appSettings.bm25_min_should_match)
      if (appSettings.bm25_use_phrase !== null) setBm25UsePhrase(appSettings.bm25_use_phrase)
      if (appSettings.bm25_analyzer) setBm25Analyzer(appSettings.bm25_analyzer)
      if (appSettings.structure_requests_per_minute !== null) {
        setStructureRequestsPerMinute(appSettings.structure_requests_per_minute)
      }
      if (appSettings.use_llm_chat_titles !== null) {
        setUseLlmChatTitles(appSettings.use_llm_chat_titles)
      }
      if (appSettings.active_prompt_version_id) {
        setActivePromptVersionId(appSettings.active_prompt_version_id)
      }
      if (appSettings.active_self_check_prompt_version_id) {
        setActiveSelfCheckPromptVersionId(appSettings.active_self_check_prompt_version_id)
      }
      if (appSettings.show_prompt_versions !== null) {
        setShowPromptVersions(appSettings.show_prompt_versions)
      }
      if (appSettings.kb_chunk_size !== null) setKbChunkSize(appSettings.kb_chunk_size)
      if (appSettings.kb_chunk_overlap !== null) setKbChunkOverlap(appSettings.kb_chunk_overlap)
      if (appSettings.kb_upsert_batch_size !== null) setKbUpsertBatchSize(appSettings.kb_upsert_batch_size)

      // Load system settings (API keys, databases)
      const systemSettings = await apiClient.getSystemSettings()
      if (systemSettings.openai_api_key) setOpenaiApiKey(systemSettings.openai_api_key)
      if (systemSettings.voyage_api_key) setVoyageApiKey(systemSettings.voyage_api_key)
      if (systemSettings.anthropic_api_key) setAnthropicApiKey(systemSettings.anthropic_api_key)
      if (systemSettings.deepseek_api_key) setDeepseekApiKey(systemSettings.deepseek_api_key)
      if (systemSettings.ollama_base_url) setOllamaBaseUrl(systemSettings.ollama_base_url)
      if (systemSettings.mcp_enabled !== null && systemSettings.mcp_enabled !== undefined) {
        setMcpEnabled(systemSettings.mcp_enabled)
      }
      if (systemSettings.mcp_path) setMcpPath(systemSettings.mcp_path)
      if (systemSettings.mcp_public_base_url) setMcpPublicBaseUrl(systemSettings.mcp_public_base_url)
      if (systemSettings.mcp_default_kb_id) setMcpDefaultKbId(systemSettings.mcp_default_kb_id)
      if (systemSettings.mcp_tools_enabled && Array.isArray(systemSettings.mcp_tools_enabled)) {
        setMcpToolsEnabled(systemSettings.mcp_tools_enabled)
      }
      if (systemSettings.mcp_auth_mode) {
        const mode = String(systemSettings.mcp_auth_mode).toLowerCase()
        if (mode === 'bearer' || mode === 'refresh' || mode === 'oauth2') {
          setMcpAuthMode(mode)
        }
      }
      if (systemSettings.qdrant_url) setQdrantUrl(systemSettings.qdrant_url)
      if (systemSettings.qdrant_api_key) setQdrantApiKey(systemSettings.qdrant_api_key)
      if (systemSettings.opensearch_url) setOpensearchUrl(systemSettings.opensearch_url)
      if (systemSettings.opensearch_username) setOpensearchUsername(systemSettings.opensearch_username)
      if (systemSettings.opensearch_password) setOpensearchPassword(systemSettings.opensearch_password)
      if (systemSettings.mcp_access_token_ttl_minutes !== undefined && systemSettings.mcp_access_token_ttl_minutes !== null) {
        setMcpAccessTokenTtlMinutes(systemSettings.mcp_access_token_ttl_minutes)
      }
      if (systemSettings.mcp_refresh_token_ttl_days !== undefined && systemSettings.mcp_refresh_token_ttl_days !== null) {
        setMcpRefreshTokenTtlDays(systemSettings.mcp_refresh_token_ttl_days)
      }
      if (systemSettings.system_name) setSystemName(systemSettings.system_name)
      if (systemSettings.max_file_size_mb) setMaxFileSizeMb(systemSettings.max_file_size_mb)

      // Check OpenSearch availability
      const info = await apiClient.getApiInfo()
      setOpensearchAvailable(info.integrations?.opensearch_available ?? null)

      // Load prompt versions (for prompt editor tab)
      setPromptsLoading(true)
      try {
        const prompts = await apiClient.listPromptVersions()
        setPromptVersions(prompts)
        if (appSettings.active_prompt_version_id) {
          try {
            const activePrompt = await apiClient.getPromptVersion(appSettings.active_prompt_version_id)
            setPromptSelected(activePrompt)
          } catch {
            setPromptSelected(null)
          }
        }
      } finally {
        setPromptsLoading(false)
      }

      // Load self-check prompt versions
      setSelfCheckPromptsLoading(true)
      try {
        const prompts = await apiClient.listSelfCheckPromptVersions()
        setSelfCheckPromptVersions(prompts)
        if (appSettings.active_self_check_prompt_version_id) {
          try {
            const activePrompt = await apiClient.getSelfCheckPromptVersion(appSettings.active_self_check_prompt_version_id)
            setSelfCheckPromptSelected(activePrompt)
          } catch {
            setSelfCheckPromptSelected(null)
          }
        }
      } finally {
        setSelfCheckPromptsLoading(false)
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const loadKbList = async () => {
    try {
      setKbTransferLoading(true)
      const data = await apiClient.getKnowledgeBases(1, 100)
      setKbList(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load knowledge bases')
    } finally {
      setKbTransferLoading(false)
    }
  }

  const loadMcpTokens = async () => {
    try {
      const tokens = await apiClient.listMcpTokens()
      setMcpTokens(tokens)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load MCP tokens')
    }
  }

  const loadMcpRefreshTokens = async () => {
    try {
      const tokens = await apiClient.listMcpRefreshTokens()
      setMcpRefreshTokens(tokens)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load MCP refresh tokens')
    }
  }

  const loadMcpOAuthEvents = async () => {
    try {
      const events = await apiClient.listMcpOAuthEvents(mcpOAuthEventsLimit)
      setMcpOAuthEvents(events)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load MCP OAuth events')
    }
  }

  const handleSaveMcpSettings = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      const payload: any = {
        mcp_enabled: mcpEnabled,
        mcp_path: mcpPath,
        mcp_public_base_url: mcpPublicBaseUrl || null,
        mcp_default_kb_id: mcpDefaultKbId || null,
        mcp_tools_enabled: mcpToolsEnabled,
        mcp_auth_mode: mcpAuthMode,
      }
      if (mcpAccessTokenTtlMinutes !== '') {
        payload.mcp_access_token_ttl_minutes = Number(mcpAccessTokenTtlMinutes)
      }
      if (mcpRefreshTokenTtlDays !== '') {
        payload.mcp_refresh_token_ttl_days = Number(mcpRefreshTokenTtlDays)
      }

      await apiClient.updateSystemSettings(payload)
      setSuccess('MCP settings saved')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save MCP settings')
    } finally {
      setSaving(false)
    }
  }

  const handleCreateMcpToken = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)
      const payload: any = {
        name: mcpTokenName || undefined,
        expires_in_days: mcpTokenTTL === '' ? undefined : Number(mcpTokenTTL),
      }
      const result = await apiClient.createMcpToken(payload)
      setMcpCreatedToken(result.token)
      setMcpTokenName('')
      setMcpTokenTTL('')
      await loadMcpTokens()
      setSuccess('Token created')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create MCP token')
    } finally {
      setSaving(false)
    }
  }

  const handleIssueOAuthToken = async () => {
    if (!mcpOAuthUsername.trim() || !mcpOAuthPassword) {
      setError('Enter username and password to issue OAuth tokens')
      return
    }
    try {
      setMcpOAuthLoading(true)
      setError(null)
      setSuccess(null)
      setMcpOAuthIssued(null)
      const result = await apiClient.createMcpOAuthToken({
        username: mcpOAuthUsername.trim(),
        password: mcpOAuthPassword,
      })
      setMcpOAuthIssued(result)
      setMcpOAuthPassword('')
      await loadMcpRefreshTokens()
      setSuccess('OAuth tokens issued')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to issue OAuth tokens')
    } finally {
      setMcpOAuthLoading(false)
    }
  }

  const handleRevokeRefreshToken = async (jti: string) => {
    try {
      setSaving(true)
      setError(null)
      await apiClient.revokeMcpRefreshToken(jti)
      await loadMcpRefreshTokens()
      setSuccess('Refresh token revoked')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke refresh token')
    } finally {
      setSaving(false)
    }
  }

  const handleRevokeMcpToken = async (tokenId: string) => {
    try {
      setSaving(true)
      setError(null)
      await apiClient.revokeMcpToken(tokenId)
      await loadMcpTokens()
      setSuccess('Token revoked')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke MCP token')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteMcpToken = async (tokenId: string) => {
    if (!window.confirm('Delete this token permanently? This cannot be undone.')) return
    try {
      setSaving(true)
      setError(null)
      await apiClient.deleteMcpToken(tokenId)
      await loadMcpTokens()
      setSuccess('Token deleted')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete MCP token')
    } finally {
      setSaving(false)
    }
  }

  const toggleKbSelection = (id: string) => {
    setKbSelection((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const handleExportKbs = async () => {
    if (kbSelection.length === 0) {
      setError('Select at least one knowledge base to export')
      return
    }
    if (exportInclude.chats && !exportInclude.documents) {
      setError('Chats export requires documents to be included')
      return
    }
    try {
      setExportingKbArchive(true)
      setError(null)
      setSuccess(null)
      const { blob, filename } = await apiClient.exportKnowledgeBases({
        kb_ids: kbSelection,
        include: exportInclude,
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setSuccess('Export started. Download should begin automatically.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export KBs')
    } finally {
      setExportingKbArchive(false)
    }
  }

  const handleImportKbs = async () => {
    if (!importFile) {
      setError('Select an export archive to import')
      return
    }
    if (importMode === 'merge' && !targetKbId) {
      setError('Select a target KB for merge')
      return
    }
    if (importInclude.chats && !importInclude.documents) {
      setError('Chats import requires documents to be included')
      return
    }
    try {
      setImportingKbArchive(true)
      setError(null)
      setSuccess(null)
      const result = await apiClient.importKnowledgeBases(importFile, {
        mode: importMode,
        remap_ids: remapIds,
        target_kb_id: importMode === 'merge' ? targetKbId : null,
        include: importInclude,
      })
      setSuccess(`Import complete. KBs created: ${result.kb_created}, updated: ${result.kb_updated}`)
      setImportFile(null)
      await loadKbList()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import KBs')
    } finally {
      setImportingKbArchive(false)
    }
  }

  const handleExportChatsMarkdown = async () => {
    if (kbSelection.length === 0) {
      setError('Select at least one knowledge base to export chats')
      return
    }
    try {
      setExportingChatsMd(true)
      setError(null)
      setSuccess(null)
      const { blob, filename } = await apiClient.exportChatsMarkdown({
        kb_ids: kbSelection,
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setSuccess('Chats export started. Download should begin automatically.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export chats')
    } finally {
      setExportingChatsMd(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const handleSaveQueryDefaults = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      await apiClient.updateAppSettings({
        llm_model: llmModel,
        llm_provider: llmProvider,
        temperature,
        top_k: topK,
        max_context_chars: maxContextChars,
        score_threshold: scoreThreshold,
        use_structure: useStructure,
        retrieval_mode: retrievalMode,
        lexical_top_k: lexicalTopK,
        hybrid_dense_weight: hybridDenseWeight,
        hybrid_lexical_weight: hybridLexicalWeight,
        bm25_match_mode: bm25MatchMode,
        bm25_min_should_match: bm25MinShouldMatch,
        bm25_use_phrase: bm25UsePhrase,
        bm25_analyzer: bm25Analyzer,
        structure_requests_per_minute: structureRequestsPerMinute,
        use_llm_chat_titles: useLlmChatTitles,
      })

      setSuccess('Query defaults saved successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveKBDefaults = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      await apiClient.updateAppSettings({
        kb_chunk_size: kbChunkSize,
        kb_chunk_overlap: kbChunkOverlap,
        kb_upsert_batch_size: kbUpsertBatchSize,
      })

      setSuccess('KB defaults saved successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const refreshPromptVersions = async () => {
    try {
      setPromptsLoading(true)
      const prompts = await apiClient.listPromptVersions()
      setPromptVersions(prompts)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompt versions')
    } finally {
      setPromptsLoading(false)
    }
  }

  const refreshSelfCheckPromptVersions = async () => {
    try {
      setSelfCheckPromptsLoading(true)
      const prompts = await apiClient.listSelfCheckPromptVersions()
      setSelfCheckPromptVersions(prompts)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load self-check prompt versions')
    } finally {
      setSelfCheckPromptsLoading(false)
    }
  }

  const handleSavePromptDraft = async (activate: boolean) => {
    if (!promptDraftSystemContent.trim()) {
      setError('System prompt content is required')
      return
    }

    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      const created = await apiClient.createPromptVersion({
        name: promptDraftName?.trim() || null,
        system_content: promptDraftSystemContent,
        activate,
      })

      if (activate) {
        setActivePromptVersionId(created.id)
      }

      setPromptDraftName('')
      setPromptDraftSystemContent('')
      await refreshPromptVersions()
      setPromptSelected(created)
      setSuccess(activate ? 'Prompt activated successfully!' : 'Prompt draft saved successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save prompt')
    } finally {
      setSaving(false)
    }
  }

  const handleActivatePromptVersion = async (promptId: string) => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)
      const activated = await apiClient.activatePromptVersion(promptId)
      setActivePromptVersionId(activated.id)
      setPromptSelected(activated)
      await refreshPromptVersions()
      setSuccess('Prompt version activated')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate prompt')
    } finally {
      setSaving(false)
    }
  }

  const handleSelectPromptVersion = async (promptId: string) => {
    try {
      setPromptsLoading(true)
      const prompt = await apiClient.getPromptVersion(promptId)
      setPromptSelected(prompt)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompt')
    } finally {
      setPromptsLoading(false)
    }
  }

  const handleLoadPromptToEditor = (prompt: PromptVersionDetail) => {
    setPromptDraftName(prompt.name || '')
    setPromptDraftSystemContent(prompt.system_content)
  }

  const handleSavePromptDisplaySettings = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)
      await apiClient.updateAppSettings({
        show_prompt_versions: showPromptVersions,
      })
      setSuccess('Prompt display settings saved')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save prompt settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveSelfCheckPromptDraft = async (activate: boolean) => {
    if (!selfCheckPromptDraftSystemContent.trim()) {
      setError('System prompt content is required')
      return
    }

    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      const created = await apiClient.createSelfCheckPromptVersion({
        name: selfCheckPromptDraftName?.trim() || null,
        system_content: selfCheckPromptDraftSystemContent,
        activate,
      })

      if (activate) {
        setActiveSelfCheckPromptVersionId(created.id)
      }

      setSelfCheckPromptDraftName('')
      setSelfCheckPromptDraftSystemContent('')
      await refreshSelfCheckPromptVersions()
      setSelfCheckPromptSelected(created)
      setSuccess(activate ? 'Self-check prompt activated successfully!' : 'Self-check prompt draft saved successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save self-check prompt')
    } finally {
      setSaving(false)
    }
  }

  const handleActivateSelfCheckPromptVersion = async (promptId: string) => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)
      const activated = await apiClient.activateSelfCheckPromptVersion(promptId)
      setActiveSelfCheckPromptVersionId(activated.id)
      setSelfCheckPromptSelected(activated)
      await refreshSelfCheckPromptVersions()
      setSuccess('Self-check prompt activated')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate self-check prompt')
    } finally {
      setSaving(false)
    }
  }

  const handleSelectSelfCheckPromptVersion = async (promptId: string) => {
    try {
      setSelfCheckPromptsLoading(true)
      const prompt = await apiClient.getSelfCheckPromptVersion(promptId)
      setSelfCheckPromptSelected(prompt)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load self-check prompt')
    } finally {
      setSelfCheckPromptsLoading(false)
    }
  }

  const handleLoadSelfCheckPromptToEditor = (prompt: SelfCheckPromptVersionDetail) => {
    setSelfCheckPromptDraftName(prompt.name || '')
    setSelfCheckPromptDraftSystemContent(prompt.system_content)
  }

  const handleSaveAIProviders = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      const payload: any = {}

      // Only send values that were changed (not masked)
      if (openaiApiKey && !openaiApiKey.startsWith('*')) payload.openai_api_key = openaiApiKey
      if (voyageApiKey && !voyageApiKey.startsWith('*')) payload.voyage_api_key = voyageApiKey
      if (anthropicApiKey && !anthropicApiKey.startsWith('*')) payload.anthropic_api_key = anthropicApiKey
      if (deepseekApiKey && !deepseekApiKey.startsWith('*')) payload.deepseek_api_key = deepseekApiKey
      if (ollamaBaseUrl) payload.ollama_base_url = ollamaBaseUrl
      if (systemName) payload.system_name = systemName
      if (maxFileSizeMb) payload.max_file_size_mb = maxFileSizeMb

      if (Object.keys(payload).length === 0) {
        setError('No changes to save')
        setSaving(false)
        return
      }

      await apiClient.updateSystemSettings(payload)

      setSuccess('AI provider settings saved successfully!')
      setTimeout(() => setSuccess(null), 3000)

      // Reload to get masked values
      await loadAllSettings()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveDatabases = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      const payload: any = {}

      if (qdrantUrl) payload.qdrant_url = qdrantUrl
      if (qdrantApiKey && !qdrantApiKey.startsWith('*')) payload.qdrant_api_key = qdrantApiKey
      if (opensearchUrl) payload.opensearch_url = opensearchUrl
      if (opensearchUsername) payload.opensearch_username = opensearchUsername
      if (opensearchPassword && !opensearchPassword.startsWith('*')) payload.opensearch_password = opensearchPassword

      if (Object.keys(payload).length === 0) {
        setError('No changes to save')
        setSaving(false)
        return
      }

      await apiClient.updateSystemSettings(payload)

      setSuccess('Database settings saved successfully!')
      setTimeout(() => setSuccess(null), 3000)

      // Reload to get masked values
      await loadAllSettings()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleChangePostgresPassword = async () => {
    if (!postgresNewPassword || postgresNewPassword.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    if (!confirm('Are you sure you want to change PostgreSQL password? This will restart the database connection.')) {
      return
    }

    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      await apiClient.changePostgresPassword(postgresUsername, postgresNewPassword)

      setSuccess('PostgreSQL password changed successfully! Connection pool recreated.')
      setPostgresNewPassword('')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to change PostgreSQL password')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8 pb-4 border-b border-gray-700">
          <h1 className="text-3xl font-bold text-white">Settings</h1>
        </div>
        <div className="text-center py-12 text-gray-400">
          Loading settings...
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8 pb-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-white">Settings</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors text-sm"
            >
              ← Back to Dashboard
            </button>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors text-sm"
            >
              Logout
            </button>
          </div>
        </div>
        <p className="text-gray-400">Configure system settings and defaults</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-gray-700 mb-6 overflow-x-auto">
        <button
          onClick={() => setActiveTab('query')}
          className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === 'query'
              ? 'border-primary-500 text-primary-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          Query Defaults
        </button>
        <button
          onClick={() => setActiveTab('kb-defaults')}
          className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === 'kb-defaults'
              ? 'border-primary-500 text-primary-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          KB Defaults
        </button>
        <button
          onClick={() => setActiveTab('ai-providers')}
          className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === 'ai-providers'
              ? 'border-primary-500 text-primary-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          AI Providers
        </button>
        <button
          onClick={() => setActiveTab('databases')}
          className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === 'databases'
              ? 'border-primary-500 text-primary-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          Databases
        </button>
        <button
          onClick={() => setActiveTab('prompts')}
          className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === 'prompts'
              ? 'border-primary-500 text-primary-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          Prompts
        </button>
        <button
          onClick={() => setActiveTab('kb-transfer')}
          className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === 'kb-transfer'
              ? 'border-primary-500 text-primary-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          KB Transfer
        </button>
        <button
          onClick={() => setActiveTab('mcp')}
          className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === 'mcp'
              ? 'border-primary-500 text-primary-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
          }`}
        >
          MCP
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500 rounded-lg text-red-200">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-6 p-4 bg-green-500/10 border border-green-500 rounded-lg text-green-200">
          {success}
        </div>
      )}

      {/* Tab Content */}
      <div>
        {activeTab === 'query' && (
          <QueryDefaultsTab
            llmModel={llmModel}
            setLlmModel={setLlmModel}
            llmProvider={llmProvider}
            setLlmProvider={setLlmProvider}
            temperature={temperature}
            setTemperature={setTemperature}
            topK={topK}
            setTopK={setTopK}
            maxContextChars={maxContextChars}
            setMaxContextChars={setMaxContextChars}
            scoreThreshold={scoreThreshold}
            setScoreThreshold={setScoreThreshold}
            retrievalMode={retrievalMode}
            setRetrievalMode={setRetrievalMode}
            lexicalTopK={lexicalTopK}
            setLexicalTopK={setLexicalTopK}
            hybridDenseWeight={hybridDenseWeight}
            setHybridDenseWeight={setHybridDenseWeight}
            hybridLexicalWeight={hybridLexicalWeight}
            setHybridLexicalWeight={setHybridLexicalWeight}
            linkHybridWeights={linkHybridWeights}
            setLinkHybridWeights={setLinkHybridWeights}
            handleDenseWeightChange={handleDenseWeightChange}
            handleLexicalWeightChange={handleLexicalWeightChange}
            bm25MatchMode={bm25MatchMode}
            setBm25MatchMode={setBm25MatchMode}
            bm25MinShouldMatch={bm25MinShouldMatch}
            setBm25MinShouldMatch={setBm25MinShouldMatch}
            bm25UsePhrase={bm25UsePhrase}
            setBm25UsePhrase={setBm25UsePhrase}
            bm25Analyzer={bm25Analyzer}
            setBm25Analyzer={setBm25Analyzer}
            useStructure={useStructure}
            setUseStructure={setUseStructure}
            structureRequestsPerMinute={structureRequestsPerMinute}
            setStructureRequestsPerMinute={setStructureRequestsPerMinute}
            useLlmChatTitles={useLlmChatTitles}
            setUseLlmChatTitles={setUseLlmChatTitles}
            opensearchAvailable={opensearchAvailable}
            onSave={handleSaveQueryDefaults}
            saving={saving}
          />
        )}

        {activeTab === 'kb-defaults' && (
          <KBDefaultsTab
            kbChunkSize={kbChunkSize}
            setKbChunkSize={setKbChunkSize}
            kbChunkOverlap={kbChunkOverlap}
            setKbChunkOverlap={setKbChunkOverlap}
            kbUpsertBatchSize={kbUpsertBatchSize}
            setKbUpsertBatchSize={setKbUpsertBatchSize}
            onSave={handleSaveKBDefaults}
            saving={saving}
          />
        )}

        {activeTab === 'ai-providers' && (
          <AIProvidersTab
            openaiApiKey={openaiApiKey}
            setOpenaiApiKey={setOpenaiApiKey}
            showOpenaiKey={showOpenaiKey}
            setShowOpenaiKey={setShowOpenaiKey}
            voyageApiKey={voyageApiKey}
            setVoyageApiKey={setVoyageApiKey}
            showVoyageKey={showVoyageKey}
            setShowVoyageKey={setShowVoyageKey}
            anthropicApiKey={anthropicApiKey}
            setAnthropicApiKey={setAnthropicApiKey}
            showAnthropicKey={showAnthropicKey}
            setShowAnthropicKey={setShowAnthropicKey}
            deepseekApiKey={deepseekApiKey}
            setDeepseekApiKey={setDeepseekApiKey}
            showDeepseekKey={showDeepseekKey}
            setShowDeepseekKey={setShowDeepseekKey}
            ollamaBaseUrl={ollamaBaseUrl}
            setOllamaBaseUrl={setOllamaBaseUrl}
            systemName={systemName}
            setSystemName={setSystemName}
            maxFileSizeMb={maxFileSizeMb}
            setMaxFileSizeMb={setMaxFileSizeMb}
            onSave={handleSaveAIProviders}
            saving={saving}
          />
        )}

        {activeTab === 'databases' && (
          <DatabasesTab
            qdrantUrl={qdrantUrl}
            setQdrantUrl={setQdrantUrl}
            qdrantApiKey={qdrantApiKey}
            setQdrantApiKey={setQdrantApiKey}
            showQdrantKey={showQdrantKey}
            setShowQdrantKey={setShowQdrantKey}
            opensearchUrl={opensearchUrl}
            setOpensearchUrl={setOpensearchUrl}
            opensearchUsername={opensearchUsername}
            setOpensearchUsername={setOpensearchUsername}
            opensearchPassword={opensearchPassword}
            setOpensearchPassword={setOpensearchPassword}
            showOpensearchPassword={showOpensearchPassword}
            setShowOpensearchPassword={setShowOpensearchPassword}
            postgresUsername={postgresUsername}
            setPostgresUsername={setPostgresUsername}
            postgresNewPassword={postgresNewPassword}
            setPostgresNewPassword={setPostgresNewPassword}
            onSave={handleSaveDatabases}
            onChangePostgresPassword={handleChangePostgresPassword}
            saving={saving}
          />
        )}

        {activeTab === 'prompts' && (
          <PromptsTab
            promptVersions={promptVersions}
            promptsLoading={promptsLoading}
            activePromptVersionId={activePromptVersionId}
            promptSelected={promptSelected}
            promptDraftName={promptDraftName}
            setPromptDraftName={setPromptDraftName}
            promptDraftSystemContent={promptDraftSystemContent}
            setPromptDraftSystemContent={setPromptDraftSystemContent}
            selfCheckPromptVersions={selfCheckPromptVersions}
            selfCheckPromptsLoading={selfCheckPromptsLoading}
            activeSelfCheckPromptVersionId={activeSelfCheckPromptVersionId}
            selfCheckPromptSelected={selfCheckPromptSelected}
            selfCheckPromptDraftName={selfCheckPromptDraftName}
            setSelfCheckPromptDraftName={setSelfCheckPromptDraftName}
            selfCheckPromptDraftSystemContent={selfCheckPromptDraftSystemContent}
            setSelfCheckPromptDraftSystemContent={setSelfCheckPromptDraftSystemContent}
            showPromptVersions={showPromptVersions}
            setShowPromptVersions={setShowPromptVersions}
            onRefreshPrompts={refreshPromptVersions}
            onSelectPrompt={handleSelectPromptVersion}
            onActivatePrompt={handleActivatePromptVersion}
            onSaveDraft={() => handleSavePromptDraft(false)}
            onActivateDraft={() => handleSavePromptDraft(true)}
            onSaveDisplaySettings={handleSavePromptDisplaySettings}
            onLoadToEditor={handleLoadPromptToEditor}
            onRefreshSelfCheckPrompts={refreshSelfCheckPromptVersions}
            onSelectSelfCheckPrompt={handleSelectSelfCheckPromptVersion}
            onActivateSelfCheckPrompt={handleActivateSelfCheckPromptVersion}
            onSaveSelfCheckDraft={() => handleSaveSelfCheckPromptDraft(false)}
            onActivateSelfCheckDraft={() => handleSaveSelfCheckPromptDraft(true)}
            onLoadSelfCheckToEditor={handleLoadSelfCheckPromptToEditor}
            saving={saving}
          />
        )}

        {activeTab === 'kb-transfer' && (
          <KBTransferTab
            kbList={kbList}
            kbTransferLoading={kbTransferLoading}
            kbSelection={kbSelection}
            toggleKbSelection={toggleKbSelection}
            exportInclude={exportInclude}
            setExportInclude={setExportInclude}
            importInclude={importInclude}
            setImportInclude={setImportInclude}
            importMode={importMode}
            setImportMode={setImportMode}
            remapIds={remapIds}
            setRemapIds={setRemapIds}
            targetKbId={targetKbId}
            setTargetKbId={setTargetKbId}
            importFile={importFile}
            setImportFile={setImportFile}
            onExport={handleExportKbs}
            onExportChatsMarkdown={handleExportChatsMarkdown}
            onImport={handleImportKbs}
            exporting={exportingKbArchive}
            exportingChatsMd={exportingChatsMd}
            importing={importingKbArchive}
          />
        )}

        {activeTab === 'mcp' && (
            <MCPSettingsTab
              mcpEnabled={mcpEnabled}
              setMcpEnabled={setMcpEnabled}
              mcpPath={mcpPath}
              setMcpPath={setMcpPath}
              mcpPublicBaseUrl={mcpPublicBaseUrl}
              setMcpPublicBaseUrl={setMcpPublicBaseUrl}
              mcpDefaultKbId={mcpDefaultKbId}
              setMcpDefaultKbId={setMcpDefaultKbId}
              mcpToolsEnabled={mcpToolsEnabled}
              setMcpToolsEnabled={setMcpToolsEnabled}
              mcpAuthMode={mcpAuthMode}
              setMcpAuthMode={setMcpAuthMode}
              mcpTokens={mcpTokens}
              mcpTokenName={mcpTokenName}
              setMcpTokenName={setMcpTokenName}
            mcpTokenTTL={mcpTokenTTL}
            setMcpTokenTTL={setMcpTokenTTL}
            mcpCreatedToken={mcpCreatedToken}
            setMcpCreatedToken={setMcpCreatedToken}
            mcpAccessTokenTtlMinutes={mcpAccessTokenTtlMinutes}
            setMcpAccessTokenTtlMinutes={setMcpAccessTokenTtlMinutes}
            mcpRefreshTokenTtlDays={mcpRefreshTokenTtlDays}
            setMcpRefreshTokenTtlDays={setMcpRefreshTokenTtlDays}
            mcpRefreshTokens={mcpRefreshTokens}
            mcpOAuthUsername={mcpOAuthUsername}
            setMcpOAuthUsername={setMcpOAuthUsername}
            mcpOAuthPassword={mcpOAuthPassword}
            setMcpOAuthPassword={setMcpOAuthPassword}
            mcpOAuthIssued={mcpOAuthIssued}
            setMcpOAuthIssued={setMcpOAuthIssued}
            onSave={handleSaveMcpSettings}
            onCreateToken={handleCreateMcpToken}
            onRevokeToken={handleRevokeMcpToken}
            onDeleteToken={handleDeleteMcpToken}
            onIssueOAuthToken={handleIssueOAuthToken}
            onRevokeRefreshToken={handleRevokeRefreshToken}
            saving={saving}
            oauthLoading={mcpOAuthLoading}
            mcpOAuthEvents={mcpOAuthEvents}
            mcpOAuthEventsLimit={mcpOAuthEventsLimit}
            setMcpOAuthEventsLimit={setMcpOAuthEventsLimit}
            mcpOAuthEventsFilter={mcpOAuthEventsFilter}
            setMcpOAuthEventsFilter={setMcpOAuthEventsFilter}
            onRefreshOAuthEvents={loadMcpOAuthEvents}
          />
        )}
      </div>
    </div>
  )
}

// Tab Components
type KBTransferTabProps = {
  kbList: KnowledgeBase[]
  kbTransferLoading: boolean
  kbSelection: string[]
  toggleKbSelection: (id: string) => void
  exportInclude: {
    documents: boolean
    vectors: boolean
    bm25: boolean
    uploads: boolean
    chats: boolean
  }
  setExportInclude: React.Dispatch<React.SetStateAction<{
    documents: boolean
    vectors: boolean
    bm25: boolean
    uploads: boolean
    chats: boolean
  }>>
  importInclude: {
    documents: boolean
    vectors: boolean
    bm25: boolean
    uploads: boolean
    chats: boolean
  }
  setImportInclude: React.Dispatch<React.SetStateAction<{
    documents: boolean
    vectors: boolean
    bm25: boolean
    uploads: boolean
    chats: boolean
  }>>
  importMode: 'create' | 'merge'
  setImportMode: (value: 'create' | 'merge') => void
  remapIds: boolean
  setRemapIds: (value: boolean) => void
  targetKbId: string
  setTargetKbId: (value: string) => void
  importFile: File | null
  setImportFile: (file: File | null) => void
  onExport: () => void
  onExportChatsMarkdown: () => void
  onImport: () => void
  exporting: boolean
  exportingChatsMd: boolean
  importing: boolean
}

type MCPSettingsTabProps = {
  mcpEnabled: boolean
  setMcpEnabled: (value: boolean) => void
  mcpPath: string
  setMcpPath: (value: string) => void
  mcpPublicBaseUrl: string
  setMcpPublicBaseUrl: (value: string) => void
  mcpDefaultKbId: string
  setMcpDefaultKbId: (value: string) => void
  mcpToolsEnabled: string[]
  setMcpToolsEnabled: (value: string[]) => void
  mcpAuthMode: 'bearer' | 'refresh' | 'oauth2'
  setMcpAuthMode: (value: 'bearer' | 'refresh' | 'oauth2') => void
  mcpTokens: MCPToken[]
  mcpTokenName: string
  setMcpTokenName: (value: string) => void
  mcpTokenTTL: number | ''
  setMcpTokenTTL: (value: number | '') => void
  mcpCreatedToken: string | null
  setMcpCreatedToken: (value: string | null) => void
  mcpAccessTokenTtlMinutes: number | ''
  setMcpAccessTokenTtlMinutes: (value: number | '') => void
  mcpRefreshTokenTtlDays: number | ''
  setMcpRefreshTokenTtlDays: (value: number | '') => void
  mcpRefreshTokens: MCPRefreshToken[]
  mcpOAuthUsername: string
  setMcpOAuthUsername: (value: string) => void
  mcpOAuthPassword: string
  setMcpOAuthPassword: (value: string) => void
  mcpOAuthIssued: OAuthTokenResponse | null
  setMcpOAuthIssued: (value: OAuthTokenResponse | null) => void
  mcpOAuthEvents: MCPOAuthEvent[]
  mcpOAuthEventsLimit: number
  setMcpOAuthEventsLimit: (value: number) => void
  mcpOAuthEventsFilter: string
  setMcpOAuthEventsFilter: (value: string) => void
  onRefreshOAuthEvents: () => void
  onSave: () => void
  onCreateToken: () => void
  onRevokeToken: (tokenId: string) => void
  onDeleteToken: (tokenId: string) => void
  onIssueOAuthToken: () => void
  onRevokeRefreshToken: (jti: string) => void
  saving: boolean
  oauthLoading: boolean
}

function MCPSettingsTab(props: MCPSettingsTabProps) {
  const {
    mcpEnabled,
    setMcpEnabled,
    mcpPath,
    setMcpPath,
    mcpPublicBaseUrl,
    setMcpPublicBaseUrl,
    mcpDefaultKbId,
    setMcpDefaultKbId,
    mcpToolsEnabled,
    setMcpToolsEnabled,
    mcpAuthMode,
    setMcpAuthMode,
    mcpTokens,
    mcpTokenName,
    setMcpTokenName,
    mcpTokenTTL,
    setMcpTokenTTL,
    mcpCreatedToken,
    setMcpCreatedToken,
    mcpAccessTokenTtlMinutes,
    setMcpAccessTokenTtlMinutes,
    mcpRefreshTokenTtlDays,
    setMcpRefreshTokenTtlDays,
    mcpRefreshTokens,
    mcpOAuthUsername,
    setMcpOAuthUsername,
    mcpOAuthPassword,
    setMcpOAuthPassword,
    mcpOAuthIssued,
    setMcpOAuthIssued,
    mcpOAuthEvents,
    mcpOAuthEventsLimit,
    setMcpOAuthEventsLimit,
    mcpOAuthEventsFilter,
    setMcpOAuthEventsFilter,
    onRefreshOAuthEvents,
    onSave,
    onCreateToken,
    onRevokeToken,
    onDeleteToken,
    onIssueOAuthToken,
    onRevokeRefreshToken,
    saving,
    oauthLoading,
  } = props
  const [copySuccess, setCopySuccess] = useState<string | null>(null)

  const endpointProxy = `${window.location.origin}${mcpPath.startsWith('/') ? mcpPath : `/${mcpPath}`}`
  const mcpPathNormalized = mcpPath.startsWith('/') ? mcpPath : `/${mcpPath}`
  let normalizedBaseUrl = mcpPublicBaseUrl.trim().replace(/\/$/, '')
  if (normalizedBaseUrl.endsWith(mcpPathNormalized)) {
    normalizedBaseUrl = normalizedBaseUrl.slice(0, -mcpPathNormalized.length).replace(/\/$/, '')
  }

  const toggleTool = (toolId: string) => {
    if (mcpToolsEnabled.includes(toolId)) {
      setMcpToolsEnabled(mcpToolsEnabled.filter((t) => t !== toolId))
    } else {
      setMcpToolsEnabled([...mcpToolsEnabled, toolId])
    }
  }

  const handleCopyToken = async () => {
    if (!mcpCreatedToken) return
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(mcpCreatedToken)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = mcpCreatedToken
        textarea.style.position = 'fixed'
        textarea.style.top = '0'
        textarea.style.left = '0'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      setCopySuccess('Copied')
      setTimeout(() => setCopySuccess(null), 2000)
    } catch {
      setCopySuccess('Copy failed')
      setTimeout(() => setCopySuccess(null), 2000)
    }
  }

  const handleCopyValue = async (value: string) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = value
        textarea.style.position = 'fixed'
        textarea.style.top = '0'
        textarea.style.left = '0'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      setCopySuccess('Copied')
      setTimeout(() => setCopySuccess(null), 2000)
    } catch {
      setCopySuccess('Copy failed')
      setTimeout(() => setCopySuccess(null), 2000)
    }
  }

  const formatDateTime = (value?: string | null) => {
    if (!value) return '—'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString()
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">MCP</h2>
        <p className="text-gray-400">Expose RAG as a FastMCP server for AuthMCP Gateway</p>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 space-y-4">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={mcpEnabled}
            onChange={(e) => setMcpEnabled(e.target.checked)}
          />
          <span className="text-gray-200">Enable MCP endpoint</span>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">MCP Endpoint Path</label>
          <input
            type="text"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            value={mcpPath}
            onChange={(e) => setMcpPath(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">Changing this requires server restart</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Public API Base URL</label>
          <input
            type="text"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="https://rag.example.com"
            value={mcpPublicBaseUrl}
            onChange={(e) => setMcpPublicBaseUrl(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">
            Used for OAuth metadata and endpoint display. Leave empty to rely on proxy URL.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Default KB ID (Optional)</label>
          <input
            type="text"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="UUID"
            value={mcpDefaultKbId}
            onChange={(e) => setMcpDefaultKbId(e.target.value)}
          />
        </div>

        <div className="text-sm text-gray-300 space-y-1">
          {normalizedBaseUrl && (
            <div>
              MCP endpoint:{' '}
              <span className="text-gray-100">
                {`${normalizedBaseUrl}${mcpPath.startsWith('/') ? mcpPath : `/${mcpPath}`}`}
              </span>
            </div>
          )}
          <div>
            Proxy endpoint:{' '}
            <span className="text-gray-100">{endpointProxy}</span>
          </div>
        </div>

        <div className="pt-2 space-y-2">
          <div className="text-sm font-medium text-gray-300">MCP Auth Mode</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { value: 'bearer', label: 'Bearer', help: 'Static MCP tokens (AuthMCP).' },
              { value: 'refresh', label: 'Refresh Token', help: 'Access + refresh tokens (AuthMCP).' },
              { value: 'oauth2', label: 'OAuth2 PKCE', help: 'Direct clients with authorization code flow.' },
            ].map((mode) => (
              <label key={mode.value} className="flex items-start gap-2 text-gray-300">
                <input
                  type="radio"
                  name="mcpAuthMode"
                  value={mode.value}
                  checked={mcpAuthMode === mode.value}
                  onChange={() => setMcpAuthMode(mode.value as 'bearer' | 'refresh' | 'oauth2')}
                />
                <span className="flex flex-col">
                  <span className="font-medium">{mode.label}</span>
                  <span className="text-xs text-gray-400">{mode.help}</span>
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex justify-end">
          <Button variant="primary" onClick={onSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save MCP Settings'}
          </Button>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 space-y-3">
        <h3 className="text-lg font-semibold text-gray-100">Available Tools</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {MCP_TOOL_OPTIONS.map((tool) => (
            <label key={tool.id} className="flex items-start gap-2 text-gray-300" title={tool.description}>
              <input
                type="checkbox"
                checked={mcpToolsEnabled.includes(tool.id)}
                onChange={() => toggleTool(tool.id)}
              />
              <span className="flex flex-col">
                <span>{tool.label}</span>
                <span className="text-xs text-gray-400">{tool.description}</span>
              </span>
            </label>
          ))}
        </div>
      </div>

      {mcpAuthMode === 'bearer' && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 space-y-4">
          <h3 className="text-lg font-semibold text-gray-100">MCP Tokens</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            type="text"
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="Token name"
            value={mcpTokenName}
            onChange={(e) => setMcpTokenName(e.target.value)}
          />
          <input
            type="number"
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="TTL days (optional)"
            value={mcpTokenTTL}
            onChange={(e) => setMcpTokenTTL(e.target.value === '' ? '' : Number(e.target.value))}
          />
          <Button variant="primary" onClick={onCreateToken} disabled={saving}>
            {saving ? 'Creating...' : 'Create Token'}
          </Button>
        </div>

        {mcpCreatedToken && (
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
            <div className="text-sm text-gray-300 mb-2">Token (shown once)</div>
            <div className="font-mono text-sm text-gray-100 break-all">{mcpCreatedToken}</div>
            <div className="mt-3 flex gap-2">
              <Button variant="secondary" onClick={handleCopyToken}>Copy</Button>
              {copySuccess && <span className="text-xs text-gray-400 self-center">{copySuccess}</span>}
              <Button variant="secondary" onClick={() => setMcpCreatedToken(null)}>Dismiss</Button>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {mcpTokens.length === 0 && (
            <div className="text-sm text-gray-400">No tokens yet</div>
          )}
          {mcpTokens.map((token) => (
            <div key={token.id} className="flex items-center justify-between bg-gray-900 rounded-lg p-3 border border-gray-700">
              <div className="text-sm text-gray-200">
                <div className="font-mono">prefix: {token.token_prefix}</div>
                <div className="text-gray-400">{token.name || 'Unnamed token'}</div>
                {token.expires_at && <div className="text-gray-400">expires: {formatDateTime(token.expires_at)}</div>}
                {token.revoked_at && <div className="text-red-300">revoked: {formatDateTime(token.revoked_at)}</div>}
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => onRevokeToken(token.id)} disabled={saving}>
                  Revoke
                </Button>
                <Button variant="secondary" onClick={() => onDeleteToken(token.id)} disabled={saving}>
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
        </div>
      )}

      {mcpAuthMode === 'refresh' && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-100">OAuth (Gateway)</h3>
          <p className="text-sm text-gray-400">
            Issue access + refresh tokens for AuthMCP Gateway using an admin account.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Access TTL (minutes)</label>
            <input
              type="number"
              min={1}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="e.g. 30"
              value={mcpAccessTokenTtlMinutes}
              onChange={(e) => setMcpAccessTokenTtlMinutes(e.target.value === '' ? '' : Number(e.target.value))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Refresh TTL (days)</label>
            <input
              type="number"
              min={1}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="e.g. 30"
              value={mcpRefreshTokenTtlDays}
              onChange={(e) => setMcpRefreshTokenTtlDays(e.target.value === '' ? '' : Number(e.target.value))}
            />
          </div>
        </div>
        <p className="text-xs text-gray-400">
          Applies to newly issued OAuth tokens. Save with <span className="text-gray-200">Save MCP Settings</span> above.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            type="text"
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="Admin username"
            value={mcpOAuthUsername}
            onChange={(e) => setMcpOAuthUsername(e.target.value)}
          />
          <input
            type="password"
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="Admin password"
            value={mcpOAuthPassword}
            onChange={(e) => setMcpOAuthPassword(e.target.value)}
          />
          <Button variant="primary" onClick={onIssueOAuthToken} disabled={oauthLoading}>
            {oauthLoading ? 'Issuing...' : 'Issue OAuth Tokens'}
          </Button>
        </div>

        {mcpOAuthIssued && (
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-700 space-y-3">
            <div className="text-sm text-gray-300">
              Access token (expires in {mcpOAuthIssued.expires_in}s)
            </div>
            <div className="font-mono text-xs text-gray-100 break-all">{mcpOAuthIssued.access_token}</div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => handleCopyValue(mcpOAuthIssued.access_token)}>
                Copy access
              </Button>
              {copySuccess && <span className="text-xs text-gray-400 self-center">{copySuccess}</span>}
            </div>
            {mcpOAuthIssued.refresh_token && (
              <>
                <div className="text-sm text-gray-300">Refresh token</div>
                <div className="font-mono text-xs text-gray-100 break-all">{mcpOAuthIssued.refresh_token}</div>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => handleCopyValue(mcpOAuthIssued.refresh_token || '')}>
                    Copy refresh
                  </Button>
                </div>
              </>
            )}
          </div>
        )}

        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-200">Refresh Tokens</div>
          {mcpRefreshTokens.length === 0 && (
            <div className="text-sm text-gray-400">No refresh tokens yet</div>
          )}
          {mcpRefreshTokens.map((token) => (
            <div key={token.jti} className="flex items-center justify-between bg-gray-900 rounded-lg p-3 border border-gray-700">
              <div className="text-sm text-gray-200">
                <div className="font-mono">jti: {token.jti}</div>
                <div className="text-gray-400">admin: {token.admin_username}</div>
                <div className="text-gray-400">created: {formatDateTime(token.created_at)}</div>
                <div className="text-gray-400">expires: {formatDateTime(token.expires_at)}</div>
                {token.revoked_at && <div className="text-red-300">revoked: {formatDateTime(token.revoked_at)}</div>}
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => onRevokeRefreshToken(token.jti)} disabled={saving}>
                  Revoke
                </Button>
              </div>
            </div>
          ))}
        </div>
        </div>
      )}

      {mcpAuthMode === 'oauth2' && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 space-y-3">
          <h3 className="text-lg font-semibold text-gray-100">OAuth2 (PKCE)</h3>
          <p className="text-sm text-gray-400">
            Direct clients use Authorization Code + PKCE to obtain access tokens.
          </p>
          <div className="text-sm text-gray-300 space-y-1">
            {normalizedBaseUrl && (
              <div>
                Authorize URL:{' '}
                <span className="text-gray-100">{`${normalizedBaseUrl}/authorize`}</span>
              </div>
            )}
            {normalizedBaseUrl && (
              <div>
                Token URL:{' '}
                <span className="text-gray-100">{`${normalizedBaseUrl}/token`}</span>
              </div>
            )}
            {!normalizedBaseUrl && (
              <div className="text-gray-400">
                Set Public API Base URL to show OAuth endpoints.
              </div>
            )}
          </div>
        </div>
      )}

      {mcpAuthMode !== 'bearer' && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 space-y-3">
          <div>
            <h3 className="text-lg font-semibold text-gray-100">Recent OAuth Events</h3>
            <p className="text-sm text-gray-400">Last successful OAuth activity.</p>
          </div>
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Filter</label>
              <select
                className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                value={mcpOAuthEventsFilter}
                onChange={(e) => setMcpOAuthEventsFilter(e.target.value)}
              >
                <option value="all">All</option>
                <option value="authorize">authorize</option>
                <option value="token">token</option>
                <option value="refresh">refresh</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Limit</label>
              <select
                className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                value={mcpOAuthEventsLimit}
                onChange={(e) => setMcpOAuthEventsLimit(Number(e.target.value))}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
            <Button variant="secondary" onClick={onRefreshOAuthEvents}>
              Refresh
            </Button>
          </div>
          {mcpOAuthEvents.length === 0 && (
            <div className="text-sm text-gray-400">No OAuth events recorded yet.</div>
          )}
          {mcpOAuthEvents.length > 0 && (
            <div className="space-y-2">
              {mcpOAuthEvents
                .filter((event) => mcpOAuthEventsFilter === 'all' || event.event_type === mcpOAuthEventsFilter)
                .map((event) => (
                <div key={event.id} className="bg-gray-900 rounded-lg p-3 border border-gray-700 text-sm text-gray-200">
                  <div className="flex flex-wrap gap-2 text-gray-300">
                    <span className="font-semibold">{event.event_type}</span>
                    {event.admin_username && <span>admin: {event.admin_username}</span>}
                    {event.client_id && <span>client: {event.client_id}</span>}
                    {event.ip_address && <span>ip: {event.ip_address}</span>}
                  </div>
                  <div className="text-gray-400">time: {formatDateTime(event.created_at)}</div>
                  {event.user_agent && (
                    <div className="text-gray-500 break-words">ua: {event.user_agent}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const KBTransferTab: React.FC<KBTransferTabProps> = ({
  kbList,
  kbTransferLoading,
  kbSelection,
  toggleKbSelection,
  exportInclude,
  setExportInclude,
  importInclude,
  setImportInclude,
  importMode,
  setImportMode,
  remapIds,
  setRemapIds,
  targetKbId,
  setTargetKbId,
  importFile,
  setImportFile,
  onExport,
  onExportChatsMarkdown,
  onImport,
  exporting,
  exportingChatsMd,
  importing,
}) => {
  return (
    <div className="space-y-8">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-2">Export Knowledge Bases</h3>
        <p className="text-sm text-gray-400 mb-4">
          Select one or more KBs and export a portable archive.
        </p>

        <div className="mb-4">
          <div className="text-sm text-gray-300 mb-2">Knowledge Bases</div>
          <div className="max-h-48 overflow-y-auto border border-gray-700 rounded-md p-3">
            {kbTransferLoading && (
              <div className="text-gray-400 text-sm">Loading knowledge bases...</div>
            )}
            {!kbTransferLoading && kbList.length === 0 && (
              <div className="text-gray-400 text-sm">No knowledge bases found.</div>
            )}
            {!kbTransferLoading && kbList.length > 0 && (
              <div className="space-y-2">
                {kbList.map((kb) => (
                  <label key={kb.id} className="flex items-center gap-2 text-sm text-gray-200">
                    <input
                      type="checkbox"
                      checked={kbSelection.includes(kb.id)}
                      onChange={() => toggleKbSelection(kb.id)}
                      className="rounded border-gray-600 bg-gray-900"
                    />
                    <span>{kb.name}</span>
                    <span className="text-gray-500 text-xs">{kb.id}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={exportInclude.documents}
              onChange={(e) => setExportInclude({ ...exportInclude, documents: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Documents</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={exportInclude.vectors}
              onChange={(e) => setExportInclude({ ...exportInclude, vectors: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Qdrant Vectors</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={exportInclude.bm25}
              onChange={(e) => setExportInclude({ ...exportInclude, bm25: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>OpenSearch BM25</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={exportInclude.uploads}
              onChange={(e) => setExportInclude({ ...exportInclude, uploads: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Uploads (optional)</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={exportInclude.chats}
              onChange={(e) => setExportInclude({ ...exportInclude, chats: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Chats (JSONL)</span>
          </label>
        </div>

        <Button onClick={onExport} disabled={exporting}>
          {exporting ? 'Exporting...' : 'Export Selected KBs'}
        </Button>

        <div className="mt-4 text-sm text-gray-400">
          Markdown export is separate from KB archives.
        </div>
        <div className="mt-3">
          <Button onClick={onExportChatsMarkdown} disabled={exportingChatsMd}>
            {exportingChatsMd ? 'Exporting...' : 'Export Chats (Markdown)'}
          </Button>
        </div>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-2">Import Knowledge Bases</h3>
        <p className="text-sm text-gray-400 mb-4">
          Import a KB archive generated by the export tool.
        </p>

        <div className="mb-4">
          <input
            type="file"
            accept=".tar.gz"
            onChange={(e) => setImportFile(e.target.files?.[0] || null)}
            className="text-sm text-gray-300"
          />
          {importFile && (
            <div className="text-xs text-gray-400 mt-2">{importFile.name}</div>
          )}
        </div>

        <div className="mb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <span>Mode</span>
            <select
              value={importMode}
              onChange={(e) => setImportMode(e.target.value as 'create' | 'merge')}
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm"
            >
              <option value="create">create</option>
              <option value="merge">merge</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={remapIds}
              onChange={(e) => setRemapIds(e.target.checked)}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Remap IDs</span>
          </label>
        </div>

        {importMode === 'merge' && (
          <div className="mb-4">
            <label className="block text-sm text-gray-300 mb-2">Target Knowledge Base</label>
            <select
              value={targetKbId}
              onChange={(e) => setTargetKbId(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-2 text-sm text-gray-200"
            >
              <option value="">Select a KB...</option>
              {kbList.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name} ({kb.id})
                </option>
              ))}
            </select>
            <div className="text-xs text-gray-500 mt-2">
              Merge requires a single-KB archive. The target KB must already exist.
            </div>
          </div>
        )}

        <div className="mb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={importInclude.documents}
              onChange={(e) => setImportInclude({ ...importInclude, documents: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Documents</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={importInclude.vectors}
              onChange={(e) => setImportInclude({ ...importInclude, vectors: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Qdrant Vectors</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={importInclude.bm25}
              onChange={(e) => setImportInclude({ ...importInclude, bm25: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>OpenSearch BM25</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={importInclude.uploads}
              onChange={(e) => setImportInclude({ ...importInclude, uploads: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Uploads (optional)</span>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={importInclude.chats}
              onChange={(e) => setImportInclude({ ...importInclude, chats: e.target.checked })}
              className="rounded border-gray-600 bg-gray-900"
            />
            <span>Chats (JSONL)</span>
          </label>
        </div>

        <Button onClick={onImport} disabled={importing || !importFile}>
          {importing ? 'Importing...' : 'Import KB Archive'}
        </Button>
      </div>
    </div>
  )
}

type QueryDefaultsTabProps = {
  llmModel: string
  setLlmModel: (value: string) => void
  llmProvider: string
  setLlmProvider: (value: string) => void
  temperature: number
  setTemperature: (value: number) => void
  topK: number
  setTopK: (value: number) => void
  maxContextChars: number
  setMaxContextChars: (value: number) => void
  scoreThreshold: number
  setScoreThreshold: (value: number) => void
  retrievalMode: 'dense' | 'hybrid'
  setRetrievalMode: (value: 'dense' | 'hybrid') => void
  lexicalTopK: number
  setLexicalTopK: (value: number) => void
  hybridDenseWeight: number
  hybridLexicalWeight: number
  linkHybridWeights: boolean
  setLinkHybridWeights: (value: boolean) => void
  handleDenseWeightChange: (value: number) => void
  handleLexicalWeightChange: (value: number) => void
  bm25MatchMode: string
  setBm25MatchMode: (value: string) => void
  bm25MinShouldMatch: number
  setBm25MinShouldMatch: (value: number) => void
  bm25UsePhrase: boolean
  setBm25UsePhrase: (value: boolean) => void
  bm25Analyzer: string
  setBm25Analyzer: (value: string) => void
  useStructure: boolean
  setUseStructure: (value: boolean) => void
  structureRequestsPerMinute: number
  setStructureRequestsPerMinute: (value: number) => void
  useLlmChatTitles: boolean
  setUseLlmChatTitles: (value: boolean) => void
  opensearchAvailable: boolean | null
  onSave: () => void
  saving: boolean
}

function QueryDefaultsTab({
  llmModel, setLlmModel,
  llmProvider, setLlmProvider,
  temperature, setTemperature,
  topK, setTopK,
  maxContextChars, setMaxContextChars,
  scoreThreshold, setScoreThreshold,
  retrievalMode, setRetrievalMode,
  lexicalTopK, setLexicalTopK,
  hybridDenseWeight,
  hybridLexicalWeight,
  linkHybridWeights, setLinkHybridWeights,
  handleDenseWeightChange, handleLexicalWeightChange,
  bm25MatchMode, setBm25MatchMode,
  bm25MinShouldMatch, setBm25MinShouldMatch,
  bm25UsePhrase, setBm25UsePhrase,
  bm25Analyzer, setBm25Analyzer,
  useStructure, setUseStructure,
  structureRequestsPerMinute, setStructureRequestsPerMinute,
  useLlmChatTitles, setUseLlmChatTitles,
  opensearchAvailable,
  onSave, saving
}: QueryDefaultsTabProps) {

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Query Defaults</h2>
        <p className="text-gray-400">
          Default settings for chat queries and RAG retrieval
        </p>
      </div>

      {/* LLM Model */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">LLM Model</h3>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">Model & Provider</label>
          <LLMSelector
            value={llmModel}
            provider={llmProvider}
            onChange={(model, provider) => {
              setLlmModel(model)
              setLlmProvider(provider)
            }}
          />
        </div>
      </div>

      {/* RAG Parameters */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">RAG Parameters</h3>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Temperature: {temperature.toFixed(2)}
          </label>
          <input
            type="range"
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
            min="0"
            max="2"
            step="0.1"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
          />
          <p className="text-xs text-gray-400 mt-1">Controls randomness (0 = focused, 2 = creative)</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Top K Results: {topK}</label>
          <input
            type="range"
            className="slider w-full"
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value))}
            min="1"
            max="20"
            step="1"
          />
          <p className="text-xs text-gray-400 mt-1">Number of chunks to retrieve</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Score Threshold: {scoreThreshold.toFixed(2)}
          </label>
          <input
            type="range"
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
            min="0"
            max="1"
            step="0.05"
            value={scoreThreshold}
            onChange={(e) => setScoreThreshold(parseFloat(e.target.value))}
          />
          <p className="text-xs text-gray-400 mt-1">Minimum relevance score (0 = no filter)</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Max Context Characters</label>
          <input
            type="number"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            value={maxContextChars}
            onChange={(e) => setMaxContextChars(parseInt(e.target.value))}
            min="0"
          />
          <p className="text-xs text-gray-400 mt-1">Max total context length (0 = unlimited)</p>
        </div>
      </div>

      {/* Chat Titles */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Chat Titles</h3>
        <div className="flex items-center gap-3">
          <input
            id="use-llm-chat-titles"
            type="checkbox"
            checked={useLlmChatTitles}
            onChange={(e) => setUseLlmChatTitles(e.target.checked)}
            className="rounded border-gray-600 bg-gray-800"
          />
          <label htmlFor="use-llm-chat-titles" className="text-sm text-gray-300">
            Generate chat titles with LLM
          </label>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          When enabled, new chat titles are generated from the first Q&amp;A. Otherwise, the
          title falls back to the first user question.
        </p>
      </div>

      {/* Retrieval Mode */}
      {opensearchAvailable && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-gray-100 mb-4">Retrieval Mode</h3>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">Mode</label>
            <select
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              value={retrievalMode}
              onChange={(e) => setRetrievalMode(e.target.value as 'dense' | 'hybrid')}
            >
              <option value="dense">Dense (Vector Only)</option>
              <option value="hybrid">Hybrid (Vector + BM25)</option>
            </select>
            <p className="text-xs text-gray-400 mt-1">Dense for semantic, Hybrid for keyword + semantic</p>
          </div>

          {retrievalMode === 'hybrid' && (
            <>
              <div className="mb-4 flex items-center gap-2 text-xs text-gray-400">
                <input
                  id="link-hybrid-weights-settings"
                  type="checkbox"
                  checked={linkHybridWeights}
                  onChange={(e) => setLinkHybridWeights(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-800"
                />
                <label htmlFor="link-hybrid-weights-settings">
                  Link weights (lexical = 1 − dense)
                </label>
              </div>
              <p className="mb-4 text-[11px] text-gray-500">
                Weights are normalized server-side if they don’t sum to 1.0.
              </p>
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">Lexical Top K: {lexicalTopK}</label>
                <input
                  type="range"
                  className="slider w-full"
                  value={lexicalTopK}
                  onChange={(e) => setLexicalTopK(parseInt(e.target.value))}
                  min="1"
                  max="100"
                  step="1"
                />
                <p className="text-xs text-gray-400 mt-1">Number of BM25 candidates before reranking</p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Dense Weight: {hybridDenseWeight.toFixed(2)}
                </label>
                <input
                  type="range"
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                  min="0"
                  max="1"
                  step="0.1"
                  value={hybridDenseWeight}
                  onChange={(e) => handleDenseWeightChange(parseFloat(e.target.value))}
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Lexical Weight: {hybridLexicalWeight.toFixed(2)}
                </label>
                <input
                  type="range"
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                  min="0"
                  max="1"
                  step="0.1"
                  value={hybridLexicalWeight}
                  onChange={(e) => handleLexicalWeightChange(parseFloat(e.target.value))}
                />
              </div>

              {/* BM25 Settings */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">BM25 Match Mode</label>
                <select
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  value={bm25MatchMode}
                  onChange={(e) => setBm25MatchMode(e.target.value)}
                >
                  <option value="strict">Strict (must match most terms)</option>
                  <option value="balanced">Balanced (default)</option>
                  <option value="loose">Loose (flexible matching)</option>
                </select>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  BM25 Min Should Match: {bm25MinShouldMatch}%
                </label>
                <input
                  type="range"
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                  min="0"
                  max="100"
                  step="5"
                  value={bm25MinShouldMatch}
                  onChange={(e) => setBm25MinShouldMatch(parseInt(e.target.value))}
                />
              </div>

              <div className="mb-6">
                <label
                  className="flex items-center text-sm font-medium text-gray-300"
                  title="Adds an exact match_phrase clause to BM25 (OpenSearch) queries."
                >
                  <input
                    type="checkbox"
                    className="mr-2 w-4 h-4 text-primary-500 bg-gray-700 border-gray-600 rounded focus:ring-primary-500"
                    checked={bm25UsePhrase}
                    onChange={(e) => setBm25UsePhrase(e.target.checked)}
                  />
                  Use Phrase Matching
                </label>
                <p className="text-xs text-gray-400 mt-1">
                  Adds an exact phrase (match_phrase) to BM25 for stricter wording.
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">BM25 Analyzer</label>
                <select
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  value={bm25Analyzer}
                  onChange={(e) => setBm25Analyzer(e.target.value)}
                >
                  <option value="auto">Auto (detect language)</option>
                  <option value="mixed">Mixed (multilingual)</option>
                  <option value="ru">Russian</option>
                  <option value="en">English</option>
                </select>
              </div>
            </>
          )}
        </div>
      )}

      {/* Structure Analysis */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Structure Analysis</h3>

        <div className="mb-6">
          <label className="flex items-center text-sm font-medium text-gray-300">
            <input
              type="checkbox"
              className="mr-2 w-4 h-4 text-primary-500 bg-gray-700 border-gray-600 rounded focus:ring-primary-500"
              checked={useStructure}
              onChange={(e) => setUseStructure(e.target.checked)}
            />
            Enable Structure-Aware Retrieval
          </label>
          <p className="text-xs text-gray-400 mt-1">Use LLM to identify document structure before retrieval</p>
        </div>

        {useStructure && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">Requests Per Minute</label>
            <input
              type="number"
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              value={structureRequestsPerMinute}
              onChange={(e) => setStructureRequestsPerMinute(parseInt(e.target.value))}
              min="0"
              max="100"
            />
            <p className="text-xs text-gray-400 mt-1">Rate limit for structure analysis (0 = unlimited)</p>
          </div>
        )}
      </div>

      <div className="flex justify-end">
        <Button
          variant="primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Query Defaults'}
        </Button>
      </div>
    </div>
  )
}

type KBDefaultsTabProps = {
  kbChunkSize: number
  setKbChunkSize: (value: number) => void
  kbChunkOverlap: number
  setKbChunkOverlap: (value: number) => void
  kbUpsertBatchSize: number
  setKbUpsertBatchSize: (value: number) => void
  onSave: () => void
  saving: boolean
}

function KBDefaultsTab({
  kbChunkSize, setKbChunkSize,
  kbChunkOverlap, setKbChunkOverlap,
  kbUpsertBatchSize, setKbUpsertBatchSize,
  onSave, saving
}: KBDefaultsTabProps) {

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Knowledge Base Defaults</h2>
        <p className="text-gray-400">
          Default settings for new knowledge bases
        </p>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Default Chunk Size</label>
          <div className="flex items-center gap-4">
            <input
              type="range"
              className="w-full"
              value={kbChunkSize}
              onChange={(e) => setKbChunkSize(parseInt(e.target.value))}
              min="100"
              max="4000"
              step="50"
            />
            <span className="min-w-[4rem] text-right text-gray-200">{kbChunkSize}</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Characters per chunk (recommended: 1000-1500)</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Default Chunk Overlap</label>
          <div className="flex items-center gap-4">
            <input
              type="range"
              className="w-full"
              value={kbChunkOverlap}
              onChange={(e) => setKbChunkOverlap(parseInt(e.target.value))}
              min="0"
              max="500"
              step="10"
            />
            <span className="min-w-[7rem] text-right text-gray-200">
              {kbChunkOverlap} ({kbChunkSize > 0 ? Math.round((kbChunkOverlap / kbChunkSize) * 100) : 0}%)
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Overlapping characters (recommended: 15-20% of chunk size)</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Upsert Batch Size</label>
          <div className="flex items-center gap-4">
            <input
              type="range"
              className="w-full"
              value={kbUpsertBatchSize}
              onChange={(e) => setKbUpsertBatchSize(parseInt(e.target.value))}
              min="64"
              max="1024"
              step="32"
            />
            <span className="min-w-[4rem] text-right text-gray-200">{kbUpsertBatchSize}</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">Vectors per batch for Qdrant upload (higher = faster but more memory)</p>
        </div>
      </div>

      <div className="flex justify-end">
        <Button
          variant="primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save KB Defaults'}
        </Button>
      </div>
    </div>
  )
}

function AIProvidersTab(props: any) {
  const {
    openaiApiKey, setOpenaiApiKey, showOpenaiKey, setShowOpenaiKey,
    voyageApiKey, setVoyageApiKey, showVoyageKey, setShowVoyageKey,
    anthropicApiKey, setAnthropicApiKey, showAnthropicKey, setShowAnthropicKey,
    deepseekApiKey, setDeepseekApiKey, showDeepseekKey, setShowDeepseekKey,
    ollamaBaseUrl, setOllamaBaseUrl,
    systemName, setSystemName,
    maxFileSizeMb, setMaxFileSizeMb,
    onSave, saving
  } = props

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">AI Providers</h2>
        <p className="text-gray-400">
          Configure API keys for cloud AI services or Ollama URL for local LLM
        </p>
      </div>

      <div className="p-4 bg-blue-500/10 border border-blue-500 rounded-lg text-blue-200">
        API keys are masked for security. To change a key, enter the new value and click Save.
      </div>

      {/* API Keys */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Cloud AI Services</h3>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">OpenAI API Key</label>
          <div className="flex gap-2">
            <input
              type={showOpenaiKey ? 'text' : 'password'}
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="sk-proj-..."
              value={openaiApiKey}
              onChange={(e) => setOpenaiApiKey(e.target.value)}
            />
            <button
              type="button"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              onClick={() => setShowOpenaiKey(!showOpenaiKey)}
            >
              {showOpenaiKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1">Used for embeddings and chat (GPT models)</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">VoyageAI API Key (Optional)</label>
          <div className="flex gap-2">
            <input
              type={showVoyageKey ? 'text' : 'password'}
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="pa-..."
              value={voyageApiKey}
              onChange={(e) => setVoyageApiKey(e.target.value)}
            />
            <button
              type="button"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              onClick={() => setShowVoyageKey(!showVoyageKey)}
            >
              {showVoyageKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1">Alternative embedding provider</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Anthropic API Key (Optional)</label>
          <div className="flex gap-2">
            <input
              type={showAnthropicKey ? 'text' : 'password'}
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="sk-ant-..."
              value={anthropicApiKey}
              onChange={(e) => setAnthropicApiKey(e.target.value)}
            />
            <button
              type="button"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              onClick={() => setShowAnthropicKey(!showAnthropicKey)}
            >
              {showAnthropicKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1">Used for Claude models</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">DeepSeek API Key (Optional)</label>
          <div className="flex gap-2">
            <input
              type={showDeepseekKey ? 'text' : 'password'}
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="sk-..."
              value={deepseekApiKey}
              onChange={(e) => setDeepseekApiKey(e.target.value)}
            />
            <button
              type="button"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              onClick={() => setShowDeepseekKey(!showDeepseekKey)}
            >
              {showDeepseekKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1">Used for DeepSeek chat and reasoner models</p>
        </div>

      </div>

      {/* Ollama */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Local / Self-Hosted LLM</h3>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Ollama API URL (Optional)</label>
          <input
            type="text"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="http://localhost:11434 or https://your-cloud-ollama.com"
            value={ollamaBaseUrl}
            onChange={(e) => setOllamaBaseUrl(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">Ollama server URL (local or cloud-hosted)</p>
        </div>
      </div>

      {/* System Settings */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">System Settings</h3>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">System Name</label>
          <input
            type="text"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="Knowledge Base Platform"
            value={systemName}
            onChange={(e) => setSystemName(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">Displayed in UI</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Max File Size (MB)</label>
          <input
            type="number"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            value={maxFileSizeMb}
            onChange={(e) => setMaxFileSizeMb(parseInt(e.target.value))}
            min="1"
            max="500"
          />
          <p className="text-xs text-gray-400 mt-1">Maximum upload file size</p>
        </div>
      </div>

      <div className="flex justify-end">
        <Button
          variant="primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save AI Provider Settings'}
        </Button>
      </div>
    </div>
  )
}

function PromptsTab(props: any) {
  const {
    promptVersions,
    promptsLoading,
    activePromptVersionId,
    promptSelected,
    promptDraftName,
    setPromptDraftName,
    promptDraftSystemContent,
    setPromptDraftSystemContent,
    selfCheckPromptVersions,
    selfCheckPromptsLoading,
    activeSelfCheckPromptVersionId,
    selfCheckPromptSelected,
    selfCheckPromptDraftName,
    setSelfCheckPromptDraftName,
    selfCheckPromptDraftSystemContent,
    setSelfCheckPromptDraftSystemContent,
    showPromptVersions,
    setShowPromptVersions,
    onRefreshPrompts,
    onSelectPrompt,
    onActivatePrompt,
    onSaveDraft,
    onActivateDraft,
    onSaveDisplaySettings,
    onLoadToEditor,
    onRefreshSelfCheckPrompts,
    onSelectSelfCheckPrompt,
    onActivateSelfCheckPrompt,
    onSaveSelfCheckDraft,
    onActivateSelfCheckDraft,
    onLoadSelfCheckToEditor,
    saving,
  } = props

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">KB Chat Prompt</h2>
        <p className="text-gray-400">
          Used for Knowledge Base chat (RAG) responses across all KBs.
        </p>
        <p className="text-xs text-gray-500 mt-2">
          One active version at a time. Create a new version to change behavior.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-gray-100 mb-4">Chat Prompt Version</h3>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">Title</label>
            <input
              type="text"
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              value={promptDraftName}
              onChange={(e) => setPromptDraftName(e.target.value)}
              placeholder="Auto-generated if empty (e.g., KB Chat Prompt — 2026-02-05 14:32 UTC)"
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">System Prompt</label>
            <textarea
              className="w-full min-h-[240px] px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              value={promptDraftSystemContent}
              onChange={(e) => setPromptDraftSystemContent(e.target.value)}
              placeholder="Enter the system prompt..."
            />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            User template is fixed in code for safety and consistency.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={onSaveDraft}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Draft'}
            </Button>
            <Button
              variant="primary"
              onClick={onActivateDraft}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Activate'}
            </Button>
          </div>
          <p className="text-xs text-gray-400 mt-3">
            Activate sets this prompt for KB chat responses.
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-100">Chat Prompt History</h3>
            <button
              className="text-sm text-primary-400 hover:text-primary-300"
              onClick={onRefreshPrompts}
              disabled={promptsLoading}
            >
              {promptsLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
          <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
            {promptVersions.length === 0 && (
              <div className="text-sm text-gray-400">No prompt versions yet.</div>
            )}
            {promptVersions.map((prompt: PromptVersionSummary) => {
              const isActive = prompt.id === activePromptVersionId
              return (
                <div
                  key={prompt.id}
                  className="flex items-center justify-between bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-100">
                        {prompt.name || 'Untitled Prompt'}
                      </span>
                      {isActive && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400">
                      {new Date(prompt.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      className="text-xs text-gray-300 hover:text-white"
                      onClick={() => onSelectPrompt(prompt.id)}
                    >
                      View
                    </button>
                    <button
                      className="text-xs text-primary-400 hover:text-primary-300"
                      onClick={() => onActivatePrompt(prompt.id)}
                      disabled={saving}
                    >
                      Activate
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          {promptSelected && (
            <div className="mt-4 border border-gray-700 rounded-lg p-4 bg-gray-900/60">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-100">
                    {promptSelected.name || 'Selected Prompt'}
                  </div>
                  <div className="text-xs text-gray-500">{promptSelected.id}</div>
                </div>
                <div className="flex items-center gap-2">
                  {promptSelected.id === activePromptVersionId && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                      Active
                    </span>
                  )}
                  <button
                    className="text-xs text-primary-400 hover:text-primary-300"
                    onClick={() => onLoadToEditor(promptSelected)}
                  >
                    Load into editor
                  </button>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-1 gap-3 text-xs text-gray-200">
                <div className="border border-gray-700 rounded-lg p-3 bg-gray-950/60">
                  <div className="text-sm font-semibold text-gray-100 mb-1">System Prompt</div>
                  <p className="text-[11px] text-gray-500 mb-2">Controls assistant behavior.</p>
                  <pre className="whitespace-pre-wrap">{promptSelected.system_content}</pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-gray-100 mb-4">Self-Check Prompt Version</h3>
          <p className="text-xs text-gray-400 mb-4">
            Used only when self-check is enabled. It validates and can rewrite the draft answer.
          </p>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">Title</label>
            <input
              type="text"
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              value={selfCheckPromptDraftName}
              onChange={(e) => setSelfCheckPromptDraftName(e.target.value)}
              placeholder="Auto-generated if empty (e.g., Self-Check Prompt — 2026-02-05 14:32 UTC)"
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">System Prompt</label>
            <textarea
              className="w-full min-h-[200px] px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              value={selfCheckPromptDraftSystemContent}
              onChange={(e) => setSelfCheckPromptDraftSystemContent(e.target.value)}
              placeholder="Enter the system prompt..."
            />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            User template is fixed in code for safety and consistency.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={onSaveSelfCheckDraft}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Draft'}
            </Button>
            <Button
              variant="primary"
              onClick={onActivateSelfCheckDraft}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Activate'}
            </Button>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-100">Self-Check History</h3>
            <button
              className="text-sm text-primary-400 hover:text-primary-300"
              onClick={onRefreshSelfCheckPrompts}
              disabled={selfCheckPromptsLoading}
            >
              {selfCheckPromptsLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
          <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
            {selfCheckPromptVersions.length === 0 && (
              <div className="text-sm text-gray-400">No self-check prompt versions yet.</div>
            )}
            {selfCheckPromptVersions.map((prompt: SelfCheckPromptVersionSummary) => {
              const isActive = prompt.id === activeSelfCheckPromptVersionId
              return (
                <div
                  key={prompt.id}
                  className="flex items-center justify-between bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-100">
                        {prompt.name || 'Untitled Prompt'}
                      </span>
                      {isActive && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400">
                      {new Date(prompt.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      className="text-xs text-gray-300 hover:text-white"
                      onClick={() => onSelectSelfCheckPrompt(prompt.id)}
                    >
                      View
                    </button>
                    <button
                      className="text-xs text-primary-400 hover:text-primary-300"
                      onClick={() => onActivateSelfCheckPrompt(prompt.id)}
                      disabled={saving}
                    >
                      Activate
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          {selfCheckPromptSelected && (
            <div className="mt-4 border border-gray-700 rounded-lg p-4 bg-gray-900/60">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-100">
                    {selfCheckPromptSelected.name || 'Selected Prompt'}
                  </div>
                  <div className="text-xs text-gray-500">{selfCheckPromptSelected.id}</div>
                </div>
                <div className="flex items-center gap-2">
                  {selfCheckPromptSelected.id === activeSelfCheckPromptVersionId && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                      Active
                    </span>
                  )}
                  <button
                    className="text-xs text-primary-400 hover:text-primary-300"
                    onClick={() => onLoadSelfCheckToEditor(selfCheckPromptSelected)}
                  >
                    Load into editor
                  </button>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-1 gap-3 text-xs text-gray-200">
                <div className="border border-gray-700 rounded-lg p-3 bg-gray-950/60">
                  <div className="text-sm font-semibold text-gray-100 mb-1">System Prompt</div>
                  <pre className="whitespace-pre-wrap">{selfCheckPromptSelected.system_content}</pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-2">Prompt Display</h3>
        <label className="flex items-center space-x-3">
          <input
            type="checkbox"
            checked={showPromptVersions}
            onChange={(e) => setShowPromptVersions(e.target.checked)}
            className="w-4 h-4 text-primary-500 bg-gray-700 border-gray-600 rounded focus:ring-primary-500"
          />
          <span className="text-gray-200 text-sm">Show prompt version badges in chat responses</span>
        </label>
        <div className="flex justify-end mt-4">
          <Button
            variant="primary"
            onClick={onSaveDisplaySettings}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Display Settings'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function DatabasesTab(props: any) {
  const {
    qdrantUrl, setQdrantUrl,
    qdrantApiKey, setQdrantApiKey, showQdrantKey, setShowQdrantKey,
    opensearchUrl, setOpensearchUrl,
    opensearchUsername, setOpensearchUsername,
    opensearchPassword, setOpensearchPassword, showOpensearchPassword, setShowOpensearchPassword,
    postgresUsername, setPostgresUsername,
    postgresNewPassword, setPostgresNewPassword,
    onSave, onChangePostgresPassword, saving
  } = props

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Database Connections</h2>
        <p className="text-gray-400">
          Configure connections to vector, lexical, and metadata databases
        </p>
      </div>

      {/* Qdrant */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Qdrant (Vector Database)</h3>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Qdrant URL</label>
          <input
            type="text"
            autoComplete="off"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="http://qdrant:6333"
            value={qdrantUrl}
            onChange={(e) => setQdrantUrl(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">Qdrant HTTP API URL</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Qdrant API Key (Optional)</label>
          <div className="flex gap-2">
            <input
              type={showQdrantKey ? 'text' : 'password'}
              autoComplete="off"
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="Optional for local deployments"
              value={qdrantApiKey}
              onChange={(e) => setQdrantApiKey(e.target.value)}
            />
            <button
              type="button"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              onClick={() => setShowQdrantKey(!showQdrantKey)}
            >
              {showQdrantKey ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>
      </div>

      {/* OpenSearch */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">OpenSearch (Lexical Search)</h3>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">OpenSearch URL</label>
          <input
            type="text"
            autoComplete="off"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="http://opensearch:9200"
            value={opensearchUrl}
            onChange={(e) => setOpensearchUrl(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">OpenSearch HTTP URL</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Username (Optional)</label>
          <input
            type="text"
            autoComplete="off"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="admin"
            value={opensearchUsername}
            onChange={(e) => setOpensearchUsername(e.target.value)}
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Password (Optional)</label>
          <div className="flex gap-2">
            <input
              type={showOpensearchPassword ? 'text' : 'password'}
              autoComplete="new-password"
              className="flex-1 px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
              placeholder="••••••••"
              value={opensearchPassword}
              onChange={(e) => setOpensearchPassword(e.target.value)}
            />
            <button
              type="button"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              onClick={() => setShowOpensearchPassword(!showOpensearchPassword)}
            >
              {showOpensearchPassword ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <Button
          variant="primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Database Settings'}
        </Button>
      </div>

      {/* PostgreSQL Password Change */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 mt-12">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">PostgreSQL Database Security</h3>

        <div className="p-4 bg-blue-500/10 border border-blue-500 rounded-lg text-blue-200 mb-6">
          Changing PostgreSQL password will recreate the connection pool automatically.
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Username</label>
          <input
            type="text"
            autoComplete="off"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            value={postgresUsername}
            onChange={(e) => setPostgresUsername(e.target.value)}
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">New Password</label>
          <input
            type="password"
            autoComplete="new-password"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            placeholder="Enter new password (min 8 characters)"
            value={postgresNewPassword}
            onChange={(e) => setPostgresNewPassword(e.target.value)}
            minLength={8}
          />
          <p className="text-xs text-gray-400 mt-1">Minimum 8 characters</p>
        </div>

        <div className="flex justify-end">
          <button
            className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={onChangePostgresPassword}
            disabled={saving || !postgresNewPassword || postgresNewPassword.length < 8}
          >
            {saving ? 'Changing...' : 'Change PostgreSQL Password'}
          </button>
        </div>
      </div>
    </div>
  )
}
