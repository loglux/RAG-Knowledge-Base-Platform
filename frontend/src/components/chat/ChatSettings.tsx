import React from 'react'
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
  opensearchAvailable?: boolean
  llmModel: string
  llmProvider: string
  useStructure: boolean
  onTopKChange: (value: number) => void
  onTemperatureChange: (value: number) => void
  onMaxContextCharsChange: (value: number) => void
  onScoreThresholdChange: (value: number) => void
  onRetrievalModeChange: (value: 'dense' | 'hybrid') => void
  onLexicalTopKChange: (value: number) => void
  onHybridDenseWeightChange: (value: number) => void
  onHybridLexicalWeightChange: (value: number) => void
  onLLMChange: (model: string, provider: string) => void
  onUseStructureChange: (value: boolean) => void
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
  opensearchAvailable,
  llmModel,
  llmProvider,
  useStructure,
  onTopKChange,
  onTemperatureChange,
  onMaxContextCharsChange,
  onScoreThresholdChange,
  onRetrievalModeChange,
  onLexicalTopKChange,
  onHybridDenseWeightChange,
  onHybridLexicalWeightChange,
  onLLMChange,
  onUseStructureChange,
  onClose,
}: ChatSettingsProps) {
  const safeTopK = Number.isFinite(topK) ? topK : 5
  const safeTemperature = Number.isFinite(temperature) ? temperature : 0.7
  const safeMaxContextChars = Number.isFinite(maxContextChars) ? maxContextChars : 0
  const safeScoreThreshold = Number.isFinite(scoreThreshold) ? scoreThreshold : 0
  const safeLexicalTopK = Number.isFinite(lexicalTopK) ? lexicalTopK : 20
  const safeHybridDenseWeight = Number.isFinite(hybridDenseWeight) ? hybridDenseWeight : 0.6
  const safeHybridLexicalWeight = Number.isFinite(hybridLexicalWeight) ? hybridLexicalWeight : 0.4

  return (
    <div className="bg-gray-800 border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Chat Settings</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="Close settings"
          >
            ✕
          </button>
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
              <span className="text-xs text-gray-400">Lexical + dense weighting</span>
            </div>

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
                  onChange={(e) => onHybridDenseWeightChange(Number(e.target.value))}
                  className="slider w-full"
                />
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
                  onChange={(e) => onHybridLexicalWeightChange(Number(e.target.value))}
                  className="slider w-full"
                />
              </div>
            </div>
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
