import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiClient } from '../services/api'
import { Button } from '../components/common/Button'

type CheckState = 'checking' | 'valid' | 'invalid'

export function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()

  const [checkState, setCheckState] = useState<CheckState>('checking')
  const [invalidReason, setInvalidReason] = useState<string | null>(null)
  const [label, setLabel] = useState<string | null>(null)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!token) {
      setCheckState('invalid')
      setInvalidReason('No invite token in the URL.')
      return
    }
    apiClient
      .checkAdminInvite(token)
      .then((result) => {
        if (result.valid) {
          setLabel(result.label ?? null)
          setCheckState('valid')
        } else {
          setInvalidReason(result.detail || 'This invite is no longer valid.')
          setCheckState('invalid')
        }
      })
      .catch(() => {
        setInvalidReason('This invite is no longer valid.')
        setCheckState('invalid')
      })
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      await apiClient.acceptAdminInvite(token, { username, password })
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create account')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
      <div className="card w-full max-w-md">
        {checkState === 'checking' && (
          <p className="text-sm text-gray-400">Checking invite...</p>
        )}

        {checkState === 'invalid' && (
          <>
            <h1 className="text-2xl font-semibold text-white mb-2">Invite not valid</h1>
            <p className="text-sm text-gray-400">{invalidReason}</p>
            <p className="text-sm text-gray-400 mt-4">
              Ask whoever invited you to create a new invite link.
            </p>
          </>
        )}

        {checkState === 'valid' && !done && (
          <>
            <h1 className="text-2xl font-semibold text-white mb-2">
              {label ? `You're invited (${label})` : "You're invited"}
            </h1>
            <p className="text-sm text-gray-400 mb-6">Pick a username and password to continue.</p>

            {error && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500 rounded text-sm text-red-400">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-300 mb-1">Username</label>
                <input
                  type="text"
                  className="input w-full"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  minLength={3}
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Password</label>
                <input
                  type="password"
                  className="input w-full"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Confirm password</label>
                <input
                  type="password"
                  className="input w-full"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  minLength={8}
                  required
                />
              </div>
              <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
                {submitting ? 'Creating account...' : 'Create account'}
              </Button>
            </form>
          </>
        )}

        {done && (
          <>
            <h1 className="text-2xl font-semibold text-white mb-2">Account created</h1>
            <p className="text-sm text-gray-400 mb-6">
              Welcome, {username}. You can now sign in with your new credentials.
            </p>
            <Button variant="primary" className="w-full" onClick={() => navigate('/login')}>
              Go to sign in
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
