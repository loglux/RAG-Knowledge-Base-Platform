/**
 * Setup API client
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const API_PREFIX = import.meta.env.VITE_API_PREFIX || '/api/v1';
const BASE_URL = API_BASE_URL + API_PREFIX;

export interface SetupStatus {
  is_complete: boolean;
  admin_users_count: number;
  settings_count: number;
  needs_setup: boolean;
}

export interface AdminCreateRequest {
  username: string;
  password: string;
  email?: string;
}

export interface APIKeysRequest {
  openai_api_key?: string;
  voyage_api_key?: string;
  anthropic_api_key?: string;
  deepseek_api_key?: string;
  ollama_base_url?: string;
}

export interface DatabaseSettingsRequest {
  qdrant_url?: string;
  qdrant_api_key?: string;
  opensearch_url?: string;
  opensearch_username?: string;
  opensearch_password?: string;
}

export interface SystemSettingsRequest {
  system_name?: string;
  max_file_size_mb?: number;
  max_chunk_size?: number;
  chunk_overlap?: number;
}

export interface SetupCompleteRequest {
  admin_id?: number;
}

export interface PostgresPasswordRequest {
  username: string;
  new_password?: string;
  generate_password?: boolean;
}

export interface PostgresPasswordResponse {
  username: string;
  password: string;
  message: string;
}

/**
 * Get setup status
 */
export async function getSetupStatus(): Promise<SetupStatus> {
  const response = await fetch(`${BASE_URL}/setup/status`);

  if (!response.ok) {
    throw new Error('Failed to get setup status');
  }

  const result = await response.json();
  return result.data;
}

/**
 * Create admin user
 */
export async function createAdminUser(data: AdminCreateRequest): Promise<any> {
  const response = await fetch(`${BASE_URL}/setup/admin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create admin user');
  }

  return response.json();
}

/**
 * Save API keys
 */
export async function saveAPIKeys(data: APIKeysRequest): Promise<void> {
  const response = await fetch(`${BASE_URL}/setup/api-keys`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to save API keys');
  }
}

/**
 * Save database settings
 */
export async function saveDatabaseSettings(data: DatabaseSettingsRequest): Promise<void> {
  const response = await fetch(`${BASE_URL}/setup/database`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to save database settings');
  }
}

/**
 * Save system settings
 */
export async function saveSystemSettings(data: SystemSettingsRequest): Promise<void> {
  const response = await fetch(`${BASE_URL}/setup/system`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to save system settings');
  }
}

/**
 * Complete setup
 */
export async function completeSetup(data: SetupCompleteRequest = {}): Promise<void> {
  const response = await fetch(`${BASE_URL}/setup/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to complete setup');
  }
}

/**
 * Generate secure password (preview only)
 */
export async function generatePasswordPreview(): Promise<string> {
  const response = await fetch(`${BASE_URL}/setup/generate-password`);

  if (!response.ok) {
    throw new Error('Failed to generate password');
  }

  const result = await response.json();
  return result.data.password;
}

/**
 * Change PostgreSQL password
 */
export async function changePostgresPassword(data: PostgresPasswordRequest): Promise<PostgresPasswordResponse> {
  const response = await fetch(`${BASE_URL}/setup/postgres-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to change PostgreSQL password');
  }

  return response.json();
}
