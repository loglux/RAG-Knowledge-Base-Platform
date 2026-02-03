// API Types
export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  chunk_size: number
  chunk_overlap: number
  upsert_batch_size: number
  chunking_strategy: 'simple' | 'smart' | 'semantic' | 'fixed_size' | 'FIXED_SIZE' | 'paragraph' | 'PARAGRAPH'
  bm25_match_mode?: string | null
  bm25_min_should_match?: number | null
  bm25_use_phrase?: boolean | null
  bm25_analyzer?: string | null
  structure_llm_model?: string | null
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
  upsert_batch_size?: number
  chunking_strategy?: 'simple' | 'smart' | 'semantic' | 'fixed_size' | 'FIXED_SIZE' | 'paragraph' | 'PARAGRAPH'
  bm25_match_mode?: string | null
  bm25_min_should_match?: number | null
  bm25_use_phrase?: boolean | null
  bm25_analyzer?: string | null
  structure_llm_model?: string | null
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
  embeddings_status?: DocumentStatus
  bm25_status?: DocumentStatus
  chunk_count: number
  knowledge_base_id: string
  user_id: string | null
  error_message: string | null
  processing_stage?: string | null
  progress_percentage?: number
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
  embeddings_status?: DocumentStatus
  bm25_status?: DocumentStatus
  chunk_count: number
  error_message: string | null
  processing_stage?: string | null
  progress_percentage?: number
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
  model?: string
  use_mmr?: boolean
  mmr_diversity?: number
  use_self_check?: boolean
}

export interface SourceChunk {
  text: string
  score: number
  document_id: string
  filename: string
  chunk_index: number
  metadata?: Record<string, unknown>
}

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  question: string
  knowledge_base_id: string
  conversation_id?: string
  conversation_history?: ConversationMessage[]
  top_k?: number
  temperature?: number
  retrieval_mode?: 'dense' | 'hybrid'
  lexical_top_k?: number
  hybrid_dense_weight?: number
  hybrid_lexical_weight?: number
  bm25_match_mode?: string | null
  bm25_min_should_match?: number | null
  bm25_use_phrase?: boolean | null
  bm25_analyzer?: string | null
  max_context_chars?: number
  score_threshold?: number
  llm_model?: string
  llm_provider?: string
  use_structure?: boolean
  use_mmr?: boolean
  mmr_diversity?: number
  use_self_check?: boolean
}

export interface ChatResponse {
  answer: string
  sources: SourceChunk[]
  query: string
  confidence_score: number
  model: string
  knowledge_base_id: string
  conversation_id?: string
  use_mmr?: boolean
  mmr_diversity?: number
  use_self_check?: boolean
}

export interface ConversationSummary {
  id: string
  knowledge_base_id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface ConversationSettings {
  top_k?: number
  temperature?: number
  max_context_chars?: number
  score_threshold?: number
  llm_model?: string
  llm_provider?: string
  use_structure?: boolean
  retrieval_mode?: 'dense' | 'hybrid'
  lexical_top_k?: number
  hybrid_dense_weight?: number
  hybrid_lexical_weight?: number
  bm25_match_mode?: string | null
  bm25_min_should_match?: number | null
  bm25_use_phrase?: boolean | null
  bm25_analyzer?: string | null
  use_mmr?: boolean
  mmr_diversity?: number
  use_self_check?: boolean
}

export interface ConversationDetail {
  id: string
  knowledge_base_id: string
  title: string | null
  settings?: ConversationSettings | null
  created_at: string
  updated_at: string
}

export interface ChatMessageResponse {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
  timestamp: string
  message_index: number
  use_self_check?: boolean
}

export interface AppSettings {
  id: number
  llm_model: string | null
  llm_provider: string | null
  temperature: number | null
  top_k: number | null
  max_context_chars: number | null
  score_threshold: number | null
  use_structure: boolean | null
  retrieval_mode: 'dense' | 'hybrid' | null
  lexical_top_k: number | null
  hybrid_dense_weight: number | null
  hybrid_lexical_weight: number | null
  bm25_match_mode: string | null
  bm25_min_should_match: number | null
  bm25_use_phrase: boolean | null
  bm25_analyzer: string | null
  structure_requests_per_minute: number | null
  kb_chunk_size: number | null
  kb_chunk_overlap: number | null
  kb_upsert_batch_size: number | null
  created_at: string
  updated_at: string
}

export interface AppSettingsUpdate {
  llm_model?: string | null
  llm_provider?: string | null
  temperature?: number | null
  top_k?: number | null
  max_context_chars?: number | null
  score_threshold?: number | null
  use_structure?: boolean | null
  retrieval_mode?: 'dense' | 'hybrid' | null
  lexical_top_k?: number | null
  hybrid_dense_weight?: number | null
  hybrid_lexical_weight?: number | null
  bm25_match_mode?: string | null
  bm25_min_should_match?: number | null
  bm25_use_phrase?: boolean | null
  bm25_analyzer?: string | null
  structure_requests_per_minute?: number | null
  kb_chunk_size?: number | null
  kb_chunk_overlap?: number | null
  kb_upsert_batch_size?: number | null
}

export interface ApiInfo {
  version: string
  environment: string
  features: {
    async_processing: boolean
    cache: boolean
    metrics: boolean
  }
  integrations?: {
    opensearch_available?: boolean
  }
  limits?: {
    max_file_size_mb?: number
    max_chunk_size?: number
    chunk_overlap?: number
  }
  supported_formats?: string[]
}

export interface SettingsMetadata {
  bm25_match_modes: string[]
  bm25_analyzers: string[]
}
