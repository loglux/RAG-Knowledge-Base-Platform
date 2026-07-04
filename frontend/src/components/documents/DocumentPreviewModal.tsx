import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Modal } from '../common/Modal'

interface DocumentPreviewModalProps {
  isOpen: boolean
  onClose: () => void
  filename: string
  content: string | null
  loading: boolean
}

export function DocumentPreviewModal({ isOpen, onClose, filename, content, loading }: DocumentPreviewModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={filename} maxWidth="2xl">
      {loading ? (
        <div className="text-gray-400 text-sm py-8 text-center">Loading preview...</div>
      ) : content ? (
        <div className="text-sm prose prose-invert prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      ) : (
        <div className="text-gray-400 text-sm py-8 text-center">No content available.</div>
      )}
    </Modal>
  )
}
