/**
 * MAGNET UI Bootstrap Manager Tests
 *
 * Tests for initialization sequencing and WebSocket buffering.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UIBootstrapManagerImpl } from '../../systems/UIBootstrapManager';
import type { BootstrapPhase } from '../../systems/UIBootstrapManager';

describe('UIBootstrapManager', () => {
  let bootstrapManager: UIBootstrapManagerImpl;

  beforeEach(() => {
    bootstrapManager = new UIBootstrapManagerImpl({
      debug: false,
      timeout: 5000,
    });
  });

  afterEach(() => {
    bootstrapManager.reset();
  });

  describe('Registration', () => {
    it('should register stores', () => {
      const initializer = vi.fn().mockResolvedValue(undefined);

      bootstrapManager.registerStore('testStore', initializer);

      const progress = bootstrapManager.getProgress();
      expect(progress.storesTotal).toBe(1);
      expect(progress.storesReady).toBe(0);
    });

    it('should register systems', () => {
      const initializer = vi.fn().mockResolvedValue(undefined);

      bootstrapManager.registerSystem('testSystem', initializer);

      const progress = bootstrapManager.getProgress();
      expect(progress.systemsTotal).toBe(1);
      expect(progress.systemsReady).toBe(0);
    });

    it('should register WebSocket connector', () => {
      const connector = vi.fn().mockResolvedValue(undefined);

      bootstrapManager.registerWebSocketConnector(connector);

      // No direct way to check, but shouldn't throw
      expect(true).toBe(true);
    });
  });

  describe('Bootstrap Process', () => {
    it('should start in idle phase', () => {
      expect(bootstrapManager.getPhase()).toBe('idle');
      expect(bootstrapManager.isReady()).toBe(false);
    });

    it('should bootstrap successfully with no registrations', async () => {
      const result = await bootstrapManager.bootstrap();

      expect(result).toBe(true);
      expect(bootstrapManager.getPhase()).toBe('ready');
      expect(bootstrapManager.isReady()).toBe(true);
    });

    it('should initialize stores in order', async () => {
      const order: string[] = [];

      bootstrapManager.registerStore('store1', async () => {
        order.push('store1');
      });
      bootstrapManager.registerStore('store2', async () => {
        order.push('store2');
      });

      await bootstrapManager.bootstrap();

      expect(order).toEqual(['store1', 'store2']);
    });

    it('should initialize systems after stores', async () => {
      const order: string[] = [];

      bootstrapManager.registerStore('store', async () => {
        order.push('store');
      });
      bootstrapManager.registerSystem('system', async () => {
        order.push('system');
      });

      await bootstrapManager.bootstrap();

      expect(order).toEqual(['store', 'system']);
    });

    it('should connect WebSocket after systems', async () => {
      const order: string[] = [];

      bootstrapManager.registerSystem('system', async () => {
        order.push('system');
      });
      bootstrapManager.registerWebSocketConnector(async () => {
        order.push('websocket');
      });

      await bootstrapManager.bootstrap();

      expect(order).toEqual(['system', 'websocket']);
    });

    it('should prevent double bootstrap', async () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      await bootstrapManager.bootstrap();
      const result = await bootstrapManager.bootstrap();

      expect(result).toBe(true);
      expect(warnSpy).toHaveBeenCalled();

      warnSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    it('should handle store initialization failure', async () => {
      bootstrapManager.registerStore('failingStore', async () => {
        throw new Error('Store init failed');
      });

      const result = await bootstrapManager.bootstrap();

      expect(result).toBe(false);
      expect(bootstrapManager.getPhase()).toBe('error');
    });

    it('should handle system initialization failure', async () => {
      bootstrapManager.registerSystem('failingSystem', async () => {
        throw new Error('System init failed');
      });

      const result = await bootstrapManager.bootstrap();

      expect(result).toBe(false);
      expect(bootstrapManager.getPhase()).toBe('error');
    });

    it('should call onError callback on failure', async () => {
      const onError = vi.fn();
      const manager = new UIBootstrapManagerImpl({
        debug: false,
        onError,
      });

      manager.registerStore('failing', async () => {
        throw new Error('Test error');
      });

      await manager.bootstrap();

      expect(onError).toHaveBeenCalled();
      expect(onError.mock.calls[0][0]).toContain('Store "failing" failed');
    });
  });

  describe('Progress Tracking', () => {
    it('should track store progress', async () => {
      let capturedProgress: number[] = [];

      bootstrapManager.registerStore('store1', async () => {});
      bootstrapManager.registerStore('store2', async () => {});

      bootstrapManager.subscribe((phase, progress) => {
        capturedProgress.push(progress.storesReady);
      });

      await bootstrapManager.bootstrap();

      expect(capturedProgress).toContain(1);
      expect(capturedProgress).toContain(2);
    });

    it('should calculate overall progress percentage', () => {
      bootstrapManager.registerStore('store1', async () => {});
      bootstrapManager.registerStore('store2', async () => {});
      bootstrapManager.registerSystem('system1', async () => {});

      const progress = bootstrapManager.getProgress();

      // 2 stores + 1 system + 1 websocket = 4 total
      expect(progress.progress).toBe(0); // None ready
    });
  });

  describe('Phase Changes', () => {
    it('should transition through phases', async () => {
      const phases: BootstrapPhase[] = [];

      bootstrapManager.registerStore('store', async () => {});
      bootstrapManager.registerSystem('system', async () => {});

      bootstrapManager.subscribe((phase) => {
        phases.push(phase);
      });

      await bootstrapManager.bootstrap();

      expect(phases).toContain('initializing');
      expect(phases).toContain('stores');
      expect(phases).toContain('systems');
      expect(phases).toContain('ready');
    });

    it('should include websocket and buffering phases when connector registered', async () => {
      const phases: BootstrapPhase[] = [];

      bootstrapManager.registerWebSocketConnector(async () => {});

      bootstrapManager.subscribe((phase) => {
        phases.push(phase);
      });

      await bootstrapManager.bootstrap();

      expect(phases).toContain('websocket');
      expect(phases).toContain('buffering');
      expect(phases).toContain('ready');
    });
  });

  describe('Callbacks', () => {
    it('should call onReady when bootstrap completes', async () => {
      const onReady = vi.fn();
      const manager = new UIBootstrapManagerImpl({
        debug: false,
        onReady,
      });

      await manager.bootstrap();

      expect(onReady).toHaveBeenCalled();
    });

    it('should not call onReady on failure', async () => {
      const onReady = vi.fn();
      const manager = new UIBootstrapManagerImpl({
        debug: false,
        onReady,
      });

      manager.registerStore('failing', async () => {
        throw new Error('Fail');
      });

      await manager.bootstrap();

      expect(onReady).not.toHaveBeenCalled();
    });
  });

  describe('Reset', () => {
    it('should reset to initial state', async () => {
      bootstrapManager.registerStore('store', async () => {});
      await bootstrapManager.bootstrap();

      bootstrapManager.reset();

      expect(bootstrapManager.getPhase()).toBe('idle');
      expect(bootstrapManager.isReady()).toBe(false);
    });

    it('should re-register stores as uninitialized after reset', async () => {
      bootstrapManager.registerStore('store', async () => {});
      await bootstrapManager.bootstrap();

      bootstrapManager.reset();

      const progress = bootstrapManager.getProgress();
      expect(progress.storesReady).toBe(0);
      expect(progress.storesTotal).toBe(1);
    });
  });

  describe('Subscription', () => {
    it('should allow unsubscription', async () => {
      const listener = vi.fn();
      const unsub = bootstrapManager.subscribe(listener);

      unsub();
      await bootstrapManager.bootstrap();

      expect(listener).not.toHaveBeenCalled();
    });
  });
});
