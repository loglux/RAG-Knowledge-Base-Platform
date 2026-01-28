import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiClient } from '../services/api'
import { useDocuments } from '../hooks/useDocuments'
import { useDocumentPolling } from '../hooks/useDocumentPolling'
import { FileUpload } from '../components/documents/FileUpload'
import { DocumentItem } from '../components/documents/DocumentItem'
import { LLMSelector } from '../components/chat/LLMSelector'
import type { KnowledgeBase, AppSettings } from '../types/index'

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
    bm25_override: false,
    bm25_match_mode: '',
    bm25_min_should_match: 0,
    bm25_use_phrase: true,
    bm25_analyzer: '',
    structure_llm_model: '',
  })
  const [settingsErrors, setSettingsErrors] = useState<Record<string, string>>({})
  const [settingsSaving, setSettingsSaving] = useState(false)
  const [structureModelOverride, setStructureModelOverride] = useState(false)
  const [reindexing, setReindexing] = useState(false)
  const [reindexMessage, setReindexMessage] = useState<string | null>(null)
  const [bm25MatchModes, setBm25MatchModes] = useState<string[] | null>(null)
  const [bm25Analyzers, setBm25Analyzers] = useState<string[] | null>(null)
  const [appDefaults, setAppDefaults] = useState<AppSettings | null>(null)
  const [bulkAnalyzing, setBulkAnalyzing] = useState(false)
  const [bulkSkipAnalyzed, setBulkSkipAnalyzed] = useState(true)
  const [bulkProgress, setBulkProgress] = useState({ done: 0, total: 0 })
  const [bulkError, setBulkError] = useState<string | null>(null)

  const buildSettingsData = (kbData: KnowledgeBase, defaults?: AppSettings | null) => {
    const bm25Override = kbData.bm25_match_mode !== null
      || kbData.bm25_min_should_match !== null
      || kbData.bm25_use_phrase !== null
      || kbData.bm25_analyzer !== null

    return {
      chunk_size: kbData.chunk_size,
      chunk_overlap: kbData.chunk_overlap,
      upsert_batch_size: kbData.upsert_batch_size,
      bm25_override: bm25Override,
      bm25_match_mode: kbData.bm25_match_mode ?? defaults?.bm25_match_mode ?? '',
      bm25_min_should_match: kbData.bm25_min_should_match ?? defaults?.bm25_min_should_match ?? 0,
      bm25_use_phrase: kbData.bm25_use_phrase ?? defaults?.bm25_use_phrase ?? true,
      bm25_analyzer: kbData.bm25_analyzer ?? defaults?.bm25_analyzer ?? '',
      structure_llm_model: kbData.structure_llm_model ?? '',
    }
  }

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
        setSettingsData(buildSettingsData(data, appDefaults))
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

  useEffect(() => {
    const loadAppDefaults = async () => {
      try {
        const data = await apiClient.getAppSettings()
        setAppDefaults(data)
      } catch (err) {
        setAppDefaults(null)
      }
    }

    loadAppDefaults()
  }, [])

  useEffect(() => {
    if (!kb || isEditingSettings) return
    setSettingsData(buildSettingsData(kb, appDefaults))
    setStructureModelOverride(Boolean(kb.structure_llm_model))
  }, [kb, appDefaults, isEditingSettings])

  useEffect(() => {
    const loadSettingsMetadata = async () => {
      try {
        const metadata = await apiClient.getSettingsMetadata()
        setBm25MatchModes(metadata.bm25_match_modes || null)
        setBm25Analyzers(metadata.bm25_analyzers || null)
      } catch (err) {
        setBm25MatchModes(null)
        setBm25Analyzers(null)
      }
    }

    loadSettingsMetadata()
  }, [])

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

    if (settingsData.bm25_override) {
      if (bm25MatchModes && bm25MatchModes.length > 0 && !bm25MatchModes.includes(settingsData.bm25_match_mode)) {
        newErrors.bm25_match_mode = 'Match mode must be one of the allowed values'
      }
      if (settingsData.bm25_min_should_match < 0 || settingsData.bm25_min_should_match > 100) {
        newErrors.bm25_min_should_match = 'Minimum should match must be between 0 and 100'
      }
      if (bm25Analyzers && bm25Analyzers.length > 0 && !bm25Analyzers.includes(settingsData.bm25_analyzer)) {
        newErrors.bm25_analyzer = 'Analyzer must be one of the allowed values'
      }
    }

    if (structureModelOverride && !settingsData.structure_llm_model) {
      newErrors.structure_llm_model = 'Select a model or disable override'
    }

    if (settingsData.structure_llm_model && settingsData.structure_llm_model.length > 100) {
      newErrors.structure_llm_model = 'Model name is too long'
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
        bm25_match_mode: settingsData.bm25_override ? settingsData.bm25_match_mode : null,
        bm25_min_should_match: settingsData.bm25_override ? settingsData.bm25_min_should_match : null,
        bm25_use_phrase: settingsData.bm25_override ? settingsData.bm25_use_phrase : null,
        bm25_analyzer: settingsData.bm25_override ? settingsData.bm25_analyzer : null,
        structure_llm_model: structureModelOverride ? (settingsData.structure_llm_model || null) : null,
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
    setSettingsData(buildSettingsData(kb, appDefaults))
    setStructureModelOverride(Boolean(kb.structure_llm_model))
    setSettingsErrors({})
    setIsEditingSettings(false)
  }

  const handleReindexBm25 = async () => {
    if (!kb) return
    const confirmed = window.confirm(
      'Reprocess all documents to rebuild BM25 index? This will re-chunk and re-embed every document.'
    )
    if (!confirmed) return

    try {
      setReindexing(true)
      setReindexMessage(null)
      const result = await apiClient.reprocessKnowledgeBase(kb.id)
      setReindexMessage(`Queued ${result.queued} documents for reprocessing.`)
    } catch (error) {
      setReindexMessage(error instanceof Error ? error.message : 'Failed to reprocess documents')
    } finally {
      setReindexing(false)
    }
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

  const handleAnalyzeAll = async () => {
    if (bulkAnalyzing) return
    setBulkError(null)

    const candidates = documents.filter((doc) => doc.status === 'completed')
    if (candidates.length === 0) {
      setBulkError('No completed documents to analyze.')
      return
    }

    setBulkAnalyzing(true)
    setBulkProgress({ done: 0, total: candidates.length })

    let processed = 0
    for (const doc of candidates) {
      try {
        if (bulkSkipAnalyzed) {
          const structure = await apiClient.getDocumentStructure(doc.id)
          if (structure?.has_structure) {
            processed += 1
            setBulkProgress({ done: processed, total: candidates.length })
            continue
          }
        }

        const analysis = await apiClient.analyzeDocument(doc.id)
        await apiClient.applyDocumentStructure(doc.id, analysis)
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to analyze document'
        setBulkError(message)
      } finally {
        processed += 1
        setBulkProgress({ done: processed, total: candidates.length })
      }
    }

    setBulkAnalyzing(false)
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
          <button
            onClick={handleAnalyzeAll}
            disabled={bulkAnalyzing}
            className="btn-secondary flex items-center space-x-2 disabled:opacity-60"
          >
            <span>🔍</span>
            <span>{bulkAnalyzing ? 'Analyzing…' : 'Analyze All'}</span>
          </button>
          <label className="flex items-center space-x-2 text-sm text-gray-400">
            <input
              type="checkbox"
              checked={bulkSkipAnalyzed}
              onChange={(e) => setBulkSkipAnalyzed(e.target.checked)}
              className="rounded border-gray-600 bg-gray-800"
            />
            <span>Skip already analyzed</span>
          </label>
        </div>
        {bulkError && (
          <div className="mb-4 p-3 rounded border border-red-500 bg-red-500/10 text-red-400 text-sm">
            {bulkError}
          </div>
        )}
        {bulkAnalyzing && (
          <div className="mb-4 text-xs text-gray-400">
            Analyzing documents: {bulkProgress.done}/{bulkProgress.total}
          </div>
        )}

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

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-gray-400">
                    TOC / Structure model
                  </label>
                  <label className="flex items-center gap-2 text-xs text-gray-300">
                    <input
                      type="checkbox"
                      checked={structureModelOverride}
                      onChange={(e) => setStructureModelOverride(e.target.checked)}
                      className="w-4 h-4 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
                      disabled={settingsSaving}
                    />
                    Override global model
                  </label>
                </div>
                <div className={structureModelOverride ? '' : 'opacity-60 pointer-events-none'}>
                  <LLMSelector
                    value={structureModelOverride ? settingsData.structure_llm_model : (appDefaults?.llm_model || '')}
                    onChange={(model, _provider) => setSettingsData({ ...settingsData, structure_llm_model: model })}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {structureModelOverride
                    ? 'Model used for TOC analysis in this KB'
                    : `Using global default: ${appDefaults?.llm_model || 'not set'}`}
                </p>
                {settingsErrors.structure_llm_model && (
                  <p className="mt-1 text-sm text-red-500">{settingsErrors.structure_llm_model}</p>
                )}
              </div>

              <div className="border-t border-gray-700 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-white">BM25 Overrides</h4>
                  <label className="flex items-center gap-2 text-xs text-gray-300">
                    <input
                      type="checkbox"
                      checked={settingsData.bm25_override}
                      onChange={(e) => setSettingsData({ ...settingsData, bm25_override: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
                      disabled={settingsSaving}
                    />
                    Override global BM25 defaults
                  </label>
                </div>

                {settingsData.bm25_override && (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <label className="block text-gray-400 mb-2">
                        Match mode
                      </label>
                      <select
                        value={settingsData.bm25_match_mode || (bm25MatchModes?.[0] ?? '')}
                        onChange={(e) => setSettingsData({ ...settingsData, bm25_match_mode: e.target.value })}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
                        disabled={settingsSaving || !bm25MatchModes || bm25MatchModes.length === 0}
                      >
                        {(!bm25MatchModes || bm25MatchModes.length === 0) && <option value="">Loading…</option>}
                        {bm25MatchModes?.map((mode) => (
                          <option key={mode} value={mode}>
                            {mode}
                          </option>
                        ))}
                      </select>
                      {settingsErrors.bm25_match_mode && (
                        <p className="mt-1 text-sm text-red-500">{settingsErrors.bm25_match_mode}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-gray-400 mb-2">
                        Minimum should match: <span className="text-white font-medium">{settingsData.bm25_min_should_match}%</span>
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="5"
                        value={settingsData.bm25_min_should_match}
                        onChange={(e) => setSettingsData({ ...settingsData, bm25_min_should_match: parseInt(e.target.value) })}
                        className="w-full"
                        disabled={settingsSaving}
                      />
                      {settingsErrors.bm25_min_should_match && (
                        <p className="mt-1 text-sm text-red-500">{settingsErrors.bm25_min_should_match}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-gray-400 mb-2">
                        Use phrase match
                      </label>
                      <label className="flex items-center gap-2 text-sm text-gray-300">
                        <input
                          type="checkbox"
                          checked={settingsData.bm25_use_phrase}
                          onChange={(e) => setSettingsData({ ...settingsData, bm25_use_phrase: e.target.checked })}
                          className="w-4 h-4 rounded border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-900"
                          disabled={settingsSaving}
                        />
                        Include exact phrase matches
                      </label>
                    </div>

                    <div>
                      <label className="block text-gray-400 mb-2">
                        Analyzer profile
                      </label>
                      <select
                        value={settingsData.bm25_analyzer || (bm25Analyzers?.[0] ?? '')}
                        onChange={(e) => setSettingsData({ ...settingsData, bm25_analyzer: e.target.value })}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100"
                        disabled={settingsSaving || !bm25Analyzers || bm25Analyzers.length === 0}
                      >
                        {(!bm25Analyzers || bm25Analyzers.length === 0) && <option value="">Loading…</option>}
                        {bm25Analyzers?.map((analyzer) => (
                          <option key={analyzer} value={analyzer}>
                            {analyzer}
                          </option>
                        ))}
                      </select>
                      {settingsErrors.bm25_analyzer && (
                        <p className="mt-1 text-sm text-red-500">{settingsErrors.bm25_analyzer}</p>
                      )}
                    </div>
                  </div>
                )}
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
                <span className="text-gray-400">TOC / Structure model:</span>
                <span className="text-white ml-2 font-medium">
                  {kb.structure_llm_model || 'Default'}
                </span>
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

          <div className="mt-6 flex items-center justify-between">
            <div className="text-xs text-gray-500">
              Reindex is required to include existing documents in BM25 hybrid search.
            </div>
            <button
              onClick={handleReindexBm25}
              className="btn-secondary text-xs px-3 py-1.5"
              disabled={reindexing}
            >
              {reindexing ? 'Reindexing…' : 'Reindex for BM25'}
            </button>
          </div>
          {reindexMessage && (
            <div className="mt-2 text-xs text-gray-400">{reindexMessage}</div>
          )}
        </div>
      </main>
    </div>
  )
}
