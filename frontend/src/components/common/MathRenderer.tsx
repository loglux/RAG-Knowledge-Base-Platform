import { useEffect, useRef } from 'react'

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
    // Typeset math after content changes
    if (containerRef.current && (window as any).MathJax?.typesetPromise) {
      (window as any).MathJax.typesetPromise([containerRef.current]).catch((err: any) => {
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
    if (element && (window as any).MathJax?.typesetPromise) {
      (window as any).MathJax.typesetPromise([element]).catch((err: any) => {
        console.error('MathJax typesetting failed:', err)
      })
    }
  }
}
