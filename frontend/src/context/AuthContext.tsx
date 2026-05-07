import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { apiClient, AUTH_FAILURE_EVENT } from '../services/api'
import type { MeResponse } from '../types/index'

interface AuthContextValue {
  user: MeResponse | null
  loading: boolean
  authStatus: 'loading' | 'authenticated' | 'anonymous'
  refreshSession: () => Promise<boolean>
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const authStatus: AuthContextValue['authStatus'] =
    loading ? 'loading' : user ? 'authenticated' : 'anonymous'

  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      const refreshed = await apiClient.refreshToken()
      if (!refreshed) {
        setUser(null)
        return false
      }

      const me = await apiClient.me()
      setUser(me)
      return true
    } catch {
      setUser(null)
      return false
    }
  }, [])

  useEffect(() => {
    let isMounted = true

    const init = async () => {
      try {
        const refreshed = await refreshSession()
        if (!refreshed && isMounted) {
          setUser(null)
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    init()
    return () => {
      isMounted = false
    }
  }, [refreshSession])

  useEffect(() => {
    const onAuthFailure = () => {
      setUser(null)
      setLoading(false)
    }

    window.addEventListener(AUTH_FAILURE_EVENT, onAuthFailure)
    return () => {
      window.removeEventListener(AUTH_FAILURE_EVENT, onAuthFailure)
    }
  }, [])

  const login = async (username: string, password: string) => {
    await apiClient.login({ username, password })
    const me = await apiClient.me()
    setUser(me)
    setLoading(false)
  }

  const logout = async () => {
    await apiClient.logout()
    setUser(null)
    setLoading(false)
  }

  return (
    <AuthContext.Provider value={{ user, loading, authStatus, refreshSession, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
