import React, { useState } from 'react'
import type { SourceChunk } from '../../types/index'

interface SourceCardProps {
  source: SourceChunk
}

export function SourceCard({ source }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const confidencePercent = Math.round(source.score * 100)
  const confidenceColor =
    confidencePercent >= 80
      ? 'text-green-500'
      : confidencePercent >= 60
      ? 'text-yellow-500'
      : 'text-orange-500'

  const contentPreview = source.text.slice(0, 120)
  const hasMore = source.text.length > 120

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-gray-400">📄</span>
          <span className="text-white font-medium">{source.filename}</span>
          <span className="text-gray-500 text-xs">Chunk #{source.chunk_index}</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`font-mono text-xs ${confidenceColor}`}>{confidencePercent}%</span>
        </div>
      </div>

      <div className="text-gray-300 text-[11px] font-mono leading-tight whitespace-pre-wrap bg-gray-900 rounded p-3 max-h-96 overflow-y-auto break-all">
        {isExpanded ? source.text : contentPreview}
        {hasMore && !isExpanded && <span className="text-gray-500">...</span>}
      </div>

      {hasMore && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 text-xs text-primary-400 hover:text-primary-300 transition-colors"
        >
          {isExpanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}
