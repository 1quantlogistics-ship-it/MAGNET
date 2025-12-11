/**
 * MAGNET UI PRS Store
 * BRAVO OWNS THIS FILE.
 *
 * Phase Readiness System (PRS) state store.
 * Manages phase/milestone state with Zustand.
 *
 * V1.4 Features:
 * - Phase status tracking
 * - Milestone notifications
 * - Progress percentage
 * - Domain hash integration
 */

import { SCHEMA_VERSION } from '../../types/schema-version';
import { createStore } from '../contracts/StoreFactory';
import type { PhaseName, PhaseStatus } from '../../api/phase';

// ============================================================================
// Types
// ============================================================================

/**
 * Phase information
 */
export interface PhaseInfo {
  name: PhaseName;
  status: PhaseStatus;
  lastModified?: string;
  modifiedBy?: string;
  phaseHash?: string;
}

/**
 * Milestone notification
 */
export interface Milestone {
  id: string;
  type: 'phase_completed' | 'phase_approved' | 'milestone_reached';
  phase: PhaseName;
  message: string;
  timestamp: string;
  dismissed: boolean;
}

/**
 * PRS Store State
 */
export interface PRSStoreState {
  /** Current design ID */
  designId: string | null;
  /** Phase information by name */
  phases: Record<PhaseName, PhaseInfo>;
  /** Currently active phase */
  activePhase: PhaseName | null;
  /** Phases pending approval */
  pendingApproval: PhaseName[];
  /** Blocked phases */
  blockedPhases: PhaseName[];
  /** Milestone notifications */
  milestones: Milestone[];
  /** Loading state */
  isLoading: boolean;
  /** Error message */
  error: string | null;
  /** Last sync timestamp */
  lastSyncAt: string | null;
  /** Schema version */
  schema_version: string;
}

/**
 * Initial phase info
 */
const INITIAL_PHASE_INFO: PhaseInfo = {
  name: 'mission',
  status: 'pending',
};

/**
 * All phase names in order
 */
export const PHASE_NAMES: readonly PhaseName[] = [
  'mission',
  'hull_form',
  'structure',
  'propulsion',
  'systems',
  'weight_stability',
  'compliance',
  'production',
] as const;

/**
 * Initial state
 */
const INITIAL_STATE: PRSStoreState = {
  designId: null,
  phases: {
    mission: { ...INITIAL_PHASE_INFO, name: 'mission' },
    hull_form: { ...INITIAL_PHASE_INFO, name: 'hull_form' },
    structure: { ...INITIAL_PHASE_INFO, name: 'structure' },
    propulsion: { ...INITIAL_PHASE_INFO, name: 'propulsion' },
    systems: { ...INITIAL_PHASE_INFO, name: 'systems' },
    weight_stability: { ...INITIAL_PHASE_INFO, name: 'weight_stability' },
    compliance: { ...INITIAL_PHASE_INFO, name: 'compliance' },
    production: { ...INITIAL_PHASE_INFO, name: 'production' },
  },
  activePhase: null,
  pendingApproval: [],
  blockedPhases: [],
  milestones: [],
  isLoading: false,
  error: null,
  lastSyncAt: null,
  schema_version: SCHEMA_VERSION,
};

// ============================================================================
// Store
// ============================================================================

/**
 * Create PRS store with factory
 */
export const prsStore = createStore<PRSStoreState>({
  name: 'prs',
  initialState: INITIAL_STATE,
  readOnlyFields: [
    'designId',
    'phases',
    'activePhase',
    'pendingApproval',
    'blockedPhases',
    'milestones',
    'isLoading',
    'error',
    'lastSyncAt',
    'schema_version',
  ],
  readWriteFields: [],
});

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get current store state
 * Uses getReadOnly() function instead of readOnly property due to Zustand getter limitations
 */
export function getPRSState(): PRSStoreState {
  return prsStore.getState().getReadOnly();
}

/**
 * Get phase status
 */
export function getPhaseStatus(phase: PhaseName): PhaseStatus {
  return getPRSState().phases[phase].status;
}

/**
 * Get active phase
 */
export function getActivePhase(): PhaseName | null {
  return getPRSState().activePhase;
}

/**
 * Get progress percentage (0-100)
 */
export function getProgress(): number {
  const state = getPRSState();
  const approved = Object.values(state.phases).filter(p => p.status === 'approved').length;
  return Math.round((approved / PHASE_NAMES.length) * 100);
}

/**
 * Get completed phases count
 */
export function getCompletedCount(): number {
  const state = getPRSState();
  return Object.values(state.phases).filter(
    p => p.status === 'completed' || p.status === 'approved'
  ).length;
}

/**
 * Get approved phases count
 */
export function getApprovedCount(): number {
  const state = getPRSState();
  return Object.values(state.phases).filter(p => p.status === 'approved').length;
}

/**
 * Check if design is complete
 */
export function isDesignComplete(): boolean {
  return getApprovedCount() === PHASE_NAMES.length;
}

/**
 * Get undismissed milestones
 */
export function getActiveMilestones(): Milestone[] {
  return getPRSState().milestones.filter(m => !m.dismissed);
}

/**
 * Get phases in a specific status
 */
export function getPhasesByStatus(status: PhaseStatus): PhaseName[] {
  const state = getPRSState();
  return Object.entries(state.phases)
    .filter(([_, info]) => info.status === status)
    .map(([name]) => name as PhaseName);
}

/**
 * Check if phase can be started
 */
export function canStartPhase(phase: PhaseName): boolean {
  const state = getPRSState();
  const info = state.phases[phase];

  // Can't start if already active or approved
  if (info.status === 'active' || info.status === 'approved') {
    return false;
  }

  // Check not blocked
  if (state.blockedPhases.includes(phase)) {
    return false;
  }

  return true;
}

/**
 * Check if phase can be approved
 */
export function canApprovePhase(phase: PhaseName): boolean {
  return getPhaseStatus(phase) === 'completed';
}

// ============================================================================
// Actions
// ============================================================================

/**
 * Set design ID
 */
export function setDesignId(designId: string | null): void {
  prsStore.getState()._update(() => ({ designId }));
}

/**
 * Set phase status
 */
export function setPhaseStatus(phase: PhaseName, status: PhaseStatus): void {
  prsStore.getState()._update((state) => ({
    phases: {
      ...state.phases,
      [phase]: {
        ...state.phases[phase],
        status,
        lastModified: new Date().toISOString(),
      },
    },
  }));
}

/**
 * Set active phase
 */
export function setActivePhase(phase: PhaseName | null): void {
  prsStore.getState()._update(() => ({ activePhase: phase }));
}

/**
 * Add to pending approval
 */
export function addPendingApproval(phase: PhaseName): void {
  prsStore.getState()._update((state) => ({
    pendingApproval: state.pendingApproval.includes(phase)
      ? state.pendingApproval
      : [...state.pendingApproval, phase],
  }));
}

/**
 * Remove from pending approval
 */
export function removePendingApproval(phase: PhaseName): void {
  prsStore.getState()._update((state) => ({
    pendingApproval: state.pendingApproval.filter(p => p !== phase),
  }));
}

/**
 * Add blocked phase
 */
export function addBlockedPhase(phase: PhaseName): void {
  prsStore.getState()._update((state) => ({
    blockedPhases: state.blockedPhases.includes(phase)
      ? state.blockedPhases
      : [...state.blockedPhases, phase],
  }));
}

/**
 * Remove blocked phase
 */
export function removeBlockedPhase(phase: PhaseName): void {
  prsStore.getState()._update((state) => ({
    blockedPhases: state.blockedPhases.filter(p => p !== phase),
  }));
}

/**
 * Add milestone notification
 */
export function addMilestone(
  type: Milestone['type'],
  phase: PhaseName,
  message: string
): string {
  const id = `${phase}-${type}-${Date.now()}`;
  const milestone: Milestone = {
    id,
    type,
    phase,
    message,
    timestamp: new Date().toISOString(),
    dismissed: false,
  };

  prsStore.getState()._update((state) => ({
    milestones: [...state.milestones, milestone],
  }));

  return id;
}

/**
 * Dismiss a milestone
 */
export function dismissMilestone(id: string): void {
  prsStore.getState()._update((state) => ({
    milestones: state.milestones.map(m =>
      m.id === id ? { ...m, dismissed: true } : m
    ),
  }));
}

/**
 * Clear all dismissed milestones
 */
export function clearDismissedMilestones(): void {
  prsStore.getState()._update((state) => ({
    milestones: state.milestones.filter(m => !m.dismissed),
  }));
}

/**
 * Set loading state
 */
export function setPRSLoading(isLoading: boolean): void {
  prsStore.getState()._update(() => ({ isLoading }));
}

/**
 * Set error state
 */
export function setPRSError(error: string | null): void {
  prsStore.getState()._update(() => ({ error }));
}

/**
 * Update last sync timestamp
 */
export function updateLastSync(): void {
  prsStore.getState()._update(() => ({
    lastSyncAt: new Date().toISOString(),
  }));
}

/**
 * Reconcile with backend state
 */
export function reconcilePRSState(
  phases: Record<PhaseName, PhaseInfo>,
  activePhase: PhaseName | null,
  pendingApproval: PhaseName[],
  blockedPhases: PhaseName[]
): void {
  prsStore.getState()._update(() => ({
    phases,
    activePhase,
    pendingApproval,
    blockedPhases,
    lastSyncAt: new Date().toISOString(),
    error: null,
  }));
}

/**
 * Reset the store to initial state
 */
export function resetPRSStore(): void {
  prsStore.getState().reset();
}

// ============================================================================
// Subscription
// ============================================================================

/**
 * Subscribe to store changes
 */
export function subscribeToPRS(
  listener: (state: PRSStoreState) => void
): () => void {
  return prsStore.subscribe((fullState) => {
    listener(fullState.getReadOnly());
  });
}

// ============================================================================
// Export store for direct access
// ============================================================================

export default prsStore;
