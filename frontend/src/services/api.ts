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
  EmbeddingModel,
} from '../types/index'

class APIClient {
  private client: AxiosInstance

  constructor() {
    const baseURL = import.meta.env.VITE_API_BASE_URL || ''
    const prefix = import.meta.env.VITE_API_PREFIX || '/api/v1'

    this.client = axios.create({
      baseURL: baseURL + prefix,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<APIError>) => {
        if (error.response?.data) {
          throw new Error(error.response.data.detail || 'An error occurred')
        }
        throw error
      }
    )
  }

  // Knowledge Bases
  async getKnowledgeBases(page = 1, pageSize = 10): Promise<PaginatedResponse<KnowledgeBase>> {
    const response = await this.client.get<PaginatedResponse<KnowledgeBase>>('/knowledge-bases/', {
      params: { page, page_size: pageSize },
    })
    return response.data
  }

  async getKnowledgeBase(id: string): Promise<KnowledgeBase> {
    const response = await this.client.get<KnowledgeBase>(`/knowledge-bases/${id}`)
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
}

export const apiClient = new APIClient()
