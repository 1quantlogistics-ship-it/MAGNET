/**
 * MAGNET UI Transaction Manager Tests
 *
 * Tests for optimistic updates and rollback functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UITransactionManagerImpl } from '../../systems/UITransactionManager';

describe('UITransactionManager', () => {
  let transactionManager: UITransactionManagerImpl;
  let mockGetSnapshot: ReturnType<typeof vi.fn>;
  let mockRestoreSnapshot: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockGetSnapshot = vi.fn((storeName: string) => ({ storeName, data: 'original' }));
    mockRestoreSnapshot = vi.fn();

    transactionManager = new UITransactionManagerImpl({
      debug: false,
    });

    transactionManager.setStoreHandlers(mockGetSnapshot, mockRestoreSnapshot);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Transaction Lifecycle', () => {
    it('should begin a transaction and return ID', () => {
      const txId = transactionManager.begin(
        'Test transaction',
        'TEST_ACTION',
        { value: 1 },
        ['testStore']
      );

      expect(txId).toMatch(/^tx_\d+_[a-z0-9]+$/);
      expect(transactionManager.getActiveTransaction()).not.toBeNull();
    });

    it('should snapshot stores on begin', () => {
      transactionManager.begin(
        'Test transaction',
        'TEST_ACTION',
        {},
        ['store1', 'store2']
      );

      expect(mockGetSnapshot).toHaveBeenCalledTimes(2);
      expect(mockGetSnapshot).toHaveBeenCalledWith('store1');
      expect(mockGetSnapshot).toHaveBeenCalledWith('store2');
    });

    it('should mark transaction as optimistic', () => {
      const txId = transactionManager.begin('Test', 'ACTION', {});
      transactionManager.markOptimistic(txId);

      const tx = transactionManager.getTransaction(txId);
      expect(tx?.status).toBe('optimistic');
    });

    it('should mark transaction as submitted', () => {
      const txId = transactionManager.begin('Test', 'ACTION', {});
      transactionManager.markSubmitted(txId);

      const tx = transactionManager.getTransaction(txId);
      expect(tx?.status).toBe('submitted');
    });

    it('should confirm transaction and move to history', () => {
      const txId = transactionManager.begin('Test', 'ACTION', {});
      transactionManager.confirm(txId);

      expect(transactionManager.getTransaction(txId)).toBeNull();
      expect(transactionManager.getActiveTransaction()).toBeNull();

      const history = transactionManager.getHistory();
      expect(history.length).toBe(1);
      expect(history[0].status).toBe('confirmed');
    });
  });

  describe('Rollback', () => {
    it('should restore store snapshots on fail', () => {
      const txId = transactionManager.begin(
        'Test transaction',
        'TEST_ACTION',
        {},
        ['store1', 'store2']
      );

      transactionManager.fail(txId, 'Test error');

      expect(mockRestoreSnapshot).toHaveBeenCalledTimes(2);
      expect(mockRestoreSnapshot).toHaveBeenCalledWith('store1', { storeName: 'store1', data: 'original' });
      expect(mockRestoreSnapshot).toHaveBeenCalledWith('store2', { storeName: 'store2', data: 'original' });
    });

    it('should mark transaction as rolled_back after fail', () => {
      const txId = transactionManager.begin('Test', 'ACTION', {}, ['store']);
      transactionManager.fail(txId, 'Error');

      const history = transactionManager.getHistory();
      const tx = history.find(t => t.id === txId);

      expect(tx?.status).toBe('rolled_back');
      expect(tx?.error).toBe('Error');
    });

    it('should clear active transaction after rollback', () => {
      const txId = transactionManager.begin('Test', 'ACTION', {});
      transactionManager.fail(txId, 'Error');

      expect(transactionManager.getActiveTransaction()).toBeNull();
    });

    it('should handle missing transaction gracefully', () => {
      // Should not throw
      transactionManager.fail('nonexistent', 'Error');
      transactionManager.confirm('nonexistent');
      transactionManager.rollback('nonexistent');
    });
  });

  describe('Pending Transactions', () => {
    it('should report pending transactions correctly', () => {
      expect(transactionManager.hasPendingTransactions()).toBe(false);

      transactionManager.begin('Test', 'ACTION', {});

      expect(transactionManager.hasPendingTransactions()).toBe(true);
    });

    it('should clear all pending transactions', () => {
      transactionManager.begin('Test 1', 'ACTION', {});
      transactionManager.begin('Test 2', 'ACTION', {});

      transactionManager.clearPending();

      expect(transactionManager.hasPendingTransactions()).toBe(false);
      expect(transactionManager.getHistory().length).toBe(2);
    });
  });

  describe('History Management', () => {
    it('should maintain history up to max size', () => {
      const manager = new UITransactionManagerImpl({
        debug: false,
        maxHistorySize: 3,
      });

      for (let i = 0; i < 5; i++) {
        const txId = manager.begin(`Test ${i}`, 'ACTION', {});
        manager.confirm(txId);
      }

      const history = manager.getHistory();
      expect(history.length).toBe(3);
    });

    it('should track duration on confirm', () => {
      const txId = transactionManager.begin('Test', 'ACTION', {});

      transactionManager.confirm(txId);

      const history = transactionManager.getHistory();
      expect(history[0].updatedAt).toBeGreaterThanOrEqual(history[0].createdAt);
    });
  });
});
