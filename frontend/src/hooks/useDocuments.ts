import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../services/api'
import type { Document, DocumentStatusResponse } from '../types/index'

export function useDocuments(kbId: string) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getDocuments(kbId)
      setDocuments(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch documents')
    } finally {
      setLoading(false)
    }
  }, [kbId])

  const uploadDocument = useCallback(async (file: File): Promise<Document> => {
    const newDoc = await apiClient.uploadDocument(kbId, file)
    setDocuments((prev) => [newDoc, ...prev])
    return newDoc
  }, [kbId])

  const deleteDocument = useCallback(async (id: string) => {
    await apiClient.deleteDocument(id)
    setDocuments((prev) => prev.filter((doc) => doc.id !== id))
  }, [])

  const reprocessDocument = useCallback(async (id: string) => {
    const updated = await apiClient.reprocessDocument(id)
    setDocuments((prev) => prev.map((doc) => (doc.id === id ? updated : doc)))
  }, [])

  const updateDocumentStatus = useCallback((id: string, status: DocumentStatusResponse) => {
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === id
          ? { ...doc, status: status.status, chunk_count: status.chunk_count, error_message: status.error_message }
          : doc
      )
    )
  }, [])

  const analyzeDocument = useCallback(async (id: string) => {
    return await apiClient.analyzeDocument(id)
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  return {
    documents,
    loading,
    error,
    refresh: fetchDocuments,
    uploadDocument,
    deleteDocument,
    reprocessDocument,
    updateDocumentStatus,
    analyzeDocument,
  }
}
