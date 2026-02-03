import React, { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Outlet, Navigate } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { KBDetailsPage } from './pages/KBDetailsPage'
import { ChatPage } from './pages/ChatPage'
import { SettingsPage } from './pages/SettingsPage'
import Setup from './pages/Setup'
import { getSetupStatus } from './api/setup'
import { AuthProvider, useAuth } from './context/AuthContext'
import { LoginPage } from './pages/LoginPage'

function SetupRedirect({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // Don't check if already on setup page
    if (location.pathname === '/setup') {
      setChecking(false)
      return
    }

    // Check setup status
    const checkSetup = async () => {
      try {
        const status = await getSetupStatus()
        if (status.needs_setup) {
          // Redirect to setup if not complete
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

  // Show loading while checking
  if (checking) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '18px',
        color: '#666'
      }}>
        Loading...
      </div>
    )
  }

  return <>{children}</>
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <SetupRedirect>
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
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '18px',
        color: '#666'
      }}>
        Loading...
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
