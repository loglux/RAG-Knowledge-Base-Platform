import React, { Suspense, lazy, useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Outlet, Navigate } from 'react-router-dom'
import { getSetupStatus } from './api/setup'
import { AuthProvider, useAuth } from './context/AuthContext'

const DashboardPage = lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })))
const KBDetailsPage = lazy(() => import('./pages/KBDetailsPage').then((module) => ({ default: module.KBDetailsPage })))
const ChatPage = lazy(() => import('./pages/ChatPage').then((module) => ({ default: module.ChatPage })))
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((module) => ({ default: module.SettingsPage })))
const Setup = lazy(() => import('./pages/Setup'))
const LoginPage = lazy(() => import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })))

function FullScreenLoading() {
  return (
    <div className="flex items-center justify-center h-screen text-lg text-gray-500">
      Loading...
    </div>
  )
}

function SetupRedirect({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    if (location.pathname === '/setup') {
      setChecking(false)
      return
    }

    const checkSetup = async () => {
      try {
        const status = await getSetupStatus()
        if (status.needs_setup) {
          navigate('/setup')
        }
      } catch (error) {
        console.error('Failed to check setup status:', error)
      } finally {
        setChecking(false)
      }
    }

    checkSetup()
  }, [navigate, location.pathname])

  if (checking) {
    return <FullScreenLoading />
  }

  return <>{children}</>
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <SetupRedirect>
          <Suspense fallback={<FullScreenLoading />}>
            <Routes>
              <Route path="/setup" element={<Setup />} />
              <Route path="/login" element={<LoginPage />} />
              <Route element={<ProtectedRoute />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/kb/:id" element={<KBDetailsPage />} />
                <Route path="/kb/:id/chat" element={<ChatPage />} />
              </Route>
            </Routes>
          </Suspense>
        </SetupRedirect>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App

function ProtectedRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <FullScreenLoading />
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
