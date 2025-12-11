/**
 * MAGNET UI State Reconciler Tests
 *
 * Tests for chain validation and cycle detection.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UIStateReconciler } from '../../systems/UIStateReconciler';
import type { ChainTrackingMeta } from '../../types/events';
import type { Domain, DomainHashes } from '../../types/domainHashes';

describe('UIStateReconciler', () => {
  let reconciler: UIStateReconciler;

  beforeEach(() => {
    // Get fresh instance - note: singleton, so we need to reset
    reconciler = UIStateReconciler.getInstance();
    reconciler.forceRefreshAll();
  });

  afterEach(() => {
    reconciler.disconnect();
  });

  describe('Chain Validation', () => {
    it('should validate first event in chain (null prev_update_id)', () => {
      const chain: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: {
          geometryHash: 'hash1',
          arrangementHash: '',
          routingHash: '',
          phaseHash: '',
        },
      };

      const result = reconciler.validateChainEvent(chain);

      expect(result.isValid).toBe(true);
      expect(result.hasGap).toBe(false);
      expect(result.hasCycle).toBe(false);
    });

    it('should validate continuous chain', () => {
      // First event
      const chain1: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: 'hash1', arrangementHash: '', routingHash: '', phaseHash: '' },
      };

      reconciler.validateChainEvent(chain1);
      reconciler.processChainEvent(chain1);

      // Second event referencing first
      const chain2: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_002',
        prev_update_id: 'update_001',
        domain_hashes: { geometryHash: 'hash2', arrangementHash: '', routingHash: '', phaseHash: '' },
      };

      const result = reconciler.validateChainEvent(chain2);

      expect(result.isValid).toBe(true);
      expect(result.hasGap).toBe(false);
    });

    it('should detect chain gap', () => {
      // First event
      const chain1: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: 'hash1', arrangementHash: '', routingHash: '', phaseHash: '' },
      };

      reconciler.validateChainEvent(chain1);
      reconciler.processChainEvent(chain1);

      // Third event with gap (references non-existent update_002)
      const chain3: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_003',
        prev_update_id: 'update_002', // Missing!
        domain_hashes: { geometryHash: 'hash3', arrangementHash: '', routingHash: '', phaseHash: '' },
      };

      const result = reconciler.validateChainEvent(chain3);

      expect(result.isValid).toBe(false);
      expect(result.hasGap).toBe(true);
    });

    it('should detect cycle when update_id is reused', () => {
      const chain1: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: 'hash1', arrangementHash: '', routingHash: '', phaseHash: '' },
      };

      reconciler.validateChainEvent(chain1);
      reconciler.processChainEvent(chain1);

      // Attempt to reuse the same update_id
      const chain2: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001', // Same ID!
        prev_update_id: null,
        domain_hashes: { geometryHash: 'hash2', arrangementHash: '', routingHash: '', phaseHash: '' },
      };

      const result = reconciler.validateChainEvent(chain2);

      expect(result.isValid).toBe(false);
      expect(result.hasCycle).toBe(true);
      expect(result.action).toBe('resync');
    });
  });

  describe('Chain State Processing', () => {
    it('should update chain state after processing', () => {
      const chain: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: 'new_hash', arrangementHash: '', routingHash: '', phaseHash: '' },
      };

      reconciler.processChainEvent(chain);

      const chainStates = reconciler.getChainStates();
      expect(chainStates.geometry.lastUpdateId).toBe('update_001');
      expect(chainStates.geometry.chainDepth).toBe(1);
    });

    it('should increment chain depth', () => {
      for (let i = 1; i <= 5; i++) {
        const chain: ChainTrackingMeta = {
          domain: 'geometry',
          update_id: `update_${i.toString().padStart(3, '0')}`,
          prev_update_id: i === 1 ? null : `update_${(i - 1).toString().padStart(3, '0')}`,
          domain_hashes: { geometryHash: `hash_${i}`, arrangementHash: '', routingHash: '', phaseHash: '' },
        };

        reconciler.processChainEvent(chain);
      }

      const chainStates = reconciler.getChainStates();
      expect(chainStates.geometry.chainDepth).toBe(5);
    });

    it('should update domain hashes', () => {
      const chain: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: {
          geometryHash: 'geo_hash_123',
          arrangementHash: 'arr_hash_456',
          routingHash: '',
          phaseHash: '',
        },
      };

      reconciler.processChainEvent(chain);

      const hashes = reconciler.getDomainHashes();
      expect(hashes.geometryHash).toBe('geo_hash_123');
      expect(hashes.arrangementHash).toBe('arr_hash_456');
    });
  });

  describe('Acknowledgment', () => {
    it('should track acknowledged updates', () => {
      const chain: ChainTrackingMeta = {
        domain: 'routing',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: '', arrangementHash: '', routingHash: 'hash1', phaseHash: '' },
      };

      reconciler.processChainEvent(chain);
      reconciler.acknowledgeUpdate('routing', 'update_001');

      const chainStates = reconciler.getChainStates();
      expect(chainStates.routing.lastAckedId).toBe('update_001');
    });

    it('should only ack if update_id matches lastUpdateId', () => {
      const chain: ChainTrackingMeta = {
        domain: 'routing',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: '', arrangementHash: '', routingHash: 'hash1', phaseHash: '' },
      };

      reconciler.processChainEvent(chain);
      reconciler.acknowledgeUpdate('routing', 'wrong_id');

      const chainStates = reconciler.getChainStates();
      expect(chainStates.routing.lastAckedId).toBeNull();
    });
  });

  describe('Force Refresh', () => {
    it('should reset single domain chain state', () => {
      const chain: ChainTrackingMeta = {
        domain: 'phase',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: '', arrangementHash: '', routingHash: '', phaseHash: 'hash1' },
      };

      reconciler.processChainEvent(chain);
      reconciler.forceRefreshDomain('phase');

      const chainStates = reconciler.getChainStates();
      expect(chainStates.phase.lastUpdateId).toBeNull();
      expect(chainStates.phase.chainDepth).toBe(0);
    });

    it('should reset all domain chain states', () => {
      const domains: Domain[] = ['geometry', 'arrangement', 'routing', 'phase'];

      // Add events to all domains
      domains.forEach((domain, i) => {
        const chain: ChainTrackingMeta = {
          domain,
          update_id: `update_${domain}`,
          prev_update_id: null,
          domain_hashes: { geometryHash: '', arrangementHash: '', routingHash: '', phaseHash: '' },
        };
        reconciler.processChainEvent(chain);
      });

      reconciler.forceRefreshAll();

      const chainStates = reconciler.getChainStates();
      domains.forEach(domain => {
        expect(chainStates[domain].lastUpdateId).toBeNull();
        expect(chainStates[domain].chainDepth).toBe(0);
      });
    });
  });

  describe('Domain Hash Comparison', () => {
    it('should detect hash mismatches', () => {
      const chain: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: {
          geometryHash: 'hash_abc',
          arrangementHash: 'hash_def',
          routingHash: '',
          phaseHash: '',
        },
      };

      reconciler.processChainEvent(chain);

      const comparison = reconciler.compareHashes({
        geometryHash: 'hash_xyz', // Different!
        arrangementHash: 'hash_def',
      });

      expect(comparison.matches).toBe(false);
      expect(comparison.mismatches).toContain('geometryHash');
    });

    it('should report match when hashes are same', () => {
      const chain: ChainTrackingMeta = {
        domain: 'geometry',
        update_id: 'update_001',
        prev_update_id: null,
        domain_hashes: {
          geometryHash: 'hash_abc',
          arrangementHash: '',
          routingHash: '',
          phaseHash: '',
        },
      };

      reconciler.processChainEvent(chain);

      const comparison = reconciler.compareHashes({
        geometryHash: 'hash_abc',
      });

      expect(comparison.matches).toBe(true);
    });
  });

  describe('Independent Domain Chains', () => {
    it('should track each domain independently', () => {
      // Process geometry event
      reconciler.processChainEvent({
        domain: 'geometry',
        update_id: 'geo_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: 'gh1', arrangementHash: '', routingHash: '', phaseHash: '' },
      });

      // Process routing event
      reconciler.processChainEvent({
        domain: 'routing',
        update_id: 'route_001',
        prev_update_id: null,
        domain_hashes: { geometryHash: '', arrangementHash: '', routingHash: 'rh1', phaseHash: '' },
      });

      const chainStates = reconciler.getChainStates();

      expect(chainStates.geometry.lastUpdateId).toBe('geo_001');
      expect(chainStates.routing.lastUpdateId).toBe('route_001');
      expect(chainStates.arrangement.lastUpdateId).toBeNull();
      expect(chainStates.phase.lastUpdateId).toBeNull();
    });
  });
});
