/**
 * MAGNET UI Intent Store
 * Module 63.1: Intent preview/apply state management
 *
 * Stores pending intent preview for apply flow.
 */

import { createStore } from '../contracts/StoreFactory';
import { UI_SCHEMA_VERSION } from '../../types/schema-version';
import type { UISchemaVersion } from '../../types/schema-version';
import type {
  IntentPreviewResponse,
  ApplyResult,
} from '../../types/intent';

// ============================================================================
// Types
// ============================================================================

/**
 * Intent flow status
 */
export type IntentStatus =
  | 'idle'
  | 'previewing'
  | 'preview_ready'
  | 'applying'
  | 'applied'
  | 'error';

/**
 * Intent read-only state
 */
export interface IntentReadOnlyState {
  schema_version: UISchemaVersion;
}

/**
 * Intent read-write state
 */
export interface IntentReadWriteState {
  /** Current intent status */
  status: IntentStatus;

  /** Pending preview response (stored for apply) */
  pendingPreview: IntentPreviewResponse | null;

  /** Last apply result */
  lastApplyResult: ApplyResult | null;

  /** Error message if status is 'error' */
  errorMessage: string | null;

  /** Original input text */
  inputText: string;
}

/**
 * Combined intent store state
 */
export interface IntentStoreState extends IntentReadOnlyState, IntentReadWriteState {}

// ============================================================================
// Initial State
// ============================================================================

const initialIntentState: IntentStoreState = {
  schema_version: UI_SCHEMA_VERSION,
  status: 'idle',
  pendingPreview: null,
  lastApplyResult: null,
  errorMessage: null,
  inputText: '',
};

// ============================================================================
// Store
// ============================================================================

/**
 * Intent store instance
 */
export const intentStore = createStore<IntentStoreState>({
  name: 'intent',
  initialState: initialIntentState,
  readOnlyFields: ['schema_version'],
  readWriteFields: [
    'status',
    'pendingPreview',
    'lastApplyResult',
    'errorMessage',
    'inputText',
  ],
});

// ============================================================================
// Actions
// ============================================================================

/**
 * Start preview - set status to previewing
 */
export function startPreview(text: string): void {
  intentStore.getState()._update(() => ({
    status: 'previewing',
    inputText: text,
    pendingPreview: null,
    errorMessage: null,
  }));
}

/**
 * Set preview result
 */
export function setPreviewResult(preview: IntentPreviewResponse): void {
  intentStore.getState()._update(() => ({
    status: 'preview_ready',
    pendingPreview: preview,
    errorMessage: null,
  }));
}

/**
 * Set preview error
 */
export function setPreviewError(message: string): void {
  intentStore.getState()._update(() => ({
    status: 'error',
    pendingPreview: null,
    errorMessage: message,
  }));
}

/**
 * Start apply - set status to applying
 */
export function startApply(): void {
  intentStore.getState()._update(() => ({
    status: 'applying',
    errorMessage: null,
  }));
}

/**
 * Set apply result
 */
export function setApplyResult(result: ApplyResult): void {
  intentStore.getState()._update(() => ({
    status: 'applied',
    lastApplyResult: result,
    pendingPreview: null,
    errorMessage: null,
  }));
}

/**
 * Set apply error
 */
export function setApplyError(message: string): void {
  intentStore.getState()._update(() => ({
    status: 'error',
    errorMessage: message,
  }));
}

/**
 * Cancel pending preview
 */
export function cancelIntent(): void {
  intentStore.getState()._update(() => ({
    status: 'idle',
    pendingPreview: null,
    errorMessage: null,
    inputText: '',
  }));
}

/**
 * Reset intent store to initial state
 */
export function resetIntent(): void {
  intentStore.getState().reset();
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get current intent status
 */
export function getIntentStatus(): IntentStatus {
  return intentStore.getState()._internal.state.status;
}

/**
 * Get pending preview
 */
export function getPendingPreview(): IntentPreviewResponse | null {
  return intentStore.getState()._internal.state.pendingPreview;
}

/**
 * Get last apply result
 */
export function getLastApplyResult(): ApplyResult | null {
  return intentStore.getState()._internal.state.lastApplyResult;
}

/**
 * Get error message
 */
export function getIntentError(): string | null {
  return intentStore.getState()._internal.state.errorMessage;
}

/**
 * Check if preview has approved actions
 */
export function hasApprovedActions(): boolean {
  const preview = getPendingPreview();
  return preview !== null && preview.approved.length > 0;
}

/**
 * Check if preview has rejected actions
 */
export function hasRejectedActions(): boolean {
  const preview = getPendingPreview();
  return preview !== null && preview.rejected.length > 0;
}

/**
 * Check if can apply (preview ready with approved actions)
 */
export function canApply(): boolean {
  const status = getIntentStatus();
  return status === 'preview_ready' && hasApprovedActions();
}
