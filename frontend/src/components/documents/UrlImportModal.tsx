import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import type { UrlPreview } from '../../types'

interface UrlImportModalProps {
  isOpen: boolean
  onClose: () => void
  onImport: () => Promise<void>
  preview: UrlPreview | null
  importing: boolean
}

export function UrlImportModal({ isOpen, onClose, onImport, preview, importing }: UrlImportModalProps) {
  if (!preview) return null

  const meta = [
    preview.sitename,
    preview.author && `by ${preview.author}`,
    preview.publish_date,
    preview.language && `lang: ${preview.language}`,
  ].filter(Boolean)

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Preview" maxWidth="xl">
      <div className="space-y-4">
        {/* Title */}
        <div>
          <h3 className="text-lg font-semibold text-white leading-snug">
            {preview.title || <span className="text-gray-500 italic">No title</span>}
          </h3>
          {meta.length > 0 && (
            <p className="mt-1 text-xs text-gray-400">{meta.join(' · ')}</p>
          )}
        </div>

        {/* Description */}
        {preview.description && (
          <p className="text-sm text-gray-300 italic border-l-2 border-gray-600 pl-3">
            {preview.description}
          </p>
        )}

        {/* Content preview */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500 uppercase tracking-wide">Content preview</span>
            <span className="text-xs text-gray-500">{preview.word_count.toLocaleString()} words</span>
          </div>
          <pre className="bg-gray-900 rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-mono max-h-52 overflow-y-auto leading-relaxed">
            {preview.content_preview}
          </pre>
        </div>

        {/* Source URL */}
        <p className="text-xs text-gray-500 truncate">
          <span className="text-gray-600">URL: </span>
          <a
            href={preview.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-400 hover:text-primary-300"
          >
            {preview.url}
          </a>
        </p>
      </div>

      {/* Footer */}
      <div className="mt-6 flex justify-end gap-3 border-t border-gray-700 pt-4">
        <Button variant="secondary" onClick={onClose} disabled={importing}>
          Cancel
        </Button>
        <Button variant="primary" onClick={onImport} disabled={importing}>
          {importing ? 'Saving…' : 'Save to KB'}
        </Button>
      </div>
    </Modal>
  )
}
