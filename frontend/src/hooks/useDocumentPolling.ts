import { useEffect, useRef } from 'react'
import { apiClient } from '../services/api'
import type { Document } from '../types/index'

export function useDocumentPolling(
  documents: Document[],
  onStatusUpdate: (id: string, status: any) => void,
  interval = 1000
) {
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    const processingDocs = documents.filter(
      (doc) => doc.status === 'processing' || doc.status === 'pending'
    )

    if (processingDocs.length === 0) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    const poll = async () => {
      for (const doc of processingDocs) {
        try {
          const status = await apiClient.getDocumentStatus(doc.id)
          // Update if status, chunk_count, or progress changed
          if (
            status.status !== doc.status ||
            status.chunk_count !== doc.chunk_count ||
            status.progress_percentage !== doc.progress_percentage ||
            status.processing_stage !== doc.processing_stage
          ) {
            onStatusUpdate(doc.id, status)
          }
        } catch (error) {
          console.error(`Failed to poll status for document ${doc.id}:`, error)
        }
      }
    }

    // Initial poll
    poll()

    // Set up interval
    intervalRef.current = setInterval(poll, interval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [documents, onStatusUpdate, interval])
}
