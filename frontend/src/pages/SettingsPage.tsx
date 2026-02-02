import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../services/api'
import { LLMSelector } from '../components/chat/LLMSelector'
import type { AppSettings } from '../types/index'
import './SettingsPage.css'

type TabType = 'query' | 'kb-defaults' | 'ai-providers' | 'databases'

export function SettingsPage() {
  const navigate = useNavigate()
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
  const [bm25MatchMode, setBm25MatchMode] = useState('balanced')
  const [bm25MinShouldMatch, setBm25MinShouldMatch] = useState(50)
  const [bm25UsePhrase, setBm25UsePhrase] = useState(true)
  const [bm25Analyzer, setBm25Analyzer] = useState('mixed')
  const [useStructure, setUseStructure] = useState(false)
  const [structureRequestsPerMinute, setStructureRequestsPerMinute] = useState(10)
  const [opensearchAvailable, setOpensearchAvailable] = useState<boolean | null>(null)

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
      <div className="settings-page">
        <div className="settings-header">
          <h1>Settings</h1>
        </div>
        <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
          Loading settings...
        </div>
      </div>
    )
  }

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h1>Settings</h1>
        <p>Configure system settings and defaults</p>
      </div>

      {/* Tab Navigation */}
      <div className="tabs-navigation">
        <button
          className={`tab-button ${activeTab === 'query' ? 'active' : ''}`}
          onClick={() => setActiveTab('query')}
        >
          Query Defaults
        </button>
        <button
          className={`tab-button ${activeTab === 'kb-defaults' ? 'active' : ''}`}
          onClick={() => setActiveTab('kb-defaults')}
        >
          KB Defaults
        </button>
        <button
          className={`tab-button ${activeTab === 'ai-providers' ? 'active' : ''}`}
          onClick={() => setActiveTab('ai-providers')}
        >
          AI Providers
        </button>
        <button
          className={`tab-button ${activeTab === 'databases' ? 'active' : ''}`}
          onClick={() => setActiveTab('databases')}
        >
          Databases
        </button>
      </div>

      {/* Alerts */}
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Tab Content */}
      <div className="tab-content">
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
    <div className="settings-section">
      <h2>Query Defaults</h2>
      <p className="settings-section-description">
        Default settings for chat queries and RAG retrieval
      </p>

      {/* LLM Model */}
      <div className="settings-group">
        <h3>LLM Model</h3>
        <div className="form-group">
          <label>Model & Provider</label>
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
      <div className="settings-group">
        <h3>RAG Parameters</h3>

        <div className="form-group">
          <label>Temperature: {temperature.toFixed(2)}</label>
          <input
            type="range"
            className="form-control"
            min="0"
            max="2"
            step="0.1"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
          />
          <small className="form-text">Controls randomness (0 = focused, 2 = creative)</small>
        </div>

        <div className="form-group">
          <label>Top K Results</label>
          <input
            type="number"
            className="form-control"
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value))}
            min="1"
            max="20"
          />
          <small className="form-text">Number of chunks to retrieve</small>
        </div>

        <div className="form-group">
          <label>Score Threshold: {scoreThreshold.toFixed(2)}</label>
          <input
            type="range"
            className="form-control"
            min="0"
            max="1"
            step="0.05"
            value={scoreThreshold}
            onChange={(e) => setScoreThreshold(parseFloat(e.target.value))}
          />
          <small className="form-text">Minimum relevance score (0 = no filter)</small>
        </div>

        <div className="form-group">
          <label>Max Context Characters</label>
          <input
            type="number"
            className="form-control"
            value={maxContextChars}
            onChange={(e) => setMaxContextChars(parseInt(e.target.value))}
            min="0"
          />
          <small className="form-text">Max total context length (0 = unlimited)</small>
        </div>
      </div>

      {/* Retrieval Mode */}
      {opensearchAvailable && (
        <div className="settings-group">
          <h3>Retrieval Mode</h3>

          <div className="form-group">
            <label>Mode</label>
            <select
              className="form-control"
              value={retrievalMode}
              onChange={(e) => setRetrievalMode(e.target.value as 'dense' | 'hybrid')}
            >
              <option value="dense">Dense (Vector Only)</option>
              <option value="hybrid">Hybrid (Vector + BM25)</option>
            </select>
            <small className="form-text">Dense for semantic, Hybrid for keyword + semantic</small>
          </div>

          {retrievalMode === 'hybrid' && (
            <>
              <div className="form-group">
                <label>Lexical Top K</label>
                <input
                  type="number"
                  className="form-control"
                  value={lexicalTopK}
                  onChange={(e) => setLexicalTopK(parseInt(e.target.value))}
                  min="1"
                  max="100"
                />
                <small className="form-text">Number of BM25 candidates before reranking</small>
              </div>

              <div className="form-group">
                <label>Dense Weight: {hybridDenseWeight.toFixed(2)}</label>
                <input
                  type="range"
                  className="form-control"
                  min="0"
                  max="1"
                  step="0.1"
                  value={hybridDenseWeight}
                  onChange={(e) => setHybridDenseWeight(parseFloat(e.target.value))}
                />
              </div>

              <div className="form-group">
                <label>Lexical Weight: {hybridLexicalWeight.toFixed(2)}</label>
                <input
                  type="range"
                  className="form-control"
                  min="0"
                  max="1"
                  step="0.1"
                  value={hybridLexicalWeight}
                  onChange={(e) => setHybridLexicalWeight(parseFloat(e.target.value))}
                />
              </div>

              {/* BM25 Settings */}
              <div className="form-group">
                <label>BM25 Match Mode</label>
                <select
                  className="form-control"
                  value={bm25MatchMode}
                  onChange={(e) => setBm25MatchMode(e.target.value)}
                >
                  <option value="strict">Strict (must match most terms)</option>
                  <option value="balanced">Balanced (default)</option>
                  <option value="loose">Loose (flexible matching)</option>
                </select>
              </div>

              <div className="form-group">
                <label>BM25 Min Should Match: {bm25MinShouldMatch}%</label>
                <input
                  type="range"
                  className="form-control"
                  min="0"
                  max="100"
                  step="5"
                  value={bm25MinShouldMatch}
                  onChange={(e) => setBm25MinShouldMatch(parseInt(e.target.value))}
                />
              </div>

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={bm25UsePhrase}
                    onChange={(e) => setBm25UsePhrase(e.target.checked)}
                  />
                  {' '}Use Phrase Matching
                </label>
                <small className="form-text">Boost exact phrase matches</small>
              </div>

              <div className="form-group">
                <label>BM25 Analyzer</label>
                <select
                  className="form-control"
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
      <div className="settings-group">
        <h3>Structure Analysis</h3>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={useStructure}
              onChange={(e) => setUseStructure(e.target.checked)}
            />
            {' '}Enable Structure-Aware Retrieval
          </label>
          <small className="form-text">Use LLM to identify document structure before retrieval</small>
        </div>

        {useStructure && (
          <div className="form-group">
            <label>Requests Per Minute</label>
            <input
              type="number"
              className="form-control"
              value={structureRequestsPerMinute}
              onChange={(e) => setStructureRequestsPerMinute(parseInt(e.target.value))}
              min="0"
              max="100"
            />
            <small className="form-text">Rate limit for structure analysis (0 = unlimited)</small>
          </div>
        )}
      </div>

      <div className="settings-actions">
        <button
          className="btn btn-primary"
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
    <div className="settings-section">
      <h2>Knowledge Base Defaults</h2>
      <p className="settings-section-description">
        Default settings for new knowledge bases
      </p>

      <div className="form-group">
        <label>Default Chunk Size</label>
        <input
          type="number"
          className="form-control"
          value={kbChunkSize}
          onChange={(e) => setKbChunkSize(parseInt(e.target.value))}
          min="100"
          max="4000"
        />
        <small className="form-text">Characters per chunk (recommended: 1000-1500)</small>
      </div>

      <div className="form-group">
        <label>Default Chunk Overlap</label>
        <input
          type="number"
          className="form-control"
          value={kbChunkOverlap}
          onChange={(e) => setKbChunkOverlap(parseInt(e.target.value))}
          min="0"
          max="500"
        />
        <small className="form-text">Overlapping characters (recommended: 15-20% of chunk size)</small>
      </div>

      <div className="form-group">
        <label>Upsert Batch Size</label>
        <input
          type="number"
          className="form-control"
          value={kbUpsertBatchSize}
          onChange={(e) => setKbUpsertBatchSize(parseInt(e.target.value))}
          min="64"
          max="1024"
        />
        <small className="form-text">Vectors per batch for Qdrant upload (higher = faster but more memory)</small>
      </div>

      <div className="settings-actions">
        <button
          className="btn btn-primary"
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
    <div className="settings-section">
      <h2>AI Providers</h2>
      <p className="settings-section-description">
        Configure API keys for cloud AI services or Ollama URL for local LLM
      </p>

      <div className="alert alert-info">
        API keys are masked for security. To change a key, enter the new value and click Save.
      </div>

      {/* API Keys */}
      <div className="settings-group">
        <h3>Cloud AI Services</h3>

        <div className="form-group">
          <label>OpenAI API Key</label>
          <div className="masked-input-group">
            <input
              type={showOpenaiKey ? 'text' : 'password'}
              className="form-control"
              placeholder="sk-proj-..."
              value={openaiApiKey}
              onChange={(e) => setOpenaiApiKey(e.target.value)}
            />
            <button
              type="button"
              className="btn-toggle-mask"
              onClick={() => setShowOpenaiKey(!showOpenaiKey)}
            >
              {showOpenaiKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <small className="form-text">Used for embeddings and chat (GPT models)</small>
        </div>

        <div className="form-group">
          <label>VoyageAI API Key (Optional)</label>
          <div className="masked-input-group">
            <input
              type={showVoyageKey ? 'text' : 'password'}
              className="form-control"
              placeholder="pa-..."
              value={voyageApiKey}
              onChange={(e) => setVoyageApiKey(e.target.value)}
            />
            <button
              type="button"
              className="btn-toggle-mask"
              onClick={() => setShowVoyageKey(!showVoyageKey)}
            >
              {showVoyageKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <small className="form-text">Alternative embedding provider</small>
        </div>

        <div className="form-group">
          <label>Anthropic API Key (Optional)</label>
          <div className="masked-input-group">
            <input
              type={showAnthropicKey ? 'text' : 'password'}
              className="form-control"
              placeholder="sk-ant-..."
              value={anthropicApiKey}
              onChange={(e) => setAnthropicApiKey(e.target.value)}
            />
            <button
              type="button"
              className="btn-toggle-mask"
              onClick={() => setShowAnthropicKey(!showAnthropicKey)}
            >
              {showAnthropicKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <small className="form-text">Used for Claude models</small>
        </div>
      </div>

      {/* Ollama */}
      <div className="settings-group">
        <h3>Local / Self-Hosted LLM</h3>

        <div className="form-group">
          <label>Ollama API URL (Optional)</label>
          <input
            type="text"
            className="form-control"
            placeholder="http://localhost:11434 or https://your-cloud-ollama.com"
            value={ollamaBaseUrl}
            onChange={(e) => setOllamaBaseUrl(e.target.value)}
          />
          <small className="form-text">Ollama server URL (local or cloud-hosted)</small>
        </div>
      </div>

      {/* System Settings */}
      <div className="settings-group">
        <h3>System Settings</h3>

        <div className="form-group">
          <label>System Name</label>
          <input
            type="text"
            className="form-control"
            placeholder="Knowledge Base Platform"
            value={systemName}
            onChange={(e) => setSystemName(e.target.value)}
          />
          <small className="form-text">Displayed in UI</small>
        </div>

        <div className="form-group">
          <label>Max File Size (MB)</label>
          <input
            type="number"
            className="form-control"
            value={maxFileSizeMb}
            onChange={(e) => setMaxFileSizeMb(parseInt(e.target.value))}
            min="1"
            max="500"
          />
          <small className="form-text">Maximum upload file size</small>
        </div>
      </div>

      <div className="settings-actions">
        <button
          className="btn btn-primary"
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
    <div className="settings-section">
      <h2>Database Connections</h2>
      <p className="settings-section-description">
        Configure connections to vector, lexical, and metadata databases
      </p>

      {/* Qdrant */}
      <div className="settings-group">
        <h3>Qdrant (Vector Database)</h3>

        <div className="form-group">
          <label>Qdrant URL</label>
          <input
            type="text"
            className="form-control"
            placeholder="http://qdrant:6333"
            value={qdrantUrl}
            onChange={(e) => setQdrantUrl(e.target.value)}
          />
          <small className="form-text">Qdrant HTTP API URL</small>
        </div>

        <div className="form-group">
          <label>Qdrant API Key (Optional)</label>
          <div className="masked-input-group">
            <input
              type={showQdrantKey ? 'text' : 'password'}
              className="form-control"
              placeholder="Optional for local deployments"
              value={qdrantApiKey}
              onChange={(e) => setQdrantApiKey(e.target.value)}
            />
            <button
              type="button"
              className="btn-toggle-mask"
              onClick={() => setShowQdrantKey(!showQdrantKey)}
            >
              {showQdrantKey ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>
      </div>

      {/* OpenSearch */}
      <div className="settings-group">
        <h3>OpenSearch (Lexical Search)</h3>

        <div className="form-group">
          <label>OpenSearch URL</label>
          <input
            type="text"
            className="form-control"
            placeholder="http://opensearch:9200"
            value={opensearchUrl}
            onChange={(e) => setOpensearchUrl(e.target.value)}
          />
          <small className="form-text">OpenSearch HTTP URL</small>
        </div>

        <div className="form-group">
          <label>Username (Optional)</label>
          <input
            type="text"
            className="form-control"
            placeholder="admin"
            value={opensearchUsername}
            onChange={(e) => setOpensearchUsername(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Password (Optional)</label>
          <div className="masked-input-group">
            <input
              type={showOpensearchPassword ? 'text' : 'password'}
              className="form-control"
              placeholder="••••••••"
              value={opensearchPassword}
              onChange={(e) => setOpensearchPassword(e.target.value)}
            />
            <button
              type="button"
              className="btn-toggle-mask"
              onClick={() => setShowOpensearchPassword(!showOpensearchPassword)}
            >
              {showOpensearchPassword ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>
      </div>

      <div className="settings-actions">
        <button
          className="btn btn-primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Database Settings'}
        </button>
      </div>

      {/* PostgreSQL Password Change */}
      <div className="settings-group" style={{ marginTop: '3rem', paddingTop: '2rem', borderTop: '2px solid #e0e0e0' }}>
        <h3>PostgreSQL Database Security</h3>

        <div className="alert alert-info">
          Changing PostgreSQL password will recreate the connection pool automatically.
        </div>

        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            className="form-control"
            value={postgresUsername}
            onChange={(e) => setPostgresUsername(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>New Password</label>
          <input
            type="password"
            className="form-control"
            placeholder="Enter new password (min 8 characters)"
            value={postgresNewPassword}
            onChange={(e) => setPostgresNewPassword(e.target.value)}
            minLength={8}
          />
          <small className="form-text">Minimum 8 characters</small>
        </div>

        <div className="settings-actions">
          <button
            className="btn btn-danger"
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
