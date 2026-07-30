import React from 'react';
import { Panel, Text, Button, Box, Flex } from '@vkontakte/vkui';

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
        <Panel mode="card" padding="m">
          <Text weight="1" color="negative">Что-то пошло не так</Text>
          <Box marginTop="s">
            <pre style={{ textAlign: 'left', fontSize: '11px', color: 'var(--vkui--color_text_secondary)', overflow: 'auto' }}>
              {this.state.error?.message}
            </pre>
          </Box>
          <Flex justify="center" marginTop="m">
            <Button
              mode="primary"
              appearance="accent"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Попробовать снова
            </Button>
          </Flex>
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