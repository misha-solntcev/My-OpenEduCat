import React from 'react';
import { Panel, Text, Button } from '@vkontakte/vkui';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

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
        <Panel mode="card">
          <div style={{ padding: 16 }}>
            <Text weight="1" color="negative">Что-то пошло не так</Text>
            <div style={{ marginTop: 12 }}>
              <pre style={{ fontFamily: 'monospace', fontSize: '11px', overflow: 'auto', margin: 0 }}>
                {this.state.error?.message}
              </pre>
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
              <Button
                mode="primary"
                appearance="accent"
                onClick={() => this.setState({ hasError: false, error: null })}
              >
                Попробовать снова
              </Button>
            </div>
          </div>
        </Panel>
      );
    }

    return this.props.children;
  }
}

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