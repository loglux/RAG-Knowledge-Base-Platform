import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useKnowledgeBases } from '../hooks/useKnowledgeBases'
import { CreateKBModal } from '../components/kb/CreateKBModal'
import { KBCard } from '../components/kb/KBCard'

export function DashboardPage() {
  const navigate = useNavigate()
  const {
    knowledgeBases,
    loading,
    error,
    createKnowledgeBase,
    deleteKnowledgeBase,
  } = useKnowledgeBases()

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  const handleCardClick = (id: string) => {
    navigate(`/kb/${id}`)
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">🧠</div>
              <h1 className="text-2xl font-bold text-white">Knowledge Base Platform</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/settings')}
                className="btn-secondary text-sm px-3 py-1.5 flex items-center gap-2"
              >
                <span aria-hidden="true">⚙️</span>
                <span>Settings</span>
              </button>
              <div className="text-sm text-gray-400">
                {loading ? 'Loading...' : `${knowledgeBases.length} knowledge bases`}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Title and Create Button */}
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-xl font-semibold text-white">Your Knowledge Bases</h2>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="btn-primary flex items-center space-x-2"
          >
            <span>+</span>
            <span>New KB</span>
          </button>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 bg-red-500 bg-opacity-10 border border-red-500 rounded-lg text-red-500">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
            <p className="mt-4 text-gray-400">Loading knowledge bases...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && knowledgeBases.length === 0 && (
          <div className="card text-center py-12">
            <div className="text-6xl mb-4">📚</div>
            <h3 className="text-xl font-semibold text-white mb-2">No knowledge bases yet</h3>
            <p className="text-gray-400 mb-6">
              Create your first knowledge base to get started
            </p>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="btn-primary"
            >
              + Create Knowledge Base
            </button>
          </div>
        )}

        {/* Knowledge Bases Grid */}
        {!loading && knowledgeBases.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {knowledgeBases.map((kb) => (
              <div key={kb.id} onClick={() => handleCardClick(kb.id)}>
                <KBCard
                  kb={kb}
                  onDelete={deleteKnowledgeBase}
                />
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create KB Modal */}
      <CreateKBModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={createKnowledgeBase}
      />
    </div>
  )
}
