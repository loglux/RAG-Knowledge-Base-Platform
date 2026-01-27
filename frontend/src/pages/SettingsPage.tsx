import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../services/api'
import { LLMSelector } from '../components/chat/LLMSelector'
import type { AppSettings } from '../types/index'

export function SettingsPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedAt, setSavedAt] = useState<string | null>(null)

  const [llmModel, setLlmModel] = useState('gpt-4o')
  const [llmProvider, setLlmProvider] = useState('openai')
  const [temperature, setTemperature] = useState(0.7)
  const [topK, setTopK] = useState(5)
  const [maxContextChars, setMaxContextChars] = useState(0)
  const [scoreThreshold, setScoreThreshold] = useState(0)
  const [useStructure, setUseStructure] = useState(false)

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
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load settings')
      } finally {
        setLoading(false)
      }
    }

    loadSettings()
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
            </div>

            <div className="flex items-center justify-end">
              <button
                onClick={handleSave}
                disabled={saving}
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
