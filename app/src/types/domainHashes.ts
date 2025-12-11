/**
 * MAGNET UI Domain Hashes
 *
 * Type definitions for domain-specific content hashes used in
 * state synchronization and chain tracking.
 *
 * These hashes enable:
 * - Detecting backend state changes per domain
 * - Validating update chain integrity
 * - Optimistic update verification
 */

// ============================================================================
// Domain Types
// ============================================================================

/**
 * Domain identifiers for independent state tracking
 */
export type Domain = 'geometry' | 'arrangement' | 'routing' | 'phase';

/**
 * All tracked domains
 */
export const DOMAINS: readonly Domain[] = [
  'geometry',
  'arrangement',
  'routing',
  'phase',
] as const;

// ============================================================================
// Domain Hashes
// ============================================================================

/**
 * Domain-specific content hashes
 *
 * Each domain maintains an independent hash that changes
 * when the backend state for that domain is modified.
 */
export interface DomainHashes {
  /** Hash of geometry state (hull, decks, compartments) */
  geometryHash: string;
  /** Hash of arrangement state (space assignments, equipment) */
  arrangementHash: string;
  /** Hash of routing state (systems topology) */
  routingHash: string;
  /** Hash of phase state (workflow progress) */
  phaseHash: string;
  /** Fallback composite hash when domain hashes unavailable */
  contentHash?: string;
}

/**
 * Partial domain hashes for incremental updates
 */
export type PartialDomainHashes = Partial<DomainHashes>;

// ============================================================================
// Chain State
// ============================================================================

/**
 * Chain state for tracking update sequences per domain
 *
 * Each domain maintains its own update chain to ensure
 * events are processed in order and detect missing updates.
 */
export interface ChainState {
  /** ID of the last received update */
  lastUpdateId: string | null;
  /** ID of the last acknowledged update */
  lastAckedId: string | null;
  /** Current chain depth (resets on force refresh) */
  chainDepth: number;
}

/**
 * Chain states for all domains
 */
export type DomainChainStates = Record<Domain, ChainState>;

// ============================================================================
// Constants
// ============================================================================

/**
 * Maximum chain depth before forcing a full refresh
 */
export const MAX_CHAIN_DEPTH = 1000;

/**
 * Initial chain state for a domain
 */
export const INITIAL_CHAIN_STATE: ChainState = {
  lastUpdateId: null,
  lastAckedId: null,
  chainDepth: 0,
};

/**
 * Initial chain states for all domains
 */
export const INITIAL_DOMAIN_CHAIN_STATES: DomainChainStates = {
  geometry: { ...INITIAL_CHAIN_STATE },
  arrangement: { ...INITIAL_CHAIN_STATE },
  routing: { ...INITIAL_CHAIN_STATE },
  phase: { ...INITIAL_CHAIN_STATE },
};

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Hash comparison result
 */
export interface HashComparisonResult {
  /** Whether all checked hashes match */
  matches: boolean;
  /** List of hash keys that don't match */
  mismatches: string[];
  /** List of hash keys that were checked */
  checked: string[];
  /** @deprecated Use `matches` instead */
  allMatch: boolean;
  /** @deprecated Use `mismatches` instead */
  changedDomains: Domain[];
  /** @deprecated */
  missingDomains: Domain[];
}

/**
 * Chain validation result
 */
export interface ChainValidationResult {
  /** Whether the chain is valid */
  isValid: boolean;
  /** Whether a gap was detected (missing update) */
  hasGap: boolean;
  /** Whether a cycle was detected */
  hasCycle: boolean;
  /** Whether max depth was exceeded */
  depthExceeded: boolean;
  /** Suggested action */
  action: 'apply' | 'buffer' | 'resync' | 'continue' | 'force_refresh';
}
