import { useEffect, useRef } from 'react'
import { apiClient } from '../services/api'
import type { Document } from '../types/index'

export function useDocumentPolling(
  documents: Document[],
  onStatusUpdate: (id: string, status: any) => void,
  interval = 2000
) {
  const timerRef = useRef<number | null>(null)
  const inFlightRef = useRef(false)
  const documentsRef = useRef<Document[]>(documents)
  const onStatusUpdateRef = useRef(onStatusUpdate)

  useEffect(() => {
    documentsRef.current = documents
  }, [documents])

  useEffect(() => {
    onStatusUpdateRef.current = onStatusUpdate
  }, [onStatusUpdate])

  useEffect(() => {
    const poll = async () => {
      if (inFlightRef.current) return
      inFlightRef.current = true

      try {
        const processingDocs = documentsRef.current.filter(
          (doc) => doc.status === 'processing' || doc.status === 'pending'
        )

        if (processingDocs.length === 0) {
          return
        }

        for (const doc of processingDocs) {
          try {
            const status = await apiClient.getDocumentStatus(doc.id)
            if (
              status.status !== doc.status ||
              status.chunk_count !== doc.chunk_count ||
              status.progress_percentage !== doc.progress_percentage ||
              status.processing_stage !== doc.processing_stage
            ) {
              onStatusUpdateRef.current(doc.id, status)
            }
          } catch (error) {
            console.error(`Failed to poll status for document ${doc.id}:`, error)
          }
        }
      } finally {
        inFlightRef.current = false
      }
    }

    const schedule = () => {
      timerRef.current = window.setTimeout(async () => {
        await poll()
        schedule()
      }, interval)
    }

    schedule()

    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [interval])
}
