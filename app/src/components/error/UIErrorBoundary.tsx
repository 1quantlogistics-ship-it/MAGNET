/**
 * MAGNET UI Error Boundary
 *
 * Error recovery wrapper for React components.
 * FM5 Compliance: Recovery model for Conductor/Validator failures.
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { addError, ErrorEntry, dismissError } from '../../stores/context/errorStore';
import { generateId } from '../../types/common';
import { ErrorDisplay } from './ErrorDisplay';

/**
 * Error boundary props
 */
interface UIErrorBoundaryProps {
  /** Child components to wrap */
  children: ReactNode;
  /** Fallback UI to show on error */
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  /** Component name for error tracking */
  componentName?: string;
  /** Called when error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Called when boundary resets */
  onReset?: () => void;
  /** Auto-dismiss error after ms (0 = never) */
  autoDismissMs?: number;
  /** Allow recovery attempt */
  recoverable?: boolean;
  /** Custom error severity */
  severity?: 'critical' | 'error' | 'warning';
}

/**
 * Error boundary state
 */
interface UIErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorEntry: ErrorEntry | null;
  retryCount: number;
}

/**
 * Maximum retry attempts before giving up
 */
const MAX_RETRY_ATTEMPTS = 3;

/**
 * UIErrorBoundary - React error boundary with recovery
 */
export class UIErrorBoundary extends Component<UIErrorBoundaryProps, UIErrorBoundaryState> {
  private autoDismissTimer: NodeJS.Timeout | null = null;

  constructor(props: UIErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorEntry: null,
      retryCount: 0,
    };
  }

  /**
   * Derive state from error
   */
  static getDerivedStateFromError(error: Error): Partial<UIErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  /**
   * Catch error and report
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const { componentName, onError, severity = 'error', autoDismissMs = 0 } = this.props;

    // Create error entry
    const errorEntry = addError({
      code: error.name || 'COMPONENT_ERROR',
      message: error.message,
      details: errorInfo.componentStack ?? undefined,
      severity,
      componentId: componentName,
      recoverable: this.isRecoverable(),
      suggestedAction: this.getSuggestedAction(),
    });

    this.setState({
      errorInfo,
      errorEntry,
    });

    // Call error handler
    onError?.(error, errorInfo);

    // Log error
    console.error(`[UIErrorBoundary] Error in ${componentName ?? 'component'}:`, error);
    console.error('[UIErrorBoundary] Component stack:', errorInfo.componentStack);

    // Set auto-dismiss timer
    if (autoDismissMs > 0 && errorEntry) {
      this.autoDismissTimer = setTimeout(() => {
        this.reset();
      }, autoDismissMs);
    }
  }

  /**
   * Cleanup on unmount
   */
  componentWillUnmount(): void {
    if (this.autoDismissTimer) {
      clearTimeout(this.autoDismissTimer);
    }
  }

  /**
   * Check if error is recoverable
   */
  private isRecoverable(): boolean {
    const { recoverable = true } = this.props;
    const { retryCount } = this.state;

    // Not recoverable if max retries reached
    if (retryCount >= MAX_RETRY_ATTEMPTS) {
      return false;
    }

    return recoverable;
  }

  /**
   * Get suggested action based on error
   */
  private getSuggestedAction(): string {
    const { error, retryCount } = this.state;

    if (retryCount >= MAX_RETRY_ATTEMPTS) {
      return 'Please refresh the page to continue.';
    }

    if (error?.name === 'NetworkError') {
      return 'Check your network connection and try again.';
    }

    if (error?.name === 'ValidationError') {
      return 'Please check your input and try again.';
    }

    return 'Click "Try Again" to recover.';
  }

  /**
   * Reset the error boundary
   */
  reset = (): void => {
    const { onReset } = this.props;
    const { errorEntry } = this.state;

    // Clear auto-dismiss timer
    if (this.autoDismissTimer) {
      clearTimeout(this.autoDismissTimer);
      this.autoDismissTimer = null;
    }

    // Dismiss error from store
    if (errorEntry) {
      dismissError(errorEntry.id);
    }

    // Reset state
    this.setState((prev) => ({
      hasError: false,
      error: null,
      errorInfo: null,
      errorEntry: null,
      retryCount: prev.retryCount + 1,
    }));

    // Call reset handler
    onReset?.();
  };

  /**
   * Render error fallback or children
   */
  render(): ReactNode {
    const { children, fallback, componentName } = this.props;
    const { hasError, error, retryCount } = this.state;

    if (hasError && error) {
      // Custom fallback
      if (fallback) {
        if (typeof fallback === 'function') {
          return fallback(error, this.reset);
        }
        return fallback;
      }

      // Default error display
      return (
        <ErrorDisplay
          error={error}
          componentName={componentName}
          onRetry={this.isRecoverable() ? this.reset : undefined}
          retryCount={retryCount}
          maxRetries={MAX_RETRY_ATTEMPTS}
        />
      );
    }

    return children;
  }
}

/**
 * HOC for wrapping components with error boundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  boundaryProps?: Omit<UIErrorBoundaryProps, 'children'>
): React.FC<P> {
  const displayName = WrappedComponent.displayName || WrappedComponent.name || 'Component';

  const WithErrorBoundary: React.FC<P> = (props) => (
    <UIErrorBoundary componentName={displayName} {...boundaryProps}>
      <WrappedComponent {...props} />
    </UIErrorBoundary>
  );

  WithErrorBoundary.displayName = `withErrorBoundary(${displayName})`;

  return WithErrorBoundary;
}

/**
 * Hook for accessing error boundary context
 */
export function useErrorBoundary(): {
  showBoundary: (error: Error) => void;
} {
  const [, setError] = React.useState<Error | null>(null);

  return {
    showBoundary: (error: Error) => {
      setError(() => {
        throw error;
      });
    },
  };
}

export default UIErrorBoundary;
