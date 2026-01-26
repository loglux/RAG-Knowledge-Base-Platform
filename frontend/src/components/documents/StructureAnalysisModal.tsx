import React from 'react'

interface TOCSection {
  id: string
  title: string
  type: string
  chunk_start: number
  chunk_end: number
  metadata: Record<string, any>
  subsections?: TOCSection[]
}

interface StructureAnalysisResult {
  document_id: string
  filename: string
  document_type: string
  description: string
  total_sections: number
  sections: TOCSection[]
}

interface StructureAnalysisModalProps {
  isOpen: boolean
  onClose: () => void
  analysis: StructureAnalysisResult | null
  onApply?: (analysis: StructureAnalysisResult) => void
  isApplied?: boolean
}

export function StructureAnalysisModal({
  isOpen,
  onClose,
  analysis,
  onApply,
  isApplied = false,
}: StructureAnalysisModalProps) {
  if (!isOpen || !analysis) return null

  const renderSection = (section: TOCSection, level = 0) => {
    const indent = level * 20
    const icon = section.type === 'question' ? '❓' : section.type === 'header' ? '📋' : '📄'

    return (
      <div key={section.id} style={{ marginLeft: `${indent}px` }}>
        <div className="flex items-center space-x-2 py-1">
          <span>{icon}</span>
          <span className="text-white font-medium">{section.title}</span>
          <span className="text-gray-500 text-sm">
            chunks {section.chunk_start}-{section.chunk_end}
          </span>
          {section.metadata.question_number && (
            <span className="text-blue-400 text-xs">
              Q{section.metadata.question_number}
            </span>
          )}
          {section.metadata.marks && (
            <span className="text-yellow-400 text-xs">{section.metadata.marks} marks</span>
          )}
        </div>
        {section.subsections?.map((sub) => renderSection(sub, level + 1))}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white">📊 Structure Analysis</h2>
              <p className="text-sm text-gray-400 mt-1">{analysis.filename}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto max-h-96">
          {/* Summary */}
          <div className="mb-6 p-4 bg-gray-700 rounded-lg">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Document Type:</span>
                <span className="text-white ml-2 font-medium">{analysis.document_type}</span>
              </div>
              <div>
                <span className="text-gray-400">Sections Found:</span>
                <span className="text-white ml-2 font-medium">{analysis.total_sections}</span>
              </div>
            </div>
            <div className="mt-3">
              <span className="text-gray-400">Description:</span>
              <p className="text-white mt-1">{analysis.description}</p>
            </div>
          </div>

          {/* Table of Contents */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-3">📑 Table of Contents</h3>
            <div className="space-y-1 bg-gray-900 p-4 rounded-lg">
              {analysis.sections.map((section) => renderSection(section))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-700 flex justify-between items-center">
          <div>
            {isApplied && (
              <span className="text-yellow-400 text-sm">⚠️ Structure exists - re-analyzing will update it</span>
            )}
          </div>
          <div className="flex space-x-3">
            <button onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            {onApply && (
              <button
                onClick={() => {
                  onApply(analysis)
                  onClose()
                }}
                className="btn-primary"
              >
                {isApplied ? '🔄 Update Structure' : '✓ Apply Structure'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
