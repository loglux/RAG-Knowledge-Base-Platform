import React, { useState, useEffect } from 'react'
import { apiClient } from '../../services/api'

interface LLMModel {
  model: string
  provider: string
  context_window?: number
  cost_input?: number
  cost_output?: number
  description: string
  family?: string
  parameter_size?: string
}

interface LLMSelectorProps {
  value: string
  onChange: (model: string, provider: string) => void
  showOllama: boolean
  onShowOllamaChange: (value: boolean) => void
}

export function LLMSelector({ value, onChange, showOllama, onShowOllamaChange }: LLMSelectorProps) {
  const [models, setModels] = useState<LLMModel[]>([])
  const [loading, setLoading] = useState(true)
  const [groupBy, setGroupBy] = useState<'provider' | 'all'>('provider')

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await apiClient.getLLMModels()
        setModels(response.models)
      } catch (error) {
        console.error('Failed to fetch LLM models:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchModels()
  }, [])

  const selectedModel = models.find(m => m.model === value)

  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'openai': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'anthropic': return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      case 'ollama': return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  // Filter out Ollama models if not enabled
  const filteredModels = showOllama ? models : models.filter(m => m.provider !== 'ollama')

  const groupedModels = filteredModels.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = []
    }
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, LLMModel[]>)

  if (loading) {
    return <div className="text-sm text-gray-400">Loading models...</div>
  }

  return (
    <div className="space-y-3">
      <div>
        <div className="flex items-center justify-between mb-2">
          <label htmlFor="llm-model" className="block text-sm font-medium text-gray-300">
            LLM Model
          </label>
          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showOllama}
              onChange={(e) => onShowOllamaChange(e.target.checked)}
              className="rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500"
            />
            Show Ollama (slow)
          </label>
        </div>
        <select
          id="llm-model"
          value={value}
          onChange={(e) => {
            const model = models.find(m => m.model === e.target.value)
            if (model) {
              onChange(model.model, model.provider)
            }
          }}
          className="input w-full text-sm"
        >
          {groupBy === 'provider' ? (
            Object.entries(groupedModels).map(([provider, providerModels]) => (
              <optgroup key={provider} label={provider.toUpperCase()}>
                {providerModels.map(model => (
                  <option key={model.model} value={model.model}>
                    {model.model}
                    {model.cost_input !== undefined && model.cost_input > 0
                      ? ` ($${model.cost_input.toFixed(2)}/M)`
                      : ' (FREE)'}
                  </option>
                ))}
              </optgroup>
            ))
          ) : (
            filteredModels.map(model => (
              <option key={model.model} value={model.model}>
                [{model.provider.toUpperCase()}] {model.model}
              </option>
            ))
          )}
        </select>
      </div>

      {selectedModel && (
        <div className="p-3 bg-gray-800 border border-gray-700 rounded-lg space-y-2">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 text-xs rounded border ${getProviderColor(selectedModel.provider)}`}>
              {selectedModel.provider.toUpperCase()}
            </span>
            {selectedModel.context_window && (
              <>
                <span className="text-xs text-gray-400">•</span>
                <span className="text-xs text-gray-400">
                  {(selectedModel.context_window / 1000).toFixed(0)}K context
                </span>
              </>
            )}
            {selectedModel.cost_input !== undefined && (
              <>
                <span className="text-xs text-gray-400">•</span>
                <span className="text-xs text-gray-400">
                  {selectedModel.cost_input === 0
                    ? 'FREE (Local)'
                    : `$${selectedModel.cost_input.toFixed(2)}/$${selectedModel.cost_output?.toFixed(2)} per M`}
                </span>
              </>
            )}
          </div>
          <p className="text-xs text-gray-500">{selectedModel.description}</p>
          {selectedModel.family && (
            <p className="text-xs text-gray-600">Family: {selectedModel.family}</p>
          )}
          {selectedModel.parameter_size && (
            <p className="text-xs text-gray-600">Params: {selectedModel.parameter_size}</p>
          )}
        </div>
      )}
    </div>
  )
}
