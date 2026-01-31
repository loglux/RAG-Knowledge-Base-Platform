import React, { useState, useEffect } from 'react'
import { Modal } from '../common/Modal'
import { apiClient } from '../../services/api'
import type { CreateKBRequest, EmbeddingModel } from '../../types/index'

interface CreateKBModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateKBRequest) => Promise<void>
}

export function CreateKBModal({ isOpen, onClose, onSubmit }: CreateKBModalProps) {
  const [formData, setFormData] = useState<CreateKBRequest>({
    name: '',
    description: '',
    embedding_model: 'text-embedding-3-large',
    chunk_size: 1000,
    chunk_overlap: 200,
    upsert_batch_size: 256,
    chunking_strategy: 'smart',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [embeddingModels, setEmbeddingModels] = useState<EmbeddingModel[]>([])
  const [loadingModels, setLoadingModels] = useState(true)
  const [kbDefaults, setKbDefaults] = useState({
    chunk_size: 1000,
    chunk_overlap: 200,
    upsert_batch_size: 256,
  })

  // Fetch available embedding models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const models = await apiClient.getEmbeddingModels()
        setEmbeddingModels(models)
      } catch (error) {
        console.error('Failed to fetch embedding models:', error)
      } finally {
        setLoadingModels(false)
      }
    }
    fetchModels()
  }, [])

  // Load KB defaults from global settings when modal opens
  useEffect(() => {
    if (!isOpen) return
    const loadDefaults = async () => {
      try {
        const settings = await apiClient.getAppSettings()
        const defaults = {
          chunk_size: settings.kb_chunk_size ?? 1000,
          chunk_overlap: settings.kb_chunk_overlap ?? 200,
          upsert_batch_size: settings.kb_upsert_batch_size ?? 256,
        }
        setKbDefaults(defaults)
        setFormData((prev) => ({
          ...prev,
          chunk_size: defaults.chunk_size,
          chunk_overlap: defaults.chunk_overlap,
          upsert_batch_size: defaults.upsert_batch_size,
        }))
      } catch (error) {
        console.error('Failed to load KB defaults:', error)
      }
    }
    loadDefaults()
  }, [isOpen])

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required'
    } else if (formData.name.length < 3) {
      newErrors.name = 'Name must be at least 3 characters'
    } else if (formData.name.length > 100) {
      newErrors.name = 'Name must be less than 100 characters'
    }

    if (formData.description && formData.description.length > 500) {
      newErrors.description = 'Description must be less than 500 characters'
    }

    if (formData.chunk_size < 100 || formData.chunk_size > 2000) {
      newErrors.chunk_size = 'Chunk size must be between 100 and 2000'
    }

    if (formData.chunk_overlap < 0 || formData.chunk_overlap > 500) {
      newErrors.chunk_overlap = 'Chunk overlap must be between 0 and 500'
    }

    if (formData.chunk_overlap >= formData.chunk_size) {
      newErrors.chunk_overlap = 'Chunk overlap must be less than chunk size'
    }

    if (formData.upsert_batch_size < 64 || formData.upsert_batch_size > 1024) {
      newErrors.upsert_batch_size = 'Batch size must be between 64 and 1024'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) {
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit(formData)
      // Reset form on success
        setFormData({
          name: '',
          description: '',
          embedding_model: 'text-embedding-3-large',
          chunk_size: kbDefaults.chunk_size,
          chunk_overlap: kbDefaults.chunk_overlap,
          upsert_batch_size: kbDefaults.upsert_batch_size,
          chunking_strategy: 'smart',
        })
      setErrors({})
      onClose()
    } catch (error) {
      setErrors({ submit: error instanceof Error ? error.message : 'Failed to create knowledge base' })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      setFormData({
        name: '',
        description: '',
        embedding_model: 'text-embedding-3-large',
        chunk_size: kbDefaults.chunk_size,
        chunk_overlap: kbDefaults.chunk_overlap,
        upsert_batch_size: kbDefaults.upsert_batch_size,
        chunking_strategy: 'fixed_size',
      })
      setErrors({})
      onClose()
    }
  }

  const selectedModel = embeddingModels.find(m => m.model === formData.embedding_model)

  const getProviderBadgeColor = (provider: string) => {
    switch (provider) {
      case 'openai': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'voyage': return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'ollama': return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const chunkingStrategies = [
    {
      value: 'simple',
      label: 'Simple (Fixed-Size)',
      description: 'Fast, basic chunking. Splits text at fixed character positions with overlap.',
      icon: '⚡',
      recommended: false,
      recommendedChunkSize: '1000-1500',
      recommendedOverlap: '150-250 (15-20% of size)',
    },
    {
      value: 'smart',
      label: 'Smart (Recursive)',
      description: 'Intelligent chunking that respects paragraph, sentence, and word boundaries.',
      icon: '🧠',
      recommended: true,
      recommendedChunkSize: '1500-2000',
      recommendedOverlap: '250-350 (15-20% of size)',
    },
    {
      value: 'semantic',
      label: 'Semantic (Coming Soon)',
      description: 'Advanced chunking using embeddings to identify semantic boundaries.',
      icon: '🎯',
      recommended: false,
      disabled: true,
      recommendedChunkSize: 'TBD',
      recommendedOverlap: 'TBD',
    },
  ]

  const selectedStrategy = chunkingStrategies.find(s => s.value === formData.chunking_strategy)

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create Knowledge Base" maxWidth="lg">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name field */}
        <div>
          <label htmlFor="kb-name" className="block text-sm font-medium text-gray-300 mb-2">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            id="kb-name"
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className={`input w-full ${errors.name ? 'border-red-500' : ''}`}
            placeholder="e.g., Python Documentation"
            disabled={isSubmitting}
            autoFocus
          />
          {errors.name && <p className="mt-1 text-sm text-red-500">{errors.name}</p>}
        </div>

        {/* Description field */}
        <div>
          <label htmlFor="kb-description" className="block text-sm font-medium text-gray-300 mb-2">
            Description (optional)
          </label>
          <textarea
            id="kb-description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className={`input w-full resize-none ${errors.description ? 'border-red-500' : ''}`}
            placeholder="e.g., Official Python 3.12 documentation"
            rows={3}
            disabled={isSubmitting}
          />
          {errors.description && <p className="mt-1 text-sm text-red-500">{errors.description}</p>}
        </div>

        {/* Embedding Model Selector */}
        <div>
          <label htmlFor="embedding-model" className="block text-sm font-medium text-gray-300 mb-2">
            Embedding Model <span className="text-red-500">*</span>
          </label>
          {loadingModels ? (
            <div className="input w-full text-gray-500">Loading models...</div>
          ) : (
            <>
              <select
                id="embedding-model"
                value={formData.embedding_model}
                onChange={(e) => setFormData({ ...formData, embedding_model: e.target.value })}
                className="input w-full"
                disabled={isSubmitting}
              >
                {embeddingModels.map((model) => (
                  <option key={model.model} value={model.model}>
                    {model.model} ({model.provider.toUpperCase()} - {model.dimension}d)
                  </option>
                ))}
              </select>

              {selectedModel && (
                <div className="mt-3 p-3 bg-gray-800 border border-gray-700 rounded-lg space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs rounded border ${getProviderBadgeColor(selectedModel.provider)}`}>
                      {selectedModel.provider.toUpperCase()}
                    </span>
                    <span className="text-xs text-gray-400">
                      {selectedModel.dimension} dimensions
                    </span>
                    <span className="text-xs text-gray-400">•</span>
                    <span className="text-xs text-gray-400">
                      ${selectedModel.cost_per_million_tokens.toFixed(2)}/M tokens
                      {selectedModel.cost_per_million_tokens === 0 && ' (FREE)'}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">{selectedModel.description}</p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Chunking Strategy Selector */}
        <div>
          <label htmlFor="chunking-strategy" className="block text-sm font-medium text-gray-300 mb-2">
            Chunking Strategy <span className="text-red-500">*</span>
          </label>
          <select
            id="chunking-strategy"
            value={formData.chunking_strategy}
            onChange={(e) => setFormData({ ...formData, chunking_strategy: e.target.value })}
            className="input w-full"
            disabled={isSubmitting}
          >
            {chunkingStrategies.map((strategy) => (
              <option key={strategy.value} value={strategy.value} disabled={strategy.disabled}>
                {strategy.icon} {strategy.label} {strategy.recommended ? '(Recommended)' : ''}
              </option>
            ))}
          </select>

          {selectedStrategy && (
            <div className="mt-3 p-3 bg-gray-800 border border-gray-700 rounded-lg">
              <div className="flex items-start gap-2">
                <span className="text-2xl">{selectedStrategy.icon}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-white">{selectedStrategy.label}</span>
                    {selectedStrategy.recommended && (
                      <span className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded">
                        Recommended
                      </span>
                    )}
                    {selectedStrategy.disabled && (
                      <span className="px-2 py-0.5 text-xs bg-gray-500/20 text-gray-400 border border-gray-500/30 rounded">
                        Coming Soon
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mb-2">{selectedStrategy.description}</p>
                  {selectedStrategy.recommendedChunkSize && (
                    <div className="space-y-1">
                      <p className="text-xs text-gray-500">
                        💡 Recommended chunk size: <span className="text-blue-400">{selectedStrategy.recommendedChunkSize}</span> chars
                      </p>
                      {selectedStrategy.recommendedOverlap && (
                        <p className="text-xs text-gray-500">
                        💡 Recommended overlap: <span className="text-blue-400">{selectedStrategy.recommendedOverlap}</span> chars
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Advanced Settings */}
        <div className="pt-4 border-t border-gray-700">
          <h3 className="text-sm font-medium text-gray-300 mb-4">Advanced Settings (optional)</h3>

          {/* Chunk Size */}
          <div className="mb-4">
            <label htmlFor="chunk-size" className="block text-sm text-gray-400 mb-2">
              Chunk Size: <span className="text-white font-medium">{formData.chunk_size}</span> characters
            </label>
            <input
              id="chunk-size"
              type="range"
              min="100"
              max="2000"
              step="100"
              value={formData.chunk_size}
              onChange={(e) => setFormData({ ...formData, chunk_size: parseInt(e.target.value) })}
              className="w-full"
              disabled={isSubmitting}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>100</span>
              <span>2000</span>
            </div>
            {errors.chunk_size && <p className="mt-1 text-sm text-red-500">{errors.chunk_size}</p>}
          </div>

          {/* Chunk Overlap */}
          <div>
            <label htmlFor="chunk-overlap" className="block text-sm text-gray-400 mb-2">
              Chunk Overlap: <span className="text-white font-medium">{formData.chunk_overlap}</span> characters
              <span className="text-gray-500">
                {' '}({formData.chunk_size > 0 ? Math.round((formData.chunk_overlap / formData.chunk_size) * 100) : 0}%)
              </span>
            </label>
            <input
              id="chunk-overlap"
              type="range"
              min="0"
              max="500"
              step="50"
              value={formData.chunk_overlap}
              onChange={(e) => setFormData({ ...formData, chunk_overlap: parseInt(e.target.value) })}
              className="w-full"
              disabled={isSubmitting}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0</span>
              <span>500</span>
            </div>
            {errors.chunk_overlap && <p className="mt-1 text-sm text-red-500">{errors.chunk_overlap}</p>}
          </div>

          {/* Upsert Batch Size */}
          <div className="mt-4">
            <label htmlFor="upsert-batch-size" className="block text-sm text-gray-400 mb-2">
              Upsert Batch Size: <span className="text-white font-medium">{formData.upsert_batch_size}</span>
            </label>
            <input
              id="upsert-batch-size"
              type="range"
              min="64"
              max="1024"
              step="64"
              value={formData.upsert_batch_size}
              onChange={(e) => setFormData({ ...formData, upsert_batch_size: parseInt(e.target.value) })}
              className="w-full"
              disabled={isSubmitting}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>64</span>
              <span>1024</span>
            </div>
            {errors.upsert_batch_size && <p className="mt-1 text-sm text-red-500">{errors.upsert_batch_size}</p>}
          </div>
        </div>

        {/* Submit error */}
        {errors.submit && (
          <div className="p-3 bg-red-500 bg-opacity-10 border border-red-500 rounded text-sm text-red-500">
            {errors.submit}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Creating...' : 'Create KB'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
