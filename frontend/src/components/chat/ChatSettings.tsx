import React, { useState } from 'react'
import { LLMSelector } from './LLMSelector'

interface ChatSettingsProps {
  topK: number
  temperature: number
  maxContextChars: number
  scoreThreshold: number
  retrievalMode: 'dense' | 'hybrid'
  lexicalTopK: number
  hybridDenseWeight: number
  hybridLexicalWeight: number
  bm25MatchMode: string
  bm25MinShouldMatch: number
  bm25UsePhrase: boolean
  bm25Analyzer: string
  bm25MatchModes?: string[]
  bm25Analyzers?: string[]
  opensearchAvailable?: boolean
  llmModel: string
  llmProvider: string
  useStructure: boolean
  useMmr: boolean
  mmrDiversity: number
  useSelfCheck: boolean
  onTopKChange: (value: number) => void
  onTemperatureChange: (value: number) => void
  onMaxContextCharsChange: (value: number) => void
  onScoreThresholdChange: (value: number) => void
  onRetrievalModeChange: (value: 'dense' | 'hybrid') => void
  onLexicalTopKChange: (value: number) => void
  onHybridDenseWeightChange: (value: number) => void
  onHybridLexicalWeightChange: (value: number) => void
  onBm25MatchModeChange: (value: string) => void
  onBm25MinShouldMatchChange: (value: number) => void
  onBm25UsePhraseChange: (value: boolean) => void
  onBm25AnalyzerChange: (value: string) => void
  onLLMChange: (model: string, provider: string) => void
  onUseStructureChange: (value: boolean) => void
  onUseMmrChange: (value: boolean) => void
  onMmrDiversityChange: (value: number) => void
  onUseSelfCheckChange: (value: boolean) => void
  onResetDefaults: () => void
  onClose: () => void
}

export function ChatSettings({
  topK,
  temperature,
  maxContextChars,
  scoreThreshold,
  retrievalMode,
  lexicalTopK,
  hybridDenseWeight,
  hybridLexicalWeight,
  bm25MatchMode,
  bm25MinShouldMatch,
  bm25UsePhrase,
  bm25Analyzer,
  bm25MatchModes,
  bm25Analyzers,
  opensearchAvailable,
  llmModel,
  llmProvider,
  useStructure,
  useMmr,
  mmrDiversity,
  useSelfCheck,
  onTopKChange,
  onTemperatureChange,
  onMaxContextCharsChange,
  onScoreThresholdChange,
  onRetrievalModeChange,
  onLexicalTopKChange,
  onHybridDenseWeightChange,
  onHybridLexicalWeightChange,
  onBm25MatchModeChange,
  onBm25MinShouldMatchChange,
  onBm25UsePhraseChange,
  onBm25AnalyzerChange,
  onLLMChange,
  onUseStructureChange,
  onUseMmrChange,
  onMmrDiversityChange,
  onUseSelfCheckChange,
  onResetDefaults,
  onClose,
}: ChatSettingsProps) {
  const safeTopK = Number.isFinite(topK) ? topK : 5
  const safeTemperature = Number.isFinite(temperature) ? temperature : 0.7
  const safeMaxContextChars = Number.isFinite(maxContextChars) ? maxContextChars : 0
  const safeScoreThreshold = Number.isFinite(scoreThreshold) ? scoreThreshold : 0
  const safeLexicalTopK = Number.isFinite(lexicalTopK) ? lexicalTopK : 20
  const safeHybridDenseWeight = Number.isFinite(hybridDenseWeight) ? hybridDenseWeight : 0.6
  const safeHybridLexicalWeight = Number.isFinite(hybridLexicalWeight) ? hybridLexicalWeight : 0.4
  const safeBm25MinShouldMatch = Number.isFinite(bm25MinShouldMatch) ? bm25MinShouldMatch : 0
  const safeBm25UsePhrase = typeof bm25UsePhrase === 'boolean' ? bm25UsePhrase : true
  const [showAdvancedBm25, setShowAdvancedBm25] = useState(false)
  const [linkHybridWeights, setLinkHybridWeights] = useState(true)
  const matchModeOptions = bm25MatchModes && bm25MatchModes.length > 0 ? bm25MatchModes : []
  const analyzerOptions = bm25Analyzers && bm25Analyzers.length > 0 ? bm25Analyzers : []
  const matchModeValue = bm25MatchMode ?? matchModeOptions[0] ?? ''
  const analyzerValue = bm25Analyzer ?? analyzerOptions[0] ?? ''
  const matchModeDisabled = matchModeOptions.length === 0
  const analyzerDisabled = analyzerOptions.length === 0

  const clamp01 = (value: number) => Math.min(1, Math.max(0, value))
  const handleDenseWeightChange = (value: number) => {
    const nextDense = clamp01(value)
    onHybridDenseWeightChange(nextDense)
    if (linkHybridWeights) {
      const nextLexical = Number((1 - nextDense).toFixed(2))
      onHybridLexicalWeightChange(nextLexical)
    }
  }

  const handleLexicalWeightChange = (value: number) => {
    const nextLexical = clamp01(value)
    onHybridLexicalWeightChange(nextLexical)
    if (linkHybridWeights) {
      const nextDense = Number((1 - nextLexical).toFixed(2))
      onHybridDenseWeightChange(nextDense)
    }
  }

  return (
    <div className="bg-gray-800 border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Chat Settings</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={onResetDefaults}
              className="text-xs px-2 py-1 rounded border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
            >
              Reset to defaults
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Close settings"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Structure-based Search Toggle */}
        <div className="mb-6 p-4 bg-gray-900 rounded-lg border border-gray-700">
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={useStructure}
              onChange={(e) => onUseStructureChange(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
            />
            <div className="flex-1">
              <span className="text-sm font-medium text-white">
                Use Document Structure for Search
              </span>
              <span className="ml-2 text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">
                Experimental
              </span>
              <p className="text-xs text-gray-400 mt-1">
                Enable AI-powered structure analysis to find specific questions, sections, and chapters.
                Works best with queries like "show me question 2" or "section 3.1".
              </p>
            </div>
          </label>
        </div>

        {/* MMR (Diversity-Aware Search) */}
        <div className="mb-6 p-4 bg-gray-900 rounded-lg border border-gray-700">
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={useMmr}
              onChange={(e) => onUseMmrChange(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
            />
            <div className="flex-1">
              <span className="text-sm font-medium text-white">
                Enable MMR (Diversity-Aware Search)
              </span>
              <p className="text-xs text-gray-400 mt-1">
                Balances relevance and diversity to avoid too many similar chunks from the same section.
              </p>
              <div className="mt-2 p-2 bg-gray-800 rounded text-xs text-gray-400 space-y-1">
                <p className="font-medium text-gray-300">💡 When to use:</p>
                <p>• <span className="text-blue-400">0.3-0.4</span> — Precision focus (legal docs, technical specs)</p>
                <p>• <span className="text-green-400">0.5-0.6</span> — Balanced (recommended default) ⭐</p>
                <p>• <span className="text-purple-400">0.7-0.8</span> — Broad exploration (research, brainstorming)</p>
                <p className="mt-1 pt-1 border-t border-gray-700 text-gray-500">
                  Higher diversity = more varied sources, lower avg relevance score
                </p>
              </div>
            </div>
          </label>

          {useMmr && (
            <div className="mt-4 pl-8">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Diversity: {mmrDiversity.toFixed(2)}
                <span className="ml-2 text-xs text-gray-500">
                  ({mmrDiversity < 0.4 ? 'Focus' : mmrDiversity < 0.7 ? 'Balanced' : 'Explore'})
                </span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={mmrDiversity}
                onChange={(e) => onMmrDiversityChange(Number(e.target.value))}
                className="slider w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0.0 - Pure relevance</span>
                <span>0.5 - Balanced</span>
                <span>1.0 - Max diversity</span>
              </div>
            </div>
          )}
        </div>

        {/* Self-Check Validation Toggle */}
        <div className="mb-6 p-4 bg-gray-900 rounded-lg border border-gray-700">
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={useSelfCheck}
              onChange={(e) => onUseSelfCheckChange(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
            />
            <div className="flex-1">
              <span className="text-sm font-medium text-white">
                Enable Self-Check Validation
              </span>
              <p className="text-xs text-gray-400 mt-1">
                Validates generated answers against retrieved context to ensure accuracy and prevent hallucinations.
                The system generates a draft answer, then validates it for factual grounding before returning.
              </p>
            </div>
          </label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* LLM Model */}
          <div>
            <LLMSelector
              value={llmModel}
              onChange={onLLMChange}
            />

            <label className="block text-sm font-medium text-gray-300 mt-8 mb-2">
              Retrieval mode
            </label>
            <select
              value={retrievalMode}
              onChange={(e) => onRetrievalModeChange(e.target.value as 'dense' | 'hybrid')}
              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
            >
              <option value="dense">Dense (vector)</option>
              <option value="hybrid">Hybrid (BM25 + vector)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Hybrid combines lexical BM25 with semantic vectors
            </p>
          </div>

          {/* Top K */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Number of sources (Top K): {safeTopK}
            </label>
            <input
              type="range"
              min="1"
              max="100"
              step="1"
              value={safeTopK}
              onChange={(e) => onTopKChange(Number(e.target.value))}
              className="slider w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              How many relevant chunks to retrieve from the knowledge base
            </p>

            <label className="block text-sm font-medium text-gray-300 mt-8 mb-2">
              Max context chars (0 = unlimited)
            </label>
            <input
              type="number"
              min="0"
              step="1000"
              value={safeMaxContextChars}
              onChange={(e) => onMaxContextCharsChange(Number(e.target.value))}
              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-px text-gray-100"
            />
            <p className="text-xs text-gray-500 mt-1">
              Larger values include more retrieved text in the prompt
            </p>

          </div>

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Temperature: {safeTemperature.toFixed(1)}
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={safeTemperature}
              onChange={(e) => onTemperatureChange(Number(e.target.value))}
              className="slider w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Lower = more focused and deterministic, Higher = more creative and varied
            </p>

            <label className="block text-sm font-medium text-gray-300 mt-4 mb-2">
              Score threshold (0–1)
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={safeScoreThreshold}
              onChange={(e) => onScoreThresholdChange(Number(e.target.value))}
              className="slider w-full"
            />
            <div className="text-xs text-gray-400 mt-1">Current: {safeScoreThreshold.toFixed(2)}</div>
            <p className="text-xs text-gray-500 mt-1">
              0 = no filter, higher = stricter filtering of low‑relevance chunks
            </p>
          </div>
        </div>

        {retrievalMode === 'hybrid' && (
          <div className="mt-6 rounded-lg border border-gray-700 bg-gray-900/60 p-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-white">BM25 / Hybrid Settings</h4>
              <div className="flex items-center gap-2 text-xs">
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
            <p className="mt-2 text-xs text-gray-500">
              Tune lexical matching and how BM25 blends with vectors. Basic is safe defaults; Advanced changes analyzer
              and usually requires reindex.
            </p>
            <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
              <input
                id="link-hybrid-weights"
                type="checkbox"
                checked={linkHybridWeights}
                onChange={(e) => setLinkHybridWeights(e.target.checked)}
                className="rounded border-gray-600 bg-gray-800"
              />
              <label htmlFor="link-hybrid-weights">
                Link weights (lexical = 1 − dense)
              </label>
            </div>
            <p className="mt-1 text-[11px] text-gray-500">
              Weights are normalized server-side if they don’t sum to 1.0.
            </p>

            {opensearchAvailable === false && (
              <div className="mt-3 rounded border border-yellow-500/40 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-200">
                OpenSearch is not reachable. Hybrid search may fail until it is available.
              </div>
            )}

            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Lexical Top K: {safeLexicalTopK}
                </label>
                <input
                  type="range"
                  min="1"
                  max="200"
                  step="1"
                  value={safeLexicalTopK}
                  onChange={(e) => onLexicalTopKChange(Number(e.target.value))}
                  className="slider w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Candidate pool from BM25 before merging
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Hybrid dense weight: {safeHybridDenseWeight.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={safeHybridDenseWeight}
                  onChange={(e) => handleDenseWeightChange(Number(e.target.value))}
                  className="slider w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Higher = more semantic/vector influence
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Hybrid lexical weight: {safeHybridLexicalWeight.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={safeHybridLexicalWeight}
                  onChange={(e) => handleLexicalWeightChange(Number(e.target.value))}
                  className="slider w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Higher = more BM25/keyword influence
                </p>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Match mode
                </label>
                <select
                  value={matchModeValue}
                  onChange={(e) => onBm25MatchModeChange(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
                  disabled={matchModeDisabled}
                >
                  {matchModeDisabled && <option value="">Loading…</option>}
                  {matchModeOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Controls how many query terms must appear
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Minimum should match: {safeBm25MinShouldMatch}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={safeBm25MinShouldMatch}
                  onChange={(e) => onBm25MinShouldMatchChange(Number(e.target.value))}
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
                    checked={safeBm25UsePhrase}
                    onChange={(e) => onBm25UsePhraseChange(e.target.checked)}
                    className="w-4 h-4 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
                  />
                  Include exact phrase matches
                </label>
                <p className="text-xs text-gray-500 mt-1">
                  Helps when the wording matters, but can miss paraphrases
                </p>
              </div>
            </div>

            {showAdvancedBm25 && (
              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Analyzer profile
                  </label>
                  <select
                    value={analyzerValue}
                    onChange={(e) => onBm25AnalyzerChange(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
                    disabled={analyzerDisabled}
                  >
                    {analyzerDisabled && <option value="">Loading…</option>}
                    {analyzerOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Requires reindex if the analyzer profile changes
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="mt-4 p-3 bg-gray-900 rounded-lg border border-gray-700">
          <p className="text-xs text-gray-400">
            💡 <strong>Tip:</strong> Increase Top K for more comprehensive answers. Lower
            temperature for factual responses, higher for creative interpretations.
          </p>
        </div>
      </div>
    </div>
  )
}
