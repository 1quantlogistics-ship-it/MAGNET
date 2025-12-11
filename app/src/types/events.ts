/**
 * MAGNET UI Event Types
 *
 * Typed event payloads for all UI events.
 * Ensures type safety throughout the event system.
 */

import type { UISchemaVersion } from './schema-version';
import type { UIEvent, UIEventType, UIEventSource } from './contracts';
import { UI_SCHEMA_VERSION } from './schema-version';

// ============================================================================
// Event Payload Types
// ============================================================================

// --- User Events ---

export interface UserSelectPayload {
  targetId: string;
  targetType: 'component' | 'panel' | 'marker' | 'recommendation';
  previousId?: string;
  modifiers?: {
    shift?: boolean;
    ctrl?: boolean;
    alt?: boolean;
  };
}

export interface UserHoverPayload {
  targetId: string;
  targetType: 'component' | 'panel' | 'marker' | 'recommendation';
  position?: { x: number; y: number };
}

export interface UserClickPayload {
  targetId: string;
  targetType: string;
  position: { x: number; y: number };
  button: 'left' | 'right' | 'middle';
}

export interface UserInputPayload {
  inputId: string;
  value: string | number | boolean;
  previousValue?: string | number | boolean;
}

export interface UserDragPayload {
  targetId: string;
  phase: 'start' | 'move' | 'end';
  position: { x: number; y: number };
  delta?: { x: number; y: number };
}

export interface UserFocusPayload {
  targetId: string;
  focused: boolean;
}

// --- Backend Events ---

export interface BackendStateChangedPayload {
  changedPaths: string[];
  newValues: Record<string, unknown>;
  previousValues?: Record<string, unknown>;
  changeSource: 'user' | 'agent' | 'system';
}

export interface BackendPhaseCompletedPayload {
  previousPhase: string;
  currentPhase: string;
  completedAt: number;
  validationsPassed: boolean;
}

export interface BackendValidationResultPayload {
  validatorId: string;
  passed: boolean;
  errors?: Array<{
    code: string;
    message: string;
    path?: string;
    severity: 'error' | 'warning' | 'info';
  }>;
  warnings?: Array<{
    code: string;
    message: string;
    path?: string;
  }>;
  metrics?: Record<string, number>;
}

export interface BackendGeometryUpdatedPayload {
  geometryId: string;
  updateType: 'full' | 'partial' | 'lod_change';
  affectedMeshes: string[];
  newHash: string;
}

// --- Agent Events ---

export interface AgentMessagePayload {
  agentId: string;
  messageId: string;
  content: string;
  role: 'assistant' | 'system';
  isStreaming: boolean;
  isComplete: boolean;
}

export interface AgentThinkingPayload {
  agentId: string;
  thinkingText?: string;
  stage: 'analyzing' | 'computing' | 'generating' | 'validating';
}

export interface AgentCompletePayload {
  agentId: string;
  success: boolean;
  result?: unknown;
  duration: number;
}

export interface AgentErrorPayload {
  agentId: string;
  errorCode: string;
  errorMessage: string;
  recoverable: boolean;
}

// --- UI Events ---

export interface UIPanelFocusPayload {
  panelId: string;
  previousPanelId?: string;
}

export interface UIPanelBlurPayload {
  panelId: string;
}

export interface UIAnimationStartPayload {
  animationId: string;
  targetId: string;
  animationType: string;
  duration: number;
}

export interface UIAnimationCompletePayload {
  animationId: string;
  targetId: string;
  completed: boolean; // false if cancelled
}

export interface UIErrorPayload {
  errorId: string;
  errorCode: string;
  message: string;
  severity: 'critical' | 'error' | 'warning';
  componentId?: string;
  recoverable: boolean;
  suggestedAction?: string;
}

export interface UISnapshotCreatedPayload {
  snapshotId: string;
  timestamp: number;
  trigger: 'auto' | 'manual' | 'phase_change';
}

// --- Reconciler Events ---

export interface ReconcilerSyncStartPayload {
  syncId: string;
  sourceTimestamp: number;
  affectedStores: string[];
}

export interface ReconcilerSyncCompletePayload {
  syncId: string;
  duration: number;
  changesApplied: number;
  errors?: string[];
}

export interface ReconcilerConflictPayload {
  syncId: string;
  conflictType: 'version_mismatch' | 'concurrent_edit' | 'schema_incompatible';
  conflictPath: string;
  localValue: unknown;
  remoteValue: unknown;
  resolution: 'local_wins' | 'remote_wins' | 'merge' | 'manual';
}

// ============================================================================
// Event Type Map
// ============================================================================

/**
 * Maps event types to their payload types for type-safe dispatch/subscribe
 */
export interface UIEventPayloadMap {
  // User events
  'user:select': UserSelectPayload;
  'user:hover': UserHoverPayload;
  'user:click': UserClickPayload;
  'user:input': UserInputPayload;
  'user:drag': UserDragPayload;
  'user:focus': UserFocusPayload;
  // Backend events
  'backend:state_changed': BackendStateChangedPayload;
  'backend:phase_completed': BackendPhaseCompletedPayload;
  'backend:validation_result': BackendValidationResultPayload;
  'backend:geometry_updated': BackendGeometryUpdatedPayload;
  // Agent events
  'agent:message': AgentMessagePayload;
  'agent:thinking': AgentThinkingPayload;
  'agent:complete': AgentCompletePayload;
  'agent:error': AgentErrorPayload;
  // UI events
  'ui:panel_focus': UIPanelFocusPayload;
  'ui:panel_blur': UIPanelBlurPayload;
  'ui:animation_start': UIAnimationStartPayload;
  'ui:animation_complete': UIAnimationCompletePayload;
  'ui:error': UIErrorPayload;
  'ui:snapshot_created': UISnapshotCreatedPayload;
  // Reconciler events
  'reconciler:sync_start': ReconcilerSyncStartPayload;
  'reconciler:sync_complete': ReconcilerSyncCompletePayload;
  'reconciler:conflict': ReconcilerConflictPayload;
}

// ============================================================================
// Type-Safe Event Utilities
// ============================================================================

/**
 * Create a typed UI event
 */
export function createUIEvent<T extends UIEventType>(
  type: T,
  payload: UIEventPayloadMap[T],
  source: UIEventSource,
  correlationId?: string
): UIEvent<UIEventPayloadMap[T]> {
  return {
    type,
    payload,
    schema_version: UI_SCHEMA_VERSION,
    timestamp: Date.now(),
    source,
    correlationId,
  };
}

/**
 * Type guard to check if event matches expected type
 */
export function isEventType<T extends UIEventType>(
  event: UIEvent<unknown>,
  type: T
): event is UIEvent<UIEventPayloadMap[T]> {
  return event.type === type;
}

/**
 * Extract typed payload from event
 */
export function getEventPayload<T extends UIEventType>(
  event: UIEvent<unknown>,
  type: T
): UIEventPayloadMap[T] | null {
  if (isEventType(event, type)) {
    return event.payload;
  }
  return null;
}

// ============================================================================
// Event Categories
// ============================================================================

export const USER_EVENT_TYPES: UIEventType[] = [
  'user:select',
  'user:hover',
  'user:click',
  'user:input',
  'user:drag',
  'user:focus',
];

export const BACKEND_EVENT_TYPES: UIEventType[] = [
  'backend:state_changed',
  'backend:phase_completed',
  'backend:validation_result',
  'backend:geometry_updated',
];

export const AGENT_EVENT_TYPES: UIEventType[] = [
  'agent:message',
  'agent:thinking',
  'agent:complete',
  'agent:error',
];

export const UI_EVENT_TYPES: UIEventType[] = [
  'ui:panel_focus',
  'ui:panel_blur',
  'ui:animation_start',
  'ui:animation_complete',
  'ui:error',
  'ui:snapshot_created',
];

export const RECONCILER_EVENT_TYPES: UIEventType[] = [
  'reconciler:sync_start',
  'reconciler:sync_complete',
  'reconciler:conflict',
];

/**
 * Check if event type is user-initiated
 */
export function isUserEvent(type: UIEventType): boolean {
  return USER_EVENT_TYPES.includes(type);
}

/**
 * Check if event type is from backend
 */
export function isBackendEvent(type: UIEventType): boolean {
  return BACKEND_EVENT_TYPES.includes(type);
}

/**
 * Check if event type is from agent
 */
export function isAgentEvent(type: UIEventType): boolean {
  return AGENT_EVENT_TYPES.includes(type);
}

// ============================================================================
// Chain-Tracked Events (V1.4 Integration)
// ============================================================================

import type { Domain, DomainHashes } from './domainHashes';

/**
 * Chain tracking metadata for ordered event processing
 *
 * Every backend event includes chain tracking to ensure
 * events are processed in order and detect missing updates.
 */
export interface ChainTrackingMeta {
  /** Unique identifier for this update */
  update_id: string;
  /** ID of the previous update in the chain (null for first) */
  prev_update_id: string | null;
  /** Domain this update belongs to */
  domain: Domain;
  /** Current domain hashes after this update */
  domain_hashes: DomainHashes;
}

/**
 * Chain-tracked UI event
 *
 * Extends base UIEvent with chain tracking for backend events.
 */
export interface ChainTrackedUIEvent<T = unknown> extends UIEvent<T> {
  /** Chain tracking metadata (present for backend events) */
  chain?: ChainTrackingMeta;
}

/**
 * Backend event with required chain tracking
 */
export interface BackendChainEvent<T = unknown> extends UIEvent<T> {
  chain: ChainTrackingMeta;
}

/**
 * Create a chain-tracked event
 */
export function createChainTrackedEvent<T extends UIEventType>(
  type: T,
  payload: UIEventPayloadMap[T],
  chain: ChainTrackingMeta
): BackendChainEvent<UIEventPayloadMap[T]> {
  return {
    type,
    payload,
    schema_version: UI_SCHEMA_VERSION,
    timestamp: Date.now(),
    source: 'backend',
    chain,
  };
}

/**
 * Check if event has chain tracking
 */
export function hasChainTracking(
  event: UIEvent<unknown>
): event is BackendChainEvent<unknown> {
  return 'chain' in event && event.chain !== undefined;
}

/**
 * Extract domain from chain-tracked event
 */
export function getEventDomain(event: UIEvent<unknown>): Domain | null {
  if (hasChainTracking(event)) {
    return event.chain.domain;
  }
  return null;
}
