/**
 * MAGNET UI State Reconciler
 *
 * Listens to backend EventBus events and reconciles UI state.
 * FM1 Compliance: Prevents UI state drift from backend state.
 */

import type { BackendStateSnapshot } from '../types/contracts';
import type {
  BackendStateChangedPayload,
  BackendPhaseCompletedPayload,
  BackendValidationResultPayload,
  BackendGeometryUpdatedPayload,
  ChainTrackingMeta,
} from '../types/events';
import { createUIEvent, hasChainTracking } from '../types/events';
import { orchestrator } from './UIOrchestrator';
import { UI_SCHEMA_VERSION } from '../types/schema-version';
import type { Domain, DomainHashes, DomainChainStates, ChainValidationResult } from '../types/domainHashes';
import { INITIAL_DOMAIN_CHAIN_STATES, MAX_CHAIN_DEPTH } from '../types/domainHashes';
import { validateChain, updateChainState, resetChainState, compareDomainHashes, mergeDomainHashes } from '../utils/hashUtils';

/**
 * Backend event types we listen for
 */
type BackendEventType =
  | 'state_changed'
  | 'phase_completed'
  | 'validation_result'
  | 'geometry_updated';

/**
 * Backend event handler function
 */
type BackendEventHandler = (event: unknown) => void;

/**
 * Reconciler configuration
 */
interface ReconcilerConfig {
  /** Enable debug logging */
  debug?: boolean;
  /** Debounce reconciliation (ms) */
  debounceMs?: number;
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect delay (ms) */
  reconnectDelay?: number;
}

/**
 * UIStateReconciler - Bridges backend and UI state
 *
 * V1.4 Enhanced with:
 * - Per-domain chain tracking
 * - Chain validation and cycle detection
 * - Domain hash comparison
 */
class UIStateReconciler {
  private static instance: UIStateReconciler;
  private config: Required<ReconcilerConfig>;
  private isConnected: boolean = false;
  private eventHandlers: Map<BackendEventType, BackendEventHandler> = new Map();
  private debounceTimer: NodeJS.Timeout | null = null;
  private pendingState: Partial<BackendStateSnapshot> | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;

  // V1.4: Chain tracking state
  private chainStates: DomainChainStates = { ...INITIAL_DOMAIN_CHAIN_STATES };
  private domainHashes: DomainHashes = {
    geometryHash: '',
    arrangementHash: '',
    routingHash: '',
    phaseHash: '',
  };
  private cycleDetectionSet: Set<string> = new Set();

  // Mock backend connection (replace with actual backend integration)
  private backendConnection: {
    subscribe: (event: BackendEventType, handler: BackendEventHandler) => void;
    unsubscribe: (event: BackendEventType, handler: BackendEventHandler) => void;
    disconnect: () => void;
  } | null = null;

  private constructor(config: ReconcilerConfig = {}) {
    this.config = {
      debug: config.debug ?? process.env.NODE_ENV === 'development',
      debounceMs: config.debounceMs ?? 50,
      autoReconnect: config.autoReconnect ?? true,
      reconnectDelay: config.reconnectDelay ?? 5000,
    };

    this.setupEventHandlers();
  }

  /**
   * Get singleton instance
   */
  static getInstance(): UIStateReconciler {
    if (!UIStateReconciler.instance) {
      UIStateReconciler.instance = new UIStateReconciler();
    }
    return UIStateReconciler.instance;
  }

  /**
   * Connect to backend EventBus
   */
  connect(backendConnection?: typeof this.backendConnection): void {
    if (this.isConnected) {
      console.warn('[UIStateReconciler] Already connected');
      return;
    }

    // Use provided connection or create mock
    this.backendConnection = backendConnection || this.createMockConnection();

    // Subscribe to backend events
    for (const [eventType, handler] of this.eventHandlers) {
      this.backendConnection.subscribe(eventType, handler);
    }

    this.isConnected = true;

    if (this.config.debug) {
      console.log('[UIStateReconciler] Connected to backend');
    }
  }

  /**
   * Disconnect from backend EventBus
   */
  disconnect(): void {
    if (!this.isConnected || !this.backendConnection) {
      return;
    }

    // Unsubscribe from all events
    for (const [eventType, handler] of this.eventHandlers) {
      this.backendConnection.unsubscribe(eventType, handler);
    }

    this.backendConnection.disconnect();
    this.backendConnection = null;
    this.isConnected = false;

    // Cancel pending debounce
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }

    if (this.config.debug) {
      console.log('[UIStateReconciler] Disconnected from backend');
    }
  }

  /**
   * Check if connected to backend
   */
  getConnectionStatus(): boolean {
    return this.isConnected;
  }

  /**
   * Force reconciliation with provided state
   */
  forceReconcile(state: BackendStateSnapshot): void {
    if (this.config.debug) {
      console.log('[UIStateReconciler] Force reconcile');
    }
    orchestrator.reconcile(state);
  }

  /**
   * Handle incoming backend state change
   */
  private handleStateChanged(event: BackendStateChangedPayload): void {
    if (this.config.debug) {
      console.log('[UIStateReconciler] State changed:', event.changedPaths);
    }

    // Accumulate changes for debounced reconciliation
    this.pendingState = {
      ...this.pendingState,
      designState: {
        ...this.pendingState?.designState,
        ...event.newValues,
      },
      timestamp: Date.now(),
      schema_version: UI_SCHEMA_VERSION,
    };

    this.scheduleReconciliation();

    // Emit to UI event bus
    orchestrator.emit('backend:state_changed', event, 'backend');
  }

  /**
   * Handle backend phase completion
   */
  private handlePhaseCompleted(event: BackendPhaseCompletedPayload): void {
    if (this.config.debug) {
      console.log('[UIStateReconciler] Phase completed:', event.currentPhase);
    }

    // Update pending state
    this.pendingState = {
      ...this.pendingState,
      phase: event.currentPhase,
      timestamp: Date.now(),
      schema_version: UI_SCHEMA_VERSION,
    };

    // Phase changes trigger immediate reconciliation
    this.flushReconciliation();

    // Emit to UI event bus
    orchestrator.emit('backend:phase_completed', event, 'backend');
  }

  /**
   * Handle validation results
   */
  private handleValidationResult(event: BackendValidationResultPayload): void {
    if (this.config.debug) {
      console.log('[UIStateReconciler] Validation result:', event.validatorId, event.passed);
    }

    // Update pending state
    this.pendingState = {
      ...this.pendingState,
      validationResults: {
        ...this.pendingState?.validationResults,
        [event.validatorId]: event,
      },
      timestamp: Date.now(),
      schema_version: UI_SCHEMA_VERSION,
    };

    this.scheduleReconciliation();

    // Emit to UI event bus
    orchestrator.emit('backend:validation_result', event, 'backend');
  }

  /**
   * Handle geometry updates
   */
  private handleGeometryUpdated(event: BackendGeometryUpdatedPayload): void {
    if (this.config.debug) {
      console.log('[UIStateReconciler] Geometry updated:', event.updateType);
    }

    // Update pending state
    this.pendingState = {
      ...this.pendingState,
      geometryHash: event.newHash,
      timestamp: Date.now(),
      schema_version: UI_SCHEMA_VERSION,
    };

    // Geometry changes can be batched unless it's a full update
    if (event.updateType === 'full') {
      this.flushReconciliation();
    } else {
      this.scheduleReconciliation();
    }

    // Emit to UI event bus
    orchestrator.emit('backend:geometry_updated', event, 'backend');
  }

  /**
   * Schedule debounced reconciliation
   */
  private scheduleReconciliation(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.flushReconciliation();
    }, this.config.debounceMs);
  }

  /**
   * Execute reconciliation with pending state
   */
  private flushReconciliation(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }

    if (!this.pendingState) {
      return;
    }

    const state: BackendStateSnapshot = {
      schema_version: this.pendingState.schema_version || UI_SCHEMA_VERSION,
      timestamp: this.pendingState.timestamp || Date.now(),
      designState: this.pendingState.designState || {},
      phase: this.pendingState.phase || '',
      validationResults: this.pendingState.validationResults,
      geometryHash: this.pendingState.geometryHash,
    };

    this.pendingState = null;
    orchestrator.reconcile(state);
  }

  /**
   * Setup event handlers for backend events
   */
  private setupEventHandlers(): void {
    this.eventHandlers.set('state_changed', (event) => {
      this.handleStateChanged(event as BackendStateChangedPayload);
    });

    this.eventHandlers.set('phase_completed', (event) => {
      this.handlePhaseCompleted(event as BackendPhaseCompletedPayload);
    });

    this.eventHandlers.set('validation_result', (event) => {
      this.handleValidationResult(event as BackendValidationResultPayload);
    });

    this.eventHandlers.set('geometry_updated', (event) => {
      this.handleGeometryUpdated(event as BackendGeometryUpdatedPayload);
    });
  }

  /**
   * Create mock backend connection for development
   */
  private createMockConnection(): typeof this.backendConnection {
    const handlers = new Map<BackendEventType, Set<BackendEventHandler>>();

    return {
      subscribe: (event, handler) => {
        if (!handlers.has(event)) {
          handlers.set(event, new Set());
        }
        handlers.get(event)!.add(handler);
      },
      unsubscribe: (event, handler) => {
        handlers.get(event)?.delete(handler);
      },
      disconnect: () => {
        handlers.clear();
      },
    };
  }

  /**
   * Handle disconnection (for auto-reconnect)
   */
  private handleDisconnection(): void {
    this.isConnected = false;

    if (this.config.autoReconnect) {
      if (this.config.debug) {
        console.log(
          `[UIStateReconciler] Will attempt reconnect in ${this.config.reconnectDelay}ms`
        );
      }

      this.reconnectTimer = setTimeout(() => {
        this.connect();
      }, this.config.reconnectDelay);
    }
  }

  // ==========================================================================
  // V1.4: Chain Validation Methods
  // ==========================================================================

  /**
   * Validate an incoming chain-tracked event
   * Returns validation result with suggested action
   */
  validateChainEvent(chain: ChainTrackingMeta): ChainValidationResult {
    const { domain, update_id, prev_update_id } = chain;
    const currentChainState = this.chainStates[domain];

    // Check for cycle (update_id already processed)
    if (this.cycleDetectionSet.has(update_id)) {
      if (this.config.debug) {
        console.warn(`[UIStateReconciler] Cycle detected for update_id: ${update_id}`);
      }
      return {
        isValid: false,
        hasGap: false,
        hasCycle: true,
        depthExceeded: false,
        action: 'resync',
      };
    }

    // Validate chain continuity
    const result = validateChain(currentChainState, update_id, prev_update_id);

    if (this.config.debug && !result.isValid) {
      console.warn(`[UIStateReconciler] Chain validation failed for domain "${domain}":`, result);
    }

    return result;
  }

  /**
   * Process a valid chain-tracked event
   * Updates chain state and domain hashes
   */
  processChainEvent(chain: ChainTrackingMeta): void {
    const { domain, update_id, domain_hashes } = chain;

    // Update chain state
    this.chainStates[domain] = updateChainState(
      this.chainStates[domain],
      update_id,
      false // Not yet ACKed
    );

    // Track for cycle detection
    this.cycleDetectionSet.add(update_id);

    // Trim cycle detection set if too large
    if (this.cycleDetectionSet.size > MAX_CHAIN_DEPTH * 4) {
      const entries = Array.from(this.cycleDetectionSet);
      this.cycleDetectionSet = new Set(entries.slice(-MAX_CHAIN_DEPTH));
    }

    // Update domain hashes
    this.domainHashes = mergeDomainHashes(this.domainHashes, domain_hashes);

    if (this.config.debug) {
      console.log(`[UIStateReconciler] Processed chain event for domain "${domain}":`, {
        update_id,
        chainDepth: this.chainStates[domain].chainDepth,
      });
    }
  }

  /**
   * Mark an update as acknowledged
   */
  acknowledgeUpdate(domain: Domain, updateId: string): void {
    const chainState = this.chainStates[domain];
    if (chainState.lastUpdateId === updateId) {
      this.chainStates[domain] = {
        ...chainState,
        lastAckedId: updateId,
      };
    }
  }

  /**
   * Force refresh for a domain (resets chain state)
   */
  forceRefreshDomain(domain: Domain): void {
    if (this.config.debug) {
      console.log(`[UIStateReconciler] Force refresh for domain "${domain}"`);
    }

    this.chainStates[domain] = resetChainState();
    // Clear cycle detection for this domain's updates
    // (we can't easily filter by domain, so just clear if over threshold)
  }

  /**
   * Force refresh all domains
   */
  forceRefreshAll(): void {
    if (this.config.debug) {
      console.log('[UIStateReconciler] Force refresh all domains');
    }

    this.chainStates = { ...INITIAL_DOMAIN_CHAIN_STATES };
    this.cycleDetectionSet.clear();
  }

  /**
   * Get current chain states (for debugging/testing)
   */
  getChainStates(): DomainChainStates {
    return { ...this.chainStates };
  }

  /**
   * Get current domain hashes
   */
  getDomainHashes(): DomainHashes {
    return { ...this.domainHashes };
  }

  /**
   * Compare incoming hashes with current state
   */
  compareHashes(incoming: Partial<DomainHashes>) {
    return compareDomainHashes(this.domainHashes, incoming);
  }
}

/**
 * Export singleton instance
 */
export const reconciler = UIStateReconciler.getInstance();

/**
 * Hook for using reconciler in React components
 */
export function useReconciler(): {
  connect: () => void;
  disconnect: () => void;
  isConnected: boolean;
  forceReconcile: (state: BackendStateSnapshot) => void;
} {
  const instance = UIStateReconciler.getInstance();
  return {
    connect: () => instance.connect(),
    disconnect: () => instance.disconnect(),
    isConnected: instance.getConnectionStatus(),
    forceReconcile: (state) => instance.forceReconcile(state),
  };
}

export { UIStateReconciler };
