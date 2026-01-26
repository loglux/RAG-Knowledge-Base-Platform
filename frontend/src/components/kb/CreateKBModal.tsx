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
    chunking_strategy: 'fixed_size',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [embeddingModels, setEmbeddingModels] = useState<EmbeddingModel[]>([])
  const [loadingModels, setLoadingModels] = useState(true)

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
        chunk_size: 1000,
        chunk_overlap: 200,
        chunking_strategy: 'fixed_size',
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
        chunk_size: 1000,
        chunk_overlap: 200,
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
