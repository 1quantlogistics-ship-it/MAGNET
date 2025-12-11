/**
 * MAGNET UI Contracts
 *
 * Core architectural contracts that enforce:
 * - FM3: UIOrchestrator as authoritative message broker
 * - FM4: Lifecycle-aware component contracts
 * - FM2: Domain-bounded store contracts
 */

import type { UISchemaVersion } from './schema-version';

// ============================================================================
// UIOrchestrator Contract (FM3 Compliance)
// ============================================================================

/**
 * Event types that flow through the UIOrchestrator
 */
export type UIEventType =
  // User-initiated events
  | 'user:select'
  | 'user:hover'
  | 'user:click'
  | 'user:input'
  | 'user:drag'
  | 'user:focus'
  // Backend sync events
  | 'backend:state_changed'
  | 'backend:phase_completed'
  | 'backend:validation_result'
  | 'backend:geometry_updated'
  // Agent events
  | 'agent:message'
  | 'agent:thinking'
  | 'agent:complete'
  | 'agent:error'
  // UI lifecycle events
  | 'ui:panel_focus'
  | 'ui:panel_blur'
  | 'ui:animation_start'
  | 'ui:animation_complete'
  | 'ui:error'
  | 'ui:snapshot_created'
  // Reconciliation events
  | 'reconciler:sync_start'
  | 'reconciler:sync_complete'
  | 'reconciler:conflict';

/**
 * Handler function type for UI events
 */
export type UIEventHandler<T = unknown> = (event: UIEvent<T>) => void | Promise<void>;

/**
 * Unsubscribe function returned by subscribe
 */
export type Unsubscribe = () => void;

/**
 * Backend state snapshot for reconciliation
 */
export interface BackendStateSnapshot {
  schema_version: UISchemaVersion;
  timestamp: number;
  designState: Record<string, unknown>;
  phase: string;
  validationResults?: Record<string, unknown>;
  geometryHash?: string;
}

/**
 * UIOrchestrator Contract
 *
 * All UI mutations MUST flow through the orchestrator.
 * Components do NOT write directly to stores.
 */
export interface UIOrchestratorContract {
  /**
   * Subscribe to specific event types
   * @param eventType - The event type to listen for
   * @param handler - Callback function for the event
   * @returns Unsubscribe function
   */
  subscribe: <T = unknown>(eventType: UIEventType, handler: UIEventHandler<T>) => Unsubscribe;

  /**
   * Subscribe to multiple event types with a single handler
   */
  subscribeMany: <T = unknown>(eventTypes: UIEventType[], handler: UIEventHandler<T>) => Unsubscribe;

  /**
   * Dispatch an event through the orchestrator
   * This is the ONLY way to mutate UI state
   */
  dispatch: <T = unknown>(event: UIEvent<T>) => void;

  /**
   * Dispatch and wait for all handlers to complete
   */
  dispatchAsync: <T = unknown>(event: UIEvent<T>) => Promise<void>;

  /**
   * Reconcile UI state with backend state
   * Called by UIStateReconciler when backend emits state changes
   */
  reconcile: (backendState: BackendStateSnapshot) => void;

  /**
   * Reset all UI state to initial values
   * Used on session end or critical errors
   */
  reset: () => void;

  /**
   * Get current orchestrator status
   */
  getStatus: () => OrchestratorStatus;
}

export interface OrchestratorStatus {
  isReconciling: boolean;
  pendingEvents: number;
  lastReconcileTimestamp: number | null;
  subscriberCount: number;
}

// ============================================================================
// UIStore Contract (FM2 Compliance)
// ============================================================================

/**
 * UIStore Contract
 *
 * Enforces domain-bounded stores with explicit read/write separation.
 * Stores cannot be mutated directly - all changes flow through orchestrator.
 */
export interface UIStoreContract<TReadOnly, TReadWrite = Partial<TReadOnly>> {
  /**
   * Read-only derived/computed state
   * Components can freely read but NEVER mutate
   */
  readonly readOnly: TReadOnly;

  /**
   * Read-write state (internal use only)
   * Mutations only through reconcile() or via orchestrator dispatch
   */
  readonly readWrite: TReadWrite;

  /**
   * Reconcile store state from authoritative source
   * Called by orchestrator during backend sync
   */
  reconcile: (source: Partial<TReadOnly>) => void;

  /**
   * Reset store to initial state
   */
  reset: () => void;

  /**
   * Get current state snapshot for debugging/persistence
   */
  getSnapshot: () => TReadOnly;

  /**
   * Check if store has unsaved local changes
   */
  isDirty: () => boolean;
}

// ============================================================================
// Component Contract (FM4 Compliance)
// ============================================================================

/**
 * Lifecycle callbacks for components
 */
export interface ComponentLifecycle {
  /**
   * Called when component mounts
   */
  onMount?: () => void;

  /**
   * Called when component unmounts
   */
  onUnmount?: () => void;

  /**
   * Called when component visibility changes
   * @param visible - Whether component is now visible
   */
  onVisibilityChange?: (visible: boolean) => void;

  /**
   * Called when animation state changes
   * @param animating - Whether component is animating
   */
  onAnimationStateChange?: (animating: boolean) => void;
}

/**
 * Component Contract
 *
 * Ensures components declare their props, events, and lifecycle hooks.
 * Used by Bravo to implement module components with consistent interfaces.
 */
export interface ComponentContract<
  TProps extends Record<string, unknown>,
  TEvents extends Record<string, unknown> = Record<string, never>
> {
  /**
   * Component props interface
   */
  props: TProps;

  /**
   * Events emitted by this component
   */
  events: TEvents;

  /**
   * Lifecycle hooks
   */
  lifecycle: ComponentLifecycle;

  /**
   * Display name for debugging
   */
  displayName: string;
}

// ============================================================================
// UIEvent Interface
// ============================================================================

/**
 * UIEvent
 *
 * All events flowing through the UIOrchestrator use this structure.
 * Schema-versioned for reconciliation compatibility.
 */
export interface UIEvent<T = unknown> {
  /**
   * Event type identifier
   */
  type: UIEventType;

  /**
   * Event payload
   */
  payload: T;

  /**
   * Schema version for compatibility checking
   */
  schema_version: UISchemaVersion;

  /**
   * Unix timestamp when event was created
   */
  timestamp: number;

  /**
   * Source of the event
   */
  source: UIEventSource;

  /**
   * Optional correlation ID for tracking related events
   */
  correlationId?: string;

  /**
   * Optional metadata
   */
  meta?: Record<string, unknown>;
}

export type UIEventSource =
  | 'user'        // User interaction
  | 'agent'       // AI agent response
  | 'backend'     // Backend state change
  | 'reconciler'  // Reconciliation process
  | 'system';     // Internal system event

// ============================================================================
// Store Factory Types
// ============================================================================

/**
 * Configuration for creating domain-bounded stores
 */
export interface StoreConfig<TState> {
  /**
   * Unique store identifier
   */
  name: string;

  /**
   * Initial state
   */
  initialState: TState;

  /**
   * Fields that are read-only (derived from backend)
   */
  readOnlyFields: (keyof TState)[];

  /**
   * Fields that can be locally modified
   */
  readWriteFields: (keyof TState)[];

  /**
   * Optional reconciliation transformer
   */
  reconcileTransform?: (backendState: Partial<TState>, currentState: TState) => TState;
}

// ============================================================================
// Animation Scheduler Types
// ============================================================================

/**
 * Animation priority levels
 */
export type AnimationPriority = 'critical' | 'high' | 'normal' | 'low';

/**
 * Animation task registered with scheduler
 */
export interface AnimationTask {
  id: string;
  priority: AnimationPriority;
  callback: (deltaTime: number) => boolean; // Returns true when complete
  startTime: number;
  duration?: number;
}

/**
 * Animation Scheduler Contract
 */
export interface AnimationSchedulerContract {
  /**
   * Register an animation task
   */
  register: (task: Omit<AnimationTask, 'startTime'>) => Unsubscribe;

  /**
   * Pause all animations
   */
  pause: () => void;

  /**
   * Resume animations
   */
  resume: () => void;

  /**
   * Cancel a specific animation
   */
  cancel: (taskId: string) => void;

  /**
   * Cancel all animations
   */
  cancelAll: () => void;

  /**
   * Check if any animations are running
   */
  isAnimating: () => boolean;
}
