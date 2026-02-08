import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import type { ChatMessage } from '../../types/index'

interface MessageBubbleProps {
  message: ChatMessage
  onDelete?: () => void
  showPromptVersion?: boolean
  sourceAnchorPrefix?: string
}

export function MessageBubble({ message, onDelete, showPromptVersion, sourceAnchorPrefix }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const timestamp = new Date(message.timestamp).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })
  const [copied, setCopied] = useState(false)
  const sourceCount = message.sources?.length ?? 0
  const sourceLinkPattern = /\b(Источник|Source)\s+(\d+)\b/g

  const renderedContent =
    !isUser && sourceCount > 0 && sourceAnchorPrefix
      ? message.content.replace(sourceLinkPattern, (match, label, num) => {
          const index = Number(num)
          if (!Number.isFinite(index) || index < 1 || index > sourceCount) {
            return match
          }
          return `[${label} ${num}](#${sourceAnchorPrefix}-${num})`
        })
      : message.content

  const handleCopy = async () => {
    let ok = false

    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(message.content)
        ok = true
      } catch {
        ok = false
      }
    }

    if (!ok) {
      try {
        const textarea = document.createElement('textarea')
        textarea.value = message.content
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        ok = document.execCommand('copy')
        document.body.removeChild(textarea)
      } catch {
        ok = false
      }
    }

    if (ok) {
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } else {
      setCopied(false)
    }
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-3xl rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-800 text-gray-100 border border-gray-700'
        }`}
      >
        <div className="flex items-baseline justify-between mb-1">
          <div className="flex items-baseline space-x-2">
            <span className="text-xs font-medium opacity-75">
              {isUser ? 'You' : 'Assistant'}
            </span>
            {!isUser && message.model && (
              <span className="text-[11px] text-gray-400">{message.model}</span>
            )}
            {!isUser && message.use_self_check && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                Self-check
              </span>
            )}
            {!isUser && showPromptVersion && message.prompt_version_id && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-300 border border-sky-500/30">
                Prompt {message.prompt_version_id.slice(0, 8)}
              </span>
            )}
            <span className="text-xs opacity-50">{timestamp}</span>
          </div>
          <div className="flex items-center gap-2">
            {onDelete && (
              <button
                type="button"
                onClick={onDelete}
                className="text-xs text-red-400 hover:text-red-300 transition-colors"
                aria-label="Delete message"
                title="Delete this Q&A pair"
              >
                Delete
              </button>
            )}
            <button
              type="button"
              onClick={handleCopy}
              className={`text-xs transition-colors ${
                copied ? 'text-green-400' : 'text-gray-400 hover:text-gray-200'
              }`}
              aria-label="Copy message"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>
        <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <ReactMarkdown
              remarkPlugins={[
                remarkGfm,
                [remarkMath, { singleDollarTextMath: true }]
              ]}
              rehypePlugins={[
                [rehypeKatex, { strict: false, throwOnError: false }]
              ]}
              components={{
                code: ({ inline, className, children, ...props }) => {
                  const childText = String(children).trim()

                  // Check if this is a single-line path/command (likely should be inline)
                  const isSingleLinePath = !inline && childText.split('\n').length === 1 &&
                    (childText.endsWith('/') || childText.length < 50)

                  if (isSingleLinePath) {
                    // Render short paths as inline code instead of blocks
                    return (
                      <code className="bg-gray-900 px-2 py-1 rounded text-xs font-mono border border-gray-700 inline-block" {...props}>
                        {children}
                      </code>
                    )
                  }

                  return !inline ? (
                    <pre className="bg-gray-900 rounded p-3 overflow-x-auto my-2 text-xs font-mono border border-gray-700">
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  ) : (
                    <code className="bg-gray-900 px-1.5 py-0.5 rounded text-xs font-mono border border-gray-700" {...props}>
                      {children}
                    </code>
                  )
                },
                ul: ({ children }) => (
                  <ul className="list-disc list-outside ml-5 space-y-1 my-2">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-outside ml-5 space-y-1 my-2">{children}</ol>
                ),
                li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                p: ({ children }) => <p className="my-2 leading-relaxed">{children}</p>,
                strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
                h1: ({ children }) => <h1 className="text-xl font-bold my-3">{children}</h1>,
                h2: ({ children }) => <h2 className="text-lg font-bold my-2">{children}</h2>,
                h3: ({ children }) => <h3 className="text-base font-bold my-2">{children}</h3>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-primary-500 pl-4 my-2 italic text-gray-400">
                    {children}
                  </blockquote>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-400 hover:text-primary-300 underline"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {renderedContent}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  )
}
