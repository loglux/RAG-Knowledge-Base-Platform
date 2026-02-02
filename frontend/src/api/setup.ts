/**
 * Setup API client
 */

import { API_BASE_URL } from './config';

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

/**
 * Get setup status
 */
export async function getSetupStatus(): Promise<SetupStatus> {
  const response = await fetch(`${API_BASE_URL}/setup/status`);

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
  const response = await fetch(`${API_BASE_URL}/setup/admin`, {
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
  const response = await fetch(`${API_BASE_URL}/setup/api-keys`, {
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
  const response = await fetch(`${API_BASE_URL}/setup/database`, {
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
  const response = await fetch(`${API_BASE_URL}/setup/system`, {
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
  const response = await fetch(`${API_BASE_URL}/setup/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to complete setup');
  }
}
