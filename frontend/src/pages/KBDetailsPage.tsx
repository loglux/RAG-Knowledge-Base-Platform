import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiClient } from '../services/api'
import { useDocuments } from '../hooks/useDocuments'
import { useDocumentPolling } from '../hooks/useDocumentPolling'
import { FileUpload } from '../components/documents/FileUpload'
import { DocumentItem } from '../components/documents/DocumentItem'
import type { KnowledgeBase } from '../types/index'

export function KBDetailsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [kbLoading, setKbLoading] = useState(true)
  const [kbError, setKbError] = useState<string | null>(null)
  const [isEditingName, setIsEditingName] = useState(false)
  const [nameDraft, setNameDraft] = useState('')
  const [nameSaving, setNameSaving] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)
  const [isEditingSettings, setIsEditingSettings] = useState(false)
  const [settingsData, setSettingsData] = useState({
    chunk_size: 1000,
    chunk_overlap: 200,
    upsert_batch_size: 256,
  })
  const [settingsErrors, setSettingsErrors] = useState<Record<string, string>>({})
  const [settingsSaving, setSettingsSaving] = useState(false)

  const {
    documents,
    loading: docsLoading,
    error: docsError,
    uploadDocument,
    deleteDocument,
    reprocessDocument,
    updateDocumentStatus,
    refresh: refreshDocuments,
    analyzeDocument,
  } = useDocuments(id!)

  // Poll for document status updates
  useDocumentPolling(documents, updateDocumentStatus)

  useEffect(() => {
    const fetchKB = async () => {
      try {
        setKbLoading(true)
        setKbError(null)
        const data = await apiClient.getKnowledgeBase(id!)
        setKb(data)
        setNameDraft(data.name)
        setSettingsData({
          chunk_size: data.chunk_size,
          chunk_overlap: data.chunk_overlap,
          upsert_batch_size: data.upsert_batch_size,
        })
      } catch (err) {
        setKbError(err instanceof Error ? err.message : 'Failed to load knowledge base')
      } finally {
        setKbLoading(false)
      }
    }

    if (id) {
      fetchKB()
    }
  }, [id])

  const validateSettings = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (settingsData.chunk_size < 100 || settingsData.chunk_size > 2000) {
      newErrors.chunk_size = 'Chunk size must be between 100 and 2000'
    }

    if (settingsData.chunk_overlap < 0 || settingsData.chunk_overlap > 500) {
      newErrors.chunk_overlap = 'Chunk overlap must be between 0 and 500'
    }

    if (settingsData.chunk_overlap >= settingsData.chunk_size) {
      newErrors.chunk_overlap = 'Chunk overlap must be less than chunk size'
    }

    if (settingsData.upsert_batch_size < 64 || settingsData.upsert_batch_size > 1024) {
      newErrors.upsert_batch_size = 'Batch size must be between 64 and 1024'
    }

    setSettingsErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSaveSettings = async () => {
    if (!kb) return
    if (!validateSettings()) return

    setSettingsSaving(true)
    try {
      const updated = await apiClient.updateKnowledgeBase(kb.id, {
        chunk_size: settingsData.chunk_size,
        chunk_overlap: settingsData.chunk_overlap,
        upsert_batch_size: settingsData.upsert_batch_size,
      })
      setKb(updated)
      setIsEditingSettings(false)
      setSettingsErrors({})
    } catch (error) {
      setSettingsErrors({
        submit: error instanceof Error ? error.message : 'Failed to update settings',
      })
    } finally {
      setSettingsSaving(false)
    }
  }

  const handleCancelSettings = () => {
    if (!kb) return
    setSettingsData({
      chunk_size: kb.chunk_size,
      chunk_overlap: kb.chunk_overlap,
      upsert_batch_size: kb.upsert_batch_size,
    })
    setSettingsErrors({})
    setIsEditingSettings(false)
  }

  const handleStartEditName = () => {
    if (!kb) return
    setNameDraft(kb.name)
    setNameError(null)
    setIsEditingName(true)
  }

  const handleCancelEditName = () => {
    if (!kb) return
    setNameDraft(kb.name)
    setNameError(null)
    setIsEditingName(false)
  }

  const handleSaveName = async () => {
    if (!kb) return
    const nextName = nameDraft.trim()
    if (!nextName) {
      setNameError('Name cannot be empty')
      return
    }

    setNameSaving(true)
    try {
      const updated = await apiClient.updateKnowledgeBase(kb.id, { name: nextName })
      setKb(updated)
      setNameDraft(updated.name)
      setIsEditingName(false)
      setNameError(null)
    } catch (error) {
      setNameError(error instanceof Error ? error.message : 'Failed to update name')
    } finally {
      setNameSaving(false)
    }
  }

  const handleUpload = async (files: File[]) => {
    for (const file of files) {
      try {
        await uploadDocument(file)
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error)
        throw error
      }
    }
  }

  const handleDelete = async () => {
    if (!kb) return
    if (!confirm(`Delete "${kb.name}" and all its documents? This cannot be undone.`)) return

    try {
      await apiClient.deleteKnowledgeBase(kb.id)
      navigate('/')
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to delete knowledge base')
    }
  }

  if (kbLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
          <p className="mt-4 text-gray-400">Loading knowledge base...</p>
        </div>
      </div>
    )
  }

  if (kbError || !kb) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="card max-w-md text-center">
          <div className="text-6xl mb-4">❌</div>
          <h2 className="text-xl font-semibold text-white mb-2">Error</h2>
          <p className="text-gray-400 mb-4">{kbError || 'Knowledge base not found'}</p>
          <button onClick={() => navigate('/')} className="btn-primary">
            Go Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="text-gray-400 hover:text-white transition-colors"
                aria-label="Go back"
              >
                ← Back
              </button>
              <div>
                {isEditingName ? (
                  <div className="flex items-center gap-2">
                    <input
                      value={nameDraft}
                      onChange={(e) => setNameDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleSaveName()
                        }
                        if (e.key === 'Escape') {
                          e.preventDefault()
                          handleCancelEditName()
                        }
                      }}
                      className="input text-lg font-semibold py-1 px-3"
                      placeholder="Knowledge base name"
                      disabled={nameSaving}
                    />
                    <button
                      onClick={handleSaveName}
                      className="btn-primary text-sm px-3 py-1.5"
                      disabled={nameSaving}
                    >
                      {nameSaving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={handleCancelEditName}
                      className="btn-secondary text-sm px-3 py-1.5"
                      disabled={nameSaving}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold text-white">📖 {kb.name}</h1>
                    <button
                      onClick={handleStartEditName}
                      className="text-gray-400 hover:text-white transition-colors"
                      aria-label="Edit knowledge base name"
                    >
                      ✏️
                    </button>
                  </div>
                )}
                {nameError && <p className="text-red-400 text-sm mt-1">{nameError}</p>}
                {kb.description && <p className="text-gray-400 text-sm mt-1">{kb.description}</p>}
              </div>
            </div>
            <button
              onClick={handleDelete}
              className="text-gray-400 hover:text-red-500 transition-colors px-3 py-2"
              aria-label="Delete knowledge base"
            >
              🗑️
            </button>
          </div>

          <div className="flex items-center space-x-6 mt-4 text-sm text-gray-400">
            <span>{kb.document_count} documents</span>
            <span>•</span>
            <span>{kb.total_chunks} chunks</span>
            <span>•</span>
            <span>Created {new Date(kb.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Action Buttons */}
        <div className="flex items-center space-x-4 mb-8">
          <button
            onClick={() => navigate(`/kb/${kb.id}/chat`)}
            className="btn-primary flex items-center space-x-2"
          >
            <span>💬</span>
            <span>Chat with KB</span>
          </button>
          <button onClick={refreshDocuments} className="btn-secondary flex items-center space-x-2">
            <span>⟳</span>
            <span>Refresh</span>
          </button>
        </div>

        {/* Documents Section */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-white mb-4">
            📄 Documents ({documents.length})
          </h2>

          {/* Upload Area */}
          <div className="mb-6">
            <FileUpload onUpload={handleUpload} accept=".txt,.md" maxSize={50} multiple />
          </div>

          {/* Document List */}
          {docsError && (
            <div className="mb-4 p-4 bg-red-500 bg-opacity-10 border border-red-500 rounded-lg text-red-500">
              {docsError}
            </div>
          )}

          {docsLoading && documents.length === 0 ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
              <p className="mt-2 text-gray-400">Loading documents...</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="card text-center py-8">
              <div className="text-4xl mb-2">📭</div>
              <p className="text-gray-400">No documents yet. Upload files to get started!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <DocumentItem
                  key={doc.id}
                  document={doc}
                  onReprocess={reprocessDocument}
                  onDelete={deleteDocument}
                  onAnalyze={analyzeDocument}
                />
              ))}
            </div>
          )}
        </div>

        {/* KB Settings */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Configuration</h3>
            {!isEditingSettings && (
              <button
                onClick={() => setIsEditingSettings(true)}
                className="btn-secondary text-xs px-3 py-1.5"
              >
                Edit
              </button>
            )}
          </div>

          {isEditingSettings ? (
            <div className="space-y-4 text-sm">
              <div>
                <label htmlFor="kb-chunk-size" className="block text-gray-400 mb-2">
                  Chunk Size: <span className="text-white font-medium">{settingsData.chunk_size}</span> characters
                </label>
                <input
                  id="kb-chunk-size"
                  type="range"
                  min="100"
                  max="2000"
                  step="100"
                  value={settingsData.chunk_size}
                  onChange={(e) => setSettingsData({ ...settingsData, chunk_size: parseInt(e.target.value) })}
                  className="w-full"
                  disabled={settingsSaving}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>100</span>
                  <span>2000</span>
                </div>
                {settingsErrors.chunk_size && <p className="mt-1 text-sm text-red-500">{settingsErrors.chunk_size}</p>}
              </div>

              <div>
                <label htmlFor="kb-chunk-overlap" className="block text-gray-400 mb-2">
                  Chunk Overlap: <span className="text-white font-medium">{settingsData.chunk_overlap}</span> characters
                  <span className="text-gray-500">
                    {' '}({settingsData.chunk_size > 0 ? Math.round((settingsData.chunk_overlap / settingsData.chunk_size) * 100) : 0}%)
                  </span>
                </label>
                <input
                  id="kb-chunk-overlap"
                  type="range"
                  min="0"
                  max="500"
                  step="50"
                  value={settingsData.chunk_overlap}
                  onChange={(e) => setSettingsData({ ...settingsData, chunk_overlap: parseInt(e.target.value) })}
                  className="w-full"
                  disabled={settingsSaving}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0</span>
                  <span>500</span>
                </div>
                {settingsErrors.chunk_overlap && <p className="mt-1 text-sm text-red-500">{settingsErrors.chunk_overlap}</p>}
              </div>

              <div>
                <label htmlFor="kb-upsert-batch-size" className="block text-gray-400 mb-2">
                  Upsert Batch Size: <span className="text-white font-medium">{settingsData.upsert_batch_size}</span>
                </label>
                <input
                  id="kb-upsert-batch-size"
                  type="range"
                  min="64"
                  max="1024"
                  step="64"
                  value={settingsData.upsert_batch_size}
                  onChange={(e) => setSettingsData({ ...settingsData, upsert_batch_size: parseInt(e.target.value) })}
                  className="w-full"
                  disabled={settingsSaving}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>64</span>
                  <span>1024</span>
                </div>
                {settingsErrors.upsert_batch_size && <p className="mt-1 text-sm text-red-500">{settingsErrors.upsert_batch_size}</p>}
              </div>

              <div className="text-xs text-gray-500">
                Changes apply to new or reprocessed documents only.
              </div>

              {settingsErrors.submit && (
                <p className="text-sm text-red-500">{settingsErrors.submit}</p>
              )}

              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveSettings}
                  className="btn-primary text-xs px-3 py-1.5"
                  disabled={settingsSaving}
                >
                  {settingsSaving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={handleCancelSettings}
                  className="btn-secondary text-xs px-3 py-1.5"
                  disabled={settingsSaving}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Chunk Size:</span>
                <span className="text-white ml-2 font-medium">{kb.chunk_size} characters</span>
              </div>
              <div>
                <span className="text-gray-400">Chunk Overlap:</span>
                <span className="text-white ml-2 font-medium">{kb.chunk_overlap} characters</span>
                <span className="text-gray-500 ml-1">
                  ({kb.chunk_size > 0 ? Math.round((kb.chunk_overlap / kb.chunk_size) * 100) : 0}%)
                </span>
              </div>
              <div>
                <span className="text-gray-400">Upsert Batch Size:</span>
                <span className="text-white ml-2 font-medium">{kb.upsert_batch_size}</span>
              </div>
              <div>
                <span className="text-gray-400">Chunking Strategy:</span>
                <span className="text-white ml-2 font-medium">{kb.chunking_strategy}</span>
              </div>
              <div>
                <span className="text-gray-400">Collection:</span>
                <span className="text-white ml-2 font-mono text-xs">{kb.collection_name}</span>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
