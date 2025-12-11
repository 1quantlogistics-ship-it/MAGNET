/**
 * MAGNET UI Clarification Store
 *
 * Zustand store for managing AI-initiated clarification requests.
 * Queue-based system with priority processing.
 */

import type {
  ClarificationRequest,
  ClarificationStoreState,
  ClarificationStoreActions,
  ClarificationStatus,
  ClarificationResolvedEventDetail,
  ClarificationType,
  ClarificationPriority,
  ClarificationOption,
  ClarificationField,
  ScreenPosition,
  WorldPosition,
  INITIAL_CLARIFICATION_STATE,
} from '../../types/clarification';
import { SCHEMA_VERSION } from '../../types/schema-version';
import { createStore } from '../contracts/StoreFactory';
import { generateId } from '../../types/common';

// Priority ordering for queue processing
const PRIORITY_ORDER: Record<ClarificationPriority, number> = {
  required: 0,
  recommended: 1,
  optional: 2,
};

/**
 * Create clarification store with factory
 */
export const clarificationStore = createStore<ClarificationStoreState>({
  name: 'clarification',
  initialState: {
    queue: [],
    activeRequest: null,
    history: [],
    activeContextualRequest: null,
    schema_version: SCHEMA_VERSION,
  },
  readOnlyFields: ['queue', 'activeRequest', 'history', 'activeContextualRequest', 'schema_version'],
  readWriteFields: [],
});

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get current store state
 * Uses getReadOnly() function instead of readOnly property due to Zustand getter limitations
 */
export function getClarificationState(): ClarificationStoreState {
  return clarificationStore.getState().getReadOnly();
}

/**
 * Get active clarification request
 */
export function getActiveRequest(): ClarificationRequest | null {
  return getClarificationState().activeRequest;
}

/**
 * Get queue length
 */
export function getQueueLength(): number {
  return getClarificationState().queue.length;
}

/**
 * Get active contextual request (for 3D selection)
 */
export function getActiveContextualRequest(): ClarificationRequest | null {
  return getClarificationState().activeContextualRequest;
}

/**
 * Check if any clarification is active
 */
export function hasClarificationActive(): boolean {
  const state = getClarificationState();
  return state.activeRequest !== null || state.activeContextualRequest !== null;
}

// ============================================================================
// Actions
// ============================================================================

/**
 * Add a clarification request to the queue
 * Returns the generated request ID
 */
export function requestClarification(
  request: Omit<ClarificationRequest, 'id' | 'status' | 'timestamp' | 'schema_version'>
): string {
  const id = generateId('clar');

  const fullRequest: ClarificationRequest = {
    ...request,
    id,
    status: 'pending',
    timestamp: Date.now(),
    schema_version: SCHEMA_VERSION,
  };

  clarificationStore.getState()._update((state) => {
    // Add to queue
    const newQueue = [...state.queue, fullRequest];

    // Sort by priority
    newQueue.sort((a, b) =>
      PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
    );

    return { queue: newQueue };
  });

  // Process queue if no active request
  processQueue();

  return id;
}

/**
 * Process the queue - activate next request if none active
 * Contextual and regular requests can be active simultaneously
 */
function processQueue(): void {
  const state = getClarificationState();

  // Get next from queue
  if (state.queue.length === 0) return;

  const nextRequest = state.queue[0];

  // Contextual requests have their own slot and can be active alongside regular requests
  if (nextRequest.type === 'contextual') {
    // Skip if already has active contextual request
    if (state.activeContextualRequest !== null) return;

    clarificationStore.getState()._update((state) => ({
      queue: state.queue.slice(1),
      activeContextualRequest: nextRequest,
    }));

    // Continue processing to potentially activate a regular request too
    processQueue();
    return;
  }

  // Regular requests - skip if already has active request
  if (state.activeRequest !== null) return;

  clarificationStore.getState()._update((state) => ({
    queue: state.queue.slice(1),
    activeRequest: nextRequest,
  }));

  // Continue processing to potentially activate a contextual request too
  processQueue();
}

/**
 * Respond to the active clarification
 */
export function respondToClarification(requestId: string, response: unknown): void {
  resolveRequest(requestId, 'answered', response);
}

/**
 * Skip the active clarification (use default value)
 */
export function skipClarification(requestId: string): void {
  const state = getClarificationState();
  const request = state.activeRequest ?? state.activeContextualRequest;

  if (!request || request.id !== requestId) {
    console.warn(`Cannot skip clarification: request ${requestId} not found or not active`);
    return;
  }

  resolveRequest(requestId, 'skipped', request.defaultValue);
}

/**
 * Mark request as expired (timeout)
 */
export function expireClarification(requestId: string): void {
  const state = getClarificationState();
  const request = state.activeRequest ?? state.activeContextualRequest;

  if (!request || request.id !== requestId) return;

  resolveRequest(requestId, 'expired', request.defaultValue);
}

/**
 * Internal: resolve a request with final status
 */
function resolveRequest(
  requestId: string,
  status: ClarificationStatus,
  response: unknown
): void {
  const state = getClarificationState();

  // Find the request
  const isActive = state.activeRequest?.id === requestId;
  const isContextual = state.activeContextualRequest?.id === requestId;

  if (!isActive && !isContextual) {
    console.warn(`Cannot resolve clarification: request ${requestId} not active`);
    return;
  }

  const request = isActive ? state.activeRequest! : state.activeContextualRequest!;

  // Create resolved request
  const resolvedRequest: ClarificationRequest = {
    ...request,
    status,
    response,
  };

  // Update store
  clarificationStore.getState()._update((state) => ({
    activeRequest: isActive ? null : state.activeRequest,
    activeContextualRequest: isContextual ? null : state.activeContextualRequest,
    history: [...state.history, resolvedRequest],
  }));

  // Dispatch event for listeners
  dispatchResolvedEvent(resolvedRequest);

  // Process next in queue
  processQueue();
}

/**
 * Dispatch clarification:resolved custom event
 */
function dispatchResolvedEvent(request: ClarificationRequest): void {
  const detail: ClarificationResolvedEventDetail = {
    requestId: request.id,
    status: request.status,
    response: request.response,
  };

  const event = new CustomEvent('clarification:resolved', { detail });
  window.dispatchEvent(event);
}

/**
 * Reset the store to initial state
 */
export function resetClarificationStore(): void {
  clarificationStore.getState().reset();
}

/**
 * Clear history only
 */
export function clearClarificationHistory(): void {
  clarificationStore.getState()._update(() => ({
    history: [],
  }));
}

// ============================================================================
// Subscription
// ============================================================================

/**
 * Subscribe to store changes
 */
export function subscribeToClarification(
  listener: (state: ClarificationStoreState) => void
): () => void {
  return clarificationStore.subscribe((fullState) => {
    listener(fullState.getReadOnly());
  });
}

// ============================================================================
// Export store for direct access
// ============================================================================

export default clarificationStore;
