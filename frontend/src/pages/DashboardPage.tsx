import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useKnowledgeBases } from '../hooks/useKnowledgeBases'
import { useAuth } from '../context/AuthContext'
import { CreateKBModal } from '../components/kb/CreateKBModal'
import { KBCard } from '../components/kb/KBCard'
import { apiClient } from '../services/api'
import { Button } from '../components/common/Button'

export function DashboardPage() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [activeTab, setActiveTab] = useState<'active' | 'trash'>('active')
  const {
    knowledgeBases,
    loading,
    error,
    page,
    totalPages,
    total,
    createKnowledgeBase,
    deleteKnowledgeBase,
    refresh,
    nextPage,
    prevPage,
    goToPage,
  } = useKnowledgeBases(12, { deleted: activeTab === 'trash' })

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  const handleCardClick = (id: string) => {
    navigate(`/kb/${id}`)
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const handleRestore = async (id: string) => {
    await apiClient.restoreKnowledgeBase(id)
    await refresh()
  }

  const handlePurge = async (id: string) => {
    if (!confirm('Permanently delete this knowledge base? This cannot be undone.')) return
    await apiClient.purgeKnowledgeBase(id)
    await refresh()
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
              <Button
                onClick={() => navigate('/settings')}
                size="sm"
                className="flex items-center gap-2"
              >
                <span aria-hidden="true">⚙️</span>
                <span>Settings</span>
              </Button>
              <Button
                onClick={handleLogout}
                size="sm"
                className="flex items-center gap-2"
              >
                <span aria-hidden="true">⎋</span>
                <span>Logout</span>
              </Button>
              <div className="text-sm text-gray-400">
                {loading ? 'Loading...' : `${total} knowledge base${total !== 1 ? 's' : ''}`}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center gap-2 border-b border-gray-700 mb-6 overflow-x-auto">
          <button
            onClick={() => setActiveTab('active')}
            className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === 'active'
                ? 'border-primary-500 text-primary-500'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Active
          </button>
          <button
            onClick={() => setActiveTab('trash')}
            className={`px-6 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === 'trash'
                ? 'border-primary-500 text-primary-500'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Trash
          </button>
        </div>

        {/* Title and Create Button */}
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-xl font-semibold text-white">
            {activeTab === 'trash' ? 'Deleted Knowledge Bases' : 'Your Knowledge Bases'}
          </h2>
          {activeTab === 'active' && (
            <Button
              onClick={() => setIsCreateModalOpen(true)}
              variant="primary"
              className="flex items-center space-x-2"
            >
              <span>+</span>
              <span>New KB</span>
            </Button>
          )}
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
            <h3 className="text-xl font-semibold text-white mb-2">
              {activeTab === 'trash' ? 'Trash is empty' : 'No knowledge bases yet'}
            </h3>
            <p className="text-gray-400 mb-6">
              {activeTab === 'trash'
                ? 'Deleted knowledge bases will appear here'
                : 'Create your first knowledge base to get started'}
            </p>
            {activeTab === 'active' && (
              <Button
                onClick={() => setIsCreateModalOpen(true)}
                variant="primary"
              >
                + Create Knowledge Base
              </Button>
            )}
          </div>
        )}

        {/* Knowledge Bases Grid */}
        {!loading && knowledgeBases.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {knowledgeBases.map((kb) => (
                <div
                  key={kb.id}
                  onClick={activeTab === 'active' ? () => handleCardClick(kb.id) : undefined}
                >
                  {activeTab === 'trash' ? (
                    <div className="card cursor-default">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="text-lg font-semibold text-white">📖 {kb.name}</h3>
                          {kb.description && (
                            <p className="text-gray-400 text-sm mt-1 line-clamp-2">{kb.description}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-sm text-gray-400 mb-4">
                        <span>{kb.document_count} docs</span>
                        <span>{kb.total_chunks} chunks</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleRestore(kb.id)
                          }}
                          variant="primary"
                          size="sm"
                        >
                          Restore
                        </Button>
                        <Button
                          onClick={(e) => {
                            e.stopPropagation()
                            handlePurge(kb.id)
                          }}
                          size="sm"
                        >
                          Purge
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <KBCard
                      kb={kb}
                      onDelete={deleteKnowledgeBase}
                    />
                  )}
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex items-center justify-between border-t border-gray-700 pt-6">
                <div className="text-sm text-gray-400">
                  Page {page} of {totalPages} · {total} total
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    onClick={prevPage}
                    disabled={page === 1}
                    className="disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    ← Previous
                  </Button>
                  <div className="flex items-center space-x-1">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => {
                      // Show first page, last page, current page, and pages around current
                      const showPage =
                        pageNum === 1 ||
                        pageNum === totalPages ||
                        Math.abs(pageNum - page) <= 1

                      // Show ellipsis
                      const showEllipsisBefore = pageNum === page - 2 && page > 3
                      const showEllipsisAfter = pageNum === page + 2 && page < totalPages - 2

                      if (showEllipsisBefore || showEllipsisAfter) {
                        return (
                          <span key={pageNum} className="px-2 text-gray-500">
                            ...
                          </span>
                        )
                      }

                      if (!showPage) return null

                      return (
                        <button
                          key={pageNum}
                          onClick={() => goToPage(pageNum)}
                          className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                            pageNum === page
                              ? 'bg-primary-500 text-white'
                              : 'text-gray-400 hover:text-white hover:bg-gray-700'
                          }`}
                        >
                          {pageNum}
                        </button>
                      )
                    })}
                  </div>
                  <Button
                    onClick={nextPage}
                    disabled={page === totalPages}
                    className="disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next →
                  </Button>
                </div>
              </div>
            )}
          </>
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
