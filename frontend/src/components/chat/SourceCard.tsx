import React, { useState } from 'react'
import type { SourceChunk } from '../../types/index'

interface SourceCardProps {
  source: SourceChunk
  index: number
  anchorPrefix?: string
}

export function SourceCard({ source, index, anchorPrefix }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const anchorId = anchorPrefix ? `${anchorPrefix}-${index + 1}` : undefined

  const confidencePercent = Math.round(source.score * 100)
  const confidenceColor =
    confidencePercent >= 80
      ? 'text-green-500'
      : confidencePercent >= 60
      ? 'text-yellow-500'
      : 'text-orange-500'

  const contentPreview = source.text.slice(0, 120)
  const hasMore = source.text.length > 120
  const metadata = source.metadata || {}
  const sourceType = typeof metadata.source_type === 'string' ? metadata.source_type : null
  const denseScoreRaw = typeof metadata.dense_score_raw === 'number' ? metadata.dense_score_raw : null
  const lexicalScoreRaw = typeof metadata.lexical_score_raw === 'number' ? metadata.lexical_score_raw : null
  const combinedScore = typeof metadata.combined_score === 'number' ? metadata.combined_score : null

  return (
    <div id={anchorId} className="panel p-3 text-sm scroll-mt-24">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] text-gray-400 font-mono">
            Source {index + 1}
          </span>
          <span className="text-gray-400">📄</span>
          <span className="text-white font-medium">{source.filename}</span>
          <span className="text-gray-500 text-xs">Chunk #{source.chunk_index}</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`font-mono text-xs ${confidenceColor}`}>{confidencePercent}%</span>
        </div>
      </div>

      {(sourceType || denseScoreRaw !== null || lexicalScoreRaw !== null || combinedScore !== null) && (
        <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px] text-gray-400">
          {sourceType && (
            <span className="rounded border border-gray-600 px-2 py-0.5">
              source: {sourceType}
            </span>
          )}
          {denseScoreRaw !== null && (
            <span className="rounded border border-blue-500/40 bg-blue-500/10 px-2 py-0.5 text-blue-300">
              dense: {denseScoreRaw.toFixed(3)}
            </span>
          )}
          {lexicalScoreRaw !== null && (
            <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-amber-300">
              bm25: {lexicalScoreRaw.toFixed(3)}
            </span>
          )}
          {combinedScore !== null && (
            <span className="rounded border border-gray-600 px-2 py-0.5">
              combined: {combinedScore.toFixed(3)}
            </span>
          )}
        </div>
      )}

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
