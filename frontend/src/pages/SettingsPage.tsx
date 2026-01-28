import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../services/api'
import { LLMSelector } from '../components/chat/LLMSelector'
import type { AppSettings } from '../types/index'

export function SettingsPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedAt, setSavedAt] = useState<string | null>(null)

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
  const [showAdvancedBm25, setShowAdvancedBm25] = useState(false)
  const [bm25MatchModes, setBm25MatchModes] = useState<string[] | null>(null)
  const [bm25Analyzers, setBm25Analyzers] = useState<string[] | null>(null)
  const [useStructure, setUseStructure] = useState(false)
  const [structureRequestsPerMinute, setStructureRequestsPerMinute] = useState(10)
  const [kbChunkSize, setKbChunkSize] = useState(1000)
  const [kbChunkOverlap, setKbChunkOverlap] = useState(200)
  const [kbUpsertBatchSize, setKbUpsertBatchSize] = useState(256)
  const [opensearchAvailable, setOpensearchAvailable] = useState<boolean | null>(null)

  useEffect(() => {
    const loadSettings = async () => {
      try {
        setLoading(true)
        const data: AppSettings = await apiClient.getAppSettings()
        if (data.llm_model) setLlmModel(data.llm_model)
        if (data.llm_provider) setLlmProvider(data.llm_provider)
        if (data.temperature !== null) setTemperature(data.temperature)
        if (data.top_k !== null) setTopK(data.top_k)
        if (data.max_context_chars !== null) setMaxContextChars(data.max_context_chars)
        if (data.score_threshold !== null) setScoreThreshold(data.score_threshold)
        if (data.use_structure !== null) setUseStructure(data.use_structure)
        if (data.retrieval_mode) setRetrievalMode(data.retrieval_mode)
        if (data.lexical_top_k !== null) setLexicalTopK(data.lexical_top_k)
        if (data.hybrid_dense_weight !== null) setHybridDenseWeight(data.hybrid_dense_weight)
        if (data.hybrid_lexical_weight !== null) setHybridLexicalWeight(data.hybrid_lexical_weight)
        if (data.bm25_match_mode) setBm25MatchMode(data.bm25_match_mode)
        if (data.bm25_min_should_match !== null) setBm25MinShouldMatch(data.bm25_min_should_match)
        if (data.bm25_use_phrase !== null) setBm25UsePhrase(data.bm25_use_phrase)
        if (data.bm25_analyzer) setBm25Analyzer(data.bm25_analyzer)
        if (data.structure_requests_per_minute !== null) {
          setStructureRequestsPerMinute(data.structure_requests_per_minute)
        }
        if (data.kb_chunk_size !== null) setKbChunkSize(data.kb_chunk_size)
        if (data.kb_chunk_overlap !== null) setKbChunkOverlap(data.kb_chunk_overlap)
        if (data.kb_upsert_batch_size !== null) setKbUpsertBatchSize(data.kb_upsert_batch_size)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load settings')
      } finally {
        setLoading(false)
      }
    }

    loadSettings()
  }, [])

  useEffect(() => {
    const loadInfo = async () => {
      try {
        const info = await apiClient.getApiInfo()
        setOpensearchAvailable(info.integrations?.opensearch_available ?? null)
      } catch (err) {
        setOpensearchAvailable(null)
      }
    }

    loadInfo()
  }, [])

  useEffect(() => {
    const loadSettingsMetadata = async () => {
      try {
        const metadata = await apiClient.getSettingsMetadata()
        setBm25MatchModes(metadata.bm25_match_modes || null)
        setBm25Analyzers(metadata.bm25_analyzers || null)
      } catch (err) {
        setBm25MatchModes(null)
        setBm25Analyzers(null)
      }
    }

    loadSettingsMetadata()
  }, [])

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)
      const updated = await apiClient.updateAppSettings({
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
        kb_chunk_size: kbChunkSize,
        kb_chunk_overlap: kbChunkOverlap,
        kb_upsert_batch_size: kbUpsertBatchSize,
      })
      setSavedAt(new Date(updated.updated_at).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleLLMChange = (model: string, provider: string) => {
    setLlmModel(model)
    setLlmProvider(provider)
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/')}
              className="text-gray-400 hover:text-white transition-colors"
            >
              ← Back
            </button>
            <h1 className="text-xl font-semibold text-white">Global Settings</h1>
            <div className="text-xs text-gray-400">
              {savedAt ? `Saved ${savedAt}` : ''}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500 bg-opacity-10 border border-red-500 rounded-lg text-red-500">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-10 w-10 border-b-2 border-primary-500"></div>
            <p className="mt-4 text-gray-400">Loading settings...</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 space-y-6">
              <div>
                <LLMSelector value={llmModel} onChange={handleLLMChange} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Number of sources (Top K): {topK}
                </label>
                <input
                  type="range"
                  min="1"
                  max="100"
                  step="1"
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="slider w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Default number of chunks to retrieve
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Temperature: {temperature.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="slider w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Default response creativity
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Score threshold (0–1)
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={scoreThreshold}
                  onChange={(e) => setScoreThreshold(Number(e.target.value))}
                  className="slider w-full"
                />
                <div className="text-xs text-gray-400 mt-1">Current: {scoreThreshold.toFixed(2)}</div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Max context chars (0 = unlimited)
                </label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  value={maxContextChars}
                  onChange={(e) => setMaxContextChars(Number(e.target.value))}
                  className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Default context limit
                </p>
              </div>

                <div className="md:col-span-2">
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useStructure}
                      onChange={(e) => setUseStructure(e.target.checked)}
                      className="w-5 h-5 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
                    />
                    <span className="text-sm text-gray-300">Use Document Structure by default</span>
                  </label>
                  <p className="text-xs text-gray-500 mt-2">
                    Enable structure-based search when possible
                  </p>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    TOC requests per minute: {structureRequestsPerMinute}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="120"
                    step="1"
                    value={structureRequestsPerMinute}
                    onChange={(e) => setStructureRequestsPerMinute(Number(e.target.value))}
                    className="slider w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    0 = unlimited. Limits structure analysis requests to avoid provider rate limits.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-300">BM25 / Hybrid Defaults</h2>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <button
                    onClick={() => setShowAdvancedBm25(false)}
                    className={`px-2 py-0.5 rounded border ${showAdvancedBm25 ? 'border-gray-700 text-gray-400' : 'border-primary-500 text-primary-200 bg-primary-500/10'}`}
                  >
                    Basic
                  </button>
                  <button
                    onClick={() => setShowAdvancedBm25(true)}
                    className={`px-2 py-0.5 rounded border ${showAdvancedBm25 ? 'border-primary-500 text-primary-200 bg-primary-500/10' : 'border-gray-700 text-gray-400'}`}
                  >
                    Advanced
                  </button>
                </div>
              </div>
              <p className="text-xs text-gray-500">
                Defaults for hybrid retrieval. Basic is safe; Advanced changes analyzer and usually needs reindex.
              </p>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Retrieval mode
                </label>
                <select
                  value={retrievalMode}
                  onChange={(e) => setRetrievalMode(e.target.value as 'dense' | 'hybrid')}
                  className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
                >
                  <option value="dense">Dense (vector)</option>
                  <option value="hybrid">Hybrid (BM25 + vector)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Default retrieval strategy for new chats
                </p>
                {retrievalMode === 'hybrid' && opensearchAvailable === false && (
                  <div className="mt-2 rounded border border-yellow-500/40 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-200">
                    OpenSearch is not reachable. Hybrid search may fail until it is available.
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Lexical Top K: {lexicalTopK}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="200"
                    step="1"
                    value={lexicalTopK}
                    onChange={(e) => setLexicalTopK(Number(e.target.value))}
                    className="slider w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Candidate pool from BM25 before merging
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Hybrid dense weight: {hybridDenseWeight.toFixed(2)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={hybridDenseWeight}
                    onChange={(e) => setHybridDenseWeight(Number(e.target.value))}
                    className="slider w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Higher = more semantic/vector influence
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Hybrid lexical weight: {hybridLexicalWeight.toFixed(2)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={hybridLexicalWeight}
                    onChange={(e) => setHybridLexicalWeight(Number(e.target.value))}
                    className="slider w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Higher = more BM25/keyword influence
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Match mode
                  </label>
                  <select
                    value={bm25MatchMode || (bm25MatchModes?.[0] ?? '')}
                    onChange={(e) => setBm25MatchMode(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
                    disabled={!bm25MatchModes || bm25MatchModes.length === 0}
                  >
                    {(!bm25MatchModes || bm25MatchModes.length === 0) && <option value="">Loading…</option>}
                    {bm25MatchModes?.map((mode) => (
                      <option key={mode} value={mode}>
                        {mode}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Controls how many query terms must appear
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Minimum should match: {bm25MinShouldMatch}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={bm25MinShouldMatch}
                    onChange={(e) => setBm25MinShouldMatch(Number(e.target.value))}
                    className="slider w-full"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    0 = no minimum, higher = stricter lexical match
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Use phrase match
                  </label>
                  <label className="flex items-center gap-2 text-sm text-gray-300">
                    <input
                      type="checkbox"
                      checked={bm25UsePhrase}
                      onChange={(e) => setBm25UsePhrase(e.target.checked)}
                      className="w-4 h-4 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
                    />
                    Include exact phrase matches
                  </label>
                  <p className="text-xs text-gray-500 mt-1">
                    Helps when wording matters, but can miss paraphrases
                  </p>
                </div>

                {showAdvancedBm25 && (
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Analyzer profile
                    </label>
                    <select
                      value={bm25Analyzer || (bm25Analyzers?.[0] ?? '')}
                      onChange={(e) => setBm25Analyzer(e.target.value)}
                      className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
                      disabled={!bm25Analyzers || bm25Analyzers.length === 0}
                    >
                      {(!bm25Analyzers || bm25Analyzers.length === 0) && <option value="">Loading…</option>}
                      {bm25Analyzers?.map((analyzer) => (
                        <option key={analyzer} value={analyzer}>
                          {analyzer}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Requires reindex after changing analyzer profile
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">
                Knowledge Base Defaults
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Chunk Size: <span className="text-white font-medium">{kbChunkSize}</span> characters
                  </label>
                  <input
                    type="range"
                    min="100"
                    max="2000"
                    step="100"
                    value={kbChunkSize}
                    onChange={(e) => setKbChunkSize(Number(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>100</span>
                    <span>2000</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Larger chunks preserve more context; smaller chunks improve precision.
                  </p>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Chunk Overlap: <span className="text-white font-medium">{kbChunkOverlap}</span> characters
                    <span className="text-gray-500">
                      {' '}({kbChunkSize > 0 ? Math.round((kbChunkOverlap / kbChunkSize) * 100) : 0}%)
                    </span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="500"
                    step="50"
                    value={kbChunkOverlap}
                    onChange={(e) => setKbChunkOverlap(Number(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>0</span>
                    <span>500</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Overlap helps preserve continuity between neighboring chunks.
                  </p>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Upsert Batch Size: <span className="text-white font-medium">{kbUpsertBatchSize}</span>
                  </label>
                  <input
                    type="range"
                    min="64"
                    max="1024"
                    step="64"
                    value={kbUpsertBatchSize}
                    onChange={(e) => setKbUpsertBatchSize(Number(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>64</span>
                    <span>1024</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Larger batches ingest faster but use more memory.
                  </p>
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-3">
                Changes apply to new or reprocessed documents only.
              </p>
            </div>

            <div className="flex items-center justify-between">
              <button
                onClick={async () => {
                  try {
                    setResetting(true)
                    setError(null)
                    const data = await apiClient.resetAppSettings()
                    if (data.llm_model) setLlmModel(data.llm_model)
                    if (data.llm_provider) setLlmProvider(data.llm_provider)
                    if (data.temperature !== null) setTemperature(data.temperature)
                    if (data.top_k !== null) setTopK(data.top_k)
                    if (data.max_context_chars !== null) setMaxContextChars(data.max_context_chars)
                    if (data.score_threshold !== null) setScoreThreshold(data.score_threshold)
                    if (data.use_structure !== null) setUseStructure(data.use_structure)
                    if (data.retrieval_mode) setRetrievalMode(data.retrieval_mode)
                    if (data.lexical_top_k !== null) setLexicalTopK(data.lexical_top_k)
                    if (data.hybrid_dense_weight !== null) setHybridDenseWeight(data.hybrid_dense_weight)
                    if (data.hybrid_lexical_weight !== null) setHybridLexicalWeight(data.hybrid_lexical_weight)
                    if (data.bm25_match_mode) setBm25MatchMode(data.bm25_match_mode)
                    if (data.bm25_min_should_match !== null) setBm25MinShouldMatch(data.bm25_min_should_match)
                    if (data.bm25_use_phrase !== null) setBm25UsePhrase(data.bm25_use_phrase)
                    if (data.bm25_analyzer) setBm25Analyzer(data.bm25_analyzer)
                    if (data.kb_chunk_size !== null) setKbChunkSize(data.kb_chunk_size)
                    if (data.kb_chunk_overlap !== null) setKbChunkOverlap(data.kb_chunk_overlap)
                    if (data.kb_upsert_batch_size !== null) setKbUpsertBatchSize(data.kb_upsert_batch_size)
                    setSavedAt(new Date(data.updated_at).toLocaleTimeString('en-US', {
                      hour: '2-digit',
                      minute: '2-digit',
                    }))
                  } catch (err) {
                    setError(err instanceof Error ? err.message : 'Failed to reset settings')
                  } finally {
                    setResetting(false)
                  }
                }}
                className="btn-secondary text-xs px-3 py-1.5"
                disabled={saving || resetting}
              >
                {resetting ? 'Resetting…' : 'Reset to defaults'}
              </button>
              <button
                onClick={handleSave}
                disabled={saving || resetting}
                className="btn-primary"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
