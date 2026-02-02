/**
 * Setup Wizard Page
 *
 * First-run configuration wizard for the Knowledge Base Platform.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Setup.css';
import {
  getSetupStatus,
  createAdminUser,
  saveAPIKeys,
  saveDatabaseSettings,
  saveSystemSettings,
  completeSetup,
  type AdminCreateRequest,
  type APIKeysRequest,
  type DatabaseSettingsRequest,
  type SystemSettingsRequest,
} from '../api/setup';

type Step = 'welcome' | 'admin' | 'api-keys' | 'database' | 'system' | 'complete';

const Setup: React.FC = () => {
  const navigate = useNavigate();

  // Current step
  const [currentStep, setCurrentStep] = useState<Step>('welcome');

  // Loading and error states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form data for each step
  const [adminData, setAdminData] = useState<AdminCreateRequest>({
    username: '',
    password: '',
    email: '',
  });

  const [apiKeysData, setAPIKeysData] = useState<APIKeysRequest>({
    openai_api_key: '',
    voyage_api_key: '',
    anthropic_api_key: '',
  });

  const [databaseData, setDatabaseData] = useState<DatabaseSettingsRequest>({
    qdrant_url: 'http://qdrant:6333',
    qdrant_api_key: '',
    opensearch_url: 'http://opensearch:9200',
    opensearch_username: '',
    opensearch_password: '',
  });

  const [systemData, setSystemData] = useState<SystemSettingsRequest>({
    system_name: 'Knowledge Base Platform',
    max_file_size_mb: 50,
    max_chunk_size: 1500,
    chunk_overlap: 200,
  });

  // Check if setup is already complete on mount
  useEffect(() => {
    checkSetupStatus();
  }, []);

  const checkSetupStatus = async () => {
    try {
      const status = await getSetupStatus();
      if (status.is_complete) {
        // Setup already complete, redirect to main app
        navigate('/');
      }
    } catch (err) {
      console.error('Failed to check setup status:', err);
    }
  };

  // Step 1: Create Admin User
  const handleCreateAdmin = async () => {
    setLoading(true);
    setError(null);

    try {
      // Validate
      if (!adminData.username || adminData.username.length < 3) {
        throw new Error('Username must be at least 3 characters');
      }
      if (!adminData.password || adminData.password.length < 8) {
        throw new Error('Password must be at least 8 characters');
      }

      await createAdminUser(adminData);
      setCurrentStep('api-keys');
    } catch (err: any) {
      setError(err.message || 'Failed to create admin user');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Save API Keys
  const handleSaveAPIKeys = async () => {
    setLoading(true);
    setError(null);

    try {
      // Validate at least one key
      const hasKey = apiKeysData.openai_api_key ||
                     apiKeysData.voyage_api_key ||
                     apiKeysData.anthropic_api_key;

      if (!hasKey) {
        throw new Error('At least one API key is required');
      }

      await saveAPIKeys(apiKeysData);
      setCurrentStep('database');
    } catch (err: any) {
      setError(err.message || 'Failed to save API keys');
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Save Database Settings (optional)
  const handleSaveDatabaseSettings = async () => {
    setLoading(true);
    setError(null);

    try {
      // Only save if user changed defaults
      const hasChanges =
        databaseData.qdrant_url !== 'http://qdrant:6333' ||
        databaseData.qdrant_api_key ||
        databaseData.opensearch_url !== 'http://opensearch:9200' ||
        databaseData.opensearch_username ||
        databaseData.opensearch_password;

      if (hasChanges) {
        await saveDatabaseSettings(databaseData);
      }

      setCurrentStep('system');
    } catch (err: any) {
      setError(err.message || 'Failed to save database settings');
    } finally {
      setLoading(false);
    }
  };

  // Step 4: Save System Settings (optional)
  const handleSaveSystemSettings = async () => {
    setLoading(true);
    setError(null);

    try {
      await saveSystemSettings(systemData);
      setCurrentStep('complete');
    } catch (err: any) {
      setError(err.message || 'Failed to save system settings');
    } finally {
      setLoading(false);
    }
  };

  // Step 5: Complete Setup
  const handleCompleteSetup = async () => {
    setLoading(true);
    setError(null);

    try {
      await completeSetup();

      // Redirect to main app
      setTimeout(() => {
        window.location.href = '/';
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to complete setup');
      setLoading(false);
    }
  };

  // Render current step
  const renderStep = () => {
    switch (currentStep) {
      case 'welcome':
        return (
          <div className="setup-step">
            <h2>Welcome to Knowledge Base Platform</h2>
            <p className="setup-description">
              This wizard will help you configure your knowledge base platform in a few simple steps.
            </p>

            <div className="setup-info">
              <h3>What we'll configure:</h3>
              <ul>
                <li>✓ Admin account for system management</li>
                <li>✓ API keys for AI services (OpenAI, Voyage, Anthropic)</li>
                <li>✓ Database connections (optional)</li>
                <li>✓ System settings (optional)</li>
              </ul>
            </div>

            <div className="setup-actions">
              <button
                className="btn btn-primary"
                onClick={() => setCurrentStep('admin')}
              >
                Get Started →
              </button>
            </div>
          </div>
        );

      case 'admin':
        return (
          <div className="setup-step">
            <h2>Step 1: Create Admin Account</h2>
            <p className="setup-description">
              Create an administrator account to manage the system.
            </p>

            <div className="form-group">
              <label>Username *</label>
              <input
                type="text"
                className="form-control"
                placeholder="admin"
                value={adminData.username}
                onChange={(e) => setAdminData({ ...adminData, username: e.target.value })}
                minLength={3}
                required
              />
              <small className="form-text">Minimum 3 characters</small>
            </div>

            <div className="form-group">
              <label>Password *</label>
              <input
                type="password"
                className="form-control"
                placeholder="••••••••"
                value={adminData.password}
                onChange={(e) => setAdminData({ ...adminData, password: e.target.value })}
                minLength={8}
                required
              />
              <small className="form-text">Minimum 8 characters</small>
            </div>

            <div className="form-group">
              <label>Email (optional)</label>
              <input
                type="email"
                className="form-control"
                placeholder="admin@example.com"
                value={adminData.email}
                onChange={(e) => setAdminData({ ...adminData, email: e.target.value })}
              />
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="setup-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setCurrentStep('welcome')}
                disabled={loading}
              >
                ← Back
              </button>
              <button
                className="btn btn-primary"
                onClick={handleCreateAdmin}
                disabled={loading || !adminData.username || !adminData.password}
              >
                {loading ? 'Creating...' : 'Create Admin →'}
              </button>
            </div>
          </div>
        );

      case 'api-keys':
        return (
          <div className="setup-step">
            <h2>Step 2: API Keys</h2>
            <p className="setup-description">
              Configure API keys for AI services. At least one key is required.
            </p>

            <div className="form-group">
              <label>OpenAI API Key (Recommended)</label>
              <input
                type="password"
                className="form-control"
                placeholder="sk-proj-..."
                value={apiKeysData.openai_api_key}
                onChange={(e) => setAPIKeysData({ ...apiKeysData, openai_api_key: e.target.value })}
              />
              <small className="form-text">Used for embeddings and chat (GPT-4)</small>
            </div>

            <div className="form-group">
              <label>VoyageAI API Key (Optional)</label>
              <input
                type="password"
                className="form-control"
                placeholder="pa-..."
                value={apiKeysData.voyage_api_key}
                onChange={(e) => setAPIKeysData({ ...apiKeysData, voyage_api_key: e.target.value })}
              />
              <small className="form-text">Alternative embedding provider</small>
            </div>

            <div className="form-group">
              <label>Anthropic API Key (Optional)</label>
              <input
                type="password"
                className="form-control"
                placeholder="sk-ant-..."
                value={apiKeysData.anthropic_api_key}
                onChange={(e) => setAPIKeysData({ ...apiKeysData, anthropic_api_key: e.target.value })}
              />
              <small className="form-text">Used for Claude models</small>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="setup-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setCurrentStep('admin')}
                disabled={loading}
              >
                ← Back
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSaveAPIKeys}
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Save & Continue →'}
              </button>
            </div>
          </div>
        );

      case 'database':
        return (
          <div className="setup-step">
            <h2>Step 3: Database Settings (Optional)</h2>
            <p className="setup-description">
              Configure database connections. Default values work for Docker deployments.
            </p>

            <div className="form-section">
              <h3>Qdrant (Vector Database)</h3>
              <div className="form-group">
                <label>Qdrant URL</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="http://qdrant:6333"
                  value={databaseData.qdrant_url}
                  onChange={(e) => setDatabaseData({ ...databaseData, qdrant_url: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Qdrant API Key (if required)</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="Optional"
                  value={databaseData.qdrant_api_key}
                  onChange={(e) => setDatabaseData({ ...databaseData, qdrant_api_key: e.target.value })}
                />
              </div>
            </div>

            <div className="form-section">
              <h3>OpenSearch (Lexical Search)</h3>
              <div className="form-group">
                <label>OpenSearch URL</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="http://opensearch:9200"
                  value={databaseData.opensearch_url}
                  onChange={(e) => setDatabaseData({ ...databaseData, opensearch_url: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>OpenSearch Username (if required)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Optional"
                  value={databaseData.opensearch_username}
                  onChange={(e) => setDatabaseData({ ...databaseData, opensearch_username: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>OpenSearch Password (if required)</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="Optional"
                  value={databaseData.opensearch_password}
                  onChange={(e) => setDatabaseData({ ...databaseData, opensearch_password: e.target.value })}
                />
              </div>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="setup-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setCurrentStep('api-keys')}
                disabled={loading}
              >
                ← Back
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setCurrentStep('system')}
                disabled={loading}
              >
                Skip
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSaveDatabaseSettings}
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Save & Continue →'}
              </button>
            </div>
          </div>
        );

      case 'system':
        return (
          <div className="setup-step">
            <h2>Step 4: System Settings (Optional)</h2>
            <p className="setup-description">
              Configure general system settings. Defaults are recommended for most users.
            </p>

            <div className="form-group">
              <label>System Name</label>
              <input
                type="text"
                className="form-control"
                placeholder="Knowledge Base Platform"
                value={systemData.system_name}
                onChange={(e) => setSystemData({ ...systemData, system_name: e.target.value })}
              />
              <small className="form-text">Displayed in the UI</small>
            </div>

            <div className="form-group">
              <label>Max File Size (MB)</label>
              <input
                type="number"
                className="form-control"
                placeholder="50"
                value={systemData.max_file_size_mb}
                onChange={(e) => setSystemData({ ...systemData, max_file_size_mb: parseInt(e.target.value) })}
                min={1}
                max={1000}
              />
            </div>

            <div className="form-group">
              <label>Max Chunk Size (characters)</label>
              <input
                type="number"
                className="form-control"
                placeholder="1500"
                value={systemData.max_chunk_size}
                onChange={(e) => setSystemData({ ...systemData, max_chunk_size: parseInt(e.target.value) })}
                min={100}
                max={10000}
              />
              <small className="form-text">Recommended: 1500-2000</small>
            </div>

            <div className="form-group">
              <label>Chunk Overlap (characters)</label>
              <input
                type="number"
                className="form-control"
                placeholder="200"
                value={systemData.chunk_overlap}
                onChange={(e) => setSystemData({ ...systemData, chunk_overlap: parseInt(e.target.value) })}
                min={0}
                max={2000}
              />
              <small className="form-text">Recommended: 15-20% of chunk size</small>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="setup-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setCurrentStep('database')}
                disabled={loading}
              >
                ← Back
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setCurrentStep('complete')}
                disabled={loading}
              >
                Skip
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSaveSystemSettings}
                disabled={loading}
              >
                {loading ? 'Saving...' : 'Save & Continue →'}
              </button>
            </div>
          </div>
        );

      case 'complete':
        return (
          <div className="setup-step">
            <h2>🎉 Setup Complete!</h2>
            <p className="setup-description">
              Your Knowledge Base Platform is now configured and ready to use.
            </p>

            <div className="setup-summary">
              <h3>What's next?</h3>
              <ul>
                <li>✓ Create your first knowledge base</li>
                <li>✓ Upload documents</li>
                <li>✓ Start chatting with your knowledge</li>
              </ul>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="setup-actions">
              <button
                className="btn btn-primary btn-large"
                onClick={handleCompleteSetup}
                disabled={loading}
              >
                {loading ? 'Finalizing...' : 'Launch Platform →'}
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // Progress indicator
  const steps = ['welcome', 'admin', 'api-keys', 'database', 'system', 'complete'];
  const currentStepIndex = steps.indexOf(currentStep);
  const progress = ((currentStepIndex + 1) / steps.length) * 100;

  return (
    <div className="setup-container">
      <div className="setup-progress">
        <div className="setup-progress-bar" style={{ width: `${progress}%` }} />
      </div>

      <div className="setup-content">
        <div className="setup-header">
          <h1>Knowledge Base Platform</h1>
          <p className="setup-subtitle">Initial Setup Wizard</p>
        </div>

        {renderStep()}
      </div>
    </div>
  );
};

export default Setup;
