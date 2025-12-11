/**
 * MAGNET UI Orchestrator
 *
 * First-class message broker for all UI mutations.
 * All state changes flow through the orchestrator - no direct store writes.
 *
 * FM3 Compliance: Authoritative control over UI state mutations.
 */

import type {
  UIOrchestratorContract,
  UIEvent,
  UIEventType,
  UIEventHandler,
  Unsubscribe,
  OrchestratorStatus,
  BackendStateSnapshot,
} from '../types/contracts';
import type { UIEventPayloadMap } from '../types/events';
import { createUIEvent } from '../types/events';
import { UIEventBus } from './UIEventBus';
import { getRegisteredStores, resetAllStores, getDirtyStores } from '../stores/contracts/StoreFactory';
import { isCompatibleVersion, UI_SCHEMA_VERSION } from '../types/schema-version';

/**
 * Orchestrator configuration
 */
interface OrchestratorConfig {
  /** Enable debug logging */
  debug?: boolean;
  /** Enable event batching */
  enableBatching?: boolean;
  /** Batch window in ms */
  batchWindow?: number;
}

/**
 * UIOrchestrator - Central coordinator for all UI state
 */
class UIOrchestrator implements UIOrchestratorContract {
  private static instance: UIOrchestrator;
  private config: Required<OrchestratorConfig>;
  private isReconciling: boolean = false;
  private lastReconcileTimestamp: number | null = null;
  private pendingEvents: UIEvent<unknown>[] = [];
  private batchTimeout: NodeJS.Timeout | null = null;

  private constructor(config: OrchestratorConfig = {}) {
    this.config = {
      debug: config.debug ?? process.env.NODE_ENV === 'development',
      enableBatching: config.enableBatching ?? true,
      batchWindow: config.batchWindow ?? 16, // ~1 frame at 60fps
    };
  }

  /**
   * Get singleton instance
   */
  static getInstance(): UIOrchestrator {
    if (!UIOrchestrator.instance) {
      UIOrchestrator.instance = new UIOrchestrator();
    }
    return UIOrchestrator.instance;
  }

  /**
   * Reset singleton (for testing)
   */
  static resetInstance(): void {
    UIOrchestrator.instance = new UIOrchestrator();
  }

  // ============================================================================
  // UIOrchestratorContract Implementation
  // ============================================================================

  /**
   * Subscribe to a specific event type
   */
  subscribe<T extends UIEventType>(
    eventType: T,
    handler: UIEventHandler<UIEventPayloadMap[T]>
  ): Unsubscribe {
    return UIEventBus.subscribe(eventType, handler as UIEventHandler<unknown>);
  }

  /**
   * Subscribe to multiple event types
   */
  subscribeMany<T extends UIEventType>(
    eventTypes: T[],
    handler: UIEventHandler<UIEventPayloadMap[T[number]]>
  ): Unsubscribe {
    return UIEventBus.subscribeMany(eventTypes, handler as UIEventHandler<unknown>);
  }

  /**
   * Dispatch an event
   * This is the ONLY way to mutate UI state from components
   */
  dispatch<T extends UIEventType>(event: UIEvent<UIEventPayloadMap[T]>): void {
    if (this.config.debug) {
      console.log('[UIOrchestrator] Dispatch:', event.type, event.payload);
    }

    // Validate schema version
    if (!isCompatibleVersion(event.schema_version)) {
      console.error(
        `[UIOrchestrator] Incompatible schema version: ${event.schema_version}, expected: ${UI_SCHEMA_VERSION}`
      );
      return;
    }

    if (this.config.enableBatching && this.shouldBatch(event.type)) {
      this.queueEvent(event as UIEvent<unknown>);
    } else {
      this.processEvent(event as UIEvent<unknown>);
    }
  }

  /**
   * Dispatch and wait for all handlers to complete
   */
  async dispatchAsync<T extends UIEventType>(
    event: UIEvent<UIEventPayloadMap[T]>
  ): Promise<void> {
    if (this.config.debug) {
      console.log('[UIOrchestrator] DispatchAsync:', event.type, event.payload);
    }

    // Validate schema version
    if (!isCompatibleVersion(event.schema_version)) {
      console.error(
        `[UIOrchestrator] Incompatible schema version: ${event.schema_version}`
      );
      return;
    }

    await this.processEventAsync(event as UIEvent<unknown>);
  }

  /**
   * Reconcile UI state with backend state
   * Called by UIStateReconciler when backend emits state changes
   */
  reconcile(backendState: BackendStateSnapshot): void {
    if (this.isReconciling) {
      console.warn('[UIOrchestrator] Already reconciling, skipping...');
      return;
    }

    // Validate schema version
    if (!isCompatibleVersion(backendState.schema_version)) {
      console.error(
        `[UIOrchestrator] Cannot reconcile: incompatible schema version ${backendState.schema_version}`
      );

      // Emit conflict event
      this.dispatch(
        createUIEvent(
          'reconciler:conflict',
          {
            syncId: `sync_${Date.now()}`,
            conflictType: 'schema_incompatible',
            conflictPath: 'root',
            localValue: UI_SCHEMA_VERSION,
            remoteValue: backendState.schema_version,
            resolution: 'manual',
          },
          'reconciler'
        )
      );
      return;
    }

    this.isReconciling = true;
    const syncId = `sync_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    // Emit sync start
    this.dispatch(
      createUIEvent(
        'reconciler:sync_start',
        {
          syncId,
          sourceTimestamp: backendState.timestamp,
          affectedStores: getDirtyStores(),
        },
        'reconciler'
      )
    );

    const startTime = Date.now();
    let changesApplied = 0;
    const errors: string[] = [];

    try {
      // Reconcile each registered store
      const stores = getRegisteredStores();

      for (const [name, store] of stores) {
        try {
          // Get relevant state from backend snapshot
          const storeState = this.extractStoreState(name, backendState);

          if (storeState) {
            const typedStore = store as { getState: () => { reconcile: (s: unknown) => void } };
            typedStore.getState().reconcile(storeState);
            changesApplied++;
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          errors.push(`${name}: ${message}`);
          console.error(`[UIOrchestrator] Reconcile error for store "${name}":`, error);
        }
      }

      this.lastReconcileTimestamp = Date.now();

      // Emit sync complete
      this.dispatch(
        createUIEvent(
          'reconciler:sync_complete',
          {
            syncId,
            duration: Date.now() - startTime,
            changesApplied,
            errors: errors.length > 0 ? errors : undefined,
          },
          'reconciler'
        )
      );

      if (this.config.debug) {
        console.log(
          `[UIOrchestrator] Reconcile complete: ${changesApplied} stores updated in ${Date.now() - startTime}ms`
        );
      }
    } finally {
      this.isReconciling = false;
    }
  }

  /**
   * Reset all UI state to initial values
   */
  reset(): void {
    if (this.config.debug) {
      console.log('[UIOrchestrator] Resetting all stores');
    }

    // Clear pending events
    this.pendingEvents = [];
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }

    // Reset all stores
    resetAllStores();

    // Clear event bus
    UIEventBus.clear();

    this.lastReconcileTimestamp = null;
  }

  /**
   * Get orchestrator status
   */
  getStatus(): OrchestratorStatus {
    return {
      isReconciling: this.isReconciling,
      pendingEvents: this.pendingEvents.length,
      lastReconcileTimestamp: this.lastReconcileTimestamp,
      subscriberCount: UIEventBus.getTotalListenerCount(),
    };
  }

  // ============================================================================
  // Convenience Methods
  // ============================================================================

  /**
   * Dispatch a typed event (shorthand)
   */
  emit<T extends UIEventType>(
    type: T,
    payload: UIEventPayloadMap[T],
    source: 'user' | 'agent' | 'backend' | 'reconciler' | 'system' = 'system'
  ): void {
    const event = createUIEvent(type, payload, source);
    this.dispatch(event);
  }

  /**
   * Dispatch a user event
   */
  emitUserEvent<T extends UIEventType>(
    type: T,
    payload: UIEventPayloadMap[T]
  ): void {
    this.emit(type, payload, 'user');
  }

  /**
   * Dispatch a system event
   */
  emitSystemEvent<T extends UIEventType>(
    type: T,
    payload: UIEventPayloadMap[T]
  ): void {
    this.emit(type, payload, 'system');
  }

  // ============================================================================
  // Private Methods
  // ============================================================================

  private shouldBatch(eventType: UIEventType): boolean {
    // Don't batch critical events
    const noBatchEvents: UIEventType[] = [
      'ui:error',
      'reconciler:sync_start',
      'reconciler:sync_complete',
      'reconciler:conflict',
      'agent:error',
    ];
    return !noBatchEvents.includes(eventType);
  }

  private queueEvent(event: UIEvent<unknown>): void {
    this.pendingEvents.push(event);

    if (!this.batchTimeout) {
      this.batchTimeout = setTimeout(() => {
        this.flushBatch();
      }, this.config.batchWindow);
    }
  }

  private flushBatch(): void {
    this.batchTimeout = null;
    const events = [...this.pendingEvents];
    this.pendingEvents = [];

    for (const event of events) {
      this.processEvent(event);
    }
  }

  private processEvent(event: UIEvent<unknown>): void {
    UIEventBus.emit(event);
  }

  private async processEventAsync(event: UIEvent<unknown>): Promise<void> {
    await UIEventBus.emitAsync(event);
  }

  private extractStoreState(
    storeName: string,
    backendState: BackendStateSnapshot
  ): Record<string, unknown> | null {
    // Map store names to backend state paths
    const storeMapping: Record<string, string> = {
      geometry: 'designState.geometry',
      ars: 'designState.recommendations',
      // Add more mappings as needed
    };

    const path = storeMapping[storeName];
    if (!path) {
      return null;
    }

    // Navigate to nested path
    const parts = path.split('.');
    let value: unknown = backendState;

    for (const part of parts) {
      if (value && typeof value === 'object' && part in value) {
        value = (value as Record<string, unknown>)[part];
      } else {
        return null;
      }
    }

    return value as Record<string, unknown> | null;
  }
}

/**
 * Export singleton instance
 */
export const orchestrator = UIOrchestrator.getInstance();

/**
 * Hook for using orchestrator in React components
 */
export function useOrchestrator(): UIOrchestratorContract & {
  emit: UIOrchestrator['emit'];
  emitUserEvent: UIOrchestrator['emitUserEvent'];
  emitSystemEvent: UIOrchestrator['emitSystemEvent'];
  getStatus: UIOrchestrator['getStatus'];
} {
  return UIOrchestrator.getInstance();
}

export { UIOrchestrator };
