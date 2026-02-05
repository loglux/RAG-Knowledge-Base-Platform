import React from 'react'
import { Button } from '../common/Button'
import { useNavigate } from 'react-router-dom'
import type { KnowledgeBase } from '../../types/index'

interface KBCardProps {
  kb: KnowledgeBase
  onDelete?: (id: string) => void
}

export function KBCard({ kb, onDelete }: KBCardProps) {
  const navigate = useNavigate()

  const formattedDate = new Date(kb.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onDelete && confirm(`Delete "${kb.name}"? This action cannot be undone.`)) {
      onDelete(kb.id)
    }
  }

  const handleChatClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigate(`/kb/${kb.id}/chat`)
  }

  const handleDocumentsClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigate(`/kb/${kb.id}`)
  }

  const getProviderBadgeColor = (provider: string) => {
    switch (provider) {
      case 'openai': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'voyage': return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'ollama': return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  return (
    <div className="card hover:shadow-xl transition-all hover:scale-105">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-white flex-1">{kb.name}</h3>
      </div>

      {kb.description && (
        <p className="text-gray-400 text-sm mb-4 line-clamp-2">{kb.description}</p>
      )}

      {/* Embedding Model Badge */}
      <div className="mb-4">
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs ${getProviderBadgeColor(kb.embedding_provider)}`}>
          <span className="font-medium">{kb.embedding_provider.toUpperCase()}</span>
          <span className="opacity-60">•</span>
          <span className="opacity-90">{kb.embedding_model}</span>
          <span className="opacity-60">•</span>
          <span className="opacity-75">{kb.embedding_dimension}d</span>
        </div>
      </div>

      <div className="space-y-2 mb-4 text-sm text-gray-400">
        <div className="flex justify-between">
          <span>Documents:</span>
          <span className="text-white font-medium">{kb.document_count}</span>
        </div>
        <div className="flex justify-between">
          <span>Chunks:</span>
          <span className="text-white font-medium">{kb.total_chunks}</span>
        </div>
        <div className="flex justify-between">
          <span>Created:</span>
          <span className="text-gray-300">{formattedDate}</span>
        </div>
      </div>

      <div className="pt-4 border-t border-gray-700 flex space-x-2">
        <Button
          variant="primary"
          size="sm"
          className="flex-1"
          onClick={handleChatClick}
        >
          💬 Chat
        </Button>
        <Button
          size="sm"
          className="flex-1"
          onClick={handleDocumentsClick}
        >
          📄 Documents
        </Button>
        {onDelete && (
          <Button
            size="sm"
            className="px-3"
            onClick={handleDelete}
            aria-label="Delete knowledge base"
          >
            🗑️
          </Button>
        )}
      </div>
    </div>
  )
}
