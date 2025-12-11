/**
 * MAGNET UI Hash Utils Tests
 *
 * Tests for hash comparison and chain validation utilities.
 */

import { describe, it, expect } from 'vitest';
import {
  validateChain,
  updateChainState,
  resetChainState,
  compareDomainHashes,
  mergeDomainHashes,
} from '../../utils/hashUtils';
import type { ChainState, DomainHashes } from '../../types/domainHashes';
import { MAX_CHAIN_DEPTH } from '../../types/domainHashes';

describe('hashUtils', () => {
  describe('validateChain', () => {
    it('should validate first event in chain', () => {
      const chainState: ChainState = {
        lastUpdateId: null,
        lastAckedId: null,
        chainDepth: 0,
      };

      const result = validateChain(chainState, 'update_001', null);

      expect(result.isValid).toBe(true);
      expect(result.hasGap).toBe(false);
      expect(result.hasCycle).toBe(false);
      expect(result.action).toBe('apply');
    });

    it('should validate continuous chain', () => {
      const chainState: ChainState = {
        lastUpdateId: 'update_001',
        lastAckedId: null,
        chainDepth: 1,
      };

      const result = validateChain(chainState, 'update_002', 'update_001');

      expect(result.isValid).toBe(true);
      expect(result.hasGap).toBe(false);
    });

    it('should detect chain gap', () => {
      const chainState: ChainState = {
        lastUpdateId: 'update_001',
        lastAckedId: null,
        chainDepth: 1,
      };

      const result = validateChain(chainState, 'update_003', 'update_002');

      expect(result.isValid).toBe(false);
      expect(result.hasGap).toBe(true);
      expect(result.action).toBe('buffer');
    });

    it('should detect depth exceeded', () => {
      const chainState: ChainState = {
        lastUpdateId: 'update_999',
        lastAckedId: null,
        chainDepth: MAX_CHAIN_DEPTH,
      };

      const result = validateChain(chainState, 'update_1000', 'update_999');

      expect(result.isValid).toBe(false);
      expect(result.depthExceeded).toBe(true);
      expect(result.action).toBe('resync');
    });

    it('should allow re-initialization with null prev_update_id', () => {
      const chainState: ChainState = {
        lastUpdateId: 'update_old',
        lastAckedId: 'update_old',
        chainDepth: 5,
      };

      // A new chain starting fresh
      const result = validateChain(chainState, 'update_new', null);

      expect(result.isValid).toBe(true);
    });
  });

  describe('updateChainState', () => {
    it('should update lastUpdateId', () => {
      const chainState: ChainState = {
        lastUpdateId: null,
        lastAckedId: null,
        chainDepth: 0,
      };

      const newState = updateChainState(chainState, 'update_001');

      expect(newState.lastUpdateId).toBe('update_001');
    });

    it('should increment chainDepth', () => {
      const chainState: ChainState = {
        lastUpdateId: 'update_001',
        lastAckedId: null,
        chainDepth: 5,
      };

      const newState = updateChainState(chainState, 'update_002');

      expect(newState.chainDepth).toBe(6);
    });

    it('should update lastAckedId when acked=true', () => {
      const chainState: ChainState = {
        lastUpdateId: null,
        lastAckedId: null,
        chainDepth: 0,
      };

      const newState = updateChainState(chainState, 'update_001', true);

      expect(newState.lastAckedId).toBe('update_001');
    });

    it('should not update lastAckedId when acked=false', () => {
      const chainState: ChainState = {
        lastUpdateId: null,
        lastAckedId: 'old_ack',
        chainDepth: 0,
      };

      const newState = updateChainState(chainState, 'update_001', false);

      expect(newState.lastAckedId).toBe('old_ack');
    });
  });

  describe('resetChainState', () => {
    it('should return initial chain state', () => {
      const state = resetChainState();

      expect(state.lastUpdateId).toBeNull();
      expect(state.lastAckedId).toBeNull();
      expect(state.chainDepth).toBe(0);
    });
  });

  describe('compareDomainHashes', () => {
    it('should report match when all provided hashes match', () => {
      const current: DomainHashes = {
        geometryHash: 'hash_a',
        arrangementHash: 'hash_b',
        routingHash: 'hash_c',
        phaseHash: 'hash_d',
      };

      const incoming = {
        geometryHash: 'hash_a',
        arrangementHash: 'hash_b',
      };

      const result = compareDomainHashes(current, incoming);

      expect(result.matches).toBe(true);
      expect(result.mismatches).toHaveLength(0);
    });

    it('should report mismatches', () => {
      const current: DomainHashes = {
        geometryHash: 'hash_a',
        arrangementHash: 'hash_b',
        routingHash: 'hash_c',
        phaseHash: 'hash_d',
      };

      const incoming = {
        geometryHash: 'different_hash',
        arrangementHash: 'hash_b',
      };

      const result = compareDomainHashes(current, incoming);

      expect(result.matches).toBe(false);
      expect(result.mismatches).toContain('geometryHash');
      expect(result.mismatches).not.toContain('arrangementHash');
    });

    it('should ignore empty incoming hashes', () => {
      const current: DomainHashes = {
        geometryHash: 'hash_a',
        arrangementHash: 'hash_b',
        routingHash: 'hash_c',
        phaseHash: 'hash_d',
      };

      const incoming = {
        geometryHash: 'hash_a',
        arrangementHash: '', // Empty, should be ignored
      };

      const result = compareDomainHashes(current, incoming);

      expect(result.matches).toBe(true);
    });

    it('should list all checked hashes', () => {
      const current: DomainHashes = {
        geometryHash: 'hash_a',
        arrangementHash: 'hash_b',
        routingHash: 'hash_c',
        phaseHash: 'hash_d',
      };

      const incoming = {
        geometryHash: 'hash_a',
        routingHash: 'hash_c',
      };

      const result = compareDomainHashes(current, incoming);

      expect(result.checked).toContain('geometryHash');
      expect(result.checked).toContain('routingHash');
      expect(result.checked).not.toContain('arrangementHash');
    });
  });

  describe('mergeDomainHashes', () => {
    it('should merge incoming non-empty hashes', () => {
      const current: DomainHashes = {
        geometryHash: 'old_geo',
        arrangementHash: 'old_arr',
        routingHash: 'old_route',
        phaseHash: 'old_phase',
      };

      const incoming = {
        geometryHash: 'new_geo',
        arrangementHash: '', // Empty, should not overwrite
      };

      const result = mergeDomainHashes(current, incoming);

      expect(result.geometryHash).toBe('new_geo');
      expect(result.arrangementHash).toBe('old_arr'); // Preserved
      expect(result.routingHash).toBe('old_route');
    });

    it('should preserve contentHash if present', () => {
      const current: DomainHashes = {
        geometryHash: 'geo',
        arrangementHash: 'arr',
        routingHash: 'route',
        phaseHash: 'phase',
        contentHash: 'old_content',
      };

      const incoming = {
        contentHash: 'new_content',
      };

      const result = mergeDomainHashes(current, incoming);

      expect(result.contentHash).toBe('new_content');
    });

    it('should handle partial incoming hashes', () => {
      const current: DomainHashes = {
        geometryHash: 'geo',
        arrangementHash: 'arr',
        routingHash: 'route',
        phaseHash: 'phase',
      };

      const incoming = {
        phaseHash: 'new_phase',
      };

      const result = mergeDomainHashes(current, incoming);

      expect(result.geometryHash).toBe('geo');
      expect(result.arrangementHash).toBe('arr');
      expect(result.routingHash).toBe('route');
      expect(result.phaseHash).toBe('new_phase');
    });

    it('should not mutate original objects', () => {
      const current: DomainHashes = {
        geometryHash: 'geo',
        arrangementHash: 'arr',
        routingHash: 'route',
        phaseHash: 'phase',
      };

      const incoming = {
        geometryHash: 'new_geo',
      };

      mergeDomainHashes(current, incoming);

      expect(current.geometryHash).toBe('geo');
    });
  });
});
