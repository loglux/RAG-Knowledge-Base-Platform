import React, { createContext, useContext, useEffect, useState } from 'react'
import { apiClient } from '../services/api'
import type { MeResponse } from '../types/index'

interface AuthContextValue {
  user: MeResponse | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let isMounted = true
    const init = async () => {
      try {
        const refreshed = await apiClient.refreshToken()
        if (!refreshed) {
          if (isMounted) setUser(null)
          return
        }
        const me = await apiClient.me()
        if (isMounted) setUser(me)
      } catch {
        if (isMounted) setUser(null)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    init()
    return () => { isMounted = false }
  }, [])

  const login = async (username: string, password: string) => {
    await apiClient.login({ username, password })
    const me = await apiClient.me()
    setUser(me)
  }

  const logout = async () => {
    await apiClient.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
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
