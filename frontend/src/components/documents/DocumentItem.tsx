import React, { useState, useEffect } from 'react'
import type { Document } from '../../types/index'
import { apiClient } from '../../services/api'
import { StructureAnalysisModal } from './StructureAnalysisModal'

interface DocumentItemProps {
  document: Document
  onReprocess?: (id: string) => void
  onDelete?: (id: string) => void
  onAnalyze?: (id: string) => Promise<any>
}

export function DocumentItem({ document, onReprocess, onDelete, onAnalyze }: DocumentItemProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [hasStructure, setHasStructure] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)

  // Check if document already has structure
  useEffect(() => {
    const checkStructure = async () => {
      if (document.status === 'completed') {
        try {
          const structure = await apiClient.getDocumentStructure(document.id)
          if (structure.has_structure) {
            setHasStructure(true)
          }
        } catch {
          // Structure doesn't exist yet
        }
      }
    }
    checkStructure()
  }, [document.id, document.status])

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

  const handleAnalyze = async () => {
    if (!onAnalyze) return

    setIsAnalyzing(true)
    try {
      const result = await onAnalyze(document.id)
      console.log('Analysis result:', result)
      setAnalysisResult(result)
      setShowModal(true)
    } catch (error) {
      console.error('Analysis failed:', error)
      alert(error instanceof Error ? error.message : 'Analysis failed')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleApplyStructure = async (analysis: any) => {
    try {
      await apiClient.applyDocumentStructure(document.id, analysis)
      setHasStructure(true)
      setAnalysisResult(analysis) // Save for viewing later
      alert('Structure applied successfully!')
    } catch (error) {
      console.error('Failed to apply structure:', error)
      alert(error instanceof Error ? error.message : 'Failed to apply structure')
    }
  }

  const handleViewStructure = async () => {
    if (analysisResult) {
      // Already have it in memory
      setShowModal(true)
      return
    }

    // Load from backend
    try {
      const structure = await apiClient.getDocumentStructure(document.id)
      if (structure.has_structure) {
        // Convert to analysis format
        const analysis = {
          document_id: document.id,
          filename: document.filename,
          document_type: structure.document_type || 'unknown',
          description: 'Saved structure',
          total_sections: structure.sections.length,
          sections: structure.sections,
        }
        setAnalysisResult(analysis)
        setShowModal(true)
      }
    } catch (error) {
      console.error('Failed to load structure:', error)
      alert('Failed to load structure')
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
          </div>
        </div>

        <div className="flex items-center space-x-2 ml-4">
          {hasStructure && (
            <button
              onClick={handleViewStructure}
              className="text-yellow-400 hover:text-yellow-300 transition-colors"
              title="View structure (click to see)"
            >
              ✨
            </button>
          )}

          {document.status === 'completed' && onAnalyze && (
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className="text-gray-400 hover:text-blue-400 p-2 rounded transition-colors disabled:opacity-50"
              aria-label="Analyze structure"
              title={isAnalyzing ? "Analyzing..." : "Analyze structure"}
            >
              {isAnalyzing ? '⏳' : '🔍'}
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

      <StructureAnalysisModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        analysis={analysisResult}
        onApply={handleApplyStructure}
        isApplied={hasStructure}
      />
    </div>
  )
}
