import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '../context/AuthContext'
import { apiClient } from '../services/api'
import { Button } from '../components/common/Button'
import { useDocuments } from '../hooks/useDocuments'
import { useDocumentPolling } from '../hooks/useDocumentPolling'
import { FileUpload } from '../components/documents/FileUpload'
import { DocumentItem } from '../components/documents/DocumentItem'
import { UrlImportModal } from '../components/documents/UrlImportModal'
import { LLMSelector } from '../components/chat/LLMSelector'
import type { KnowledgeBase, AppSettings, QAEvalRun, QAEvalRunDetail, KBRetrievalSettingsEnvelope, KBRetrievalSettingsStored, ChunkingStrategy, FeedbackItem, UrlPreview } from '../types/index'

export function KBDetailsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { logout } = useAuth()

  const getChunkingStrategyDisplay = (strategy: ChunkingStrategy) => {
    const strategies: Record<ChunkingStrategy, { icon: string; label: string; description: string }> = {
      simple: {
        icon: '⚡',
        label: 'Simple (Fixed-Size)',
        description: 'Fast chunking at fixed character positions',
      },
      smart: {
        icon: '🧠',
        label: 'Smart (Recursive)',
        description: 'Intelligent chunking respecting boundaries',
      },
      semantic: {
        icon: '🎯',
        label: 'Semantic',
        description: 'Advanced semantic boundary detection',
      },
    }
    return strategies[strategy]
  }

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
    chunking_strategy: 'smart' as ChunkingStrategy,
    contextual_description_mode: 'default' as 'default' | 'enabled' | 'disabled',
    pdf_table_strategy_mode: 'default' as 'default' | 'lines' | 'text',
    pdf_heading_sensitivity: '' as string,
    pdf_min_doc_length: '' as string,
  })
  const [settingsErrors, setSettingsErrors] = useState<Record<string, string>>({})
  const [settingsSaving, setSettingsSaving] = useState(false)
  const [mainTab, setMainTab] = useState<'documents' | 'settings' | 'evaluation'>('documents')
  const [configTab, setConfigTab] = useState<'chunking' | 'search' | 'llm'>('chunking')
  const [isEditingLlm, setIsEditingLlm] = useState(false)
  const [llmDraft, setLlmDraft] = useState<{
    llm_model: string | null
    llm_provider: string | null
    temperature: number | null
    use_self_check: boolean | null
    chat_title_mode: 'default' | 'enabled' | 'disabled'
  }>({ llm_model: null, llm_provider: null, temperature: null, use_self_check: null, chat_title_mode: 'default' })
  const [llmSaving, setLlmSaving] = useState(false)
  const [retrievalEnvelope, setRetrievalEnvelope] = useState<KBRetrievalSettingsEnvelope | null>(null)
  const [isEditingRetrieval, setIsEditingRetrieval] = useState(false)
  const [retrievalDraft, setRetrievalDraft] = useState<KBRetrievalSettingsStored>({})
  const [retrievalSaving, setRetrievalSaving] = useState(false)
  const [linkHybridWeights, setLinkHybridWeights] = useState(true)
  const [reindexing, setReindexing] = useState(false)
  const [reindexMessage, setReindexMessage] = useState<string | null>(null)
  const [detectDuplicatesOnUpload, setDetectDuplicatesOnUpload] = useState(false)
  const [detectDuplicatesOnReindex, setDetectDuplicatesOnReindex] = useState(false)
  const [contextualDescriptionRequestMode, setContextualDescriptionRequestMode] = useState<
    'inherit' | 'enabled' | 'disabled'
  >('inherit')
  const [addMode, setAddMode] = useState<'file' | 'url'>('file')
  const [importUrl, setImportUrl] = useState('')
  const [urlPreviewing, setUrlPreviewing] = useState(false)
  const [urlPreview, setUrlPreview] = useState<UrlPreview | null>(null)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [urlImporting, setUrlImporting] = useState(false)
  const [regenTitlesLoading, setRegenTitlesLoading] = useState(false)
  const [regenTitlesMessage, setRegenTitlesMessage] = useState<string | null>(null)
  const [regenIncludeExisting, setRegenIncludeExisting] = useState(false)
  const [regenLimit, setRegenLimit] = useState('')
  const [bm25MatchModes, setBm25MatchModes] = useState<string[] | null>(null)
  const [bm25Analyzers, setBm25Analyzers] = useState<string[] | null>(null)
  const [appDefaults, setAppDefaults] = useState<AppSettings | null>(null)
  const [qaRuns, setQaRuns] = useState<QAEvalRun[]>([])
  const [qaRunsLoading, setQaRunsLoading] = useState(false)
  const [qaRunsError, setQaRunsError] = useState<string | null>(null)
  const [qaGoldCount, setQaGoldCount] = useState<number | null>(null)
  const [qaFile, setQaFile] = useState<File | null>(null)
  const [qaUploadMessage, setQaUploadMessage] = useState<string | null>(null)
  const [qaUploading, setQaUploading] = useState(false)
  const [qaRunConfig, setQaRunConfig] = useState({
    top_k: 5,
    retrieval_mode: 'dense' as 'dense' | 'hybrid',
  })
  const [qaRunning, setQaRunning] = useState(false)
  const [qaPresetRunning, setQaPresetRunning] = useState(false)
  const [qaRunError, setQaRunError] = useState<string | null>(null)
  const [qaSelectedRun, setQaSelectedRun] = useState<QAEvalRunDetail | null>(null)
  const [qaFilter, setQaFilter] = useState('')
  const [qaOnlyLow, setQaOnlyLow] = useState(false)
  const [qaDeleting, setQaDeleting] = useState(false)
  const [qaDetailsSeed, setQaDetailsSeed] = useState(0)
  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>([])
  const [feedbackLoading, setFeedbackLoading] = useState(false)

  const loadRetrievalSettings = async (kbId: string) => {
    try {
      const envelope = await apiClient.getKBRetrievalSettings(kbId)
      setRetrievalEnvelope(envelope)
      setRetrievalDraft(envelope.stored ?? {})
    } catch {
      // Silently ignore - retrieval settings are optional
    }
  }

  const buildSettingsData = (kbData: KnowledgeBase) => {
    const mode: 'default' | 'enabled' | 'disabled' =
      kbData.contextual_description_enabled == null
        ? 'default'
        : kbData.contextual_description_enabled
        ? 'enabled'
        : 'disabled'
    const pdfStrategyMode: 'default' | 'lines' | 'text' =
      kbData.pdf_table_strategy === 'lines'
        ? 'lines'
        : kbData.pdf_table_strategy === 'text'
        ? 'text'
        : 'default'
    return {
      chunk_size: kbData.chunk_size,
      chunk_overlap: kbData.chunk_overlap,
      upsert_batch_size: kbData.upsert_batch_size,
      chunking_strategy: kbData.chunking_strategy as ChunkingStrategy,
      contextual_description_mode: mode,
      pdf_table_strategy_mode: pdfStrategyMode,
      pdf_heading_sensitivity:
        kbData.pdf_heading_size_sensitivity != null
          ? String(kbData.pdf_heading_size_sensitivity)
          : '',
      pdf_min_doc_length:
        kbData.pdf_min_doc_length != null ? String(kbData.pdf_min_doc_length) : '',
    }
  }

  const renderEffectiveRetrievalRow = (label: string, field: string, value: string) => {
    if (!retrievalEnvelope) return null
    const source = retrievalEnvelope.explain[field] ?? 'defaults'
    const isKbOverride = source === 'kb_retrieval_settings' || source === 'kb_columns'
    return (
      <div key={field} className="flex items-center justify-between">
        <span className="text-gray-400">{label}:</span>
        <div className="flex items-center gap-2">
          <span className="text-white font-medium">{value}</span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${isKbOverride ? 'bg-primary-500/20 text-primary-400' : 'bg-gray-700 text-gray-400'}`}>
            {isKbOverride ? 'KB' : 'global'}
          </span>
        </div>
      </div>
    )
  }

  const {
    documents,
    loading: docsLoading,
    error: docsError,
    uploadDocument,
    importDocumentFromUrl,
    deleteDocument,
    reprocessDocument,
    updateDocumentStatus,
    refresh: refreshDocuments,
    recomputeDocumentDuplicates,
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
        loadRetrievalSettings(id!)
        setNameDraft(data.name)
        setSettingsData(buildSettingsData(data))
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
    const loadRuns = async () => {
      if (!id) return
      setQaRunsLoading(true)
      setQaRunsError(null)
      try {
        const runs = await apiClient.listAutoTuneRuns(id)
        setQaRuns(runs)
        const count = await apiClient.getGoldQACount(id)
        setQaGoldCount(count.count)
      } catch (err) {
        setQaRunsError(err instanceof Error ? err.message : 'Failed to load auto-tuning runs')
      } finally {
        setQaRunsLoading(false)
      }
    }

    loadRuns()
  }, [id])

  const loadFeedback = useCallback(async () => {
    if (!id) return
    setFeedbackLoading(true)
    try {
      const items = await apiClient.listKbFeedback(id)
      setFeedbackItems(items)
    } catch (err) {
      console.error('Failed to load feedback:', err)
    } finally {
      setFeedbackLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (mainTab === 'evaluation') {
      loadFeedback()
    }
  }, [mainTab, loadFeedback])

  useEffect(() => {
    if (!id) return
    const hasRunning = qaRuns.some((run) => run.status === 'running')
    if (!hasRunning) return
    const timer = setInterval(async () => {
      try {
        const runs = await apiClient.listAutoTuneRuns(id)
        setQaRuns(runs)
        if (qaSelectedRun) {
          const detail = await apiClient.getAutoTuneRun(id, qaSelectedRun.run.id)
          setQaSelectedRun(detail)
        }
      } catch {
        // ignore polling errors
      }
    }, 2000)
    return () => clearInterval(timer)
  }, [id, qaRuns, qaSelectedRun])

  useEffect(() => {
    const loadAppDefaults = async () => {
      try {
        const data = await apiClient.getAppSettings()
        setAppDefaults(data)
      } catch {
        setAppDefaults(null)
      }
    }

    loadAppDefaults()
  }, [])

  const handleUploadQaFile = async () => {
    if (!id || !qaFile) return
    setQaUploading(true)
    setQaUploadMessage(null)
    setQaRunsError(null)
    try {
      const result = await apiClient.uploadGoldQA(id, qaFile, true)
      setQaUploadMessage(`Uploaded ${result.added_count} questions`)
      const runs = await apiClient.listAutoTuneRuns(id)
      setQaRuns(runs)
      const count = await apiClient.getGoldQACount(id)
      setQaGoldCount(count.count)
    } catch (err) {
      setQaUploadMessage(err instanceof Error ? err.message : 'Failed to upload QA file')
    } finally {
      setQaUploading(false)
    }
  }

  const handleRunGoldEval = async () => {
    if (!id) return
    setQaRunning(true)
    setQaRunError(null)
    try {
      const run = await apiClient.runGoldEval(id, {
        top_k: qaRunConfig.top_k,
        retrieval_mode: qaRunConfig.retrieval_mode,
      })
      const runs = await apiClient.listAutoTuneRuns(id)
      setQaRuns(runs)
      const detail = await apiClient.getAutoTuneRun(id, run.id)
      setQaSelectedRun(detail)
    } catch (err) {
      setQaRunError(err instanceof Error ? err.message : 'Failed to run evaluation')
    } finally {
      setQaRunning(false)
    }
  }

  const qaPresetConfigs = [
    { label: 'Dense top_k=5', config: { top_k: 5, retrieval_mode: 'dense' as const } },
    { label: 'Dense top_k=10', config: { top_k: 10, retrieval_mode: 'dense' as const } },
    { label: 'Hybrid top_k=5 lex=5 w=0.6', config: { top_k: 5, retrieval_mode: 'hybrid' as const, lexical_top_k: 5, hybrid_dense_weight: 0.6, hybrid_lexical_weight: 0.4 } },
    { label: 'Hybrid top_k=5 lex=5 w=0.8', config: { top_k: 5, retrieval_mode: 'hybrid' as const, lexical_top_k: 5, hybrid_dense_weight: 0.8, hybrid_lexical_weight: 0.2 } },
    { label: 'Hybrid top_k=5 lex=10 w=0.6', config: { top_k: 5, retrieval_mode: 'hybrid' as const, lexical_top_k: 10, hybrid_dense_weight: 0.6, hybrid_lexical_weight: 0.4 } },
    { label: 'Hybrid top_k=5 lex=10 w=0.8', config: { top_k: 5, retrieval_mode: 'hybrid' as const, lexical_top_k: 10, hybrid_dense_weight: 0.8, hybrid_lexical_weight: 0.2 } },
    { label: 'Hybrid top_k=10 lex=5 w=0.6', config: { top_k: 10, retrieval_mode: 'hybrid' as const, lexical_top_k: 5, hybrid_dense_weight: 0.6, hybrid_lexical_weight: 0.4 } },
    { label: 'Hybrid top_k=10 lex=5 w=0.8', config: { top_k: 10, retrieval_mode: 'hybrid' as const, lexical_top_k: 5, hybrid_dense_weight: 0.8, hybrid_lexical_weight: 0.2 } },
    { label: 'Hybrid top_k=10 lex=10 w=0.6', config: { top_k: 10, retrieval_mode: 'hybrid' as const, lexical_top_k: 10, hybrid_dense_weight: 0.6, hybrid_lexical_weight: 0.4 } },
    { label: 'Hybrid top_k=10 lex=10 w=0.8', config: { top_k: 10, retrieval_mode: 'hybrid' as const, lexical_top_k: 10, hybrid_dense_weight: 0.8, hybrid_lexical_weight: 0.2 } },
  ]

  const handleRunPresetSuite = async () => {
    if (!id || qaPresetRunning) return
    setQaPresetRunning(true)
    setQaRunError(null)
    try {
      for (const preset of qaPresetConfigs) {
        await apiClient.runGoldEval(id, preset.config)
      }
      const runs = await apiClient.listAutoTuneRuns(id)
      setQaRuns(runs)
    } catch (err) {
      setQaRunError(err instanceof Error ? err.message : 'Failed to run preset suite')
    } finally {
      setQaPresetRunning(false)
    }
  }

  const handleSelectRun = async (runId: string) => {
    if (!id) return
    try {
      const detail = await apiClient.getAutoTuneRun(id, runId)
      setQaSelectedRun(detail)
    } catch (err) {
      setQaRunsError(err instanceof Error ? err.message : 'Failed to load run details')
    }
  }

  const handleDeleteRun = async (runId: string) => {
    if (!id) return
    if (!window.confirm('Delete this run?')) return
    setQaDeleting(true)
    try {
      await apiClient.deleteAutoTuneRun(id, runId)
      const runs = await apiClient.listAutoTuneRuns(id)
      setQaRuns(runs)
      if (qaSelectedRun?.run.id === runId) {
        setQaSelectedRun(null)
      }
    } catch (err) {
      setQaRunsError(err instanceof Error ? err.message : 'Failed to delete run')
    } finally {
      setQaDeleting(false)
    }
  }

  const handleDeleteAllRuns = async () => {
    if (!id) return
    if (!window.confirm('Delete all runs for this KB?')) return
    setQaDeleting(true)
    try {
      await apiClient.deleteAllAutoTuneRuns(id)
      setQaRuns([])
      setQaSelectedRun(null)
    } catch (err) {
      setQaRunsError(err instanceof Error ? err.message : 'Failed to delete runs')
    } finally {
      setQaDeleting(false)
    }
  }

  useEffect(() => {
    if (!kb || isEditingSettings) return
    setSettingsData(buildSettingsData(kb))
  }, [kb, isEditingSettings])

  useEffect(() => {
    const loadSettingsMetadata = async () => {
      try {
        const metadata = await apiClient.getSettingsMetadata()
        setBm25MatchModes(metadata.bm25_match_modes || null)
        setBm25Analyzers(metadata.bm25_analyzers || null)
      } catch {
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

    const headingSens = settingsData.pdf_heading_sensitivity.trim()
    if (headingSens !== '') {
      const parsed = parseFloat(headingSens)
      if (Number.isNaN(parsed) || parsed < 1.0 || parsed > 2.0) {
        newErrors.pdf_heading_sensitivity = 'Heading sensitivity must be between 1.0 and 2.0'
      }
    }

    const minLen = settingsData.pdf_min_doc_length.trim()
    if (minLen !== '') {
      const parsed = parseInt(minLen)
      if (Number.isNaN(parsed) || parsed < 0 || parsed > 10000) {
        newErrors.pdf_min_doc_length = 'Min doc length must be between 0 and 10000'
      }
    }

    setSettingsErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSaveSettings = async () => {
    if (!kb) return
    if (!validateSettings()) return

    setSettingsSaving(true)
    try {
      const headingSens = settingsData.pdf_heading_sensitivity.trim()
      const minLen = settingsData.pdf_min_doc_length.trim()
      const updated = await apiClient.updateKnowledgeBase(kb.id, {
        chunk_size: settingsData.chunk_size,
        chunk_overlap: settingsData.chunk_overlap,
        upsert_batch_size: settingsData.upsert_batch_size,
        chunking_strategy: settingsData.chunking_strategy,
        contextual_description_enabled:
          settingsData.contextual_description_mode === 'default'
            ? null
            : settingsData.contextual_description_mode === 'enabled',
        pdf_table_strategy:
          settingsData.pdf_table_strategy_mode === 'default'
            ? null
            : settingsData.pdf_table_strategy_mode,
        pdf_heading_size_sensitivity: headingSens === '' ? null : parseFloat(headingSens),
        pdf_min_doc_length: minLen === '' ? null : parseInt(minLen),
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
    setSettingsData(buildSettingsData(kb))
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
      setRegenTitlesMessage(null)
      setReindexing(true)
      setReindexMessage(null)
      const contextualOverride =
        contextualDescriptionRequestMode === 'inherit'
          ? null
          : contextualDescriptionRequestMode === 'enabled'
      const result = await apiClient.reprocessKnowledgeBase(
        kb.id,
        detectDuplicatesOnReindex,
        contextualOverride
      )
      setReindexMessage(`Queued ${result.queued} documents for reprocessing.`)
    } catch (error) {
      setReindexMessage(error instanceof Error ? error.message : 'Failed to reprocess documents')
    } finally {
      setReindexing(false)
    }
  }

  const handleRegenerateTitles = async () => {
    if (!kb) return
    const limitValue = regenLimit.trim().length > 0 ? Number(regenLimit) : undefined
    if (limitValue !== undefined && (!Number.isFinite(limitValue) || limitValue <= 0)) {
      setRegenTitlesMessage('Limit must be a positive number')
      return
    }
    setRegenTitlesLoading(true)
    setRegenTitlesMessage(null)
    try {
      const result = await apiClient.regenerateChatTitles(kb.id, regenIncludeExisting, limitValue)
      setRegenTitlesMessage(`Updated ${result.updated} chats (skipped ${result.skipped}, total ${result.total})`)
    } catch (error) {
      setRegenTitlesMessage(error instanceof Error ? error.message : 'Failed to regenerate titles')
    } finally {
      setRegenTitlesLoading(false)
    }
  }

  const handleReprocessWithNewStrategy = async () => {
    if (!kb) return
    const strategyLabel = {
      simple: 'Simple (Fixed-Size)',
      smart: 'Smart (Recursive)',
      semantic: 'Semantic',
    }[kb.chunking_strategy] || kb.chunking_strategy

    const confirmed = window.confirm(
      `Reprocess all documents with current chunking strategy (${strategyLabel})?\n\n` +
      'This will:\n' +
      '• Re-chunk every document using the current strategy\n' +
      '• Re-embed all chunks\n' +
      '• Rebuild both vector and BM25 indexes\n\n' +
      'This operation cannot be undone.'
    )
    if (!confirmed) return

    try {
      setReindexing(true)
      setReindexMessage(null)
      const contextualOverride =
        contextualDescriptionRequestMode === 'inherit'
          ? null
          : contextualDescriptionRequestMode === 'enabled'
      const result = await apiClient.reprocessKnowledgeBase(
        kb.id,
        detectDuplicatesOnReindex,
        contextualOverride
      )
      setReindexMessage(`Queued ${result.queued} documents for reprocessing with ${strategyLabel} strategy.`)
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
    const contextualOverride =
      contextualDescriptionRequestMode === 'inherit'
        ? null
        : contextualDescriptionRequestMode === 'enabled'
    for (const file of files) {
      try {
        await uploadDocument(file, detectDuplicatesOnUpload, contextualOverride)
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error)
        toast.error(`Failed to upload ${file.name}`, {
          description: error instanceof Error ? error.message : undefined,
        })
        throw error
      }
    }
  }


  const handlePreviewUrl = async () => {
    const url = importUrl.trim()
    if (!url) return
    setUrlPreviewing(true)
    try {
      const preview = await apiClient.previewDocumentFromUrl(url)
      setUrlPreview(preview)
      setShowPreviewModal(true)
    } catch (error) {
      toast.error('Failed to fetch URL', {
        description: error instanceof Error ? error.message : undefined,
      })
    } finally {
      setUrlPreviewing(false)
    }
  }

  const handleConfirmImport = async () => {
    if (!urlPreview) return
    const contextualOverride =
      contextualDescriptionRequestMode === 'inherit'
        ? null
        : contextualDescriptionRequestMode === 'enabled'
    setUrlImporting(true)
    try {
      await importDocumentFromUrl(urlPreview.url, detectDuplicatesOnUpload, contextualOverride)
      toast.success('Page imported successfully')
      setShowPreviewModal(false)
      setUrlPreview(null)
      setImportUrl('')
    } catch (error) {
      toast.error('Failed to import URL', {
        description: error instanceof Error ? error.message : undefined,
      })
    } finally {
      setUrlImporting(false)
    }
  }

  const handleDelete = async () => {
    if (!kb) return
    if (!confirm(`Delete "${kb.name}" and all its documents? This cannot be undone.`)) return

    try {
      await apiClient.deleteKnowledgeBase(kb.id)
      navigate('/')
    } catch (error) {
      toast.error('Failed to delete knowledge base', {
        description: error instanceof Error ? error.message : undefined,
      })
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
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
          <Button variant="primary" onClick={() => navigate('/')}>
            Go Home
          </Button>
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
                    <Button
                      onClick={handleSaveName}
                      variant="primary"
                      size="sm"
                      disabled={nameSaving}
                    >
                      {nameSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      onClick={handleCancelEditName}
                      size="sm"
                      disabled={nameSaving}
                    >
                      Cancel
                    </Button>
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
            <div className="flex items-center gap-3">
              <Button onClick={handleLogout} size="sm">
                Logout
              </Button>
              <button
                onClick={handleDelete}
                className="text-gray-400 hover:text-red-500 transition-colors px-3 py-2"
                aria-label="Delete knowledge base"
              >
                🗑️
              </button>
            </div>
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
        {/* Top bar: Chat button + main tab navigation */}
        <div className="flex items-center justify-between mb-6">
          <Button
            onClick={() => navigate(`/kb/${kb.id}/chat`)}
            variant="primary"
            className="flex items-center space-x-2"
          >
            <span>💬</span>
            <span>Chat with KB</span>
          </Button>
        </div>

        {/* Main Tabs */}
        <div className="flex gap-0 border-b border-gray-700 mb-6">
          {([
            { key: 'documents', label: `📄 Documents (${documents.length})` },
            { key: 'settings',   label: '⚙️ Settings' },
            { key: 'evaluation', label: '🎯 Evaluation' },
          ] as const).map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setMainTab(key)}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                mainTab === key
                  ? 'border-primary-500 text-primary-500'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ── Documents Tab ── */}
        {mainTab === 'documents' && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-white">Documents</h2>
            <div className="flex items-center gap-3">
              <Button onClick={refreshDocuments} size="xs-wide" className="flex items-center gap-1.5">
                ⟳ Refresh
              </Button>
            </div>
          </div>


          {/* Add Document Area */}
          <div className="mb-6">
            {/* Mode toggle */}
            <div className="flex gap-1 mb-4 bg-gray-800 rounded-lg p-1 w-fit">
              <button
                onClick={() => setAddMode('file')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  addMode === 'file'
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                📁 Upload File
              </button>
              <button
                onClick={() => setAddMode('url')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  addMode === 'url'
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                🌐 Import URL
              </button>
            </div>

            {addMode === 'file' ? (
              <FileUpload onUpload={handleUpload} accept=".txt,.md,.fb2,.docx,.pdf" maxSize={50} multiple />
            ) : (
              <div className="flex gap-2">
                <input
                  type="url"
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !urlPreviewing && handlePreviewUrl()}
                  placeholder="https://example.com/article"
                  className="flex-1 bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 text-sm placeholder-gray-500 focus:outline-none focus:border-primary-500"
                  disabled={urlPreviewing}
                />
                <Button
                  onClick={handlePreviewUrl}
                  disabled={urlPreviewing || !importUrl.trim()}
                  size="sm"
                >
                  {urlPreviewing ? 'Fetching…' : 'Preview'}
                </Button>
              </div>
            )}

            <label className="mt-2 flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={detectDuplicatesOnUpload}
                onChange={(e) => setDetectDuplicatesOnUpload(e.target.checked)}
                className="rounded border-gray-600 bg-gray-800"
              />
              Compute duplicate chunks on upload
            </label>
            <div className="mt-3">
              <label className="block text-sm text-gray-400 mb-1">
                Contextual description for upload/reprocess operations
              </label>
              <select
                value={contextualDescriptionRequestMode}
                onChange={(e) =>
                  setContextualDescriptionRequestMode(
                    e.target.value as 'inherit' | 'enabled' | 'disabled'
                  )
                }
                className="w-full max-w-md bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 text-sm"
              >
                <option value="inherit">Inherit KB/global settings</option>
                <option value="enabled">Force enabled for this operation</option>
                <option value="disabled">Force disabled for this operation</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Applies to uploads, URL imports and reprocess/reindex actions from this tab.
              </p>
              <p className="mt-1 text-xs text-gray-500">
                Use <strong>Force enabled</strong> for one-time quality-focused reindex.
                Use <strong>Force disabled</strong> for faster, lower-cost bulk operations.
              </p>
            </div>
            <p className="mt-2 text-sm text-gray-500">
              Reindex/reprocess actions on this tab rebuild both vector and BM25 indexes for existing documents.
              Use this after changing chunking settings or BM25 analyzer.
            </p>
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
                  onReprocess={(docId) =>
                    reprocessDocument(
                      docId,
                      detectDuplicatesOnReindex,
                      contextualDescriptionRequestMode === 'inherit'
                        ? null
                        : contextualDescriptionRequestMode === 'enabled'
                    )
                  }
                  onDelete={deleteDocument}
                  onRecomputeDuplicates={recomputeDocumentDuplicates}
                />
              ))}
            </div>
          )}

          <div className="mt-6 border-t border-gray-700 pt-4 space-y-3">
            <div className="text-sm text-gray-500">
              Full reindex rebuilds chunking output, vector index, and BM25 index for all existing documents.
            </div>
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Use after changing chunking strategy/size/overlap or BM25 analyzer.
              </div>
              <Button
                onClick={handleReindexBm25}
                size="xs-wide"
                disabled={reindexing}
              >
                {reindexing ? 'Reindexing…' : 'Reindex All (Full)'}
              </Button>
            </div>

            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Full reindex using the current chunking strategy and settings.
              </div>
              <Button
                onClick={handleReprocessWithNewStrategy}
                size="xs-wide"
                disabled={reindexing}
              >
                {reindexing ? 'Reprocessing…' : 'Reindex All (Strategy)'}
              </Button>
            </div>

            <div className="text-sm text-gray-500">
              Duplicate analysis on upload: {detectDuplicatesOnUpload ? 'enabled' : 'disabled'}.
            </div>
            <div className="text-xs text-gray-500">
              Duplicate analysis on reindex: {detectDuplicatesOnReindex ? 'enabled' : 'disabled'}.
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={detectDuplicatesOnReindex}
                onChange={(e) => setDetectDuplicatesOnReindex(e.target.checked)}
                className="rounded border-gray-600 bg-gray-800"
              />
              Compute duplicate chunks on reindex
            </label>
            {reindexMessage && (
              <div className="text-sm text-gray-400">{reindexMessage}</div>
            )}
          </div>
        </div>
        )}

        {/* ── Evaluation Tab ── */}
        {mainTab === 'evaluation' && (
        <div className="card mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-white">Auto-tuning (Gold QA)</h3>
              <p className="text-xs text-gray-400 mt-1">
                Upload a QA file and run evaluation to see baseline metrics for this KB.
              </p>
              {qaGoldCount !== null && (
                <p className="text-xs text-gray-500 mt-1">
                  Gold QA samples: {qaGoldCount}
                </p>
              )}
            </div>
          </div>

          <div className="space-y-4 text-sm">
            <div>
              <label className="block text-gray-400 mb-2">Upload QA file (CSV or JSON)</label>
              <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
                <input
                  type="file"
                  accept=".csv,.json"
                  onChange={(e) => setQaFile(e.target.files?.[0] || null)}
                  className="text-xs text-gray-300"
                />
                <Button
                  onClick={handleUploadQaFile}
                  disabled={!qaFile || qaUploading}
                  size="xs-wide"
                  className="disabled:opacity-60"
                >
                  {qaUploading ? 'Uploading…' : 'Upload'}
                </Button>
              </div>
              {qaUploadMessage && (
                <div className="mt-2 text-xs text-gray-400">{qaUploadMessage}</div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
              <div>
                <label className="block text-gray-400 mb-2">Top K</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={qaRunConfig.top_k}
                  onChange={(e) => setQaRunConfig({
                    ...qaRunConfig,
                    top_k: Math.max(1, Math.min(50, Number(e.target.value) || 1)),
                  })}
                  className="w-28 bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 text-sm"
                />
              </div>
              <div>
                <label className="block text-gray-400 mb-2">Retrieval mode</label>
                <select
                  value={qaRunConfig.retrieval_mode}
                  onChange={(e) => setQaRunConfig({
                    ...qaRunConfig,
                    retrieval_mode: e.target.value as 'dense' | 'hybrid',
                  })}
                  className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 text-sm"
                >
                  <option value="dense">Dense</option>
                  <option value="hybrid">Hybrid</option>
                </select>
              </div>
              <div>
                <Button
                  onClick={handleRunGoldEval}
                  disabled={qaRunning}
                  variant="primary"
                  size="xs-wide"
                  className="disabled:opacity-60"
                >
                  {qaRunning ? 'Running…' : 'Run Evaluation'}
                </Button>
              </div>
              <div>
                <Button
                  onClick={handleRunPresetSuite}
                  disabled={qaPresetRunning || qaRunning}
                  size="xs-wide"
                  className="disabled:opacity-60"
                >
                  {qaPresetRunning ? 'Running presets…' : 'Run Preset Suite'}
                </Button>
              </div>
            </div>

            {qaRunError && (
              <div className="text-xs text-red-400">{qaRunError}</div>
            )}
          </div>

          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-gray-200">Runs</h4>
              {qaRuns.length > 0 && (
                <Button
                  onClick={handleDeleteAllRuns}
                  disabled={qaDeleting}
                  size="xs"
                  className="disabled:opacity-60"
                >
                  Clear All
                </Button>
              )}
            </div>
            {qaRunsError && <div className="text-xs text-red-400 mb-2">{qaRunsError}</div>}
            {qaRunsLoading ? (
              <div className="text-xs text-gray-400">Loading runs…</div>
            ) : qaRuns.length === 0 ? (
              <div className="text-xs text-gray-500">No runs yet.</div>
            ) : (
              <div className="space-y-2">
                {qaRuns.map((run) => {
                  const metrics = run.metrics as Record<string, unknown> | null | undefined
                  const config = run.config as Record<string, unknown> | null | undefined
                  const exact = typeof metrics?.exact_match_avg === 'number'
                    ? metrics.exact_match_avg.toFixed(3)
                    : '—'
                  const f1 = typeof metrics?.f1_avg === 'number'
                    ? metrics.f1_avg.toFixed(3)
                    : '—'
                  const concise = typeof metrics?.concise_f1_avg === 'number'
                    ? (metrics.concise_f1_avg as number).toFixed(3)
                    : '—'
                  const recall = typeof metrics?.recall_avg === 'number'
                    ? (metrics.recall_avg as number).toFixed(3)
                    : '—'
                  const noAnswerAcc = typeof metrics?.no_answer_accuracy === 'number'
                    ? (metrics.no_answer_accuracy as number).toFixed(3)
                    : '—'
                  const noAnswerAccRaw = typeof metrics?.no_answer_accuracy === 'number'
                    ? (metrics.no_answer_accuracy as number)
                    : null
                  const recallRaw = typeof metrics?.recall_avg === 'number'
                    ? (metrics.recall_avg as number)
                    : null
                  const recommendedScore = (recallRaw !== null && noAnswerAccRaw !== null)
                    ? ((recallRaw + noAnswerAccRaw) / 2).toFixed(3)
                    : '—'
                  const denseWeight = typeof config?.dense_weight === 'number'
                    ? config.dense_weight
                    : (typeof config?.hybrid_dense_weight === 'number' ? config.hybrid_dense_weight : null)
                  const lexicalWeight = typeof config?.lexical_weight === 'number'
                    ? config.lexical_weight
                    : (typeof config?.hybrid_lexical_weight === 'number' ? config.hybrid_lexical_weight : null)
                  const configLabel = config
                    ? [
                        config.retrieval_mode ? String(config.retrieval_mode) : null,
                        config.top_k ? `top_k=${String(config.top_k)}` : null,
                        config.lexical_top_k ? `lex=${String(config.lexical_top_k)}` : null,
                        denseWeight !== null ? `dense_w=${denseWeight}` : null,
                        lexicalWeight !== null ? `lex_w=${lexicalWeight}` : null,
                        config.use_mmr ? 'mmr' : null,
                      ].filter(Boolean).join(' ')
                    : null
                  const processed = run.processed_count ?? 0
                  const total = run.sample_count
                  const progress = total > 0 ? Math.round((processed / total) * 100) : 0
                  return (
                    <div
                      key={run.id}
                      className="flex items-center justify-between bg-gray-900/60 border border-gray-800 rounded px-3 py-2 text-xs"
                    >
                      <div className="text-gray-300">
                        <div className="font-medium">
                          {run.mode} • {run.status}
                        </div>
                        {configLabel && (
                          <div className="text-gray-500">
                            {configLabel}
                          </div>
                        )}
                        <div className="text-gray-500">
                          EM {exact} • F1 {f1} • Concise {concise} • Recall {recall} • No‑answer {noAnswerAcc} • Recommended {recommendedScore} • {run.sample_count} samples
                        </div>
                        {run.status === 'running' && (
                          <div className="mt-1 text-[11px] text-gray-500">
                            Progress: {processed}/{total} ({progress}%)
                            <div className="mt-1 h-1.5 w-40 bg-gray-800 rounded">
                              <div
                                className="h-1.5 bg-primary-500 rounded"
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                      <Button
                        onClick={() => handleSelectRun(run.id)}
                        size="xs"
                      >
                        View
                      </Button>
                      <Button
                        onClick={() => handleDeleteRun(run.id)}
                        disabled={qaDeleting}
                        size="xs"
                      >
                        Delete
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {qaSelectedRun && (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-gray-200">
                  Run Details
                </h4>
                <Button
                  onClick={() => setQaDetailsSeed((value) => value + 1)}
                  size="xs"
                >
                  Collapse All
                </Button>
              </div>
              {qaSelectedRun.run.metrics && (
                <div className="mb-4 text-xs text-gray-300 bg-gray-900/70 border border-gray-800 rounded px-3 py-2">
                  {(() => {
                    const recallRaw = typeof qaSelectedRun.run.metrics?.recall_avg === 'number'
                      ? (qaSelectedRun.run.metrics.recall_avg as number)
                      : null
                    const noAnswerRaw = typeof qaSelectedRun.run.metrics?.no_answer_accuracy === 'number'
                      ? (qaSelectedRun.run.metrics.no_answer_accuracy as number)
                      : null
                    const recommendedScore = (recallRaw !== null && noAnswerRaw !== null)
                      ? ((recallRaw + noAnswerRaw) / 2).toFixed(3)
                      : '—'
                    return (
                      <div className="mb-1">
                        Recommended score (Recall + No‑answer)/2: {recommendedScore}
                      </div>
                    )
                  })()}
                  <div>
                    EM: {typeof qaSelectedRun.run.metrics?.exact_match_avg === 'number'
                      ? qaSelectedRun.run.metrics.exact_match_avg.toFixed(3)
                      : '—'} • F1: {typeof qaSelectedRun.run.metrics?.f1_avg === 'number'
                      ? qaSelectedRun.run.metrics.f1_avg.toFixed(3)
                      : '—'} • Concise: {typeof qaSelectedRun.run.metrics?.concise_f1_avg === 'number'
                      ? (qaSelectedRun.run.metrics.concise_f1_avg as number).toFixed(3)
                      : '—'} • Recall: {typeof qaSelectedRun.run.metrics?.recall_avg === 'number'
                      ? (qaSelectedRun.run.metrics.recall_avg as number).toFixed(3)
                      : '—'} • No‑answer: {typeof qaSelectedRun.run.metrics?.no_answer_accuracy === 'number'
                      ? (qaSelectedRun.run.metrics.no_answer_accuracy as number).toFixed(3)
                      : '—'}
                  </div>
                </div>
              )}
              <div className="mb-3 flex flex-col sm:flex-row gap-3 sm:items-center text-xs text-gray-400">
                <input
                  value={qaFilter}
                  onChange={(e) => setQaFilter(e.target.value)}
                  placeholder="Filter by question text"
                  className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-gray-100 w-full sm:w-64"
                />
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={qaOnlyLow}
                    onChange={(e) => setQaOnlyLow(e.target.checked)}
                    className="rounded border-gray-600 bg-gray-800"
                  />
                  <span>Only low F1 (&lt; 0.4)</span>
                </label>
              </div>
              <div
                key={qaDetailsSeed}
                className="space-y-3 max-h-[420px] overflow-y-auto pr-2"
              >
                {qaSelectedRun.results
                  .filter((result) => {
                    const matches = result.question.toLowerCase().includes(qaFilter.toLowerCase())
                    if (!matches) return false
                    if (!qaOnlyLow) return true
                    const f1 = typeof result.metrics?.f1 === 'number' ? result.metrics.f1 : 1
                    return f1 < 0.4
                  })
                  .map((result) => (
                  <details key={result.id} className="bg-gray-900/70 border border-gray-800 rounded px-3 py-2">
                    <summary className="cursor-pointer text-xs text-gray-200">
                      {result.question}
                    </summary>
                    <div className="mt-2 text-xs text-gray-400 space-y-2">
                      <div>
                        <span className="text-gray-500">Expected:</span>{' '}
                        <span className="text-gray-200">{result.expected_answer}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Answer:</span>{' '}
                        <span className="text-gray-200">{result.answer || '—'}</span>
                      </div>
                      <div className="text-gray-500">
                        Metrics: {result.metrics ? JSON.stringify(result.metrics) : '—'}
                      </div>
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}

          {/* ── Recent Feedback (chat ↔ eval bridge) ── */}
          <div className="mt-8 pt-6 border-t border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h4 className="text-sm font-semibold text-gray-200">Recent Feedback from Chat</h4>
                <p className="text-xs text-gray-400 mt-1">
                  👍 messages auto-promote to gold samples. 👎 messages collect here for review.
                </p>
              </div>
              <Button onClick={loadFeedback} disabled={feedbackLoading} size="xs">
                {feedbackLoading ? 'Refreshing…' : 'Refresh'}
              </Button>
            </div>

            {feedbackItems.length === 0 ? (
              <div className="text-xs text-gray-500">
                No rated messages yet. Rate answers with 👍/👎 in chat to see them here.
              </div>
            ) : (
              <div className="space-y-2">
                {feedbackItems.map((item) => {
                  const ratedAt = new Date(item.rated_at).toLocaleString()
                  const isUp = item.rating === 1
                  const isDown = item.rating === -1
                  return (
                    <div
                      key={item.message_id}
                      className={`p-3 rounded border text-sm ${
                        isUp
                          ? 'border-emerald-500/40 bg-emerald-500/5'
                          : isDown
                          ? 'border-rose-500/40 bg-rose-500/5'
                          : 'border-gray-700 bg-gray-800'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span>{isUp ? '👍' : isDown ? '👎' : '·'}</span>
                          <span className="text-xs text-gray-500">{ratedAt}</span>
                          {item.promoted_to_gold_sample_id && (
                            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/40">
                              Promoted to gold
                            </span>
                          )}
                        </div>
                      </div>
                      {item.question && (
                        <div className="text-gray-400 text-xs mb-1">
                          <span className="text-gray-500">Q:</span>{' '}
                          <span className="line-clamp-2">{item.question}</span>
                        </div>
                      )}
                      <div className="text-gray-200 text-xs">
                        <span className="text-gray-500">A:</span>{' '}
                        <span className="line-clamp-3">{item.answer}</span>
                      </div>
                      {item.rating_comment && (
                        <div className="mt-1 text-xs text-gray-400 italic">
                          “{item.rating_comment}”
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
        )}

        {/* URL Import Preview Modal */}
        <UrlImportModal
          isOpen={showPreviewModal}
          onClose={() => { setShowPreviewModal(false); setUrlPreview(null) }}
          onImport={handleConfirmImport}
          preview={urlPreview}
          importing={urlImporting}
        />

        {/* ── Settings Tab ── */}
        {mainTab === 'settings' && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Configuration</h3>
            {configTab === 'chunking' && !isEditingSettings && (
              <Button
                onClick={() => setIsEditingSettings(true)}
                size="xs-wide"
              >
                Edit
              </Button>
            )}
            {configTab === 'search' && !isEditingRetrieval && (
              <Button
                onClick={() => {
                  setRetrievalDraft(retrievalEnvelope?.stored ?? {})
                  setIsEditingRetrieval(true)
                }}
                size="xs-wide"
              >
                Edit
              </Button>
            )}
            {configTab === 'llm' && !isEditingLlm && (
              <Button
                onClick={() => {
                  setLlmDraft({
                    llm_model: kb.llm_model ?? null,
                    llm_provider: kb.llm_provider ?? null,
                    temperature: kb.temperature ?? null,
                    use_self_check: kb.use_self_check ?? null,
                    chat_title_mode:
                      kb.use_llm_chat_titles == null
                        ? 'default'
                        : (kb.use_llm_chat_titles ? 'enabled' : 'disabled'),
                  })
                  setIsEditingLlm(true)
                }}
                size="xs-wide"
              >
                Edit
              </Button>
            )}
          </div>

          {/* Config Tabs */}
          <div className="flex gap-0 border-b border-gray-700 mb-4">
            <button
              onClick={() => setConfigTab('chunking')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                configTab === 'chunking'
                  ? 'border-primary-500 text-primary-500'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              Chunking
            </button>
            <button
              onClick={() => setConfigTab('search')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                configTab === 'search'
                  ? 'border-primary-500 text-primary-500'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              Search & Retrieval
            </button>
            <button
              onClick={() => setConfigTab('llm')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                configTab === 'llm'
                  ? 'border-primary-500 text-primary-500'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              LLM & Chat
            </button>
          </div>

          {configTab === 'chunking' && isEditingSettings ? (
            <div className="space-y-4 text-sm">
              {/* Chunking Strategy */}
              <div>
                <label htmlFor="kb-chunking-strategy" className="block text-gray-400 mb-2">
                  Chunking Strategy
                </label>
                <select
                  id="kb-chunking-strategy"
                  value={settingsData.chunking_strategy}
                  onChange={(e) => {
                    const newStrategy = e.target.value as ChunkingStrategy
                    // Auto-adjust chunk size for semantic chunking
                    const newChunkSize = newStrategy === 'semantic' ? 800 : settingsData.chunk_size
                    setSettingsData({
                      ...settingsData,
                      chunking_strategy: newStrategy,
                      chunk_size: newChunkSize
                    })
                  }}
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100"
                  disabled={settingsSaving}
                >
                  <option value="simple">⚡ Simple (Fixed-Size)</option>
                  <option value="smart">🧠 Smart (Recursive) - Recommended</option>
                  <option value="semantic">🎯 Semantic (Embeddings) ✓</option>
                </select>
                <p className="mt-2 text-sm text-yellow-500">
                  ⚠️ Changing this affects only NEW documents. To apply to existing documents, save settings and run full reindex from the Documents tab.
                </p>
              </div>

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
                <div className="flex justify-between text-sm text-gray-500 mt-1">
                  <span>100</span>
                  <span>2000</span>
                </div>
                {settingsErrors.chunk_size && <p className="mt-1 text-sm text-red-500">{settingsErrors.chunk_size}</p>}
              </div>

              {/* Chunk Overlap - not used in semantic chunking */}
              {settingsData.chunking_strategy !== 'semantic' && (
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
                  <div className="flex justify-between text-sm text-gray-500 mt-1">
                    <span>0</span>
                    <span>500</span>
                  </div>
                  {settingsErrors.chunk_overlap && <p className="mt-1 text-sm text-red-500">{settingsErrors.chunk_overlap}</p>}
                </div>
              )}

              {/* Info message for semantic chunking */}
              {settingsData.chunking_strategy === 'semantic' && (
                <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <p className="text-sm text-blue-400">
                    ℹ️ <strong>Semantic chunking</strong> finds natural topic boundaries using embeddings.
                    Chunk overlap is not used - boundaries are determined by semantic similarity.
                  </p>
                </div>
              )}

              <div>
                <label htmlFor="kb-contextual-description-mode" className="block text-gray-400 mb-2">
                  Contextual Description (Ingestion)
                </label>
                <select
                  id="kb-contextual-description-mode"
                  value={settingsData.contextual_description_mode}
                  onChange={(e) =>
                    setSettingsData({
                      ...settingsData,
                      contextual_description_mode: e.target.value as
                        | 'default'
                        | 'enabled'
                        | 'disabled',
                    })
                  }
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100"
                  disabled={settingsSaving}
                >
                  <option value="default">
                    Inherit global default ({appDefaults?.contextual_description_enabled ? 'enabled' : 'disabled'})
                  </option>
                  <option value="enabled">Enabled for this KB</option>
                  <option value="disabled">Disabled for this KB</option>
                </select>
                <p className="mt-2 text-sm text-gray-500">
                  Controls LLM-generated contextual descriptions during upload/reprocess for this KB.
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  Enable for quality-focused KBs with long/complex documents; disable for fast or cost-sensitive ingestion.
                </p>
              </div>

              <div className="border-t border-gray-700 pt-4">
                <h4 className="text-gray-200 font-medium mb-1">PDF Parsing Overrides</h4>
                <p className="text-xs text-gray-500 mb-4">
                  Override app-wide defaults for this KB. Leave on “Inherit” to use the global value.
                </p>

                <div className="space-y-4">
                  <div>
                    <label
                      htmlFor="kb-pdf-table-strategy"
                      className="block text-gray-400 mb-2 text-sm"
                    >
                      Table Extraction Strategy
                    </label>
                    <select
                      id="kb-pdf-table-strategy"
                      value={settingsData.pdf_table_strategy_mode}
                      onChange={(e) =>
                        setSettingsData({
                          ...settingsData,
                          pdf_table_strategy_mode: e.target.value as 'default' | 'lines' | 'text',
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100"
                      disabled={settingsSaving}
                    >
                      <option value="default">
                        Inherit global default ({appDefaults?.pdf_table_strategy || 'lines'})
                      </option>
                      <option value="lines">Lines (visible borders)</option>
                      <option value="text">Text (detect by gaps)</option>
                    </select>
                    <p className="mt-2 text-xs text-gray-500">
                      <span className="text-gray-300">Lines</span> finds tables by visible
                      borders (typical reports, books).{' '}
                      <span className="text-gray-300">Text</span> finds them by column
                      alignment and gaps (borderless / OCRed PDFs). Override only if the
                      default misses obvious tables in this KB.
                    </p>
                  </div>

                  <div>
                    <label
                      htmlFor="kb-pdf-heading-sensitivity"
                      className="block text-gray-400 mb-2 text-sm"
                    >
                      Heading Size Sensitivity (1.00–2.00)
                    </label>
                    <input
                      id="kb-pdf-heading-sensitivity"
                      type="number"
                      step="0.05"
                      min="1.0"
                      max="2.0"
                      placeholder={`Inherit (${
                        appDefaults?.pdf_heading_size_sensitivity ?? 1.15
                      })`}
                      value={settingsData.pdf_heading_sensitivity}
                      onChange={(e) =>
                        setSettingsData({
                          ...settingsData,
                          pdf_heading_sensitivity: e.target.value,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100"
                      disabled={settingsSaving}
                    />
                    {settingsErrors.pdf_heading_sensitivity && (
                      <p className="mt-1 text-sm text-red-500">
                        {settingsErrors.pdf_heading_sensitivity}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="kb-pdf-min-doc-length"
                      className="block text-gray-400 mb-2 text-sm"
                    >
                      Minimum Document Length (chars)
                    </label>
                    <input
                      id="kb-pdf-min-doc-length"
                      type="number"
                      min="0"
                      max="10000"
                      placeholder={`Inherit (${appDefaults?.pdf_min_doc_length ?? 100})`}
                      value={settingsData.pdf_min_doc_length}
                      onChange={(e) =>
                        setSettingsData({
                          ...settingsData,
                          pdf_min_doc_length: e.target.value,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100"
                      disabled={settingsSaving}
                    />
                    {settingsErrors.pdf_min_doc_length && (
                      <p className="mt-1 text-sm text-red-500">
                        {settingsErrors.pdf_min_doc_length}
                      </p>
                    )}
                  </div>
                </div>
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
                <div className="flex justify-between text-sm text-gray-500 mt-1">
                  <span>64</span>
                  <span>1024</span>
                </div>
                {settingsErrors.upsert_batch_size && <p className="mt-1 text-sm text-red-500">{settingsErrors.upsert_batch_size}</p>}
              </div>

              <div className="text-sm text-gray-500">
                Changes apply to new or reprocessed documents only. Reindex actions are available in the Documents tab.
              </div>

              {settingsErrors.submit && (
                <p className="text-sm text-red-500">{settingsErrors.submit}</p>
              )}

              <div className="flex items-center gap-2">
                <Button
                  onClick={handleSaveSettings}
                  variant="primary"
                  size="xs-wide"
                  disabled={settingsSaving}
                >
                  {settingsSaving ? 'Saving...' : 'Save'}
                </Button>
                <Button
                  onClick={handleCancelSettings}
                  size="xs-wide"
                  disabled={settingsSaving}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : configTab === 'chunking' ? (
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
                <span className="text-gray-400">Contextual Description:</span>
                <span className="text-white ml-2 font-medium">
                  {kb.contextual_description_enabled == null
                    ? `Inherit global (${appDefaults?.contextual_description_enabled ? 'enabled' : 'disabled'})`
                    : kb.contextual_description_enabled
                    ? 'Enabled'
                    : 'Disabled'}
                </span>
              </div>
              <div className="md:col-span-2">
                <span className="text-gray-400">Chunking Strategy:</span>
                <div className="mt-2 p-3 bg-gray-800 border border-gray-700 rounded-lg">
                  <div className="flex items-start gap-2">
                    <span className="text-xl">{getChunkingStrategyDisplay(kb.chunking_strategy).icon}</span>
                    <div>
                      <div className="text-sm font-medium text-white">
                        {getChunkingStrategyDisplay(kb.chunking_strategy).label}
                      </div>
                      <div className="text-sm text-gray-400 mt-0.5">
                        {getChunkingStrategyDisplay(kb.chunking_strategy).description}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div>
                <span className="text-gray-400">Embedding Model:</span>
                <span className="text-white ml-2 font-medium">{kb.embedding_model}</span>
                <span className="text-gray-500 ml-2 text-xs">
                  {kb.embedding_provider} · {kb.embedding_dimension}d
                </span>
              </div>
              <div>
                <span className="text-gray-400">Collection:</span>
                <span className="text-white ml-2 min-w-0 break-all font-mono text-sm">{kb.collection_name}</span>
              </div>
            </div>
          ) : null}

          {configTab === 'search' && (
            <div className="space-y-4 text-sm">
              {isEditingRetrieval ? (
                /* ── Edit mode ── */
                <div className="space-y-4">
                  <div className="space-y-4 p-3 bg-gray-800 rounded-lg">
                    <div className="text-base text-gray-200 font-semibold">Core Retrieval</div>
                    <div>
                      <label className="block text-gray-400 mb-2">Retrieval Mode</label>
                      <select
                        value={retrievalDraft.retrieval_mode ?? ''}
                        onChange={(e) => setRetrievalDraft({ ...retrievalDraft, retrieval_mode: (e.target.value || null) as 'dense' | 'hybrid' | 'lexical' | null })}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100"
                      >
                        <option value="">— use global default ({retrievalEnvelope?.effective.retrieval_mode ?? 'dense'}) —</option>
                        <option value="dense">Dense (vector)</option>
                        <option value="hybrid">Hybrid (vector + BM25)</option>
                        <option value="lexical">Lexical (BM25 only)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-gray-400 mb-2">
                        Top-K: <span className="text-white font-medium">{retrievalDraft.top_k ?? retrievalEnvelope?.effective.top_k ?? 5}</span>
                      </label>
                      <input
                        type="range"
                        min="1" max="50" step="1"
                        value={retrievalDraft.top_k ?? retrievalEnvelope?.effective.top_k ?? 5}
                        onChange={(e) => setRetrievalDraft({ ...retrievalDraft, top_k: parseInt(e.target.value) })}
                        className="w-full"
                      />
                      <div className="flex justify-between text-sm text-gray-500 mt-1"><span>1</span><span>50</span></div>
                      {retrievalDraft.top_k == null && (
                        <p className="text-sm text-gray-500 mt-1">Using global default</p>
                      )}
                    </div>
                    <div>
                      <label className="block text-gray-400 mb-2">
                        Score Threshold: <span className="text-white font-medium">{(retrievalDraft.score_threshold ?? retrievalEnvelope?.effective.score_threshold ?? 0).toFixed(2)}</span>
                      </label>
                      <input
                        type="range"
                        min="0" max="1" step="0.05"
                        value={retrievalDraft.score_threshold ?? retrievalEnvelope?.effective.score_threshold ?? 0}
                        onChange={(e) => setRetrievalDraft({ ...retrievalDraft, score_threshold: parseFloat(e.target.value) })}
                        className="w-full"
                      />
                      {retrievalDraft.score_threshold == null && (
                        <p className="text-sm text-gray-500 mt-1">Using global default</p>
                      )}
                    </div>
                  </div>

                  <div className="space-y-3 p-3 bg-gray-800 rounded-lg">
                    <div className="text-base text-gray-200 font-semibold">Context Assembly</div>
                    <div>
                      <label className="block text-gray-400 mb-2">
                        Max context chars: <span className="text-white font-medium">
                          {(retrievalDraft.max_context_chars ?? retrievalEnvelope?.effective.max_context_chars ?? 0) === 0
                            ? 'unlimited'
                            : (retrievalDraft.max_context_chars ?? retrievalEnvelope?.effective.max_context_chars ?? 0).toLocaleString()}
                        </span>
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="1000"
                        value={retrievalDraft.max_context_chars ?? retrievalEnvelope?.effective.max_context_chars ?? 0}
                        onChange={(e) => setRetrievalDraft({ ...retrievalDraft, max_context_chars: parseInt(e.target.value) || 0 })}
                        className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 text-sm"
                      />
                      <p className="text-sm text-gray-500 mt-1">0 = unlimited</p>
                    </div>
                  </div>

                  {/* Hybrid weights + BM25 - show when mode is hybrid or lexical */}
                  {(['hybrid', 'lexical'].includes(retrievalDraft.retrieval_mode ?? retrievalEnvelope?.effective.retrieval_mode ?? '')) && (
                    <div className="space-y-3 p-3 bg-gray-800 rounded-lg">
                      <div className="text-base text-gray-200 font-semibold">Hybrid / Lexical Retrieval</div>
                      {(retrievalDraft.retrieval_mode ?? retrievalEnvelope?.effective.retrieval_mode) === 'hybrid' && (<>
                      <div className="flex items-center justify-between">
                        <div className="text-base text-gray-200 font-semibold">Hybrid Weights</div>
                        <label className="flex items-center gap-1.5 text-sm text-gray-400 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={linkHybridWeights}
                            onChange={(e) => setLinkHybridWeights(e.target.checked)}
                            className="rounded"
                          />
                          Link weights (lexical = 1 − dense)
                        </label>
                      </div>
                      <div>
                        <label className="block text-gray-400 mb-1 text-sm">
                          Dense weight: <span className="text-white">{(retrievalDraft.hybrid_dense_weight ?? retrievalEnvelope?.effective.hybrid_dense_weight ?? 0.6).toFixed(2)}</span>
                        </label>
                        <input
                          type="range" min="0" max="1" step="0.05"
                          value={retrievalDraft.hybrid_dense_weight ?? retrievalEnvelope?.effective.hybrid_dense_weight ?? 0.6}
                          onChange={(e) => {
                            const dense = parseFloat(e.target.value)
                            setRetrievalDraft({
                              ...retrievalDraft,
                              hybrid_dense_weight: dense,
                              ...(linkHybridWeights ? { hybrid_lexical_weight: parseFloat((1 - dense).toFixed(2)) } : {}),
                            })
                          }}
                          className="w-full"
                        />
                      </div>
                      <div>
                        <label className="block text-gray-400 mb-1 text-sm">
                          Lexical weight: <span className="text-white">{(retrievalDraft.hybrid_lexical_weight ?? retrievalEnvelope?.effective.hybrid_lexical_weight ?? 0.4).toFixed(2)}</span>
                        </label>
                        <input
                          type="range" min="0" max="1" step="0.05"
                          value={retrievalDraft.hybrid_lexical_weight ?? retrievalEnvelope?.effective.hybrid_lexical_weight ?? 0.4}
                          disabled={linkHybridWeights}
                          onChange={(e) => {
                            const lexical = parseFloat(e.target.value)
                            setRetrievalDraft({
                              ...retrievalDraft,
                              hybrid_lexical_weight: lexical,
                              ...(linkHybridWeights ? { hybrid_dense_weight: parseFloat((1 - lexical).toFixed(2)) } : {}),
                            })
                          }}
                          className="w-full disabled:opacity-40"
                        />
                      </div>
                      <div>
                        <label className="block text-gray-400 mb-1 text-sm">
                          Lexical Top-K: <span className="text-white">{retrievalDraft.lexical_top_k ?? retrievalEnvelope?.effective.lexical_top_k ?? 20}</span>
                        </label>
                        <input
                          type="range" min="1" max="100" step="1"
                          value={retrievalDraft.lexical_top_k ?? retrievalEnvelope?.effective.lexical_top_k ?? 20}
                          onChange={(e) => setRetrievalDraft({ ...retrievalDraft, lexical_top_k: parseInt(e.target.value) })}
                          className="w-full"
                        />
                      </div>
                      </>)}
                      <div className="border-t border-gray-700 pt-3 mt-1">
                        <div className="text-base text-gray-200 font-semibold mb-3">BM25 Settings</div>
                        <div className="grid grid-cols-1 gap-3">
                          <div>
                            <label className="block text-gray-400 mb-1 text-sm">Match mode</label>
                            <select
                              value={retrievalDraft.bm25_match_mode ?? retrievalEnvelope?.effective.bm25_match_mode ?? ''}
                              onChange={(e) => setRetrievalDraft({ ...retrievalDraft, bm25_match_mode: e.target.value || null })}
                              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100 text-sm"
                            >
                              <option value="">— global default —</option>
                              {(bm25MatchModes ?? ['strict', 'balanced', 'loose']).map((m) => (
                                <option key={m} value={m}>{m}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-gray-400 mb-1 text-sm">
                              Min should match: <span className="text-white">{retrievalDraft.bm25_min_should_match ?? retrievalEnvelope?.effective.bm25_min_should_match ?? 0}%</span>
                            </label>
                            <input
                              type="range" min="0" max="100" step="5"
                              value={retrievalDraft.bm25_min_should_match ?? retrievalEnvelope?.effective.bm25_min_should_match ?? 0}
                              onChange={(e) => setRetrievalDraft({ ...retrievalDraft, bm25_min_should_match: parseInt(e.target.value) })}
                              className="w-full"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={retrievalDraft.bm25_use_phrase ?? retrievalEnvelope?.effective.bm25_use_phrase ?? false}
                              onChange={(e) => setRetrievalDraft({ ...retrievalDraft, bm25_use_phrase: e.target.checked })}
                              className="rounded"
                            />
                            <label className="text-sm text-gray-400">Use phrase match</label>
                          </div>
                          <div>
                            <label className="block text-gray-400 mb-1 text-sm">
                              Analyzer <span className="text-gray-500">(advanced — requires reindex)</span>
                            </label>
                            <select
                              value={retrievalDraft.bm25_analyzer ?? retrievalEnvelope?.effective.bm25_analyzer ?? ''}
                              onChange={(e) => setRetrievalDraft({ ...retrievalDraft, bm25_analyzer: e.target.value || null })}
                              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-100 text-sm"
                            >
                              <option value="">— global default —</option>
                              {(bm25Analyzers ?? ['auto', 'ru', 'en']).map((a) => (
                                <option key={a} value={a}>{a}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                        <p className="text-sm text-gray-500">
                          BM25 analyzer affects index build. After changing it, run full reindex in the Documents tab.
                          Other BM25 fields (match mode / min should match / phrase) apply immediately to new queries.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Rerank */}
                  <div className="space-y-2 p-3 bg-gray-800 rounded-lg">
                    <div className="flex items-center justify-between">
                      <label className="text-base text-gray-200 font-semibold">Reranking</label>
                      <label className="flex items-center gap-2 text-sm text-gray-300">
                        <input
                          type="checkbox"
                          checked={retrievalDraft.rerank_enabled ?? retrievalEnvelope?.effective.rerank_enabled ?? false}
                          onChange={(e) => setRetrievalDraft({ ...retrievalDraft, rerank_enabled: e.target.checked })}
                          className="rounded border-gray-600 bg-gray-900"
                        />
                        Enabled
                      </label>
                    </div>
                    {(retrievalDraft.rerank_enabled ?? retrievalEnvelope?.effective.rerank_enabled) && (
                      <div className="space-y-3 mt-2">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-gray-400 mb-1 text-sm">Provider</label>
                            <input
                              type="text"
                              value={retrievalDraft.rerank_provider ?? retrievalEnvelope?.effective.rerank_provider ?? ''}
                              onChange={(e) => setRetrievalDraft({ ...retrievalDraft, rerank_provider: e.target.value || null })}
                              placeholder="e.g. cohere, voyage"
                              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-gray-100 text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-gray-400 mb-1 text-sm">Model</label>
                            <input
                              type="text"
                              value={retrievalDraft.rerank_model ?? retrievalEnvelope?.effective.rerank_model ?? ''}
                              onChange={(e) => setRetrievalDraft({ ...retrievalDraft, rerank_model: e.target.value || null })}
                              placeholder="e.g. rerank-2.5-lite"
                              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-gray-100 text-sm"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-gray-400 mb-1 text-sm">
                            Candidate pool: <span className="text-white">{retrievalDraft.rerank_candidate_pool ?? retrievalEnvelope?.effective.rerank_candidate_pool ?? 20}</span>
                          </label>
                          <input
                            type="range" min="1" max="100" step="1"
                            value={retrievalDraft.rerank_candidate_pool ?? retrievalEnvelope?.effective.rerank_candidate_pool ?? 20}
                            onChange={(e) => setRetrievalDraft({ ...retrievalDraft, rerank_candidate_pool: parseInt(e.target.value) })}
                            className="w-full"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 mb-1 text-sm">
                            Top-N after rerank: <span className="text-white">{retrievalDraft.rerank_top_n ?? retrievalEnvelope?.effective.rerank_top_n ?? '—'}</span>
                          </label>
                          <input
                            type="range" min="1" max="50" step="1"
                            value={retrievalDraft.rerank_top_n ?? retrievalEnvelope?.effective.rerank_top_n ?? 5}
                            onChange={(e) => setRetrievalDraft({ ...retrievalDraft, rerank_top_n: parseInt(e.target.value) })}
                            className="w-full"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 mb-1 text-sm">
                            Min rerank score: <span className="text-white">{(retrievalDraft.rerank_min_score ?? retrievalEnvelope?.effective.rerank_min_score ?? 0).toFixed(2)}</span>
                          </label>
                          <input
                            type="range" min="0" max="1" step="0.05"
                            value={retrievalDraft.rerank_min_score ?? retrievalEnvelope?.effective.rerank_min_score ?? 0}
                            onChange={(e) => setRetrievalDraft({ ...retrievalDraft, rerank_min_score: parseFloat(e.target.value) })}
                            className="w-full"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 pt-2">
                    <Button
                      onClick={async () => {
                        if (!id) return
                        setRetrievalSaving(true)
                        try {
                          // Remove null/undefined fields before sending
                          const payload: KBRetrievalSettingsStored = {}
                          Object.entries(retrievalDraft).forEach(([k, v]) => {
                            if (v !== null && v !== undefined && v !== '') {
                              (payload as Record<string, unknown>)[k] = v
                            }
                          })
                          const updated = await apiClient.updateKBRetrievalSettings(id, payload)
                          setRetrievalEnvelope(updated)
                          setRetrievalDraft(updated.stored ?? {})
                          setIsEditingRetrieval(false)
                        } catch {
                          // ignore
                        } finally {
                          setRetrievalSaving(false)
                        }
                      }}
                      variant="primary"
                      size="xs-wide"
                      disabled={retrievalSaving}
                    >
                      {retrievalSaving ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      onClick={() => {
                        setRetrievalDraft(retrievalEnvelope?.stored ?? {})
                        setIsEditingRetrieval(false)
                      }}
                      size="xs-wide"
                      disabled={retrievalSaving}
                    >
                      Cancel
                    </Button>
                    {retrievalEnvelope?.stored && Object.keys(retrievalEnvelope.stored).length > 0 && (
                      <Button
                        onClick={async () => {
                          if (!id || !window.confirm('Reset all search settings to global defaults for this KB?')) return
                          setRetrievalSaving(true)
                          try {
                            const updated = await apiClient.clearKBRetrievalSettings(id)
                            setRetrievalEnvelope(updated)
                            setRetrievalDraft({})
                            setIsEditingRetrieval(false)
                          } catch {
                            // ignore
                          } finally {
                            setRetrievalSaving(false)
                          }
                        }}
                        size="xs-wide"
                        disabled={retrievalSaving}
                      >
                        Reset to Global
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                /* ── View mode ── */
                retrievalEnvelope ? (
                  <div className="space-y-4">
                    <div className="text-sm text-gray-500">Badge indicates source: `KB` override or inherited `global` default.</div>

                    <div className="space-y-2 p-3 bg-gray-800 rounded-lg">
                      <div className="text-base text-gray-200 font-semibold">Core Retrieval</div>
                      {renderEffectiveRetrievalRow('Retrieval Mode', 'retrieval_mode', retrievalEnvelope.effective.retrieval_mode)}
                      {renderEffectiveRetrievalRow('Top-K', 'top_k', String(retrievalEnvelope.effective.top_k))}
                      {renderEffectiveRetrievalRow('Score Threshold', 'score_threshold', String(retrievalEnvelope.effective.score_threshold))}
                    </div>

                    <div className="space-y-2 p-3 bg-gray-800 rounded-lg">
                      <div className="text-base text-gray-200 font-semibold">Context Assembly</div>
                      {renderEffectiveRetrievalRow('Max Context Chars', 'max_context_chars', retrievalEnvelope.effective.max_context_chars === 0 ? 'unlimited' : String(retrievalEnvelope.effective.max_context_chars))}
                    </div>

                    {(['hybrid', 'lexical'].includes(retrievalEnvelope.effective.retrieval_mode)) && (
                      <div className="space-y-2 p-3 bg-gray-800 rounded-lg">
                        <div className="text-base text-gray-200 font-semibold">Hybrid / BM25</div>
                        {retrievalEnvelope.effective.retrieval_mode === 'hybrid' && (
                          <>
                            {renderEffectiveRetrievalRow('Lexical Top-K', 'lexical_top_k', String(retrievalEnvelope.effective.lexical_top_k))}
                            {renderEffectiveRetrievalRow('Dense Weight', 'hybrid_dense_weight', String(retrievalEnvelope.effective.hybrid_dense_weight))}
                            {renderEffectiveRetrievalRow('Lexical Weight', 'hybrid_lexical_weight', String(retrievalEnvelope.effective.hybrid_lexical_weight))}
                          </>
                        )}
                        {renderEffectiveRetrievalRow('BM25 Match Mode', 'bm25_match_mode', retrievalEnvelope.effective.bm25_match_mode ?? '—')}
                        {renderEffectiveRetrievalRow('BM25 Min Match', 'bm25_min_should_match', retrievalEnvelope.effective.bm25_min_should_match != null ? `${retrievalEnvelope.effective.bm25_min_should_match}%` : '—')}
                        {renderEffectiveRetrievalRow('BM25 Phrase', 'bm25_use_phrase', retrievalEnvelope.effective.bm25_use_phrase ? 'yes' : 'no')}
                        {renderEffectiveRetrievalRow('BM25 Analyzer', 'bm25_analyzer', retrievalEnvelope.effective.bm25_analyzer ?? '—')}
                      </div>
                    )}

                    <div className="space-y-2 p-3 bg-gray-800 rounded-lg">
                      <div className="text-base text-gray-200 font-semibold">Reranking</div>
                      {renderEffectiveRetrievalRow('Rerank', 'rerank_enabled', retrievalEnvelope.effective.rerank_enabled ? 'enabled' : 'disabled')}
                      {retrievalEnvelope.effective.rerank_enabled && (
                        <>
                          {renderEffectiveRetrievalRow('Rerank Provider', 'rerank_provider', retrievalEnvelope.effective.rerank_provider ?? '—')}
                          {renderEffectiveRetrievalRow('Rerank Model', 'rerank_model', retrievalEnvelope.effective.rerank_model ?? '—')}
                          {renderEffectiveRetrievalRow('Candidate Pool', 'rerank_candidate_pool', String(retrievalEnvelope.effective.rerank_candidate_pool))}
                          {renderEffectiveRetrievalRow('Rerank Top-N', 'rerank_top_n', retrievalEnvelope.effective.rerank_top_n != null ? String(retrievalEnvelope.effective.rerank_top_n) : '—')}
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2" aria-busy="true" aria-live="polite">
                    <div className="h-3 w-1/2 bg-gray-700/60 rounded animate-pulse" />
                    <div className="h-3 w-2/3 bg-gray-700/60 rounded animate-pulse" />
                    <div className="h-3 w-1/3 bg-gray-700/60 rounded animate-pulse" />
                  </div>
                )
              )}
            </div>
          )}

          {/* ── LLM & Chat Tab ── */}
          {configTab === 'llm' && (
            <div className="space-y-4 text-sm">
              {isEditingLlm ? (
                <div className="space-y-5">
                  {/* LLM Model */}
                  <div>
                    <label className="block text-gray-400 mb-2">LLM Model</label>
                    <LLMSelector
                      value={llmDraft.llm_model ?? ''}
                      onChange={(model, provider) => setLlmDraft({ ...llmDraft, llm_model: model || null, llm_provider: provider || null })}
                    />
                    <p className="text-sm text-gray-500 mt-1">Leave empty to use global default</p>
                  </div>

                  {/* Temperature */}
                  <div>
                    <label className="block text-gray-400 mb-2">
                      Temperature: <span className="text-white font-medium">
                        {llmDraft.temperature != null ? llmDraft.temperature.toFixed(1) : `global default (${appDefaults?.temperature ?? 0.7})`}
                      </span>
                    </label>
                    <input
                      type="range" min="0" max="2" step="0.1"
                      value={llmDraft.temperature ?? appDefaults?.temperature ?? 0.7}
                      onChange={(e) => setLlmDraft({ ...llmDraft, temperature: parseFloat(e.target.value) })}
                      className="w-full"
                    />
                    <div className="flex justify-between text-sm text-gray-500 mt-1"><span>0 (precise)</span><span>1</span><span>2 (creative)</span></div>
                    {llmDraft.temperature != null && (
                      <button onClick={() => setLlmDraft({ ...llmDraft, temperature: null })} className="mt-1 text-sm text-gray-500 hover:text-gray-300">
                        Reset to global default
                      </button>
                    )}
                  </div>

                  {/* Self-check */}
                  <div className="p-3 bg-gray-800 rounded-lg space-y-1">
                    <label className="flex items-center gap-2 text-gray-300 text-sm">
                      <input
                        type="checkbox"
                        checked={llmDraft.use_self_check ?? false}
                        onChange={(e) => setLlmDraft({ ...llmDraft, use_self_check: e.target.checked })}
                        className="rounded border-gray-600 bg-gray-900"
                      />
                      Enable Self-Check Validation
                    </label>
                    <p className="text-sm text-gray-500 ml-5">Second LLM pass to validate the answer against retrieved chunks. More accurate but slower.</p>
                    {llmDraft.use_self_check == null && (
                      <p className="text-sm text-gray-500 ml-5">Using global default</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-gray-400 mb-2">Chat title generation</label>
                    <select
                      value={llmDraft.chat_title_mode}
                      onChange={(e) => setLlmDraft({
                        ...llmDraft,
                        chat_title_mode: e.target.value as 'default' | 'enabled' | 'disabled',
                      })}
                      className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100"
                    >
                      <option value="default">Use global default</option>
                      <option value="enabled">Enabled (LLM)</option>
                      <option value="disabled">Disabled (fallback)</option>
                    </select>
                    <p className="text-sm text-gray-500 mt-1">
                      {llmDraft.chat_title_mode === 'default'
                        ? `Using global default: ${
                          appDefaults?.use_llm_chat_titles === true
                            ? 'Enabled'
                            : appDefaults?.use_llm_chat_titles === false
                              ? 'Disabled'
                              : 'Unknown'
                        }`
                        : llmDraft.chat_title_mode === 'enabled'
                          ? 'LLM generates short titles from the first Q&A'
                          : 'Title falls back to the first user question'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      onClick={async () => {
                        if (!id || !kb) return
                        setLlmSaving(true)
                        try {
                          const chatTitleValue = llmDraft.chat_title_mode === 'default'
                            ? null
                            : llmDraft.chat_title_mode === 'enabled'
                              ? true
                              : false
                          const updated = await apiClient.updateKnowledgeBase(id, {
                            llm_model: llmDraft.llm_model,
                            llm_provider: llmDraft.llm_provider,
                            temperature: llmDraft.temperature,
                            use_self_check: llmDraft.use_self_check,
                            use_llm_chat_titles: chatTitleValue,
                          })
                          setKb(updated)
                          setIsEditingLlm(false)
                        } catch {
                          // ignore
                        } finally {
                          setLlmSaving(false)
                        }
                      }}
                      variant="primary"
                      size="xs-wide"
                      disabled={llmSaving}
                    >
                      {llmSaving ? 'Saving…' : 'Save'}
                    </Button>
                    <Button onClick={() => setIsEditingLlm(false)} size="xs-wide" disabled={llmSaving}>
                      Cancel
                    </Button>
                    {(kb.llm_model || kb.temperature != null || kb.use_self_check != null || kb.use_llm_chat_titles != null) && (
                      <Button
                        onClick={async () => {
                          if (!id || !window.confirm('Reset LLM settings to global defaults for this KB?')) return
                          setLlmSaving(true)
                          try {
                            const updated = await apiClient.updateKnowledgeBase(id, {
                              llm_model: null,
                              llm_provider: null,
                              temperature: null,
                              use_self_check: null,
                              use_llm_chat_titles: null,
                            })
                            setKb(updated)
                            setLlmDraft({
                              llm_model: null,
                              llm_provider: null,
                              temperature: null,
                              use_self_check: null,
                              chat_title_mode: 'default',
                            })
                            setIsEditingLlm(false)
                          } catch {
                            // ignore
                          } finally {
                            setLlmSaving(false)
                          }
                        }}
                        size="xs-wide"
                        disabled={llmSaving}
                      >
                        Reset to Global
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {[
                    { label: 'LLM Model', value: kb.llm_model ?? '—', isOverride: !!kb.llm_model },
                    { label: 'LLM Provider', value: kb.llm_provider ?? '—', isOverride: !!kb.llm_provider },
                    { label: 'Temperature', value: kb.temperature != null ? kb.temperature.toFixed(1) : '—', isOverride: kb.temperature != null },
                    { label: 'Self-Check', value: kb.use_self_check != null ? (kb.use_self_check ? 'enabled' : 'disabled') : '—', isOverride: kb.use_self_check != null },
                    {
                      label: 'Chat Titles',
                      value: kb.use_llm_chat_titles != null ? (kb.use_llm_chat_titles ? 'enabled' : 'disabled') : '—',
                      isOverride: kb.use_llm_chat_titles != null,
                    },
                  ].map(({ label, value, isOverride }) => (
                    <div key={label} className="flex items-center justify-between">
                      <span className="text-gray-400">{label}:</span>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{value}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${isOverride ? 'bg-primary-500/20 text-primary-400' : 'bg-gray-700 text-gray-400'}`}>
                          {isOverride ? 'KB' : 'global'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="mt-4 border-t border-gray-700 pt-4 space-y-3">
            <div className="text-sm text-gray-400">
              Regenerate chat titles for this KB (uses the first Q&amp;A per conversation).
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={regenIncludeExisting}
                  onChange={(e) => setRegenIncludeExisting(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-800"
                  disabled={regenTitlesLoading}
                />
                Regenerate existing titles
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="1"
                  placeholder="Limit (optional)"
                  value={regenLimit}
                  onChange={(e) => setRegenLimit(e.target.value)}
                  className="w-40 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-gray-100"
                  disabled={regenTitlesLoading}
                />
                <Button
                  onClick={handleRegenerateTitles}
                  size="xs-wide"
                  disabled={regenTitlesLoading}
                >
                  {regenTitlesLoading ? 'Regenerating…' : 'Regenerate Chat Titles'}
                </Button>
              </div>
            </div>
            {regenTitlesMessage && (
              <div className="text-sm text-gray-400">{regenTitlesMessage}</div>
            )}
          </div>

        </div>
        )}

      </main>
    </div>
  )
}
