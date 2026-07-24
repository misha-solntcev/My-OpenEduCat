import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/** Error Boundary для изоляции ошибок в дочерних компонентах */
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary] caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div style={{ padding: '16px', textAlign: 'center', color: 'var(--background-accent-negative)' }}>
          <div style={{ fontSize: '14px', marginBottom: '8px' }}>Что-то пошло не так</div>
          <pre style={{ textAlign: 'left', fontSize: '11px', color: 'var(--text-secondary)', overflow: 'auto' }}>
            {this.state.error?.message}
          </pre>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              marginTop: '12px',
              padding: '8px 16px',
              background: 'var(--background-accent-themed)',
              color: 'var(--text-primary-static)',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            Попробовать снова
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/** HOC для оборачивания компонента в ErrorBoundary */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: React.ReactNode
): React.FC<P> {
  return (props) => (
    <ErrorBoundary fallback={fallback}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );
}