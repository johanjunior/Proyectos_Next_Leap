import React, { Component, type ReactNode } from 'react';
import { Button, Result } from 'antd';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{ padding: 48, maxWidth: 560, margin: '0 auto', textAlign: 'center' }}>
          <Result
            status="error"
            title="Algo salió mal"
            subTitle={this.state.error.message}
            extra={
              <Button type="primary" onClick={() => this.setState({ hasError: false, error: null })}>
                Reintentar
              </Button>
            }
          />
        </div>
      );
    }
    return this.props.children;
  }
}
