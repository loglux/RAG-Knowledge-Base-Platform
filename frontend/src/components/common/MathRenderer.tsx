import { useEffect, useRef } from 'react'

interface MathJax {
  typesetPromise: (elements?: HTMLElement[]) => Promise<void>
}

declare global {
  interface Window {
    MathJax?: MathJax
  }
}

interface MathRendererProps {
  content: string
  className?: string
}

/**
 * Component for rendering text with LaTeX math formulas.
 *
 * Supports:
 * - Inline math: $formula$ or \(formula\)
 * - Display math: $$formula$$ or \[formula\]
 *
 * Uses MathJax 3 loaded from CDN (see index.html).
 */
export function MathRenderer({ content, className = '' }: MathRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current && window.MathJax?.typesetPromise) {
      window.MathJax.typesetPromise([containerRef.current]).catch((err: unknown) => {
        console.error('MathJax typesetting failed:', err)
      })
    }
  }, [content])

  return (
    <div
      ref={containerRef}
      className={className}
      dangerouslySetInnerHTML={{ __html: content }}
    />
  )
}

/**
 * Hook to manually trigger MathJax typesetting on a ref element.
 *
 * Usage:
 * const ref = useRef<HTMLDivElement>(null)
 * const typesetMath = useMathTypeset()
 *
 * useEffect(() => {
 *   typesetMath(ref.current)
 * }, [content])
 */
export function useMathTypeset() {
  return (element: HTMLElement | null) => {
    if (element && window.MathJax?.typesetPromise) {
      window.MathJax.typesetPromise([element]).catch((err: unknown) => {
        console.error('MathJax typesetting failed:', err)
      })
    }
  }
}
