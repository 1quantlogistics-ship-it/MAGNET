/**
 * MAGNET UI Error Store
 *
 * Centralized error state management (UIErrorContext).
 * Handles error recovery, display, and reporting.
 */

import { createStore } from '../contracts/StoreFactory';
import type { ErrorInfo } from '../../types/common';

/**
 * Error severity levels
 */
export type ErrorSeverity = 'critical' | 'error' | 'warning' | 'info';

/**
 * Extended error with UI-specific metadata
 */
export interface UIError extends ErrorInfo {
  id: string;
  severity: ErrorSeverity;
  componentId?: string;
  panelId?: string;
  dismissed: boolean;
  dismissedAt?: number;
  suggestedAction?: string;
  retryAction?: () => Promise<void>;
}

/**
 * Error store state
 */
export interface ErrorStoreState {
  /** All errors by ID */
  errors: Record<string, UIError>;

  /** Error IDs in order received */
  errorOrder: string[];

  /** Currently displayed error ID (for modal/toast) */
  activeErrorId: string | null;

  /** Error count by severity */
  countBySeverity: Record<ErrorSeverity, number>;

  /** Global error boundary triggered */
  hasCriticalError: boolean;

  /** Last error timestamp */
  lastErrorTimestamp: number;

  /** Max errors to retain */
  maxErrors: number;
}

/**
 * Initial error store state
 */
const initialErrorState: ErrorStoreState = {
  errors: {},
  errorOrder: [],
  activeErrorId: null,
  countBySeverity: {
    critical: 0,
    error: 0,
    warning: 0,
    info: 0,
  },
  hasCriticalError: false,
  lastErrorTimestamp: 0,
  maxErrors: 50,
};

/**
 * Create the error store
 */
export const errorStore = createStore<ErrorStoreState>({
  name: 'error',
  initialState: initialErrorState,
  readOnlyFields: ['countBySeverity', 'hasCriticalError'],
  readWriteFields: [
    'errors',
    'errorOrder',
    'activeErrorId',
    'lastErrorTimestamp',
    'maxErrors',
  ],
});

// ============================================================================
// Error Actions (called via orchestrator)
// ============================================================================

/**
 * Add a new error
 */
export function addError(error: Omit<UIError, 'id' | 'dismissed'>): string {
  const id = `err_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

  const fullError: UIError = {
    ...error,
    id,
    dismissed: false,
  };

  errorStore.getState()._update((state) => {
    const errors = { ...state.errors, [id]: fullError };
    let errorOrder = [...state.errorOrder, id];

    // Trim if exceeding max
    if (errorOrder.length > state.maxErrors) {
      const toRemove = errorOrder.slice(0, errorOrder.length - state.maxErrors);
      for (const removeId of toRemove) {
        delete errors[removeId];
      }
      errorOrder = errorOrder.slice(-state.maxErrors);
    }

    // Update counts
    const countBySeverity = { ...state.countBySeverity };
    countBySeverity[error.severity]++;

    return {
      errors,
      errorOrder,
      countBySeverity,
      hasCriticalError: state.hasCriticalError || error.severity === 'critical',
      lastErrorTimestamp: Date.now(),
      activeErrorId: error.severity === 'critical' || error.severity === 'error'
        ? id
        : state.activeErrorId,
    };
  });

  return id;
}

/**
 * Dismiss an error
 */
export function dismissError(errorId: string): void {
  errorStore.getState()._update((state) => {
    const error = state.errors[errorId];
    if (!error) return {};

    return {
      errors: {
        ...state.errors,
        [errorId]: {
          ...error,
          dismissed: true,
          dismissedAt: Date.now(),
        },
      },
      activeErrorId: state.activeErrorId === errorId ? null : state.activeErrorId,
    };
  });
}

/**
 * Clear all errors
 */
export function clearAllErrors(): void {
  errorStore.getState()._update(() => ({
    errors: {},
    errorOrder: [],
    activeErrorId: null,
    countBySeverity: {
      critical: 0,
      error: 0,
      warning: 0,
      info: 0,
    },
    hasCriticalError: false,
  }));
}

/**
 * Clear dismissed errors
 */
export function clearDismissedErrors(): void {
  errorStore.getState()._update((state) => {
    const errors: Record<string, UIError> = {};
    const errorOrder: string[] = [];
    const countBySeverity: Record<ErrorSeverity, number> = {
      critical: 0,
      error: 0,
      warning: 0,
      info: 0,
    };

    for (const id of state.errorOrder) {
      const error = state.errors[id];
      if (error && !error.dismissed) {
        errors[id] = error;
        errorOrder.push(id);
        countBySeverity[error.severity]++;
      }
    }

    return {
      errors,
      errorOrder,
      countBySeverity,
    };
  });
}

/**
 * Set active error for display
 */
export function setActiveError(errorId: string | null): void {
  errorStore.getState()._update(() => ({
    activeErrorId: errorId,
  }));
}

/**
 * Retry error action
 */
export async function retryError(errorId: string): Promise<boolean> {
  const state = errorStore.getState().readOnly;
  const error = state.errors[errorId];

  if (!error?.retryAction) {
    return false;
  }

  try {
    await error.retryAction();
    dismissError(errorId);
    return true;
  } catch {
    return false;
  }
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get active (non-dismissed) errors
 */
export function getActiveErrors(): UIError[] {
  const state = errorStore.getState().readOnly;
  return state.errorOrder
    .map((id) => state.errors[id])
    .filter((error): error is UIError => error !== undefined && !error.dismissed);
}

/**
 * Get errors by severity
 */
export function getErrorsBySeverity(severity: ErrorSeverity): UIError[] {
  return getActiveErrors().filter((error) => error.severity === severity);
}

/**
 * Get the most recent error
 */
export function getLatestError(): UIError | null {
  const activeErrors = getActiveErrors();
  return activeErrors[activeErrors.length - 1] || null;
}

/**
 * Check if there are any active errors
 */
export function hasActiveErrors(): boolean {
  return getActiveErrors().length > 0;
}

/**
 * Get error count
 */
export function getErrorCount(): Record<ErrorSeverity, number> {
  return { ...errorStore.getState().readOnly.countBySeverity };
}

// ============================================================================
// Convenience factory
// ============================================================================

/**
 * Create an error from an exception
 */
export function createErrorFromException(
  exception: unknown,
  options: {
    code?: string;
    severity?: ErrorSeverity;
    componentId?: string;
    recoverable?: boolean;
  } = {}
): Omit<UIError, 'id' | 'dismissed'> {
  const {
    code = 'UNKNOWN_ERROR',
    severity = 'error',
    componentId,
    recoverable = true,
  } = options;

  let message = 'An unexpected error occurred';
  let details: string | undefined;

  if (exception instanceof Error) {
    message = exception.message;
    details = exception.stack;
  } else if (typeof exception === 'string') {
    message = exception;
  }

  return {
    code,
    message,
    details,
    recoverable,
    timestamp: Date.now(),
    severity,
    componentId,
  };
}
