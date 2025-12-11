/**
 * MAGNET UI Hash Utilities
 *
 * Utility functions for comparing and validating domain hashes
 * and update chains.
 */

import type {
  Domain,
  DomainHashes,
  PartialDomainHashes,
  ChainState,
  DomainChainStates,
  HashComparisonResult,
  ChainValidationResult,
} from '../types/domainHashes';
import { DOMAINS, MAX_CHAIN_DEPTH } from '../types/domainHashes';

// ============================================================================
// Hash Comparison
// ============================================================================

/**
 * Compare two sets of domain hashes
 */
export function compareDomainHashes(
  current: DomainHashes,
  incoming: PartialDomainHashes
): HashComparisonResult {
  const mismatches: string[] = [];
  const checked: string[] = [];

  for (const domain of DOMAINS) {
    const hashKey = `${domain}Hash` as keyof DomainHashes;
    const currentHash = current[hashKey];
    const incomingHash = incoming[hashKey];

    // Skip undefined or empty incoming hashes
    if (incomingHash === undefined || incomingHash === '') {
      continue;
    }

    checked.push(hashKey);

    if (currentHash !== incomingHash) {
      mismatches.push(hashKey);
    }
  }

  // Also check contentHash if present
  if (incoming.contentHash !== undefined && incoming.contentHash !== '') {
    checked.push('contentHash');
    if (current.contentHash !== incoming.contentHash) {
      mismatches.push('contentHash');
    }
  }

  return {
    matches: mismatches.length === 0,
    mismatches,
    checked,
    // Legacy fields for backward compatibility
    allMatch: mismatches.length === 0,
    changedDomains: mismatches.map(h => h.replace('Hash', '') as Domain),
    missingDomains: [],
  };
}

/**
 * Check if a specific domain hash has changed
 */
export function hasDomainChanged(
  domain: Domain,
  current: DomainHashes,
  incoming: PartialDomainHashes
): boolean {
  const hashKey = `${domain}Hash` as keyof DomainHashes;
  return current[hashKey] !== incoming[hashKey];
}

/**
 * Get hash for a specific domain
 */
export function getDomainHash(hashes: DomainHashes, domain: Domain): string {
  const hashKey = `${domain}Hash` as keyof DomainHashes;
  return hashes[hashKey];
}

/**
 * Merge partial hashes into existing hashes
 * Empty strings are treated as "not provided" and don't overwrite
 */
export function mergeDomainHashes(
  current: DomainHashes,
  incoming: PartialDomainHashes
): DomainHashes {
  return {
    geometryHash: (incoming.geometryHash && incoming.geometryHash !== '')
      ? incoming.geometryHash
      : current.geometryHash,
    arrangementHash: (incoming.arrangementHash && incoming.arrangementHash !== '')
      ? incoming.arrangementHash
      : current.arrangementHash,
    routingHash: (incoming.routingHash && incoming.routingHash !== '')
      ? incoming.routingHash
      : current.routingHash,
    phaseHash: (incoming.phaseHash && incoming.phaseHash !== '')
      ? incoming.phaseHash
      : current.phaseHash,
    contentHash: (incoming.contentHash && incoming.contentHash !== '')
      ? incoming.contentHash
      : current.contentHash,
  };
}

// ============================================================================
// Chain Validation
// ============================================================================

/**
 * Validate an update chain for a domain
 */
export function validateChain(
  chainState: ChainState,
  updateId: string,
  prevUpdateId: string | null
): ChainValidationResult {
  // Check for cycle (update ID already seen)
  if (chainState.lastUpdateId === updateId) {
    return {
      isValid: false,
      hasGap: false,
      hasCycle: true,
      depthExceeded: false,
      action: 'resync',
    };
  }

  // Allow re-initialization with null prev_update_id (new chain starting)
  if (prevUpdateId === null) {
    return {
      isValid: true,
      hasGap: false,
      hasCycle: false,
      depthExceeded: false,
      action: 'apply',
    };
  }

  // Check chain continuity
  const expectedPrev = chainState.lastUpdateId;
  const hasGap = expectedPrev !== null && prevUpdateId !== expectedPrev;

  // Check depth limit
  const newDepth = chainState.chainDepth + 1;
  const depthExceeded = newDepth >= MAX_CHAIN_DEPTH;

  if (depthExceeded) {
    return {
      isValid: false,
      hasGap,
      hasCycle: false,
      depthExceeded: true,
      action: 'resync',
    };
  }

  if (hasGap) {
    return {
      isValid: false,
      hasGap: true,
      hasCycle: false,
      depthExceeded: false,
      action: 'buffer',
    };
  }

  return {
    isValid: true,
    hasGap: false,
    hasCycle: false,
    depthExceeded: false,
    action: 'apply',
  };
}

/**
 * Update chain state after processing an update
 */
export function updateChainState(
  chainState: ChainState,
  updateId: string,
  acked: boolean = false
): ChainState {
  return {
    lastUpdateId: updateId,
    lastAckedId: acked ? updateId : chainState.lastAckedId,
    chainDepth: chainState.chainDepth + 1,
  };
}

/**
 * Reset chain state (after force refresh)
 */
export function resetChainState(updateId: string | null = null): ChainState {
  return {
    lastUpdateId: updateId,
    lastAckedId: updateId,
    chainDepth: 0,
  };
}

/**
 * Get chain state for a specific domain
 */
export function getChainState(
  chainStates: DomainChainStates,
  domain: Domain
): ChainState {
  return chainStates[domain];
}

/**
 * Update chain state for a specific domain
 */
export function setChainState(
  chainStates: DomainChainStates,
  domain: Domain,
  newState: ChainState
): DomainChainStates {
  return {
    ...chainStates,
    [domain]: newState,
  };
}

// ============================================================================
// Pending ACK Tracking
// ============================================================================

/**
 * Check if there are unacknowledged updates for a domain
 */
export function hasUnackedUpdates(chainState: ChainState): boolean {
  return chainState.lastUpdateId !== chainState.lastAckedId;
}

/**
 * Get count of unacked updates across all domains
 */
export function getUnackedCount(chainStates: DomainChainStates): number {
  let count = 0;
  for (const domain of DOMAINS) {
    if (hasUnackedUpdates(chainStates[domain])) {
      count++;
    }
  }
  return count;
}

// ============================================================================
// Hash Generation (Client-side)
// ============================================================================

/**
 * Generate a simple hash from string content
 * Note: This is for client-side use only, not cryptographic
 */
export function simpleHash(content: string): string {
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, '0');
}

/**
 * Generate update ID
 */
export function generateUpdateId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `${timestamp}-${random}`;
}
