import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { KBDetailsPage } from './pages/KBDetailsPage'
import { ChatPage } from './pages/ChatPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/kb/:id" element={<KBDetailsPage />} />
        <Route path="/kb/:id/chat" element={<ChatPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
