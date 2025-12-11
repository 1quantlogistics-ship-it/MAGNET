/**
 * MAGNET UI Error Boundary
 *
 * React error boundary component that catches rendering errors
 * and displays a fallback UI with recovery options.
 */

import React, { Component, ReactNode } from 'react';
import { errorHandler, UIError } from '../../systems/UIErrorHandler';

// ============================================================================
// Types
// ============================================================================

interface ErrorBoundaryProps {
  /** Child components */
  children: ReactNode;
  /** Custom fallback UI */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** Called when error is caught */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  /** Component name for error context */
  componentName?: string;
  /** Whether to show full error details (dev mode) */
  showDetails?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  uiError: UIError | null;
}

// ============================================================================
// ErrorBoundary
// ============================================================================

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      uiError: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log to error handler
    const uiError = errorHandler.handle(error, {
      code: 'RENDER_ERROR',
      category: 'state',
      severity: 'error',
      recoverable: true,
      context: {
        componentName: this.props.componentName,
        componentStack: errorInfo.componentStack,
      },
    });

    this.setState({ errorInfo, uiError });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  /**
   * Reset error state to retry rendering
   */
  handleReset = (): void => {
    if (this.state.uiError) {
      errorHandler.dismiss(this.state.uiError.id);
    }
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      uiError: null,
    });
  };

  render(): ReactNode {
    const { hasError, error } = this.state;
    const { children, fallback, showDetails } = this.props;

    if (hasError && error) {
      // Custom fallback renderer
      if (typeof fallback === 'function') {
        return fallback(error, this.handleReset);
      }

      // Custom fallback element
      if (fallback) {
        return fallback;
      }

      // Default fallback UI
      return (
        <div className="error-boundary">
          <div className="error-boundary__content">
            <h2 className="error-boundary__title">Something went wrong</h2>
            <p className="error-boundary__message">
              {this.state.uiError?.userMessage || 'An unexpected error occurred.'}
            </p>
            {showDetails && (
              <details className="error-boundary__details">
                <summary>Error Details</summary>
                <pre>{error.message}</pre>
                {this.state.errorInfo?.componentStack && (
                  <pre>{this.state.errorInfo.componentStack}</pre>
                )}
              </details>
            )}
            <button
              className="error-boundary__retry"
              onClick={this.handleReset}
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return children;
  }
}

export default ErrorBoundary;
