import { useState } from 'react'
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

function readingTime(wordCount: number): string {
  const minutes = Math.ceil(wordCount / 200)
  return minutes === 1 ? '~1 min read' : `~${minutes} min read`
}

export function UrlImportModal({ isOpen, onClose, onImport, preview, importing }: UrlImportModalProps) {
  const [tab, setTab] = useState<'content' | 'meta'>('content')

  if (!preview) return null

  const metaRows: { label: string; value: string }[] = [
    preview.sitename   ? { label: 'Site',      value: preview.sitename }   : null,
    preview.author     ? { label: 'Author',    value: preview.author }     : null,
    preview.publish_date ? { label: 'Published', value: preview.publish_date } : null,
    preview.language   ? { label: 'Language',  value: preview.language }   : null,
    preview.canonical_url ? { label: 'Canonical', value: preview.canonical_url } : null,
    { label: 'Saved URL', value: preview.url },
  ].filter((r): r is { label: string; value: string } => r !== null)

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Import preview" maxWidth="2xl">
      <div className="flex flex-col">

        {/* Title + stats */}
        <div className="mb-3">
          <h3 className="text-base font-semibold text-white leading-snug">
            {preview.title || <span className="text-gray-500 italic">No title</span>}
          </h3>
          <p className="mt-1 text-xs text-gray-400">
            {preview.word_count.toLocaleString()} words · {readingTime(preview.word_count)}
            {preview.sitename && <> · {preview.sitename}</>}
          </p>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 mb-3 border-b border-gray-700 pb-2">
          <button
            onClick={() => setTab('content')}
            className={`px-3 py-1 text-xs rounded-t font-medium transition-colors ${
              tab === 'content'
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Content
          </button>
          <button
            onClick={() => setTab('meta')}
            className={`px-3 py-1 text-xs rounded-t font-medium transition-colors ${
              tab === 'meta'
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Metadata
          </button>
        </div>

        {/* Scrollable body */}
        <div className="overflow-y-auto" style={{ maxHeight: '52vh' }}>
          {tab === 'content' ? (
            <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
              {preview.content_md || <span className="text-gray-500 italic">No content extracted</span>}
            </pre>
          ) : (
            <div className="space-y-3">
              {preview.description && (
                <p className="text-sm text-gray-300 italic border-l-2 border-gray-600 pl-3">
                  {preview.description}
                </p>
              )}
              <table className="w-full text-xs">
                <tbody>
                  {metaRows.map(({ label, value }) => (
                    <tr key={label} className="border-b border-gray-800">
                      <td className="py-2 pr-4 text-gray-500 font-medium whitespace-nowrap align-top w-24">
                        {label}
                      </td>
                      <td className="py-2 text-gray-300 break-all">
                        {label === 'Saved URL' || label === 'Canonical' ? (
                          <a
                            href={value}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-400 hover:text-primary-300"
                          >
                            {value}
                          </a>
                        ) : (
                          value
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-4 flex justify-end gap-3 border-t border-gray-700 pt-4">
          <Button variant="secondary" onClick={onClose} disabled={importing}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onImport} disabled={importing}>
            {importing ? 'Saving…' : 'Save to KB'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
