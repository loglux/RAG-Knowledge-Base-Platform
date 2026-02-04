import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiClient } from '../services/api'
import { LLMSelector } from '../components/chat/LLMSelector'
import type { AppSettings } from '../types/index'

type TabType = 'query' | 'kb-defaults' | 'ai-providers' | 'databases'

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

  // System Settings (AI Providers)
  const [openaiApiKey, setOpenaiApiKey] = useState('')
  const [voyageApiKey, setVoyageApiKey] = useState('')
  const [anthropicApiKey, setAnthropicApiKey] = useState('')
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState('')
  const [showOpenaiKey, setShowOpenaiKey] = useState(false)
  const [showVoyageKey, setShowVoyageKey] = useState(false)
  const [showAnthropicKey, setShowAnthropicKey] = useState(false)

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

  useEffect(() => {
    loadAllSettings()
  }, [])

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
      if (appSettings.kb_chunk_size !== null) setKbChunkSize(appSettings.kb_chunk_size)
      if (appSettings.kb_chunk_overlap !== null) setKbChunkOverlap(appSettings.kb_chunk_overlap)
      if (appSettings.kb_upsert_batch_size !== null) setKbUpsertBatchSize(appSettings.kb_upsert_batch_size)

      // Load system settings (API keys, databases)
      const systemSettings = await apiClient.getSystemSettings()
      if (systemSettings.openai_api_key) setOpenaiApiKey(systemSettings.openai_api_key)
      if (systemSettings.voyage_api_key) setVoyageApiKey(systemSettings.voyage_api_key)
      if (systemSettings.anthropic_api_key) setAnthropicApiKey(systemSettings.anthropic_api_key)
      if (systemSettings.ollama_base_url) setOllamaBaseUrl(systemSettings.ollama_base_url)
      if (systemSettings.qdrant_url) setQdrantUrl(systemSettings.qdrant_url)
      if (systemSettings.qdrant_api_key) setQdrantApiKey(systemSettings.qdrant_api_key)
      if (systemSettings.opensearch_url) setOpensearchUrl(systemSettings.opensearch_url)
      if (systemSettings.opensearch_username) setOpensearchUsername(systemSettings.opensearch_username)
      if (systemSettings.opensearch_password) setOpensearchPassword(systemSettings.opensearch_password)
      if (systemSettings.system_name) setSystemName(systemSettings.system_name)
      if (systemSettings.max_file_size_mb) setMaxFileSizeMb(systemSettings.max_file_size_mb)

      // Check OpenSearch availability
      const info = await apiClient.getApiInfo()
      setOpensearchAvailable(info.integrations?.opensearch_available ?? null)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setLoading(false)
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
      </div>
    </div>
  )
}

// Tab Components
function QueryDefaultsTab(props: any) {
  const {
    llmModel, setLlmModel,
    llmProvider, setLlmProvider,
    temperature, setTemperature,
    topK, setTopK,
    maxContextChars, setMaxContextChars,
    scoreThreshold, setScoreThreshold,
    retrievalMode, setRetrievalMode,
    lexicalTopK, setLexicalTopK,
    hybridDenseWeight, setHybridDenseWeight,
    hybridLexicalWeight, setHybridLexicalWeight,
    linkHybridWeights, setLinkHybridWeights,
    handleDenseWeightChange, handleLexicalWeightChange,
    bm25MatchMode, setBm25MatchMode,
    bm25MinShouldMatch, setBm25MinShouldMatch,
    bm25UsePhrase, setBm25UsePhrase,
    bm25Analyzer, setBm25Analyzer,
    useStructure, setUseStructure,
    structureRequestsPerMinute, setStructureRequestsPerMinute,
    opensearchAvailable,
    onSave, saving
  } = props

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
                <label className="flex items-center text-sm font-medium text-gray-300">
                  <input
                    type="checkbox"
                    className="mr-2 w-4 h-4 text-primary-500 bg-gray-700 border-gray-600 rounded focus:ring-primary-500"
                    checked={bm25UsePhrase}
                    onChange={(e) => setBm25UsePhrase(e.target.checked)}
                  />
                  Use Phrase Matching
                </label>
                <p className="text-xs text-gray-400 mt-1">Boost exact phrase matches</p>
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
        <button
          className="btn-primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Query Defaults'}
        </button>
      </div>
    </div>
  )
}

function KBDefaultsTab(props: any) {
  const {
    kbChunkSize, setKbChunkSize,
    kbChunkOverlap, setKbChunkOverlap,
    kbUpsertBatchSize, setKbUpsertBatchSize,
    onSave, saving
  } = props

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
        <button
          className="btn-primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save KB Defaults'}
        </button>
      </div>
    </div>
  )
}

function AIProvidersTab(props: any) {
  const {
    openaiApiKey, setOpenaiApiKey, showOpenaiKey, setShowOpenaiKey,
    voyageApiKey, setVoyageApiKey, showVoyageKey, setShowVoyageKey,
    anthropicApiKey, setAnthropicApiKey, showAnthropicKey, setShowAnthropicKey,
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
        <button
          className="btn-primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save AI Provider Settings'}
        </button>
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
        <button
          className="btn-primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Database Settings'}
        </button>
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
