import React from 'react'

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: (error: Error, reset: () => void) => React.ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('Uncaught error in component tree:', error, info.componentStack)
  }

  reset = (): void => {
    this.setState({ error: null })
  }

  render(): React.ReactNode {
    const { error } = this.state
    if (!error) {
      return this.props.children
    }

    if (this.props.fallback) {
      return this.props.fallback(error, this.reset)
    }

    return (
      <div
        role="alert"
        className="flex min-h-screen items-center justify-center bg-gray-900 px-4"
      >
        <div className="card max-w-md w-full text-center">
          <div className="text-5xl mb-4" aria-hidden="true">💥</div>
          <h1 className="text-xl font-semibold text-white mb-2">Something went wrong</h1>
          <p className="text-gray-400 text-sm mb-1">
            The application hit an unexpected error.
          </p>
          <p className="text-gray-500 text-xs mb-6 break-words font-mono">
            {error.message}
          </p>
          <div className="flex items-center justify-center gap-2">
            <button onClick={this.reset} className="btn-primary">
              Try again
            </button>
            <button
              onClick={() => window.location.assign('/')}
              className="btn-secondary"
            >
              Go home
            </button>
          </div>
        </div>
      </div>
    )
  }
}
