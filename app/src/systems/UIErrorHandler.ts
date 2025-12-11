/**
 * MAGNET UI Error Handler
 *
 * Centralized error handling with formatting, retry logic,
 * and user-friendly message generation.
 */

import { UIEventBus } from './UIEventBus';
import { createUIEvent } from '../types/events';
import { UI_SCHEMA_VERSION } from '../types/schema-version';
import type { Unsubscribe } from '../types/contracts';

// ============================================================================
// Types
// ============================================================================

/**
 * Error severity levels
 */
export type ErrorSeverity = 'info' | 'warning' | 'error' | 'critical';

/**
 * Error categories for routing and handling
 */
export type ErrorCategory =
  | 'network'        // Network/API errors
  | 'validation'     // Input validation errors
  | 'auth'           // Authentication/authorization
  | 'websocket'      // WebSocket connection errors
  | 'state'          // State management errors
  | 'transaction'    // Transaction/rollback errors
  | 'chain'          // Chain validation errors
  | 'unknown';       // Uncategorized errors

/**
 * Structured error for UI display
 */
export interface UIError {
  id: string;
  code: string;
  message: string;
  userMessage: string;
  severity: ErrorSeverity;
  category: ErrorCategory;
  recoverable: boolean;
  retryable: boolean;
  timestamp: number;
  context?: Record<string, unknown>;
  originalError?: Error;
  suggestedAction?: string;
}

/**
 * Error handler callback
 */
export type ErrorHandler = (error: UIError) => void;

/**
 * Retry configuration
 */
export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  multiplier: number;
  maxDelay: number;
}

/**
 * Error handler configuration
 */
interface ErrorHandlerConfig {
  /** Enable debug logging */
  debug?: boolean;
  /** Default retry configuration */
  retryConfig?: Partial<RetryConfig>;
  /** Auto-dismiss info/warning after ms (0 = no auto-dismiss) */
  autoDismissMs?: number;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  multiplier: 2,
  maxDelay: 8000,
};

/**
 * User-friendly messages for common error codes
 */
const USER_MESSAGES: Record<string, string> = {
  // Network errors
  NETWORK_ERROR: 'Unable to connect. Please check your internet connection.',
  TIMEOUT_ERROR: 'The request took too long. Please try again.',
  SERVER_ERROR: 'Something went wrong on our end. Please try again later.',

  // Auth errors
  AUTH_EXPIRED: 'Your session has expired. Please log in again.',
  AUTH_INVALID: 'Invalid credentials. Please check and try again.',
  AUTH_FORBIDDEN: 'You don\'t have permission to perform this action.',

  // WebSocket errors
  WS_DISCONNECTED: 'Connection lost. Attempting to reconnect...',
  WS_RECONNECTING: 'Reconnecting to server...',
  WS_FAILED: 'Unable to establish connection. Please refresh the page.',

  // Transaction errors
  TX_FAILED: 'The operation failed. Your changes have been reverted.',
  TX_TIMEOUT: 'The operation timed out. Please try again.',
  TX_CONFLICT: 'A conflict occurred. Please refresh and try again.',

  // Chain errors
  CHAIN_GAP: 'State synchronization error. Refreshing data...',
  CHAIN_CYCLE: 'Data cycle detected. Refreshing data...',

  // Validation errors
  VALIDATION_FAILED: 'Please check your input and try again.',

  // Generic
  UNKNOWN_ERROR: 'An unexpected error occurred. Please try again.',
};

/**
 * Suggested actions for error codes
 */
const SUGGESTED_ACTIONS: Record<string, string> = {
  NETWORK_ERROR: 'Check your internet connection and try again',
  TIMEOUT_ERROR: 'Wait a moment and retry the operation',
  SERVER_ERROR: 'Try again in a few minutes',
  AUTH_EXPIRED: 'Click here to log in again',
  AUTH_FORBIDDEN: 'Contact support if you need access',
  WS_FAILED: 'Refresh the page to reconnect',
  TX_FAILED: 'Review your changes and try again',
  CHAIN_GAP: 'Data will refresh automatically',
  CHAIN_CYCLE: 'Data will refresh automatically',
};

// ============================================================================
// UIErrorHandler
// ============================================================================

class UIErrorHandlerImpl {
  private config: Required<ErrorHandlerConfig>;
  private handlers: Set<ErrorHandler> = new Set();
  private activeErrors: Map<string, UIError> = new Map();
  private retryCounters: Map<string, number> = new Map();
  private dismissTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

  constructor(config: ErrorHandlerConfig = {}) {
    this.config = {
      debug: config.debug ?? process.env.NODE_ENV === 'development',
      retryConfig: { ...DEFAULT_RETRY_CONFIG, ...config.retryConfig },
      autoDismissMs: config.autoDismissMs ?? 5000,
    };
  }

  /**
   * Handle an error
   */
  handle(
    error: Error | string,
    options: {
      code?: string;
      category?: ErrorCategory;
      severity?: ErrorSeverity;
      recoverable?: boolean;
      retryable?: boolean;
      context?: Record<string, unknown>;
    } = {}
  ): UIError {
    const uiError = this.createUIError(error, options);

    // Store active error
    this.activeErrors.set(uiError.id, uiError);

    // Log if debug enabled
    if (this.config.debug) {
      console.error(`[UIErrorHandler] ${uiError.code}:`, uiError.message, uiError.context);
    }

    // Notify handlers
    this.notifyHandlers(uiError);

    // Emit to event bus
    UIEventBus.emit(createUIEvent('ui:error', {
      errorId: uiError.id,
      errorCode: uiError.code,
      message: uiError.userMessage,
      severity: uiError.severity,
      recoverable: uiError.recoverable,
      suggestedAction: uiError.suggestedAction,
    }, 'system'));

    // Auto-dismiss for non-critical errors
    if (
      this.config.autoDismissMs > 0 &&
      (uiError.severity === 'info' || uiError.severity === 'warning')
    ) {
      this.scheduleDismiss(uiError.id, this.config.autoDismissMs);
    }

    return uiError;
  }

  /**
   * Handle network error with retry support
   */
  async handleWithRetry<T>(
    operation: () => Promise<T>,
    operationId: string,
    config: Partial<RetryConfig> = {}
  ): Promise<T> {
    const retryConfig = { ...this.config.retryConfig, ...config };
    let lastError: Error | null = null;
    let retryCount = this.retryCounters.get(operationId) || 0;

    while (retryCount <= retryConfig.maxRetries) {
      try {
        const result = await operation();
        // Success - clear retry counter
        this.retryCounters.delete(operationId);
        return result;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        retryCount++;
        this.retryCounters.set(operationId, retryCount);

        if (retryCount > retryConfig.maxRetries) {
          break;
        }

        // Calculate delay with exponential backoff
        const delay = Math.min(
          retryConfig.baseDelay * Math.pow(retryConfig.multiplier, retryCount - 1),
          retryConfig.maxDelay
        );

        if (this.config.debug) {
          console.log(`[UIErrorHandler] Retry ${retryCount}/${retryConfig.maxRetries} for ${operationId} in ${delay}ms`);
        }

        await this.delay(delay);
      }
    }

    // All retries exhausted
    this.retryCounters.delete(operationId);
    throw lastError;
  }

  /**
   * Dismiss an error
   */
  dismiss(errorId: string): void {
    const timer = this.dismissTimers.get(errorId);
    if (timer) {
      clearTimeout(timer);
      this.dismissTimers.delete(errorId);
    }

    this.activeErrors.delete(errorId);

    // Emit dismissal event
    UIEventBus.emit(createUIEvent('ui:error_dismissed', {
      errorId,
    }, 'system'));
  }

  /**
   * Dismiss all errors
   */
  dismissAll(): void {
    for (const errorId of this.activeErrors.keys()) {
      this.dismiss(errorId);
    }
  }

  /**
   * Get active errors
   */
  getActiveErrors(): UIError[] {
    return Array.from(this.activeErrors.values());
  }

  /**
   * Get error by ID
   */
  getError(errorId: string): UIError | undefined {
    return this.activeErrors.get(errorId);
  }

  /**
   * Subscribe to errors
   */
  subscribe(handler: ErrorHandler): Unsubscribe {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  /**
   * Create structured UI error
   */
  private createUIError(
    error: Error | string,
    options: {
      code?: string;
      category?: ErrorCategory;
      severity?: ErrorSeverity;
      recoverable?: boolean;
      retryable?: boolean;
      context?: Record<string, unknown>;
    }
  ): UIError {
    const message = error instanceof Error ? error.message : error;
    const code = options.code || this.inferErrorCode(error);
    const category = options.category || this.inferCategory(code);
    const severity = options.severity || this.inferSeverity(category);

    return {
      id: `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      code,
      message,
      userMessage: USER_MESSAGES[code] || USER_MESSAGES.UNKNOWN_ERROR,
      severity,
      category,
      recoverable: options.recoverable ?? severity !== 'critical',
      retryable: options.retryable ?? category === 'network',
      timestamp: Date.now(),
      context: options.context,
      originalError: error instanceof Error ? error : undefined,
      suggestedAction: SUGGESTED_ACTIONS[code],
    };
  }

  /**
   * Infer error code from error
   */
  private inferErrorCode(error: Error | string): string {
    const message = (error instanceof Error ? error.message : error).toLowerCase();

    if (message.includes('network') || message.includes('fetch')) {
      return 'NETWORK_ERROR';
    }
    if (message.includes('timeout')) {
      return 'TIMEOUT_ERROR';
    }
    if (message.includes('401') || message.includes('unauthorized')) {
      return 'AUTH_EXPIRED';
    }
    if (message.includes('403') || message.includes('forbidden')) {
      return 'AUTH_FORBIDDEN';
    }
    if (message.includes('websocket') || message.includes('ws://') || message.includes('wss://')) {
      return 'WS_FAILED';
    }
    if (message.includes('500') || message.includes('server')) {
      return 'SERVER_ERROR';
    }

    return 'UNKNOWN_ERROR';
  }

  /**
   * Infer category from error code
   */
  private inferCategory(code: string): ErrorCategory {
    if (code.startsWith('NETWORK') || code.startsWith('TIMEOUT') || code.startsWith('SERVER')) {
      return 'network';
    }
    if (code.startsWith('AUTH')) {
      return 'auth';
    }
    if (code.startsWith('WS')) {
      return 'websocket';
    }
    if (code.startsWith('TX')) {
      return 'transaction';
    }
    if (code.startsWith('CHAIN')) {
      return 'chain';
    }
    if (code.startsWith('VALIDATION')) {
      return 'validation';
    }
    return 'unknown';
  }

  /**
   * Infer severity from category
   */
  private inferSeverity(category: ErrorCategory): ErrorSeverity {
    switch (category) {
      case 'auth':
        return 'error';
      case 'network':
        return 'warning';
      case 'websocket':
        return 'warning';
      case 'transaction':
        return 'error';
      case 'chain':
        return 'warning';
      case 'validation':
        return 'warning';
      default:
        return 'error';
    }
  }

  /**
   * Schedule auto-dismiss
   */
  private scheduleDismiss(errorId: string, delay: number): void {
    const timer = setTimeout(() => {
      this.dismiss(errorId);
    }, delay);
    this.dismissTimers.set(errorId, timer);
  }

  /**
   * Notify all handlers
   */
  private notifyHandlers(error: UIError): void {
    for (const handler of this.handlers) {
      try {
        handler(error);
      } catch (err) {
        console.error('[UIErrorHandler] Handler error:', err);
      }
    }
  }

  /**
   * Delay helper
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Reset handler state
   */
  reset(): void {
    this.dismissAll();
    this.retryCounters.clear();
  }
}

// ============================================================================
// Exports
// ============================================================================

/**
 * Singleton error handler instance
 */
export const errorHandler = new UIErrorHandlerImpl({
  debug: process.env.NODE_ENV === 'development',
});

/**
 * Hook for using error handler in React components
 */
export function useErrorHandler() {
  return errorHandler;
}

export { UIErrorHandlerImpl };
