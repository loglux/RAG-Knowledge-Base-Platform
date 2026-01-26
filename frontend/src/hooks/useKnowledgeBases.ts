import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../services/api'
import type { KnowledgeBase, CreateKBRequest } from '../types/index'

export function useKnowledgeBases() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchKnowledgeBases = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getKnowledgeBases()
      setKnowledgeBases(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch knowledge bases')
    } finally {
      setLoading(false)
    }
  }, [])

  const createKnowledgeBase = useCallback(async (data: CreateKBRequest): Promise<KnowledgeBase> => {
    const newKB = await apiClient.createKnowledgeBase(data)
    setKnowledgeBases((prev) => [newKB, ...prev])
    return newKB
  }, [])

  const deleteKnowledgeBase = useCallback(async (id: string) => {
    await apiClient.deleteKnowledgeBase(id)
    setKnowledgeBases((prev) => prev.filter((kb) => kb.id !== id))
  }, [])

  useEffect(() => {
    fetchKnowledgeBases()
  }, [fetchKnowledgeBases])

  return {
    knowledgeBases,
    loading,
    error,
    refresh: fetchKnowledgeBases,
    createKnowledgeBase,
    deleteKnowledgeBase,
  }
}
