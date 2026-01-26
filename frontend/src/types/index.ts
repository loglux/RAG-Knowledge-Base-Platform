// API Types
export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  chunk_size: number
  chunk_overlap: number
  chunking_strategy: 'fixed_size' | 'semantic'
  collection_name: string
  document_count: number
  total_chunks: number
  embedding_model: string
  embedding_provider: string
  embedding_dimension: number
  user_id: string | null
  created_at: string
  updated_at: string
  is_deleted: boolean
}

export interface CreateKBRequest {
  name: string
  description?: string
  embedding_model?: string
  chunk_size?: number
  chunk_overlap?: number
  chunking_strategy?: 'fixed_size' | 'semantic'
}

export interface EmbeddingModel {
  model: string
  provider: string
  dimension: number
  description: string
  cost_per_million_tokens: number
}

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Document {
  id: string
  filename: string
  file_size: number
  file_type: string
  status: DocumentStatus
  chunk_count: number
  knowledge_base_id: string
  user_id: string | null
  error_message: string | null
  created_at: string
  updated_at: string
  processed_at: string | null
  is_deleted: boolean
  content_hash: string
}

export interface DocumentStatusResponse {
  id: string
  filename: string
  status: DocumentStatus
  chunk_count: number
  error_message: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface APIError {
  detail: string
  path?: string
  suggestion?: string
}

// Chat Types
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
  timestamp: string
}

export interface SourceChunk {
  text: string
  score: number
  document_id: string
  filename: string
  chunk_index: number
}

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  question: string
  knowledge_base_id: string
  conversation_history?: ConversationMessage[]
  top_k?: number
  temperature?: number
  llm_model?: string
  llm_provider?: string
  use_structure?: boolean
}

export interface ChatResponse {
  answer: string
  sources: SourceChunk[]
  query: string
  confidence_score: number
  model: string
  knowledge_base_id: string
}
