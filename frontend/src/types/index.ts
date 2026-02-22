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
  use_llm_chat_titles?: boolean | null
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
  use_llm_chat_titles?: boolean | null
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
  duplicate_chunks?: {
    total_groups: number
    total_chunks: number
    groups: Array<{ hash: string; chunks: number[]; count: number }>
  } | null
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

export interface KBExportInclude {
  documents: boolean
  vectors: boolean
  bm25: boolean
  uploads: boolean
  chats: boolean
}

export interface KBExportRequest {
  kb_ids: string[]
  include?: KBExportInclude
}

export interface KBImportOptions {
  mode: 'create' | 'merge' | 'replace'
  remap_ids: boolean
  target_kb_id?: string | null
  include?: KBExportInclude
}

export interface KBImportResponse {
  status: string
  kb_imported: number
  kb_created: number
  kb_updated: number
  warnings: string[]
}

// Auth Types
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  admin_id: number
  username: string
  role: string
}

export interface OAuthTokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token?: string | null
}

export interface MeResponse {
  admin_id: number
  username: string
  role: string
}

// QA Auto-Tuning Types
export interface QASampleUploadResponse {
  knowledge_base_id: string
  added_count: number
  replaced: boolean
}

export interface QAGoldCountResponse {
  knowledge_base_id: string
  count: number
}

export interface QAEvalRunConfig {
  top_k?: number
  retrieval_mode?: 'dense' | 'hybrid'
  lexical_top_k?: number
  hybrid_dense_weight?: number
  hybrid_lexical_weight?: number
  bm25_match_mode?: string | null
  bm25_min_should_match?: number | null
  bm25_use_phrase?: boolean | null
  bm25_analyzer?: string | null
  max_context_chars?: number | null
  score_threshold?: number | null
  llm_model?: string | null
  llm_provider?: string | null
  use_mmr?: boolean
  mmr_diversity?: number
  sample_limit?: number | null
}

export interface QAEvalRun {
  id: string
  knowledge_base_id: string
  mode: string
  status: string
  config?: Record<string, unknown> | null
  metrics?: Record<string, unknown> | null
  sample_count: number
  processed_count?: number
  error_message?: string | null
  created_at: string
  started_at?: string | null
  completed_at?: string | null
}

export interface QAEvalResult {
  id: string
  sample_id?: string | null
  question: string
  expected_answer: string
  answer?: string | null
  document_id?: string | null
  chunk_index?: number | null
  source_span?: string | null
  metrics?: Record<string, unknown> | null
  created_at: string
}

export interface QAEvalRunDetail {
  run: QAEvalRun
  results: QAEvalResult[]
}

// Chat Types
export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
  timestamp: string
  message_index?: number
  model?: string
  use_mmr?: boolean
  mmr_diversity?: number
  use_self_check?: boolean
  use_conversation_history?: boolean
  conversation_history_limit?: number
  prompt_version_id?: string | null
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
  rerank_enabled?: boolean
  rerank_provider?: string | null
  rerank_model?: string | null
  rerank_candidate_pool?: number | null
  rerank_top_n?: number | null
  rerank_min_score?: number | null
  max_context_chars?: number
  score_threshold?: number
  llm_model?: string
  llm_provider?: string
  use_structure?: boolean
  use_mmr?: boolean
  mmr_diversity?: number
  use_self_check?: boolean
  use_document_filter?: boolean
  document_ids?: string[]
  context_expansion?: string[] | null
  context_window?: number | null
}

export interface ChatResponse {
  answer: string
  sources: SourceChunk[]
  query: string
  confidence_score: number
  model: string
  knowledge_base_id: string
  conversation_id?: string
  user_message_id?: string
  assistant_message_id?: string
  prompt_version_id?: string | null
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
  rerank_enabled?: boolean
  rerank_provider?: string | null
  rerank_model?: string | null
  rerank_candidate_pool?: number | null
  rerank_top_n?: number | null
  rerank_min_score?: number | null
  use_mmr?: boolean
  mmr_diversity?: number
  use_self_check?: boolean
  use_conversation_history?: boolean
  conversation_history_limit?: number
  use_document_filter?: boolean
  document_ids?: string[] | null
  context_expansion?: string[] | null
  context_window?: number | null
}

export interface ConversationDetail {
  id: string
  knowledge_base_id: string
  title: string | null
  settings?: ConversationSettings | null
  created_at: string
  updated_at: string
}

export interface ConversationTitleUpdate {
  title: string | null
}

export interface ChatMessageResponse {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
  timestamp: string
  message_index: number
  model?: string
  use_self_check?: boolean
  prompt_version_id?: string | null
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
  rerank_enabled: boolean | null
  rerank_provider: string | null
  rerank_model: string | null
  rerank_candidate_pool: number | null
  rerank_top_n: number | null
  rerank_min_score: number | null
  structure_requests_per_minute: number | null
  kb_chunk_size: number | null
  kb_chunk_overlap: number | null
  kb_upsert_batch_size: number | null
  use_llm_chat_titles: boolean | null
  active_prompt_version_id: string | null
  active_self_check_prompt_version_id: string | null
  show_prompt_versions: boolean | null
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
  rerank_enabled?: boolean | null
  rerank_provider?: string | null
  rerank_model?: string | null
  rerank_candidate_pool?: number | null
  rerank_top_n?: number | null
  rerank_min_score?: number | null
  structure_requests_per_minute?: number | null
  kb_chunk_size?: number | null
  kb_chunk_overlap?: number | null
  kb_upsert_batch_size?: number | null
  use_llm_chat_titles?: boolean | null
  active_prompt_version_id?: string | null
  active_self_check_prompt_version_id?: string | null
  show_prompt_versions?: boolean | null
}

export interface PromptVersionSummary {
  id: string
  name: string | null
  created_at: string
}

export interface PromptVersionDetail {
  id: string
  name: string | null
  system_content: string
  created_at: string
}

export interface PromptVersionCreate {
  name?: string | null
  system_content: string
  activate?: boolean
}

export interface SelfCheckPromptVersionSummary {
  id: string
  name: string | null
  created_at: string
}

export interface SelfCheckPromptVersionDetail {
  id: string
  name: string | null
  system_content: string
  created_at: string
}

export interface SelfCheckPromptVersionCreate {
  name?: string | null
  system_content: string
  activate?: boolean
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
  rerank_providers?: Array<{ id: string; label: string }>
  rerank_models_by_provider?: Record<
    string,
    Array<{
      id: string
      label: string
      pricing_unit?: string
      price_per_million_tokens_usd?: number
      notes?: string
    }>
  >
  rerank_pricing_formula?: string
}

export interface MCPToken {
  id: string
  name?: string | null
  token_prefix: string
  created_at: string
  expires_at?: string | null
  revoked_at?: string | null
  last_used_at?: string | null
}

export interface MCPTokenCreateResponse {
  token: string
  record: MCPToken
}

export interface MCPRefreshToken {
  jti: string
  admin_user_id: number
  admin_username: string
  created_at: string
  expires_at: string
  revoked_at?: string | null
}

export interface MCPOAuthEvent {
  id: string
  event_type: string
  client_id?: string | null
  admin_user_id?: number | null
  admin_username?: string | null
  ip_address?: string | null
  user_agent?: string | null
  created_at: string
}
