import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { KBDetailsPage } from './pages/KBDetailsPage'
import { ChatPage } from './pages/ChatPage'
import { SettingsPage } from './pages/SettingsPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/kb/:id" element={<KBDetailsPage />} />
        <Route path="/kb/:id/chat" element={<ChatPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
