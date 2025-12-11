/**
 * MAGNET UI Transaction Manager
 *
 * Manages optimistic updates with rollback support.
 * Enables UI to update immediately while backend processes,
 * with full state restoration on failure.
 */

import type {
  Transaction,
  TransactionStatus,
  TransactionSnapshot,
  TransactionManagerState,
  TransactionEventPayload,
  RollbackConfig,
} from '../types/transaction';
import {
  DEFAULT_ROLLBACK_CONFIG,
  INITIAL_TRANSACTION_MANAGER_STATE,
} from '../types/transaction';
import type { DomainHashes, DomainChainStates } from '../types/domainHashes';
import { INITIAL_DOMAIN_CHAIN_STATES } from '../types/domainHashes';
import { UIEventBus } from './UIEventBus';
import { createUIEvent } from '../types/events';
import { UI_SCHEMA_VERSION } from '../types/schema-version';

// ============================================================================
// Types
// ============================================================================

/**
 * Store snapshot function type
 */
type GetStoreSnapshot = (storeName: string) => unknown;

/**
 * Store restore function type
 */
type RestoreStoreSnapshot = (storeName: string, snapshot: unknown) => void;

/**
 * Transaction manager configuration
 */
interface TransactionManagerConfig {
  /** Enable debug logging */
  debug?: boolean;
  /** Maximum transaction history size */
  maxHistorySize?: number;
  /** Default rollback configuration */
  rollbackConfig?: Partial<RollbackConfig>;
  /** Store snapshot getter */
  getStoreSnapshot?: GetStoreSnapshot;
  /** Store restore function */
  restoreStoreSnapshot?: RestoreStoreSnapshot;
}

// ============================================================================
// UITransactionManager
// ============================================================================

/**
 * UITransactionManager - Optimistic updates with rollback
 */
class UITransactionManagerImpl {
  private state: TransactionManagerState;
  private config: Required<Omit<TransactionManagerConfig, 'getStoreSnapshot' | 'restoreStoreSnapshot'>>;
  private getStoreSnapshot: GetStoreSnapshot;
  private restoreStoreSnapshot: RestoreStoreSnapshot;
  private chainStatesGetter: (() => DomainChainStates) | null = null;
  private domainHashesGetter: (() => DomainHashes) | null = null;

  constructor(config: TransactionManagerConfig = {}) {
    // Deep copy initial state to avoid shared references across instances
    this.state = {
      transactions: {},
      activeTransactionId: null,
      history: [],
      maxHistorySize: config.maxHistorySize ?? INITIAL_TRANSACTION_MANAGER_STATE.maxHistorySize,
    };
    this.config = {
      debug: config.debug ?? process.env.NODE_ENV === 'development',
      maxHistorySize: config.maxHistorySize ?? 50,
      rollbackConfig: { ...DEFAULT_ROLLBACK_CONFIG, ...config.rollbackConfig },
    };

    // Default store snapshot functions (no-op)
    this.getStoreSnapshot = config.getStoreSnapshot ?? (() => null);
    this.restoreStoreSnapshot = config.restoreStoreSnapshot ?? (() => {});
  }

  /**
   * Set chain state getter (from reconciler)
   */
  setChainStatesGetter(getter: () => DomainChainStates): void {
    this.chainStatesGetter = getter;
  }

  /**
   * Set domain hashes getter (from reconciler)
   */
  setDomainHashesGetter(getter: () => DomainHashes): void {
    this.domainHashesGetter = getter;
  }

  /**
   * Set store snapshot functions
   */
  setStoreHandlers(
    getSnapshot: GetStoreSnapshot,
    restoreSnapshot: RestoreStoreSnapshot
  ): void {
    this.getStoreSnapshot = getSnapshot;
    this.restoreStoreSnapshot = restoreSnapshot;
  }

  /**
   * Begin a new transaction
   */
  begin(
    description: string,
    actionType: string,
    actionPayload: unknown,
    storeNames: string[] = []
  ): string {
    // Create snapshot
    const snapshot = this.createSnapshot(storeNames);

    // Generate transaction ID
    const id = `tx_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const transaction: Transaction = {
      id,
      description,
      status: 'pending',
      snapshot,
      actionType,
      actionPayload,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      retryCount: 0,
    };

    this.state.transactions[id] = transaction;
    this.state.activeTransactionId = id;

    if (this.config.debug) {
      console.log(`[UITransactionManager] Begin transaction: ${id}`, { description, actionType });
    }

    this.emitEvent('transaction:created', id, 'pending');
    return id;
  }

  /**
   * Mark transaction as optimistically applied
   */
  markOptimistic(transactionId: string): void {
    const tx = this.state.transactions[transactionId];
    if (!tx) return;

    tx.status = 'optimistic';
    tx.updatedAt = Date.now();

    if (this.config.debug) {
      console.log(`[UITransactionManager] Optimistic update applied: ${transactionId}`);
    }

    this.emitEvent('transaction:optimistic_applied', transactionId, 'optimistic');
  }

  /**
   * Mark transaction as submitted to backend
   */
  markSubmitted(transactionId: string): void {
    const tx = this.state.transactions[transactionId];
    if (!tx) return;

    tx.status = 'submitted';
    tx.updatedAt = Date.now();

    if (this.config.debug) {
      console.log(`[UITransactionManager] Transaction submitted: ${transactionId}`);
    }

    this.emitEvent('transaction:submitted', transactionId, 'submitted');
  }

  /**
   * Confirm transaction success
   */
  confirm(transactionId: string): void {
    const tx = this.state.transactions[transactionId];
    if (!tx) return;

    const duration = Date.now() - tx.createdAt;
    tx.status = 'confirmed';
    tx.updatedAt = Date.now();

    // Move to history
    this.addToHistory(tx);
    delete this.state.transactions[transactionId];

    if (this.state.activeTransactionId === transactionId) {
      this.state.activeTransactionId = null;
    }

    if (this.config.debug) {
      console.log(`[UITransactionManager] Transaction confirmed: ${transactionId} (${duration}ms)`);
    }

    this.emitEvent('transaction:confirmed', transactionId, 'confirmed', undefined, duration);
  }

  /**
   * Mark transaction as failed and trigger rollback
   */
  fail(transactionId: string, error: string, rollbackConfig?: Partial<RollbackConfig>): void {
    const tx = this.state.transactions[transactionId];
    if (!tx) return;

    tx.status = 'failed';
    tx.error = error;
    tx.updatedAt = Date.now();

    if (this.config.debug) {
      console.error(`[UITransactionManager] Transaction failed: ${transactionId}`, error);
    }

    this.emitEvent('transaction:failed', transactionId, 'failed', error);

    // Perform rollback
    const config = { ...this.config.rollbackConfig, ...rollbackConfig };
    this.rollback(transactionId, config);
  }

  /**
   * Rollback a failed transaction
   */
  rollback(transactionId: string, config: RollbackConfig = this.config.rollbackConfig): void {
    const tx = this.state.transactions[transactionId];
    if (!tx) return;

    const { snapshot } = tx;

    if (config.logToConsole) {
      console.log(`[UITransactionManager] Rolling back transaction: ${transactionId}`);
    }

    // Restore store snapshots
    for (const [storeName, storeSnapshot] of Object.entries(snapshot.storeSnapshots)) {
      try {
        this.restoreStoreSnapshot(storeName, storeSnapshot);
      } catch (err) {
        console.error(`[UITransactionManager] Failed to restore store "${storeName}":`, err);
      }
    }

    tx.status = 'rolled_back';
    tx.updatedAt = Date.now();

    // Move to history
    this.addToHistory(tx);
    delete this.state.transactions[transactionId];

    if (this.state.activeTransactionId === transactionId) {
      this.state.activeTransactionId = null;
    }

    this.emitEvent('transaction:rolled_back', transactionId, 'rolled_back');

    // Notify user if configured
    if (config.notifyUser) {
      const message = config.notificationMessage || `Action failed: ${tx.error}`;
      // Emit error event for UI to display
      UIEventBus.emit(createUIEvent('ui:error', {
        errorId: transactionId,
        errorCode: 'TRANSACTION_ROLLBACK',
        message,
        severity: 'warning',
        recoverable: true,
        suggestedAction: 'Please try again',
      }, 'system'));
    }
  }

  /**
   * Get active transaction
   */
  getActiveTransaction(): Transaction | null {
    if (!this.state.activeTransactionId) return null;
    return this.state.transactions[this.state.activeTransactionId] || null;
  }

  /**
   * Get transaction by ID
   */
  getTransaction(transactionId: string): Transaction | null {
    return this.state.transactions[transactionId] || null;
  }

  /**
   * Get transaction history
   */
  getHistory(): Transaction[] {
    return [...this.state.history];
  }

  /**
   * Check if there are pending transactions
   */
  hasPendingTransactions(): boolean {
    return Object.keys(this.state.transactions).length > 0;
  }

  /**
   * Clear all pending transactions (cancel without rollback)
   */
  clearPending(): void {
    for (const tx of Object.values(this.state.transactions)) {
      this.addToHistory({ ...tx, status: 'failed', error: 'Cancelled' });
    }
    this.state.transactions = {};
    this.state.activeTransactionId = null;
  }

  /**
   * Create state snapshot
   */
  private createSnapshot(storeNames: string[]): TransactionSnapshot {
    const storeSnapshots: Record<string, unknown> = {};

    for (const name of storeNames) {
      storeSnapshots[name] = this.getStoreSnapshot(name);
    }

    return {
      chainStates: this.chainStatesGetter?.() ?? { ...INITIAL_DOMAIN_CHAIN_STATES },
      domainHashes: this.domainHashesGetter?.() ?? {
        geometryHash: '',
        arrangementHash: '',
        routingHash: '',
        phaseHash: '',
      },
      storeSnapshots,
      timestamp: Date.now(),
    };
  }

  /**
   * Add transaction to history
   */
  private addToHistory(tx: Transaction): void {
    this.state.history.push(tx);

    // Trim history if needed
    if (this.state.history.length > this.state.maxHistorySize) {
      this.state.history = this.state.history.slice(-this.state.maxHistorySize);
    }
  }

  /**
   * Emit transaction event
   */
  private emitEvent(
    type: string,
    transactionId: string,
    status: TransactionStatus,
    error?: string,
    duration?: number
  ): void {
    const payload: TransactionEventPayload = {
      transactionId,
      status,
      error,
      duration,
    };

    UIEventBus.emit({
      type: type as any,
      payload,
      schema_version: UI_SCHEMA_VERSION,
      timestamp: Date.now(),
      source: 'system',
    });
  }
}

// ============================================================================
// Exports
// ============================================================================

/**
 * Singleton transaction manager instance
 */
export const transactionManager = new UITransactionManagerImpl({
  debug: process.env.NODE_ENV === 'development',
});

/**
 * Hook for using transaction manager in React components
 */
export function useTransactionManager() {
  return transactionManager;
}

export { UITransactionManagerImpl };
