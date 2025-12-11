/**
 * MAGNET UI Transaction Types
 *
 * Type definitions for optimistic updates and rollback support.
 * Enables UI to update immediately while backend processes,
 * with full state restoration on failure.
 */

import type { DomainHashes, DomainChainStates } from './domainHashes';

// ============================================================================
// Transaction Status
// ============================================================================

/**
 * Transaction lifecycle states
 */
export type TransactionStatus =
  | 'pending'    // Transaction created, not yet submitted
  | 'optimistic' // Optimistic update applied to UI
  | 'submitted'  // Sent to backend, awaiting confirmation
  | 'confirmed'  // Backend confirmed success
  | 'failed'     // Backend rejected, needs rollback
  | 'rolled_back'; // Rollback completed

// ============================================================================
// Transaction Snapshot
// ============================================================================

/**
 * State snapshot for rollback support
 *
 * Captures all state needed to fully restore UI on failure.
 */
export interface TransactionSnapshot {
  /** Chain states at transaction start */
  chainStates: DomainChainStates;
  /** Domain hashes at transaction start */
  domainHashes: DomainHashes;
  /** Store snapshots by store name */
  storeSnapshots: Record<string, unknown>;
  /** Timestamp when snapshot was taken */
  timestamp: number;
}

// ============================================================================
// Transaction
// ============================================================================

/**
 * Transaction record
 */
export interface Transaction {
  /** Unique transaction ID */
  id: string;
  /** Human-readable description */
  description: string;
  /** Current status */
  status: TransactionStatus;
  /** Pre-transaction state snapshot */
  snapshot: TransactionSnapshot;
  /** Action type (for logging/debugging) */
  actionType: string;
  /** Action payload (for replay) */
  actionPayload: unknown;
  /** When transaction was created */
  createdAt: number;
  /** When transaction was last updated */
  updatedAt: number;
  /** Error message if failed */
  error?: string;
  /** Number of retry attempts */
  retryCount: number;
}

// ============================================================================
// Transaction Manager State
// ============================================================================

/**
 * Transaction manager state
 */
export interface TransactionManagerState {
  /** Active transactions by ID */
  transactions: Record<string, Transaction>;
  /** Currently active transaction ID (if any) */
  activeTransactionId: string | null;
  /** Transaction history (completed/failed) */
  history: Transaction[];
  /** Maximum history size */
  maxHistorySize: number;
}

// ============================================================================
// Transaction Events
// ============================================================================

/**
 * Transaction event types
 */
export type TransactionEventType =
  | 'transaction:created'
  | 'transaction:optimistic_applied'
  | 'transaction:submitted'
  | 'transaction:confirmed'
  | 'transaction:failed'
  | 'transaction:rolled_back';

/**
 * Transaction event payload
 */
export interface TransactionEventPayload {
  transactionId: string;
  status: TransactionStatus;
  error?: string;
  duration?: number;
}

// ============================================================================
// Rollback Configuration
// ============================================================================

/**
 * Rollback configuration
 */
export interface RollbackConfig {
  /** Whether to show user notification on rollback */
  notifyUser: boolean;
  /** Custom notification message */
  notificationMessage?: string;
  /** Whether to log rollback to console */
  logToConsole: boolean;
  /** Whether to retry failed transaction */
  autoRetry: boolean;
  /** Maximum retry attempts */
  maxRetries: number;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Default rollback configuration
 */
export const DEFAULT_ROLLBACK_CONFIG: RollbackConfig = {
  notifyUser: true,
  logToConsole: true,
  autoRetry: false,
  maxRetries: 0,
};

/**
 * Initial transaction manager state
 */
export const INITIAL_TRANSACTION_MANAGER_STATE: TransactionManagerState = {
  transactions: {},
  activeTransactionId: null,
  history: [],
  maxHistorySize: 50,
};
