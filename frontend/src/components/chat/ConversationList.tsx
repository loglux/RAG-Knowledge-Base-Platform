import React, { useMemo, useState, useEffect } from 'react'
import { Panel } from '../common/Panel'
import { PanelHeader } from '../common/PanelHeader'
import { Button } from '../common/Button'
import type { ConversationSummary } from '../../types/index'

interface ConversationListProps {
  conversations: ConversationSummary[]
  conversationsLoading: boolean
  activeConversationId: string | null
  onStartNewChat: () => void
  onSelectConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => Promise<void> | void
  onRenameConversation: (conversationId: string, title: string | null) => Promise<void> | void
  collapsed: boolean
  onToggleCollapsed: () => void
}

export function ConversationList({
  conversations,
  conversationsLoading,
  activeConversationId,
  onStartNewChat,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  collapsed,
  onToggleCollapsed,
}: ConversationListProps) {
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const [conversationSearch, setConversationSearch] = useState('')
  const [conversationPage, setConversationPage] = useState(1)
  const [conversationPageSize, setConversationPageSize] = useState(10)

  const normalizedSearch = conversationSearch.trim().toLowerCase()
  const filteredConversations = useMemo(() => {
    if (!normalizedSearch) return conversations
    return conversations.filter((conversation) => {
      const titleLabel = (conversation.title ?? '').trim() || 'untitled chat'
      return (
        titleLabel.toLowerCase().includes(normalizedSearch) ||
        conversation.id.toLowerCase().includes(normalizedSearch)
      )
    })
  }, [conversations, normalizedSearch])

  const totalConversationPages = Math.max(
    1,
    Math.ceil(filteredConversations.length / conversationPageSize)
  )

  useEffect(() => {
    setConversationPage(1)
  }, [conversationSearch, conversationPageSize])

  useEffect(() => {
    if (conversationPage > totalConversationPages) {
      setConversationPage(totalConversationPages)
    }
  }, [conversationPage, totalConversationPages])

  const pagedConversations = filteredConversations.slice(
    (conversationPage - 1) * conversationPageSize,
    conversationPage * conversationPageSize
  )

  const handleSelectConversation = (conversationId: string) => {
    if (conversationId === activeConversationId) return
    setEditingConversationId(null)
    setEditingTitle('')
    onSelectConversation(conversationId)
  }

  const handleStartNewChat = () => {
    setEditingConversationId(null)
    setEditingTitle('')
    onStartNewChat()
  }

  const handleDeleteConversation = async (conversationId: string) => {
    const ok = window.confirm('Delete this conversation? This cannot be undone.')
    if (!ok) return
    if (editingConversationId === conversationId) {
      setEditingConversationId(null)
      setEditingTitle('')
    }
    await onDeleteConversation(conversationId)
  }

  const handleEditConversation = (conversationId: string, title: string | null) => {
    setEditingConversationId(conversationId)
    setEditingTitle(title ?? '')
  }

  const handleCancelEdit = () => {
    setEditingConversationId(null)
    setEditingTitle('')
  }

  const handleSaveEdit = async () => {
    if (!editingConversationId) return
    const trimmed = editingTitle.trim()
    await onRenameConversation(editingConversationId, trimmed.length > 0 ? trimmed : null)
    setEditingConversationId(null)
    setEditingTitle('')
  }

  if (collapsed) {
    return (
      <Panel as="aside" className="h-full flex flex-col items-center py-3">
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="text-gray-300 hover:text-white transition-colors mb-4"
          aria-label="Expand chat list"
        >
          ▸
        </button>
        <button
          type="button"
          onClick={handleStartNewChat}
          className="text-gray-300 hover:text-white transition-colors text-lg"
          aria-label="New chat"
        >
          ＋
        </button>
      </Panel>
    )
  }

  return (
    <Panel as="aside" className="p-4 h-full flex flex-col overflow-hidden">
      <PanelHeader
        className="mb-3"
        title={<h2 className="text-sm font-semibold text-gray-200">Chats</h2>}
        actions={(
          <Button onClick={handleStartNewChat} size="xs">
            New chat
          </Button>
        )}
      />

      <div className="mb-3 space-y-2">
        <input
          value={conversationSearch}
          onChange={(e) => setConversationSearch(e.target.value)}
          className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="Search chats"
        />
        <div className="flex items-center justify-between text-[11px] text-gray-400">
          <span>{filteredConversations.length} chats</span>
          <select
            value={conversationPageSize}
            onChange={(e) => setConversationPageSize(Number(e.target.value))}
            className="bg-gray-900 border border-gray-700 rounded px-1 py-0.5 text-xs text-gray-200"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto pr-1">
        {conversationsLoading ? (
          <div className="text-xs text-gray-400">Loading chats...</div>
        ) : filteredConversations.length === 0 ? (
          <div className="text-xs text-gray-400">
            {conversations.length === 0 ? 'No chats yet.' : 'No chats match your search.'}
          </div>
        ) : (
          <ul className="space-y-2">
            {pagedConversations.map((conversation) => {
              const isActive = conversation.id === activeConversationId
              const isEditing = editingConversationId === conversation.id
              const titleLabel = (conversation.title ?? '').trim() || 'Untitled chat'
              const updatedLabel = new Date(conversation.updated_at).toLocaleString()

              return (
                <li key={conversation.id}>
                  <div
                    className={`border rounded-lg transition-colors ${
                      isActive
                        ? 'border-primary-500 bg-primary-500/10'
                        : 'border-gray-700 bg-gray-900/40 hover:bg-gray-900'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => handleSelectConversation(conversation.id)}
                      className="w-full text-left p-3"
                      disabled={isEditing}
                    >
                      <div className="flex flex-col gap-2">
                        {isEditing ? (
                          <div className="flex-1 min-w-0">
                            <input
                              value={editingTitle}
                              onChange={(e) => setEditingTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveEdit()
                                if (e.key === 'Escape') handleCancelEdit()
                              }}
                              className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                              placeholder="Conversation title"
                              autoFocus
                            />
                            <p className="text-[11px] text-gray-500 mt-1">{updatedLabel}</p>
                          </div>
                        ) : (
                          <>
                            <p className="text-sm font-medium text-white truncate">{titleLabel}</p>
                            <div className="flex items-center justify-between text-[11px] text-gray-500">
                              <span>{updatedLabel}</span>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleEditConversation(conversation.id, conversation.title)
                                  }}
                                  className="text-xs text-gray-400 hover:text-gray-200"
                                  aria-label="Rename conversation"
                                >
                                  Rename
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleDeleteConversation(conversation.id)
                                  }}
                                  className="text-xs text-red-400 hover:text-red-300"
                                  aria-label="Delete conversation"
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          </>
                        )}
                        {isEditing && (
                          <div className="flex items-center gap-2 text-xs">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleSaveEdit()
                              }}
                              className="text-xs text-green-400 hover:text-green-300"
                            >
                              Save
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleCancelEdit()
                              }}
                              className="text-xs text-gray-400 hover:text-gray-200"
                            >
                              Cancel
                            </button>
                          </div>
                        )}
                      </div>
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {filteredConversations.length > 0 && (
        <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
          <button
            onClick={() => setConversationPage((prev) => Math.max(1, prev - 1))}
            disabled={conversationPage <= 1}
            className="px-2 py-1 rounded border border-gray-700 disabled:opacity-50"
          >
            Prev
          </button>
          <span>
            Page {conversationPage} of {totalConversationPages}
          </span>
          <button
            onClick={() => setConversationPage((prev) => Math.min(totalConversationPages, prev + 1))}
            disabled={conversationPage >= totalConversationPages}
            className="px-2 py-1 rounded border border-gray-700 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </Panel>
  )
}
