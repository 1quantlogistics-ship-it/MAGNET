/**
 * MAGNET UI Event Bus
 *
 * Local event bus for UI layer (parallel to backend EventBus).
 * All UI events flow through this bus for consistent handling.
 */

import type {
  UIEvent,
  UIEventType,
  UIEventHandler,
  Unsubscribe,
} from '../types/contracts';
import type { Domain } from '../types/domainHashes';
import { hasChainTracking, getEventDomain } from '../types/events';

/**
 * Event bus configuration
 */
interface EventBusConfig {
  /** Enable debug logging */
  debug?: boolean;
  /** Maximum listeners per event type (prevents memory leaks) */
  maxListeners?: number;
  /** Event history size for debugging */
  historySize?: number;
}

/**
 * Event history entry
 */
interface EventHistoryEntry {
  event: UIEvent<unknown>;
  timestamp: number;
  handlerCount: number;
  domain?: Domain;
}

/**
 * Domain-specific event handler
 */
type DomainEventHandler<T = unknown> = (event: UIEvent<T>, domain: Domain) => void | Promise<void>;

/**
 * UIEventBus - Central event routing for UI layer
 */
class UIEventBusImpl {
  private listeners: Map<UIEventType, Set<UIEventHandler<unknown>>> = new Map();
  private wildcardListeners: Set<UIEventHandler<unknown>> = new Set();
  private domainListeners: Map<Domain, Set<DomainEventHandler<unknown>>> = new Map();
  private history: EventHistoryEntry[] = [];
  private config: Required<EventBusConfig>;
  private isPaused: boolean = false;
  private queuedEvents: UIEvent<unknown>[] = [];

  constructor(config: EventBusConfig = {}) {
    this.config = {
      debug: config.debug ?? false,
      maxListeners: config.maxListeners ?? 100,
      historySize: config.historySize ?? 50,
    };
  }

  /**
   * Subscribe to a specific event type
   */
  subscribe<T = unknown>(
    eventType: UIEventType,
    handler: UIEventHandler<T>
  ): Unsubscribe {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }

    const handlers = this.listeners.get(eventType)!;

    // Check max listeners
    if (handlers.size >= this.config.maxListeners) {
      console.warn(
        `[UIEventBus] Max listeners (${this.config.maxListeners}) reached for event type "${eventType}"`
      );
    }

    handlers.add(handler as UIEventHandler<unknown>);

    if (this.config.debug) {
      console.log(`[UIEventBus] Subscribed to "${eventType}" (${handlers.size} listeners)`);
    }

    // Return unsubscribe function
    return () => {
      handlers.delete(handler as UIEventHandler<unknown>);
      if (this.config.debug) {
        console.log(`[UIEventBus] Unsubscribed from "${eventType}" (${handlers.size} listeners)`);
      }
    };
  }

  /**
   * Alias for subscribe (event emitter style)
   * Supports '*' for wildcard subscriptions
   */
  on<T = unknown>(
    eventType: UIEventType | '*',
    handler: UIEventHandler<T>
  ): Unsubscribe {
    if (eventType === '*') {
      return this.subscribeAll(handler);
    }
    return this.subscribe(eventType, handler);
  }

  /**
   * Subscribe to an event type for a single emission only
   */
  once<T = unknown>(
    eventType: UIEventType,
    handler: UIEventHandler<T>
  ): Unsubscribe {
    const wrappedHandler: UIEventHandler<T> = (event) => {
      unsubscribe();
      handler(event);
    };
    const unsubscribe = this.subscribe(eventType, wrappedHandler);
    return unsubscribe;
  }

  /**
   * Subscribe to multiple event types
   */
  subscribeMany<T = unknown>(
    eventTypes: UIEventType[],
    handler: UIEventHandler<T>
  ): Unsubscribe {
    const unsubscribes = eventTypes.map((type) =>
      this.subscribe(type, handler)
    );

    return () => {
      unsubscribes.forEach((unsub) => unsub());
    };
  }

  /**
   * Subscribe to all events (wildcard)
   */
  subscribeAll<T = unknown>(handler: UIEventHandler<T>): Unsubscribe {
    this.wildcardListeners.add(handler as UIEventHandler<unknown>);

    return () => {
      this.wildcardListeners.delete(handler as UIEventHandler<unknown>);
    };
  }

  /**
   * Subscribe to events for a specific domain
   * Only receives chain-tracked events for that domain
   */
  subscribeToDomain<T = unknown>(
    domain: Domain,
    handler: DomainEventHandler<T>
  ): Unsubscribe {
    if (!this.domainListeners.has(domain)) {
      this.domainListeners.set(domain, new Set());
    }

    const handlers = this.domainListeners.get(domain)!;
    handlers.add(handler as DomainEventHandler<unknown>);

    if (this.config.debug) {
      console.log(`[UIEventBus] Subscribed to domain "${domain}" (${handlers.size} listeners)`);
    }

    return () => {
      handlers.delete(handler as DomainEventHandler<unknown>);
      if (this.config.debug) {
        console.log(`[UIEventBus] Unsubscribed from domain "${domain}" (${handlers.size} listeners)`);
      }
    };
  }

  /**
   * Subscribe to multiple domains
   */
  subscribeToDomains<T = unknown>(
    domains: Domain[],
    handler: DomainEventHandler<T>
  ): Unsubscribe {
    const unsubscribes = domains.map((domain) =>
      this.subscribeToDomain(domain, handler)
    );

    return () => {
      unsubscribes.forEach((unsub) => unsub());
    };
  }

  /**
   * Emit an event to domain-specific listeners only
   */
  emitToDomain<T = unknown>(domain: Domain, event: UIEvent<T>): void {
    // Queue if paused
    if (this.isPaused) {
      this.queuedEvents.push(event as UIEvent<unknown>);
      return;
    }

    const domainHandlers = this.domainListeners.get(domain) || new Set();
    const handlerCount = domainHandlers.size;

    // Add to history
    this.addToHistory(event as UIEvent<unknown>, handlerCount, domain);

    if (this.config.debug) {
      console.log(
        `[UIEventBus] EmitToDomain "${domain}" "${event.type}"`,
        { payload: event.payload, handlers: handlerCount }
      );
    }

    // Call domain-specific handlers
    for (const handler of domainHandlers) {
      try {
        handler(event as UIEvent<unknown>, domain);
      } catch (error) {
        console.error(`[UIEventBus] Domain handler error for "${domain}":`, error);
      }
    }
  }

  /**
   * Emit an event synchronously
   */
  emit<T = unknown>(event: UIEvent<T>): void {
    // Queue if paused
    if (this.isPaused) {
      this.queuedEvents.push(event as UIEvent<unknown>);
      return;
    }

    const handlers = this.listeners.get(event.type) || new Set();
    const domain = getEventDomain(event as UIEvent<unknown>);
    const domainHandlers = domain ? (this.domainListeners.get(domain) || new Set()) : new Set();
    const handlerCount = handlers.size + this.wildcardListeners.size + domainHandlers.size;

    // Add to history
    this.addToHistory(event as UIEvent<unknown>, handlerCount, domain ?? undefined);

    if (this.config.debug) {
      console.log(
        `[UIEventBus] Emit "${event.type}"`,
        { payload: event.payload, handlers: handlerCount, domain }
      );
    }

    // Call type-specific handlers
    for (const handler of handlers) {
      try {
        handler(event as UIEvent<unknown>);
      } catch (error) {
        console.error(`[UIEventBus] Handler error for "${event.type}":`, error);
      }
    }

    // Call domain-specific handlers if event has chain tracking
    if (domain) {
      for (const handler of domainHandlers) {
        try {
          handler(event as UIEvent<unknown>, domain);
        } catch (error) {
          console.error(`[UIEventBus] Domain handler error for "${domain}":`, error);
        }
      }
    }

    // Call wildcard handlers
    for (const handler of this.wildcardListeners) {
      try {
        handler(event as UIEvent<unknown>);
      } catch (error) {
        console.error(`[UIEventBus] Wildcard handler error:`, error);
      }
    }
  }

  /**
   * Emit an event and wait for all handlers to complete
   */
  async emitAsync<T = unknown>(event: UIEvent<T>): Promise<void> {
    // Queue if paused
    if (this.isPaused) {
      this.queuedEvents.push(event as UIEvent<unknown>);
      return;
    }

    const handlers = this.listeners.get(event.type) || new Set();
    const handlerCount = handlers.size + this.wildcardListeners.size;

    // Add to history
    this.addToHistory(event as UIEvent<unknown>, handlerCount);

    if (this.config.debug) {
      console.log(
        `[UIEventBus] EmitAsync "${event.type}"`,
        { payload: event.payload, handlers: handlerCount }
      );
    }

    const allHandlers = [
      ...Array.from(handlers),
      ...Array.from(this.wildcardListeners),
    ];

    // Execute all handlers in parallel
    await Promise.all(
      allHandlers.map(async (handler) => {
        try {
          await handler(event as UIEvent<unknown>);
        } catch (error) {
          console.error(`[UIEventBus] Async handler error for "${event.type}":`, error);
        }
      })
    );
  }

  /**
   * Pause event emission (queues events)
   */
  pause(): void {
    this.isPaused = true;
    if (this.config.debug) {
      console.log('[UIEventBus] Paused');
    }
  }

  /**
   * Resume event emission and process queued events
   */
  resume(): void {
    this.isPaused = false;
    if (this.config.debug) {
      console.log(`[UIEventBus] Resumed (${this.queuedEvents.length} queued events)`);
    }

    // Process queued events
    const queued = [...this.queuedEvents];
    this.queuedEvents = [];

    for (const event of queued) {
      this.emit(event);
    }
  }

  /**
   * Clear all queued events
   */
  clearQueue(): void {
    const count = this.queuedEvents.length;
    this.queuedEvents = [];
    if (this.config.debug) {
      console.log(`[UIEventBus] Cleared ${count} queued events`);
    }
  }

  /**
   * Get event history
   */
  getHistory(): EventHistoryEntry[] {
    return [...this.history];
  }

  /**
   * Clear event history
   */
  clearHistory(): void {
    this.history = [];
  }

  /**
   * Get listener count for an event type
   */
  getListenerCount(eventType: UIEventType): number {
    return (this.listeners.get(eventType)?.size || 0) + this.wildcardListeners.size;
  }

  /**
   * Get total listener count across all event types
   */
  getTotalListenerCount(): number {
    let count = this.wildcardListeners.size;
    for (const handlers of this.listeners.values()) {
      count += handlers.size;
    }
    return count;
  }

  /**
   * Remove all listeners
   */
  clear(): void {
    this.listeners.clear();
    this.wildcardListeners.clear();
    this.domainListeners.clear();
    this.queuedEvents = [];
    if (this.config.debug) {
      console.log('[UIEventBus] Cleared all listeners');
    }
  }

  /**
   * Enable/disable debug mode
   */
  setDebug(enabled: boolean): void {
    this.config.debug = enabled;
  }

  private addToHistory(event: UIEvent<unknown>, handlerCount: number, domain?: Domain): void {
    this.history.push({
      event,
      timestamp: Date.now(),
      handlerCount,
      domain,
    });

    // Trim history if needed
    if (this.history.length > this.config.historySize) {
      this.history = this.history.slice(-this.config.historySize);
    }
  }
}

/**
 * Singleton event bus instance
 */
export const UIEventBus = new UIEventBusImpl({
  debug: process.env.NODE_ENV === 'development',
  maxListeners: 100,
  historySize: 50,
});

/**
 * Alias for UIEventBus (backwards compatibility)
 */
export const eventBus = UIEventBus;

/**
 * Hook for using event bus in React components
 */
export function useEventBus() {
  return UIEventBus;
}

/**
 * Create a new event bus instance (for testing or isolation)
 */
export function createEventBus(config?: EventBusConfig): UIEventBusImpl {
  return new UIEventBusImpl(config);
}

export type { UIEventBusImpl, DomainEventHandler };
