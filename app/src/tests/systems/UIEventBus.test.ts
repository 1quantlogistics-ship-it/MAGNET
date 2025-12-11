/**
 * MAGNET UI Event Bus Tests
 *
 * Tests for UIEventBus domain routing and event handling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UIEventBus, createEventBus } from '../../systems/UIEventBus';
import { createUIEvent } from '../../types/events';
import type { Domain } from '../../types/domainHashes';

describe('UIEventBus', () => {
  let eventBus: typeof UIEventBus;

  beforeEach(() => {
    eventBus = createEventBus();
  });

  afterEach(() => {
    eventBus.clear();
  });

  describe('Basic Event Handling', () => {
    it('should emit and receive events', () => {
      const handler = vi.fn();
      eventBus.on('ui:panel_focus', handler);

      const event = createUIEvent('ui:panel_focus', { panelId: 'test' }, 'system');
      eventBus.emit(event);

      expect(handler).toHaveBeenCalledTimes(1);
      expect(handler).toHaveBeenCalledWith(event);
    });

    it('should allow multiple handlers for same event', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      eventBus.on('ui:panel_focus', handler1);
      eventBus.on('ui:panel_focus', handler2);

      const event = createUIEvent('ui:panel_focus', { panelId: 'test' }, 'system');
      eventBus.emit(event);

      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledTimes(1);
    });

    it('should unsubscribe correctly', () => {
      const handler = vi.fn();
      const unsubscribe = eventBus.on('ui:panel_focus', handler);

      unsubscribe();

      const event = createUIEvent('ui:panel_focus', { panelId: 'test' }, 'system');
      eventBus.emit(event);

      expect(handler).not.toHaveBeenCalled();
    });

    it('should support wildcard subscriptions', () => {
      const handler = vi.fn();
      eventBus.on('*', handler);

      eventBus.emit(createUIEvent('ui:panel_focus', {}, 'system'));
      eventBus.emit(createUIEvent('ui:panel_blur', {}, 'system'));

      expect(handler).toHaveBeenCalledTimes(2);
    });
  });

  describe('Domain Routing', () => {
    it('should route geometry events to geometry subscribers', () => {
      const handler = vi.fn();
      eventBus.subscribeToDomain('geometry', handler);

      const event = createUIEvent('backend:geometry_updated', {
        updateType: 'incremental',
      }, 'backend');

      eventBus.emitToDomain('geometry', event);

      expect(handler).toHaveBeenCalledTimes(1);
      expect(handler).toHaveBeenCalledWith(event, 'geometry');
    });

    it('should not route to other domain subscribers', () => {
      const geometryHandler = vi.fn();
      const routingHandler = vi.fn();

      eventBus.subscribeToDomain('geometry', geometryHandler);
      eventBus.subscribeToDomain('routing', routingHandler);

      const event = createUIEvent('backend:geometry_updated', {}, 'backend');
      eventBus.emitToDomain('geometry', event);

      expect(geometryHandler).toHaveBeenCalledTimes(1);
      expect(routingHandler).not.toHaveBeenCalled();
    });

    it('should support multi-domain subscriptions', () => {
      const handler = vi.fn();
      eventBus.subscribeToDomains(['geometry', 'routing'], handler);

      eventBus.emitToDomain('geometry', createUIEvent('test', {}, 'system'));
      eventBus.emitToDomain('routing', createUIEvent('test', {}, 'system'));
      eventBus.emitToDomain('phase', createUIEvent('test', {}, 'system'));

      expect(handler).toHaveBeenCalledTimes(2);
    });

    it('should unsubscribe from domain correctly', () => {
      const handler = vi.fn();
      const unsubscribe = eventBus.subscribeToDomain('geometry', handler);

      unsubscribe();

      eventBus.emitToDomain('geometry', createUIEvent('test', {}, 'system'));

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe('Once Subscriptions', () => {
    it('should only fire once for once() subscriptions', () => {
      const handler = vi.fn();
      eventBus.once('ui:panel_focus', handler);

      eventBus.emit(createUIEvent('ui:panel_focus', {}, 'system'));
      eventBus.emit(createUIEvent('ui:panel_focus', {}, 'system'));

      expect(handler).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error Handling', () => {
    it('should continue emitting to other handlers if one throws', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error');
      });
      const successHandler = vi.fn();

      eventBus.on('ui:panel_focus', errorHandler);
      eventBus.on('ui:panel_focus', successHandler);

      // Should not throw
      eventBus.emit(createUIEvent('ui:panel_focus', {}, 'system'));

      expect(errorHandler).toHaveBeenCalledTimes(1);
      expect(successHandler).toHaveBeenCalledTimes(1);
    });
  });

  describe('Clear', () => {
    it('should remove all handlers on clear', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      eventBus.on('ui:panel_focus', handler1);
      eventBus.subscribeToDomain('geometry', handler2);

      eventBus.clear();

      eventBus.emit(createUIEvent('ui:panel_focus', {}, 'system'));
      eventBus.emitToDomain('geometry', createUIEvent('test', {}, 'system'));

      expect(handler1).not.toHaveBeenCalled();
      expect(handler2).not.toHaveBeenCalled();
    });
  });
});
