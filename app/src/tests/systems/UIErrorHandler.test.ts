/**
 * MAGNET UI Error Handler Tests
 *
 * Tests for error formatting and retry logic.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UIErrorHandlerImpl } from '../../systems/UIErrorHandler';
import type { ErrorCategory, ErrorSeverity } from '../../systems/UIErrorHandler';

describe('UIErrorHandler', () => {
  let errorHandler: UIErrorHandlerImpl;

  beforeEach(() => {
    errorHandler = new UIErrorHandlerImpl({
      debug: false,
      autoDismissMs: 0, // Disable auto-dismiss for tests
    });
  });

  afterEach(() => {
    errorHandler.reset();
  });

  describe('Error Handling', () => {
    it('should create UIError from string', () => {
      const uiError = errorHandler.handle('Test error message');

      expect(uiError.message).toBe('Test error message');
      expect(uiError.id).toMatch(/^err_\d+_[a-z0-9]+$/);
      expect(uiError.timestamp).toBeDefined();
    });

    it('should create UIError from Error object', () => {
      const error = new Error('Original error');
      const uiError = errorHandler.handle(error);

      expect(uiError.message).toBe('Original error');
      expect(uiError.originalError).toBe(error);
    });

    it('should use provided error code', () => {
      const uiError = errorHandler.handle('Error', { code: 'CUSTOM_CODE' });
      expect(uiError.code).toBe('CUSTOM_CODE');
    });

    it('should use provided category', () => {
      const uiError = errorHandler.handle('Error', { category: 'auth' });
      expect(uiError.category).toBe('auth');
    });

    it('should use provided severity', () => {
      const uiError = errorHandler.handle('Error', { severity: 'critical' });
      expect(uiError.severity).toBe('critical');
    });

    it('should include context', () => {
      const uiError = errorHandler.handle('Error', {
        context: { userId: '123', action: 'test' },
      });
      expect(uiError.context).toEqual({ userId: '123', action: 'test' });
    });
  });

  describe('Error Code Inference', () => {
    it('should infer NETWORK_ERROR from message', () => {
      const uiError = errorHandler.handle('Network request failed');
      expect(uiError.code).toBe('NETWORK_ERROR');
    });

    it('should infer TIMEOUT_ERROR from message', () => {
      const uiError = errorHandler.handle('Request timeout exceeded');
      expect(uiError.code).toBe('TIMEOUT_ERROR');
    });

    it('should infer AUTH_EXPIRED from 401', () => {
      const uiError = errorHandler.handle('401 Unauthorized');
      expect(uiError.code).toBe('AUTH_EXPIRED');
    });

    it('should infer AUTH_FORBIDDEN from 403', () => {
      const uiError = errorHandler.handle('403 Forbidden');
      expect(uiError.code).toBe('AUTH_FORBIDDEN');
    });

    it('should infer WS_FAILED from websocket error', () => {
      const uiError = errorHandler.handle('WebSocket connection closed');
      expect(uiError.code).toBe('WS_FAILED');
    });

    it('should infer SERVER_ERROR from 500', () => {
      const uiError = errorHandler.handle('500 Internal Server Error');
      expect(uiError.code).toBe('SERVER_ERROR');
    });

    it('should default to UNKNOWN_ERROR', () => {
      const uiError = errorHandler.handle('Some random error');
      expect(uiError.code).toBe('UNKNOWN_ERROR');
    });
  });

  describe('Category Inference', () => {
    it('should infer network category from code', () => {
      const uiError = errorHandler.handle('Error', { code: 'NETWORK_ERROR' });
      expect(uiError.category).toBe('network');
    });

    it('should infer auth category', () => {
      const uiError = errorHandler.handle('Error', { code: 'AUTH_EXPIRED' });
      expect(uiError.category).toBe('auth');
    });

    it('should infer websocket category', () => {
      const uiError = errorHandler.handle('Error', { code: 'WS_DISCONNECTED' });
      expect(uiError.category).toBe('websocket');
    });

    it('should infer transaction category', () => {
      const uiError = errorHandler.handle('Error', { code: 'TX_FAILED' });
      expect(uiError.category).toBe('transaction');
    });

    it('should infer chain category', () => {
      const uiError = errorHandler.handle('Error', { code: 'CHAIN_GAP' });
      expect(uiError.category).toBe('chain');
    });
  });

  describe('User Messages', () => {
    it('should provide user-friendly message for known codes', () => {
      const uiError = errorHandler.handle('Error', { code: 'NETWORK_ERROR' });
      expect(uiError.userMessage).toBe('Unable to connect. Please check your internet connection.');
    });

    it('should provide fallback message for unknown codes', () => {
      const uiError = errorHandler.handle('Error', { code: 'SOME_UNKNOWN_CODE' });
      expect(uiError.userMessage).toBe('An unexpected error occurred. Please try again.');
    });

    it('should provide suggested action for known codes', () => {
      const uiError = errorHandler.handle('Error', { code: 'NETWORK_ERROR' });
      expect(uiError.suggestedAction).toBe('Check your internet connection and try again');
    });
  });

  describe('Active Errors', () => {
    it('should track active errors', () => {
      errorHandler.handle('Error 1');
      errorHandler.handle('Error 2');

      const active = errorHandler.getActiveErrors();
      expect(active).toHaveLength(2);
    });

    it('should get error by ID', () => {
      const uiError = errorHandler.handle('Test error');

      const retrieved = errorHandler.getError(uiError.id);
      expect(retrieved).toEqual(uiError);
    });

    it('should return undefined for unknown ID', () => {
      const retrieved = errorHandler.getError('nonexistent');
      expect(retrieved).toBeUndefined();
    });
  });

  describe('Dismiss', () => {
    it('should dismiss error by ID', () => {
      const uiError = errorHandler.handle('Test error');

      errorHandler.dismiss(uiError.id);

      expect(errorHandler.getError(uiError.id)).toBeUndefined();
    });

    it('should dismiss all errors', () => {
      errorHandler.handle('Error 1');
      errorHandler.handle('Error 2');

      errorHandler.dismissAll();

      expect(errorHandler.getActiveErrors()).toHaveLength(0);
    });
  });

  describe('Subscription', () => {
    it('should notify subscribers on new error', () => {
      const handler = vi.fn();
      errorHandler.subscribe(handler);

      errorHandler.handle('Test error');

      expect(handler).toHaveBeenCalledTimes(1);
      expect(handler.mock.calls[0][0].message).toBe('Test error');
    });

    it('should unsubscribe correctly', () => {
      const handler = vi.fn();
      const unsub = errorHandler.subscribe(handler);

      unsub();
      errorHandler.handle('Test error');

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe('Retry Logic', () => {
    it('should retry operation on failure', async () => {
      let attempts = 0;
      const operation = vi.fn().mockImplementation(async () => {
        attempts++;
        if (attempts < 3) {
          throw new Error('Temporary error');
        }
        return 'success';
      });

      const result = await errorHandler.handleWithRetry(
        operation,
        'test-op',
        { maxRetries: 3, baseDelay: 10, multiplier: 1, maxDelay: 10 }
      );

      expect(result).toBe('success');
      expect(operation).toHaveBeenCalledTimes(3);
    });

    it('should throw after max retries', async () => {
      const operation = vi.fn().mockRejectedValue(new Error('Persistent error'));

      await expect(
        errorHandler.handleWithRetry(
          operation,
          'test-op',
          { maxRetries: 2, baseDelay: 10, multiplier: 1, maxDelay: 10 }
        )
      ).rejects.toThrow('Persistent error');

      expect(operation).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });

    it('should succeed without retry if operation succeeds', async () => {
      const operation = vi.fn().mockResolvedValue('immediate success');

      const result = await errorHandler.handleWithRetry(
        operation,
        'test-op',
        { maxRetries: 3, baseDelay: 10, multiplier: 2, maxDelay: 100 }
      );

      expect(result).toBe('immediate success');
      expect(operation).toHaveBeenCalledTimes(1);
    });
  });

  describe('Recoverable/Retryable Flags', () => {
    it('should mark network errors as retryable', () => {
      const uiError = errorHandler.handle('Error', { code: 'NETWORK_ERROR' });
      expect(uiError.retryable).toBe(true);
    });

    it('should mark critical errors as non-recoverable', () => {
      const uiError = errorHandler.handle('Error', { severity: 'critical' });
      expect(uiError.recoverable).toBe(false);
    });

    it('should respect explicit recoverable flag', () => {
      const uiError = errorHandler.handle('Error', {
        severity: 'critical',
        recoverable: true,
      });
      expect(uiError.recoverable).toBe(true);
    });
  });

  describe('Reset', () => {
    it('should clear all state on reset', () => {
      errorHandler.handle('Error 1');
      errorHandler.handle('Error 2');

      errorHandler.reset();

      expect(errorHandler.getActiveErrors()).toHaveLength(0);
    });
  });
});
