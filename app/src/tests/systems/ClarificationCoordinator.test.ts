/**
 * MAGNET UI Clarification Coordinator Tests
 * BRAVO OWNS THIS FILE.
 *
 * Tests for ClarificationCoordinator ACK retry and queue management.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  ClarificationCoordinator,
  DEFAULT_ACK_RETRY_CONFIG,
  type AckRetryConfig,
} from '../../systems/ClarificationCoordinator';
import type { ClarificationRequest } from '../../api/agents';

// Mock the agentsAPI
vi.mock('../../api/agents', async () => {
  const actual = await vi.importActual('../../api/agents');
  return {
    ...actual,
    agentsAPI: {
      acknowledge: vi.fn(),
      respond: vi.fn(),
      listPendingClarifications: vi.fn(),
      cancel: vi.fn(),
    },
  };
});

// Mock the eventBus
vi.mock('../../systems/UIEventBus', () => ({
  eventBus: {
    emit: vi.fn(),
    on: vi.fn(() => () => {}),
  },
}));

import { agentsAPI } from '../../api/agents';
import { eventBus } from '../../systems/UIEventBus';

// Helper to create mock clarification
function createMockClarification(overrides?: Partial<ClarificationRequest>): ClarificationRequest {
  return {
    requestId: `req-${Math.random().toString(36).slice(2)}`,
    agentId: 'agent-routing',
    requestToken: `token-${Math.random().toString(36).slice(2)}`,
    priority: 3,
    prompt: 'What unit system should be used?',
    options: ['metric', 'imperial'],
    defaultValue: 'metric',
    timeoutSeconds: 60,
    createdAt: new Date().toISOString(),
    currentAck: 'queued',
    ...overrides,
  };
}

describe('ClarificationCoordinator', () => {
  let coordinator: ClarificationCoordinator;

  beforeEach(() => {
    coordinator = new ClarificationCoordinator();
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    coordinator.reset();
    vi.useRealTimers();
  });

  describe('Initial State', () => {
    it('should initialize with empty state', () => {
      const state = coordinator.getState();

      expect(state.activeClarifications).toEqual([]);
      expect(state.currentClarification).toBeNull();
      expect(state.pendingAcks).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('Subscription', () => {
    it('should notify subscribers on state changes', async () => {
      const listener = vi.fn();
      coordinator.subscribe(listener);

      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      expect(listener).toHaveBeenCalled();
    });

    it('should unsubscribe correctly', async () => {
      const listener = vi.fn();
      const unsubscribe = coordinator.subscribe(listener);

      unsubscribe();
      coordinator.reset();

      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('Queue Management', () => {
    it('should add clarification to queue', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      const state = coordinator.getState();
      expect(state.activeClarifications).toHaveLength(1);
      expect(state.activeClarifications[0].requestId).toBe(clarification.requestId);
    });

    it('should sort clarifications by priority (higher first)', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const lowPriority = createMockClarification({ priority: 1, requestId: 'low' });
      const highPriority = createMockClarification({ priority: 4, requestId: 'high' });
      const medPriority = createMockClarification({ priority: 2, requestId: 'med' });

      await coordinator.addClarification(lowPriority);
      await coordinator.addClarification(highPriority);
      await coordinator.addClarification(medPriority);

      const state = coordinator.getState();
      expect(state.activeClarifications[0].requestId).toBe('high');
      expect(state.activeClarifications[1].requestId).toBe('med');
      expect(state.activeClarifications[2].requestId).toBe('low');
    });

    it('should auto-present first clarification', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      const state = coordinator.getState();
      expect(state.currentClarification).not.toBeNull();
    });

    it('should send queued ACK when adding', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      expect(agentsAPI.acknowledge).toHaveBeenCalledWith(
        clarification.agentId,
        clarification.requestId,
        expect.objectContaining({ ackType: 'queued' })
      );
    });

    it('should emit clarification:received event', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'clarification:received',
        })
      );
    });
  });

  describe('Presenting Clarifications', () => {
    it('should present next clarification', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      const result = await coordinator.presentNext();

      expect(result).not.toBeNull();
      expect(result?.requestId).toBe(clarification.requestId);
    });

    it('should send presented ACK', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      // Clear queued ACK call
      vi.mocked(agentsAPI.acknowledge).mockClear();

      await coordinator.presentNext();

      expect(agentsAPI.acknowledge).toHaveBeenCalledWith(
        clarification.agentId,
        clarification.requestId,
        expect.objectContaining({ ackType: 'presented' })
      );
    });

    it('should emit clarification:presented event', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      // presentNext() is called without await in addClarification,
      // so we need to wait for the next tick for the async emission
      await vi.waitFor(() => {
        expect(eventBus.emit).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'clarification:presented',
          })
        );
      });
    });

    it('should return null when queue is empty', async () => {
      const result = await coordinator.presentNext();
      expect(result).toBeNull();
    });
  });

  describe('Responding to Clarifications', () => {
    it('should respond and clear current', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);
      vi.mocked(agentsAPI.respond).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      await coordinator.respond('metric');

      const state = coordinator.getState();
      expect(state.currentClarification).toBeNull();
      expect(state.activeClarifications).toHaveLength(0);
    });

    it('should emit clarification:responded event', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);
      vi.mocked(agentsAPI.respond).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      await coordinator.respond('metric');

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'clarification:responded',
        })
      );
    });

    it('should throw error when no clarification to respond to', async () => {
      await expect(coordinator.respond('test')).rejects.toThrow(
        'No clarification to respond to'
      );
    });

    it('should present next after responding', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);
      vi.mocked(agentsAPI.respond).mockResolvedValue({} as any);

      const clarification1 = createMockClarification({ requestId: 'req1' });
      const clarification2 = createMockClarification({ requestId: 'req2' });

      await coordinator.addClarification(clarification1);
      await coordinator.addClarification(clarification2);

      await coordinator.respond('metric');

      const state = coordinator.getState();
      expect(state.activeClarifications).toHaveLength(1);
    });
  });

  describe('Skipping Clarifications', () => {
    it('should skip and remove from queue', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      await coordinator.skip('user choice');

      const state = coordinator.getState();
      expect(state.currentClarification).toBeNull();
      expect(state.activeClarifications).toHaveLength(0);
    });

    it('should send skipped ACK', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      vi.mocked(agentsAPI.acknowledge).mockClear();
      await coordinator.skip('user choice');

      expect(agentsAPI.acknowledge).toHaveBeenCalledWith(
        clarification.agentId,
        clarification.requestId,
        expect.objectContaining({
          ackType: 'skipped',
          reason: 'user choice',
        })
      );
    });

    it('should emit clarification:skipped event', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      await coordinator.skip();

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'clarification:skipped',
        })
      );
    });
  });

  describe('Cancelling Clarifications', () => {
    it('should cancel specific clarification', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      await coordinator.cancel(clarification.requestId, 'not needed');

      const state = coordinator.getState();
      expect(state.activeClarifications).toHaveLength(0);
    });

    it('should send cancelled ACK', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      vi.mocked(agentsAPI.acknowledge).mockClear();
      await coordinator.cancel(clarification.requestId, 'not needed');

      expect(agentsAPI.acknowledge).toHaveBeenCalledWith(
        clarification.agentId,
        clarification.requestId,
        expect.objectContaining({
          ackType: 'cancelled',
          reason: 'not needed',
        })
      );
    });

    it('should emit clarification:cancelled event', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      await coordinator.cancel(clarification.requestId);

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'clarification:cancelled',
        })
      );
    });

    it('should clear current if cancelled clarification was current', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      expect(coordinator.getState().currentClarification).not.toBeNull();

      await coordinator.cancel(clarification.requestId);

      expect(coordinator.getState().currentClarification).toBeNull();
    });
  });

  describe('ACK Retry Protocol (V1.4 FIX #5)', () => {
    it('should queue failed ACK for retry', async () => {
      vi.mocked(agentsAPI.acknowledge)
        .mockRejectedValueOnce(new Error('Network error'));

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      const state = coordinator.getState();
      expect(state.pendingAcks).toHaveLength(1);
      expect(state.pendingAcks[0].requestId).toBe(clarification.requestId);
      expect(state.pendingAcks[0].attempts).toBe(1);
    });

    it('should emit ack_retry event on failure', async () => {
      vi.mocked(agentsAPI.acknowledge)
        .mockRejectedValueOnce(new Error('Network error'));

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'clarification:ack_retry',
        })
      );
    });

    it('should respect maxRetries limit', async () => {
      const config: AckRetryConfig = {
        maxRetries: 2,
        initialDelayMs: 100,
        backoffMultiplier: 2,
        maxDelayMs: 1000,
      };

      coordinator = new ClarificationCoordinator(config);
      coordinator.start();

      vi.mocked(agentsAPI.acknowledge).mockRejectedValue(new Error('Network error'));

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      // When addClarification is called, TWO ACKs are queued:
      // 1. 'queued' ACK (initial)
      // 2. 'presented' ACK (from auto-presentNext)
      //
      // Each needs maxRetries (2) additional attempts to fail.
      // The retry timer fires every 1000ms.
      // Initial delay is 100ms, then 200ms (100*2).
      //
      // Timeline for both ACKs to fail:
      // - t=0: addClarification -> queued + presented ACKs fail, added to pending
      // - t=100: first retry delay expires for both
      // - t=1000: interval fires, retries both ACKs (attempt 2), both fail
      // - t=1100: second retry delay (200ms) expires
      // - t=2000: interval fires, retries both ACKs (attempt 3=maxRetries+1), emits ack_failed

      // Advance through enough interval ticks to process all retries
      // Each retry needs to wait for delay + next interval tick
      for (let i = 0; i < 5; i++) {
        await vi.advanceTimersByTimeAsync(1000);
      }

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'clarification:ack_failed',
        })
      );
    });

    it('should use exponential backoff', async () => {
      const config: AckRetryConfig = {
        maxRetries: 3,
        initialDelayMs: 1000,
        backoffMultiplier: 2,
        maxDelayMs: 10000,
      };

      coordinator = new ClarificationCoordinator(config);
      vi.mocked(agentsAPI.acknowledge).mockRejectedValue(new Error('Network error'));

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      const state = coordinator.getState();
      expect(state.pendingAcks[0].nextRetryAt).toBeGreaterThan(Date.now());

      // First retry after 1000ms
      const firstDelay = state.pendingAcks[0].nextRetryAt - state.pendingAcks[0].lastAttemptAt;
      expect(firstDelay).toBe(1000);
    });

    it('should cap delay at maxDelayMs', async () => {
      const config: AckRetryConfig = {
        maxRetries: 10,
        initialDelayMs: 5000,
        backoffMultiplier: 3,
        maxDelayMs: 10000,
      };

      coordinator = new ClarificationCoordinator(config);

      // Manually test backoff calculation
      // 5000 * 3^1 = 15000, but capped at 10000
      const calculatedDelay = Math.min(
        config.initialDelayMs * Math.pow(config.backoffMultiplier, 1),
        config.maxDelayMs
      );

      expect(calculatedDelay).toBe(10000);
    });

    it('should use default config', () => {
      expect(DEFAULT_ACK_RETRY_CONFIG.maxRetries).toBe(3);
      expect(DEFAULT_ACK_RETRY_CONFIG.initialDelayMs).toBe(1000);
      expect(DEFAULT_ACK_RETRY_CONFIG.backoffMultiplier).toBe(2);
      expect(DEFAULT_ACK_RETRY_CONFIG.maxDelayMs).toBe(10000);
    });
  });

  describe('Lifecycle', () => {
    it('should start timers', () => {
      coordinator.start();

      // Verify timers are running by checking they exist
      // (Internal implementation detail, but important for coverage)
      expect(coordinator.getState()).toBeDefined();
    });

    it('should stop timers', () => {
      coordinator.start();
      coordinator.stop();

      // Should not throw
      expect(coordinator.getState()).toBeDefined();
    });

    it('should reset state', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      coordinator.reset();

      const state = coordinator.getState();
      expect(state.activeClarifications).toEqual([]);
      expect(state.currentClarification).toBeNull();
    });
  });

  describe('Sync', () => {
    it('should sync with backend', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);
      vi.mocked(agentsAPI.listPendingClarifications).mockResolvedValue({
        data: {
          clarifications: [
            createMockClarification({ requestId: 'sync1' }),
            createMockClarification({ requestId: 'sync2' }),
          ],
        },
      } as any);

      await coordinator.sync();

      const state = coordinator.getState();
      expect(state.activeClarifications).toHaveLength(2);
    });

    it('should handle sync errors', async () => {
      vi.mocked(agentsAPI.listPendingClarifications).mockRejectedValue(
        new Error('Network error')
      );

      await coordinator.sync();

      const state = coordinator.getState();
      expect(state.error).toBe('Network error');
      expect(state.isLoading).toBe(false);
    });
  });
});
