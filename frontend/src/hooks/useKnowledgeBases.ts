import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../services/api'
import type { KnowledgeBase, CreateKBRequest } from '../types/index'

export function useKnowledgeBases(pageSize = 12) {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchKnowledgeBases = useCallback(async (currentPage: number) => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getKnowledgeBases(currentPage, pageSize)
      setKnowledgeBases(data.items)
      setTotalPages(data.pages)
      setTotal(data.total)
      setPage(currentPage)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch knowledge bases')
    } finally {
      setLoading(false)
    }
  }, [pageSize])

  const createKnowledgeBase = useCallback(async (data: CreateKBRequest): Promise<KnowledgeBase> => {
    const newKB = await apiClient.createKnowledgeBase(data)
    // Refresh to page 1 to show the new KB
    await fetchKnowledgeBases(1)
    return newKB
  }, [fetchKnowledgeBases])

  const deleteKnowledgeBase = useCallback(async (id: string) => {
    await apiClient.deleteKnowledgeBase(id)
    // Refresh current page
    await fetchKnowledgeBases(page)
  }, [fetchKnowledgeBases, page])

  const goToPage = useCallback((newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchKnowledgeBases(newPage)
    }
  }, [fetchKnowledgeBases, totalPages])

  useEffect(() => {
    fetchKnowledgeBases(1)
  }, [fetchKnowledgeBases])

  return {
    knowledgeBases,
    loading,
    error,
    page,
    totalPages,
    total,
    refresh: () => fetchKnowledgeBases(page),
    createKnowledgeBase,
    deleteKnowledgeBase,
    goToPage,
    nextPage: () => goToPage(page + 1),
    prevPage: () => goToPage(page - 1),
  }
}
