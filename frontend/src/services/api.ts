import axios from 'axios'
import type { AxiosInstance, AxiosError } from 'axios'
import type { APIError } from '../types/index'
import type {
  KnowledgeBase,
  CreateKBRequest,
  Document,
  DocumentStatusResponse,
  PaginatedResponse,
  ChatRequest,
  ChatResponse,
  ConversationSummary,
  ChatMessageResponse,
  ConversationDetail,
  ConversationSettings,
  ConversationTitleUpdate,
  EmbeddingModel,
  AppSettings,
  AppSettingsUpdate,
  ApiInfo,
  SettingsMetadata,
  LoginRequest,
  TokenResponse,
  MeResponse,
  PromptVersionSummary,
  PromptVersionDetail,
  PromptVersionCreate,
  SelfCheckPromptVersionSummary,
  SelfCheckPromptVersionDetail,
  SelfCheckPromptVersionCreate,
  QASampleUploadResponse,
  QAEvalRun,
  QAEvalRunConfig,
  QAEvalRunDetail,
  QAGoldCountResponse,
} from '../types/index'

const ACCESS_TOKEN_KEY = 'kb_access_token'

class APIClient {
  private client: AxiosInstance
  private refreshPromise: Promise<boolean> | null = null

  constructor() {
    const baseURL = import.meta.env.VITE_API_BASE_URL || ''
    const prefix = import.meta.env.VITE_API_PREFIX || '/api/v1'

    this.client = axios.create({
      baseURL: baseURL + prefix,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.request.use((config) => {
      const token = this.getAccessToken()
      if (token) {
        config.headers = config.headers || {}
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<APIError>) => {
        const originalRequest = error.config as any
        const status = error.response?.status

        if (status === 401 && !originalRequest?._retry && !originalRequest?.url?.includes('/auth/')) {
          originalRequest._retry = true
          try {
            const refreshed = await this.refreshToken()
            if (refreshed) {
              return this.client(originalRequest)
            }
          } catch {
            this.handleAuthFailure()
          }
          this.handleAuthFailure()
        }

        if (error.response?.data) {
          throw new Error(error.response.data.detail || 'An error occurred')
        }
        throw error
      }
    )
  }

  private getAccessToken(): string | null {
    try {
      return localStorage.getItem(ACCESS_TOKEN_KEY)
    } catch {
      return null
    }
  }

  private setAccessToken(token: string) {
    try {
      localStorage.setItem(ACCESS_TOKEN_KEY, token)
    } catch {
      // ignore
    }
  }

  private clearAccessToken() {
    try {
      localStorage.removeItem(ACCESS_TOKEN_KEY)
    } catch {
      // ignore
    }
  }

  private handleAuthFailure() {
    this.clearAccessToken()
    if (typeof window !== 'undefined') {
      const path = window.location?.pathname || ''
      if (!path.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
  }

  // Auth
  async login(payload: LoginRequest): Promise<TokenResponse> {
    const response = await this.client.post<TokenResponse>('/auth/login', payload)
    this.setAccessToken(response.data.access_token)
    return response.data
  }

  async refreshToken(): Promise<boolean> {
    if (this.refreshPromise) {
      return this.refreshPromise
    }

    this.refreshPromise = (async () => {
      try {
        const response = await this.client.post<TokenResponse>('/auth/refresh')
        this.setAccessToken(response.data.access_token)
        return true
      } catch {
        return false
      } finally {
        this.refreshPromise = null
      }
    })()

    return this.refreshPromise
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout')
    } finally {
      this.clearAccessToken()
    }
  }

  async me(): Promise<MeResponse> {
    const response = await this.client.get<MeResponse>('/auth/me')
    return response.data
  }

  // Knowledge Bases
  async getKnowledgeBases(page = 1, pageSize = 10): Promise<PaginatedResponse<KnowledgeBase>> {
    const response = await this.client.get<PaginatedResponse<KnowledgeBase>>('/knowledge-bases/', {
      params: { page, page_size: pageSize },
    })
    return response.data
  }

  async getDeletedKnowledgeBases(page = 1, pageSize = 10): Promise<PaginatedResponse<KnowledgeBase>> {
    const response = await this.client.get<PaginatedResponse<KnowledgeBase>>('/knowledge-bases/deleted', {
      params: { page, page_size: pageSize },
    })
    return response.data
  }

  async getKnowledgeBase(id: string): Promise<KnowledgeBase> {
    const response = await this.client.get<KnowledgeBase>(`/knowledge-bases/${id}`)
    return response.data
  }

  // Prompt Versions
  async listPromptVersions(): Promise<PromptVersionSummary[]> {
    const response = await this.client.get<PromptVersionSummary[]>('/prompts/')
    return response.data
  }

  async getPromptVersion(id: string): Promise<PromptVersionDetail> {
    const response = await this.client.get<PromptVersionDetail>(`/prompts/${id}`)
    return response.data
  }

  async getActivePromptVersion(): Promise<PromptVersionDetail | null> {
    const response = await this.client.get<PromptVersionDetail | null>('/prompts/active')
    return response.data
  }

  async createPromptVersion(payload: PromptVersionCreate): Promise<PromptVersionDetail> {
    const response = await this.client.post<PromptVersionDetail>('/prompts/', payload)
    return response.data
  }

  async activatePromptVersion(id: string): Promise<PromptVersionDetail> {
    const response = await this.client.post<PromptVersionDetail>(`/prompts/${id}/activate`)
    return response.data
  }

  // Self-Check Prompts
  async listSelfCheckPromptVersions(): Promise<SelfCheckPromptVersionSummary[]> {
    const response = await this.client.get<SelfCheckPromptVersionSummary[]>('/prompts/self-check')
    return response.data
  }

  async getSelfCheckPromptVersion(id: string): Promise<SelfCheckPromptVersionDetail> {
    const response = await this.client.get<SelfCheckPromptVersionDetail>(`/prompts/self-check/${id}`)
    return response.data
  }

  async getActiveSelfCheckPromptVersion(): Promise<SelfCheckPromptVersionDetail | null> {
    const response = await this.client.get<SelfCheckPromptVersionDetail | null>('/prompts/self-check/active')
    return response.data
  }

  async createSelfCheckPromptVersion(payload: SelfCheckPromptVersionCreate): Promise<SelfCheckPromptVersionDetail> {
    const response = await this.client.post<SelfCheckPromptVersionDetail>('/prompts/self-check', payload)
    return response.data
  }

  async activateSelfCheckPromptVersion(id: string): Promise<SelfCheckPromptVersionDetail> {
    const response = await this.client.post<SelfCheckPromptVersionDetail>(`/prompts/self-check/${id}/activate`)
    return response.data
  }

  async createKnowledgeBase(data: CreateKBRequest): Promise<KnowledgeBase> {
    const response = await this.client.post<KnowledgeBase>('/knowledge-bases/', data)
    return response.data
  }

  async updateKnowledgeBase(id: string, data: Partial<CreateKBRequest>): Promise<KnowledgeBase> {
    const response = await this.client.put<KnowledgeBase>(`/knowledge-bases/${id}`, data)
    return response.data
  }

  async deleteKnowledgeBase(id: string): Promise<void> {
    await this.client.delete(`/knowledge-bases/${id}`)
  }

  async restoreKnowledgeBase(id: string): Promise<{ restored: boolean; queued: number; knowledge_base_id: string }> {
    const response = await this.client.post<{ restored: boolean; queued: number; knowledge_base_id: string }>(
      `/knowledge-bases/${id}/restore`
    )
    return response.data
  }

  async purgeKnowledgeBase(id: string): Promise<void> {
    await this.client.delete(`/knowledge-bases/${id}/purge`)
  }

  async reprocessKnowledgeBase(id: string): Promise<{ queued: number; knowledge_base_id: string }> {
    const response = await this.client.post<{ queued: number; knowledge_base_id: string }>(`/knowledge-bases/${id}/reprocess`)
    return response.data
  }

  // QA Auto-Tuning (Gold)
  async uploadGoldQA(
    kbId: string,
    file: File,
    replaceExisting = true
  ): Promise<QASampleUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await this.client.post<QASampleUploadResponse>(
      `/knowledge-bases/${kbId}/auto-tune/gold/upload`,
      formData,
      {
        params: { replace_existing: replaceExisting },
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    )
    return response.data
  }

  async getGoldQACount(kbId: string): Promise<QAGoldCountResponse> {
    const response = await this.client.get<QAGoldCountResponse>(`/knowledge-bases/${kbId}/auto-tune/gold/count`)
    return response.data
  }

  async runGoldEval(kbId: string, payload: QAEvalRunConfig): Promise<QAEvalRun> {
    const response = await this.client.post<QAEvalRun>(`/knowledge-bases/${kbId}/auto-tune/gold/run`, payload)
    return response.data
  }

  async listAutoTuneRuns(kbId: string, limit = 20): Promise<QAEvalRun[]> {
    const response = await this.client.get<QAEvalRun[]>(`/knowledge-bases/${kbId}/auto-tune/runs`, {
      params: { limit },
    })
    return response.data
  }

  async getAutoTuneRun(kbId: string, runId: string): Promise<QAEvalRunDetail> {
    const response = await this.client.get<QAEvalRunDetail>(`/knowledge-bases/${kbId}/auto-tune/runs/${runId}`)
    return response.data
  }

  async deleteAutoTuneRun(kbId: string, runId: string): Promise<void> {
    await this.client.delete(`/knowledge-bases/${kbId}/auto-tune/runs/${runId}`)
  }

  async deleteAllAutoTuneRuns(kbId: string): Promise<void> {
    await this.client.delete(`/knowledge-bases/${kbId}/auto-tune/runs`)
  }

  // Documents
  async getDocuments(kbId: string, page = 1, pageSize = 20): Promise<PaginatedResponse<Document>> {
    const response = await this.client.get<PaginatedResponse<Document>>('/documents/', {
      params: { knowledge_base_id: kbId, page, page_size: pageSize },
    })
    return response.data
  }

  async getDocument(id: string): Promise<Document> {
    const response = await this.client.get<Document>(`/documents/${id}`)
    return response.data
  }

  async getDocumentStatus(id: string): Promise<DocumentStatusResponse> {
    const response = await this.client.get<DocumentStatusResponse>(`/documents/${id}/status`)
    return response.data
  }

  async uploadDocument(kbId: string, file: File): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('knowledge_base_id', kbId)

    const response = await this.client.post<Document>('/documents/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async reprocessDocument(id: string): Promise<Document> {
    const response = await this.client.post<Document>(`/documents/${id}/reprocess`)
    return response.data
  }

  async deleteDocument(id: string): Promise<void> {
    await this.client.delete(`/documents/${id}`)
  }

  // Document Structure
  async analyzeDocument(id: string): Promise<any> {
    const response = await this.client.post(`/documents/${id}/analyze`)
    return response.data
  }

  async getDocumentStructure(id: string): Promise<any> {
    const response = await this.client.get(`/documents/${id}/structure`)
    return response.data
  }

  async applyDocumentStructure(id: string, analysis: any): Promise<any> {
    const response = await this.client.post(`/documents/${id}/structure/apply`, analysis)
    return response.data
  }

  // Chat
  async chat(data: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/chat/', data)
    return response.data
  }

  async listConversations(knowledgeBaseId: string): Promise<ConversationSummary[]> {
    const response = await this.client.get<ConversationSummary[]>('/chat/conversations', {
      params: { knowledge_base_id: knowledgeBaseId },
    })
    return response.data
  }

  async getConversationMessages(conversationId: string): Promise<ChatMessageResponse[]> {
    const response = await this.client.get<ChatMessageResponse[]>(
      `/chat/conversations/${conversationId}/messages`
    )
    return response.data
  }

  async getConversation(conversationId: string): Promise<ConversationDetail> {
    const response = await this.client.get<ConversationDetail>(
      `/chat/conversations/${conversationId}`
    )
    return response.data
  }

  async updateConversationSettings(
    conversationId: string,
    settings: ConversationSettings
  ): Promise<ConversationDetail> {
    const response = await this.client.patch<ConversationDetail>(
      `/chat/conversations/${conversationId}/settings`,
      settings
    )
    return response.data
  }

  async updateConversationTitle(
    conversationId: string,
    payload: ConversationTitleUpdate
  ): Promise<ConversationDetail> {
    const response = await this.client.patch<ConversationDetail>(
      `/chat/conversations/${conversationId}`,
      payload
    )
    return response.data
  }

  async deleteConversation(conversationId: string): Promise<{ status: string; id: string }> {
    const response = await this.client.delete(`/chat/conversations/${conversationId}`)
    return response.data
  }

  async deleteConversationMessage(
    conversationId: string,
    messageId: string,
    pair = true
  ): Promise<{ status: string; deleted_ids: string[] }> {
    const response = await this.client.delete(
      `/chat/conversations/${conversationId}/messages/${messageId}`,
      { params: { pair } }
    )
    return response.data
  }

  async regenerateChatTitles(
    knowledgeBaseId: string,
    includeExisting = false,
    limit?: number
  ): Promise<{ updated: number; skipped: number; total: number }> {
    const response = await this.client.post(
      `/knowledge_bases/${knowledgeBaseId}/regenerate_chat_titles`,
      { include_existing: includeExisting, limit }
    )
    return response.data
  }

  // Embedding Models
  async getEmbeddingModels(): Promise<EmbeddingModel[]> {
    const response = await this.client.get<EmbeddingModel[]>('/embeddings/models')
    return response.data
  }

  async getEmbeddingModel(modelName: string): Promise<EmbeddingModel> {
    const response = await this.client.get<EmbeddingModel>(`/embeddings/models/${modelName}`)
    return response.data
  }

  // LLM Models
  async getLLMModels(): Promise<{ models: any[]; providers: any; total: number }> {
    const response = await this.client.get('/llm/models')
    return response.data
  }

  // App Settings
  async getAppSettings(): Promise<AppSettings> {
    const response = await this.client.get<AppSettings>('/settings')
    return response.data
  }

  async updateAppSettings(payload: AppSettingsUpdate): Promise<AppSettings> {
    const response = await this.client.put<AppSettings>('/settings', payload)
    return response.data
  }

  async getSettingsMetadata(): Promise<SettingsMetadata> {
    const response = await this.client.get<SettingsMetadata>('/settings/metadata')
    return response.data
  }

  // System Settings (API keys, database URLs, etc.)
  async getSystemSettings(): Promise<any> {
    const response = await this.client.get('/system-settings')
    return response.data
  }

  async updateSystemSettings(payload: any): Promise<any> {
    const response = await this.client.put('/system-settings', payload)
    return response.data
  }

  async changePostgresPassword(username: string, newPassword: string): Promise<any> {
    const response = await this.client.post('/system-settings/postgres-password', {
      username,
      new_password: newPassword
    })
    return response.data
  }

  async resetAppSettings(): Promise<AppSettings> {
    const response = await this.client.post<AppSettings>('/settings/reset')
    return response.data
  }

  async getApiInfo(): Promise<ApiInfo> {
    const response = await this.client.get<ApiInfo>('/info')
    return response.data
  }
}

export const apiClient = new APIClient()
