import React, { useState } from 'react'
import { apiClient } from '../../services/api'
import type { Document } from '../../types/index'

interface DocumentItemProps {
  document: Document
  onReprocess?: (id: string) => void
  onDelete?: (id: string) => void
  onRecomputeDuplicates?: (id: string) => Promise<any>
}

const STRUCTURED_TYPES = ['fb2', 'docx', 'pdf', 'md']

export function DocumentItem({ document, onReprocess, onDelete, onRecomputeDuplicates }: DocumentItemProps) {
  const [isRecomputingDup, setIsRecomputingDup] = useState(false)
  const [headingMap, setHeadingMap] = useState<Array<{ pos: number; level: number; text: string }> | null>(null)
  const [headingMapLoading, setHeadingMapLoading] = useState(false)
  const [headingMapLoaded, setHeadingMapLoaded] = useState(false)

  const handleStructureToggle = async (e: React.MouseEvent<HTMLDetailsElement>) => {
    const details = e.currentTarget
    if (details.open || headingMapLoaded) return
    setHeadingMapLoading(true)
    try {
      const full = await apiClient.getDocument(document.id)
      setHeadingMap(full.heading_map ?? null)
    } catch {
      setHeadingMap(null)
    } finally {
      setHeadingMapLoading(false)
      setHeadingMapLoaded(true)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins} min ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return `${Math.floor(diffMins / 1440)}d ago`
  }

  const getStatusIcon = () => {
    switch (document.status) {
      case 'completed':
        return '✅'
      case 'processing':
        return '⚙️'
      case 'pending':
        return '⏳'
      case 'failed':
        return '❌'
      default:
        return '📄'
    }
  }

  const getStatusColor = () => {
    switch (document.status) {
      case 'completed':
        return 'text-green-500'
      case 'processing':
        return 'text-blue-500'
      case 'pending':
        return 'text-yellow-500'
      case 'failed':
        return 'text-red-500'
      default:
        return 'text-gray-500'
    }
  }

  const getIndexStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return '✅'
      case 'processing':
        return '⚙️'
      case 'pending':
        return '⏳'
      case 'failed':
        return '❌'
      default:
        return '•'
    }
  }

  const getIndexStatusClass = (status: string) => {
    switch (status) {
      case 'completed':
        return 'border-green-500/40 text-green-400 bg-green-500/10'
      case 'processing':
        return 'border-blue-500/40 text-blue-400 bg-blue-500/10'
      case 'pending':
        return 'border-yellow-500/40 text-yellow-400 bg-yellow-500/10'
      case 'failed':
        return 'border-red-500/40 text-red-400 bg-red-500/10'
      default:
        return 'border-gray-500/40 text-gray-400 bg-gray-500/10'
    }
  }

  const handleDelete = () => {
    if (onDelete && confirm(`Delete "${document.filename}"?`)) {
      onDelete(document.id)
    }
  }

  const handleRecomputeDuplicates = async () => {
    if (!onRecomputeDuplicates) return
    setIsRecomputingDup(true)
    try {
      await onRecomputeDuplicates(document.id)
    } catch (error) {
      console.error('Failed to recompute duplicates:', error)
      alert(error instanceof Error ? error.message : 'Failed to recompute duplicates')
    } finally {
      setIsRecomputingDup(false)
    }
  }

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <div className="text-2xl">{getStatusIcon()}</div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <h3 className="text-white font-medium truncate">{document.filename}</h3>
              <span className={`text-xs ${getStatusColor()} uppercase`}>{document.status}</span>
            </div>

            <div className="flex items-center space-x-4 mt-1 text-sm text-gray-400">
              <span>{document.chunk_count} chunks</span>
              <span>•</span>
              <span>{formatFileSize(document.file_size)}</span>
              <span>•</span>
              <span>📅 {formatDate(document.created_at)}</span>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              {(() => {
                const embeddingsStatus = document.embeddings_status ?? document.status
                const bm25Status = document.bm25_status ?? 'pending'
                return (
                  <>
                    <span
                      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 ${getIndexStatusClass(embeddingsStatus)}`}
                    >
                      Embeddings {getIndexStatusIcon(embeddingsStatus)}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 ${getIndexStatusClass(bm25Status)}`}
                    >
                      BM25 {getIndexStatusIcon(bm25Status)}
                    </span>
                  </>
                )
              })()}
            </div>

            {document.error_message && (
              <div className="mt-2 text-sm text-red-500">
                Error: {document.error_message}
              </div>
            )}

            {document.status === 'processing' && (
              <div className="mt-2">
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full transition-all duration-300"
                    style={{ width: `${document.progress_percentage || 0}%` }}
                  ></div>
                </div>
                <div className="flex justify-between items-center mt-1">
                  <p className="text-xs text-gray-400">
                    {document.processing_stage || 'Processing...'}
                  </p>
                  <p className="text-xs text-gray-500 font-medium">
                    {document.progress_percentage || 0}%
                  </p>
                </div>
              </div>
            )}

            {document.status === 'completed' && STRUCTURED_TYPES.includes(document.file_type) && (
              <details className="mt-3 text-xs text-gray-400" onClick={handleStructureToggle}>
                <summary className="cursor-pointer select-none text-gray-300">
                  Structure
                  {headingMapLoading && <span className="ml-2 text-gray-500">loading…</span>}
                  {headingMapLoaded && headingMap && (
                    <span className="ml-2 text-gray-500">({headingMap.length} headings)</span>
                  )}
                  {headingMapLoaded && !headingMap && (
                    <span className="ml-2 text-gray-500">(no headings)</span>
                  )}
                </summary>
                {headingMapLoaded && headingMap && headingMap.length > 0 && (
                  <div className="mt-2 space-y-0.5 max-h-64 overflow-y-auto font-mono">
                    {headingMap.map((h, idx) => (
                      <div
                        key={idx}
                        className="truncate text-gray-400"
                        style={{ paddingLeft: `${(h.level - 1) * 12}px` }}
                        title={h.text}
                      >
                        <span className="text-gray-600 mr-1">{'›'.repeat(h.level)}</span>
                        {h.text}
                      </div>
                    ))}
                  </div>
                )}
              </details>
            )}

            {document.duplicate_chunks && document.duplicate_chunks.total_groups > 0 && (
              <details className="mt-3 text-xs text-gray-400">
                <summary className="cursor-pointer select-none text-gray-300">
                  Duplicates: {document.duplicate_chunks.total_groups} groups
                  <span className="ml-2 text-gray-500">
                    ({document.duplicate_chunks.total_chunks} chunks)
                  </span>
                </summary>
                <div className="mt-2 space-y-1">
                  {document.duplicate_chunks.groups.slice(0, 5).map((group, idx) => (
                    <div key={idx} className="text-gray-500">
                      chunks: {group.chunks.join(', ')}
                    </div>
                  ))}
                  {document.duplicate_chunks.groups.length > 5 && (
                    <div className="text-gray-500">
                      +{document.duplicate_chunks.groups.length - 5} more groups
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2 ml-4">
          {document.status === 'completed' && onRecomputeDuplicates && (
            <button
              onClick={handleRecomputeDuplicates}
              disabled={isRecomputingDup}
              className="text-gray-400 hover:text-amber-400 p-2 rounded transition-colors disabled:opacity-50"
              aria-label="Recompute duplicate chunks"
              title={isRecomputingDup ? 'Recomputing duplicates...' : 'Recompute duplicate chunks'}
            >
              {isRecomputingDup ? '⏳' : '🧮'}
            </button>
          )}

          {document.status === 'completed' && onReprocess && (
            <button
              onClick={() => onReprocess(document.id)}
              className="text-gray-400 hover:text-white p-2 rounded transition-colors"
              aria-label="Reprocess document"
              title="Reprocess"
            >
              🔄
            </button>
          )}

          {document.status === 'failed' && onReprocess && (
            <button
              onClick={() => onReprocess(document.id)}
              className="text-yellow-500 hover:text-yellow-400 p-2 rounded transition-colors"
              aria-label="Retry processing"
              title="Retry"
            >
              🔄
            </button>
          )}

          {onDelete && (
            <button
              onClick={handleDelete}
              className="text-gray-400 hover:text-red-500 p-2 rounded transition-colors"
              aria-label="Delete document"
              title="Delete"
            >
              🗑️
            </button>
          )}
        </div>
      </div>

    </div>
  )
}
