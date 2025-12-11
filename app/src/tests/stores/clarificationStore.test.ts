/**
 * MAGNET UI Clarification Store Tests
 *
 * Tests for AI-initiated clarification request management.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  clarificationStore,
  getClarificationState,
  getActiveRequest,
  getQueueLength,
  getActiveContextualRequest,
  hasClarificationActive,
  requestClarification,
  respondToClarification,
  skipClarification,
  expireClarification,
  resetClarificationStore,
  clearClarificationHistory,
  subscribeToClarification,
} from '../../stores/domain/clarificationStore';
import type { ClarificationRequest, ClarificationPriority } from '../../types/clarification';

// ============================================================================
// Test Setup
// ============================================================================

describe('clarificationStore', () => {
  beforeEach(() => {
    resetClarificationStore();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Initial State Tests
  // ============================================================================

  describe('initial state', () => {
    it('has correct initial state', () => {
      const state = getClarificationState();

      expect(state.queue).toEqual([]);
      expect(state.activeRequest).toBeNull();
      expect(state.history).toEqual([]);
      expect(state.activeContextualRequest).toBeNull();
      expect(state.schema_version).toBeDefined();
    });
  });

  // ============================================================================
  // Selector Tests
  // ============================================================================

  describe('selectors', () => {
    describe('getActiveRequest', () => {
      it('returns null when no request is active', () => {
        expect(getActiveRequest()).toBeNull();
      });

      it('returns active request', () => {
        requestClarification({
          type: 'choice',
          priority: 'required',
          title: 'Test Question',
          message: 'Please select an option',
          options: [{ id: 'a', label: 'Option A' }],
          defaultValue: 'a',
          source: 'agent',
        });

        const active = getActiveRequest();
        expect(active).not.toBeNull();
        expect(active?.title).toBe('Test Question');
      });
    });

    describe('getQueueLength', () => {
      it('returns queue length', () => {
        expect(getQueueLength()).toBe(0);

        // Add a low priority request (will go to queue if high priority is active)
        requestClarification({
          type: 'choice',
          priority: 'required',
          title: 'First',
          message: 'First request',
          options: [],
          defaultValue: null,
          source: 'agent',
        });

        // First goes active immediately
        expect(getQueueLength()).toBe(0);

        // Add another
        requestClarification({
          type: 'choice',
          priority: 'optional',
          title: 'Second',
          message: 'Second request',
          options: [],
          defaultValue: null,
          source: 'agent',
        });

        expect(getQueueLength()).toBe(1);
      });
    });

    describe('hasClarificationActive', () => {
      it('returns false when no clarification active', () => {
        expect(hasClarificationActive()).toBe(false);
      });

      it('returns true when regular clarification active', () => {
        requestClarification({
          type: 'choice',
          priority: 'required',
          title: 'Test',
          message: 'Test',
          options: [],
          defaultValue: null,
          source: 'agent',
        });

        expect(hasClarificationActive()).toBe(true);
      });

      it('returns true when contextual clarification active', () => {
        requestClarification({
          type: 'contextual',
          priority: 'required',
          title: 'Contextual Test',
          message: 'Select in 3D',
          options: [],
          defaultValue: null,
          source: 'agent',
        });

        expect(hasClarificationActive()).toBe(true);
      });
    });
  });

  // ============================================================================
  // Request Action Tests
  // ============================================================================

  describe('requestClarification', () => {
    it('adds request and returns ID', () => {
      const id = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test Question',
        message: 'Please answer',
        options: [
          { id: 'yes', label: 'Yes' },
          { id: 'no', label: 'No' },
        ],
        defaultValue: 'yes',
        source: 'agent',
      });

      expect(id).toBeDefined();
      expect(id).toContain('clar');
    });

    it('activates first request immediately', () => {
      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'First',
        message: 'First request',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      expect(getActiveRequest()).not.toBeNull();
      expect(getQueueLength()).toBe(0);
    });

    it('queues subsequent requests', () => {
      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'First',
        message: 'First',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Second',
        message: 'Second',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      expect(getActiveRequest()?.title).toBe('First');
      expect(getQueueLength()).toBe(1);
    });

    it('sorts queue by priority', () => {
      // First request goes active
      requestClarification({
        type: 'choice',
        priority: 'optional',
        title: 'First Active',
        message: 'First',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      // Queue optional
      requestClarification({
        type: 'choice',
        priority: 'optional',
        title: 'Optional',
        message: 'Optional',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      // Queue required (should be first in queue)
      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Required',
        message: 'Required',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      // Queue recommended
      requestClarification({
        type: 'choice',
        priority: 'recommended',
        title: 'Recommended',
        message: 'Recommended',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      // Queue should be sorted: required, recommended, optional
      const state = getClarificationState();
      expect(state.queue[0].priority).toBe('required');
      expect(state.queue[1].priority).toBe('recommended');
      expect(state.queue[2].priority).toBe('optional');
    });

    it('handles contextual type separately', () => {
      requestClarification({
        type: 'contextual',
        priority: 'required',
        title: 'Select Space',
        message: 'Click on a space in the 3D view',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      expect(getActiveRequest()).toBeNull();
      expect(getActiveContextualRequest()).not.toBeNull();
      expect(getActiveContextualRequest()?.type).toBe('contextual');
    });
  });

  // ============================================================================
  // Response Action Tests
  // ============================================================================

  describe('respondToClarification', () => {
    it('resolves active request with response', () => {
      const id = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test',
        message: 'Choose',
        options: [{ id: 'a', label: 'A' }],
        defaultValue: 'a',
        source: 'agent',
      });

      respondToClarification(id, 'a');

      expect(getActiveRequest()).toBeNull();
      const state = getClarificationState();
      expect(state.history).toHaveLength(1);
      expect(state.history[0].status).toBe('answered');
      expect(state.history[0].response).toBe('a');
    });

    it('processes next queued request after response', () => {
      const id1 = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'First',
        message: 'First',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Second',
        message: 'Second',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      expect(getActiveRequest()?.title).toBe('First');

      respondToClarification(id1, 'answer1');

      expect(getActiveRequest()?.title).toBe('Second');
    });

    it('dispatches clarification:resolved event', () => {
      const eventHandler = vi.fn();
      window.addEventListener('clarification:resolved', eventHandler);

      const id = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test',
        message: 'Test',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      respondToClarification(id, 'response');

      expect(eventHandler).toHaveBeenCalled();
      const detail = eventHandler.mock.calls[0][0].detail;
      expect(detail.requestId).toBe(id);
      expect(detail.status).toBe('answered');
      expect(detail.response).toBe('response');

      window.removeEventListener('clarification:resolved', eventHandler);
    });
  });

  // ============================================================================
  // Skip Action Tests
  // ============================================================================

  describe('skipClarification', () => {
    it('skips active request with default value', () => {
      const id = requestClarification({
        type: 'choice',
        priority: 'optional',
        title: 'Test',
        message: 'Test',
        options: [{ id: 'default', label: 'Default' }],
        defaultValue: 'default',
        source: 'agent',
      });

      skipClarification(id);

      expect(getActiveRequest()).toBeNull();
      const state = getClarificationState();
      expect(state.history[0].status).toBe('skipped');
      expect(state.history[0].response).toBe('default');
    });

    it('warns when trying to skip non-active request', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      skipClarification('non-existent-id');

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Cannot skip clarification')
      );

      consoleSpy.mockRestore();
    });
  });

  // ============================================================================
  // Expire Action Tests
  // ============================================================================

  describe('expireClarification', () => {
    it('expires active request', () => {
      const id = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test',
        message: 'Test',
        options: [],
        defaultValue: 'default-val',
        source: 'agent',
      });

      expireClarification(id);

      expect(getActiveRequest()).toBeNull();
      const state = getClarificationState();
      expect(state.history[0].status).toBe('expired');
      expect(state.history[0].response).toBe('default-val');
    });

    it('does nothing for non-active request', () => {
      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test',
        message: 'Test',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      expireClarification('wrong-id');

      // Request should still be active
      expect(getActiveRequest()).not.toBeNull();
    });
  });

  // ============================================================================
  // Contextual Request Tests
  // ============================================================================

  describe('contextual requests', () => {
    it('handles contextual type separately from regular queue', () => {
      // Add regular request first
      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Regular',
        message: 'Regular request',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      // Add contextual request
      requestClarification({
        type: 'contextual',
        priority: 'required',
        title: 'Contextual',
        message: 'Contextual request',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      // Both should be active in their respective slots
      expect(getActiveRequest()?.title).toBe('Regular');
      expect(getActiveContextualRequest()?.title).toBe('Contextual');
    });

    it('resolves contextual request independently', () => {
      const regularId = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Regular',
        message: 'Regular',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      const contextualId = requestClarification({
        type: 'contextual',
        priority: 'required',
        title: 'Contextual',
        message: 'Contextual',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      respondToClarification(contextualId, { spaceId: 'space-123' });

      // Contextual should be resolved
      expect(getActiveContextualRequest()).toBeNull();
      // Regular should still be active
      expect(getActiveRequest()?.title).toBe('Regular');
    });
  });

  // ============================================================================
  // History Tests
  // ============================================================================

  describe('history management', () => {
    it('adds resolved requests to history', () => {
      const id = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test',
        message: 'Test',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      respondToClarification(id, 'answer');

      const state = getClarificationState();
      expect(state.history).toHaveLength(1);
      expect(state.history[0].id).toBe(id);
    });

    it('preserves history order', () => {
      const id1 = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'First',
        message: 'First',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      respondToClarification(id1, 'answer1');

      const id2 = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Second',
        message: 'Second',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      respondToClarification(id2, 'answer2');

      const state = getClarificationState();
      expect(state.history[0].title).toBe('First');
      expect(state.history[1].title).toBe('Second');
    });

    it('clears history', () => {
      const id = requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test',
        message: 'Test',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      respondToClarification(id, 'answer');
      expect(getClarificationState().history).toHaveLength(1);

      clearClarificationHistory();
      expect(getClarificationState().history).toHaveLength(0);
    });
  });

  // ============================================================================
  // Reset Tests
  // ============================================================================

  describe('resetClarificationStore', () => {
    it('resets store to initial state', () => {
      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test',
        message: 'Test',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      resetClarificationStore();

      const state = getClarificationState();
      expect(state.queue).toEqual([]);
      expect(state.activeRequest).toBeNull();
      expect(state.history).toEqual([]);
      expect(state.activeContextualRequest).toBeNull();
    });
  });

  // ============================================================================
  // Subscription Tests
  // ============================================================================

  describe('subscription', () => {
    it('notifies subscribers on state change', () => {
      const listener = vi.fn();
      const unsubscribe = subscribeToClarification(listener);

      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Test',
        message: 'Test',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      expect(listener).toHaveBeenCalled();

      unsubscribe();
    });

    it('stops notifying after unsubscribe', () => {
      const listener = vi.fn();
      const unsubscribe = subscribeToClarification(listener);

      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'First',
        message: 'First',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      const callCount = listener.mock.calls.length;
      unsubscribe();

      requestClarification({
        type: 'choice',
        priority: 'required',
        title: 'Second',
        message: 'Second',
        options: [],
        defaultValue: null,
        source: 'agent',
      });

      expect(listener.mock.calls.length).toBe(callCount);
    });
  });
});
