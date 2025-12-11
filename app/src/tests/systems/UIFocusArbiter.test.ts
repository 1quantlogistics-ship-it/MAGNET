/**
 * MAGNET UI Focus Arbiter Tests
 *
 * Tests for modal/focus state management.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UIFocusArbiterImpl } from '../../systems/UIFocusArbiter';
import type { FocusSurface } from '../../systems/UIFocusArbiter';

describe('UIFocusArbiter', () => {
  let focusArbiter: UIFocusArbiterImpl;

  beforeEach(() => {
    focusArbiter = new UIFocusArbiterImpl({
      debug: false,
      defaultSurface: 'workspace',
    });
  });

  afterEach(() => {
    focusArbiter.reset();
  });

  describe('Focus Requests', () => {
    it('should start with default focus surface', () => {
      expect(focusArbiter.getCurrentFocus()).toBe('workspace');
    });

    it('should grant focus request', () => {
      const granted = focusArbiter.requestFocus('chat', 'test');
      expect(granted).toBe(true);
      expect(focusArbiter.getCurrentFocus()).toBe('chat');
    });

    it('should track previous focus', () => {
      focusArbiter.requestFocus('chat', 'test');
      focusArbiter.requestFocus('settings', 'test');

      const state = focusArbiter.getState();
      expect(state.current).toBe('settings');
      expect(state.previous).toBe('chat');
    });

    it('should release focus to previous', () => {
      focusArbiter.requestFocus('chat', 'test');
      focusArbiter.requestFocus('settings', 'test');
      focusArbiter.releaseFocus('test');

      expect(focusArbiter.getCurrentFocus()).toBe('chat');
    });

    it('should release focus to default when no previous', () => {
      focusArbiter.requestFocus('chat', 'test');
      focusArbiter.releaseFocus('test');

      expect(focusArbiter.getCurrentFocus()).toBe('workspace');
    });
  });

  describe('Priority Handling', () => {
    it('should allow higher priority to preempt lower', () => {
      focusArbiter.requestFocus('workspace', 'test'); // low priority

      const granted = focusArbiter.requestFocus('error-modal', 'test'); // critical

      expect(granted).toBe(true);
      expect(focusArbiter.getCurrentFocus()).toBe('error-modal');
    });

    it('should deny lower priority when higher is focused', () => {
      focusArbiter.requestFocus('error-modal', 'test'); // critical

      const granted = focusArbiter.requestFocus('chat', 'test'); // low

      expect(granted).toBe(false);
      expect(focusArbiter.getCurrentFocus()).toBe('error-modal');
    });

    it('should allow equal priority', () => {
      focusArbiter.requestFocus('chat', 'test'); // low

      const granted = focusArbiter.requestFocus('workspace', 'test'); // low

      expect(granted).toBe(true);
      expect(focusArbiter.getCurrentFocus()).toBe('workspace');
    });
  });

  describe('Focus Lock', () => {
    it('should lock focus', () => {
      focusArbiter.requestFocus('clarification', 'modal');
      const locked = focusArbiter.lockFocus('modal');

      expect(locked).toBe(true);
      expect(focusArbiter.isLocked()).toBe(true);
    });

    it('should deny focus requests when locked by another holder', () => {
      focusArbiter.requestFocus('clarification', 'modal');
      focusArbiter.lockFocus('modal');

      const granted = focusArbiter.requestFocus('chat', 'other');

      expect(granted).toBe(false);
      expect(focusArbiter.getCurrentFocus()).toBe('clarification');
    });

    it('should allow same holder to change focus when locked', () => {
      focusArbiter.requestFocus('clarification', 'modal');
      focusArbiter.lockFocus('modal');

      const granted = focusArbiter.requestFocus('settings', 'modal');

      expect(granted).toBe(true);
      expect(focusArbiter.getCurrentFocus()).toBe('settings');
    });

    it('should unlock focus', () => {
      focusArbiter.lockFocus('modal');

      const unlocked = focusArbiter.unlockFocus('modal');

      expect(unlocked).toBe(true);
      expect(focusArbiter.isLocked()).toBe(false);
    });

    it('should deny unlock from wrong holder', () => {
      focusArbiter.lockFocus('modal');

      const unlocked = focusArbiter.unlockFocus('other');

      expect(unlocked).toBe(false);
      expect(focusArbiter.isLocked()).toBe(true);
    });

    it('should deny release when locked by another holder', () => {
      focusArbiter.requestFocus('clarification', 'modal');
      focusArbiter.lockFocus('modal');

      const released = focusArbiter.releaseFocus('other');

      expect(released).toBe(false);
      expect(focusArbiter.getCurrentFocus()).toBe('clarification');
    });
  });

  describe('Focus History', () => {
    it('should maintain focus history', () => {
      focusArbiter.requestFocus('chat', 'test');
      focusArbiter.requestFocus('settings', 'test');
      focusArbiter.requestFocus('clarification', 'test');

      const state = focusArbiter.getState();
      expect(state.history).toContain('workspace');
      expect(state.history).toContain('chat');
      expect(state.history).toContain('settings');
    });

    it('should pop from history', () => {
      focusArbiter.requestFocus('chat', 'test');
      focusArbiter.requestFocus('settings', 'test');
      focusArbiter.requestFocus('clarification', 'test');

      focusArbiter.popFocus('test');

      expect(focusArbiter.getCurrentFocus()).toBe('settings');
    });

    it('should limit history size', () => {
      const arbiter = new UIFocusArbiterImpl({
        debug: false,
        maxHistorySize: 3,
      });

      // Navigate through more surfaces than history size
      const surfaces: FocusSurface[] = ['chat', 'settings', 'clarification', 'command-palette', 'prs-panel'];
      surfaces.forEach(s => arbiter.requestFocus(s, 'test'));

      const state = arbiter.getState();
      expect(state.history.length).toBeLessThanOrEqual(3);
    });
  });

  describe('Subscription', () => {
    it('should notify subscribers of focus changes', () => {
      const listener = vi.fn();
      focusArbiter.subscribe(listener);

      focusArbiter.requestFocus('chat', 'test');

      expect(listener).toHaveBeenCalledWith('chat', 'workspace');
    });

    it('should not notify when focus unchanged', () => {
      focusArbiter.requestFocus('workspace', 'test'); // Already default
      const listener = vi.fn();
      focusArbiter.subscribe(listener);

      focusArbiter.requestFocus('workspace', 'test'); // No change

      expect(listener).not.toHaveBeenCalled();
    });

    it('should unsubscribe correctly', () => {
      const listener = vi.fn();
      const unsub = focusArbiter.subscribe(listener);

      unsub();
      focusArbiter.requestFocus('chat', 'test');

      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('isFocused', () => {
    it('should return true for currently focused surface', () => {
      focusArbiter.requestFocus('chat', 'test');
      expect(focusArbiter.isFocused('chat')).toBe(true);
    });

    it('should return false for non-focused surface', () => {
      focusArbiter.requestFocus('chat', 'test');
      expect(focusArbiter.isFocused('settings')).toBe(false);
    });
  });

  describe('Reset', () => {
    it('should reset to default state', () => {
      focusArbiter.requestFocus('chat', 'test');
      focusArbiter.requestFocus('settings', 'test');
      focusArbiter.lockFocus('test');

      focusArbiter.reset();

      expect(focusArbiter.getCurrentFocus()).toBe('workspace');
      expect(focusArbiter.isLocked()).toBe(false);
      expect(focusArbiter.getState().history).toHaveLength(0);
    });
  });
});
