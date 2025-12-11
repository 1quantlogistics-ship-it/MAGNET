/**
 * MAGNET UI PRS Orchestrator
 * BRAVO OWNS THIS FILE.
 *
 * Phase Readiness System (PRS) state machine.
 * Manages workflow phases, transitions, and milestone tracking.
 *
 * V1.4 Features:
 * - Phase state machine with dependency validation
 * - Milestone toast notifications
 * - Domain hash staleness detection
 * - Event bus integration
 */

import { eventBus } from './UIEventBus';
import {
  phaseAPI,
  PHASE_ORDER,
  PHASE_DEPENDENCIES,
  getPhaseIndex,
  getNextPhase,
  type PhaseName,
  type PhaseStatus,
  type PhaseInfo,
} from '../api/phase';

// ============================================================================
// Types
// ============================================================================

/**
 * PRS state
 */
export interface PRSState {
  /** Current design ID */
  designId: string | null;
  /** Phase statuses */
  phases: Record<PhaseName, PhaseStatus>;
  /** Currently active phase */
  activePhase: PhaseName | null;
  /** Phases pending approval */
  pendingApproval: PhaseName[];
  /** Blocked phases */
  blockedPhases: PhaseName[];
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Last sync timestamp */
  lastSyncAt: string | null;
  /** Phase hash for staleness detection */
  phaseHash: string | null;
}

/**
 * Milestone notification
 */
export interface MilestoneNotification {
  id: string;
  type: 'phase_completed' | 'phase_approved' | 'milestone_reached';
  phase: PhaseName;
  message: string;
  timestamp: string;
  dismissed: boolean;
}

/**
 * Phase transition result
 */
export interface TransitionResult {
  success: boolean;
  fromPhase: PhaseName | null;
  toPhase: PhaseName | null;
  message: string;
  blockers?: string[];
}

/**
 * PRS event types
 */
export type PRSEventType =
  | 'prs:phase_changed'
  | 'prs:phase_completed'
  | 'prs:phase_approved'
  | 'prs:milestone_reached'
  | 'prs:sync_required'
  | 'prs:error';

/**
 * PRS event payload
 */
export interface PRSEventPayload {
  phase?: PhaseName;
  status?: PhaseStatus;
  message?: string;
  error?: string;
}

// ============================================================================
// Initial State
// ============================================================================

const INITIAL_STATE: PRSState = {
  designId: null,
  phases: {
    mission: 'pending',
    hull_form: 'pending',
    structure: 'pending',
    propulsion: 'pending',
    systems: 'pending',
    weight_stability: 'pending',
    compliance: 'pending',
    production: 'pending',
  },
  activePhase: null,
  pendingApproval: [],
  blockedPhases: [],
  isLoading: false,
  error: null,
  lastSyncAt: null,
  phaseHash: null,
};

// ============================================================================
// PRS Orchestrator
// ============================================================================

/**
 * PRS Orchestrator
 *
 * State machine for design phase workflow.
 * Handles transitions, validations, and milestone tracking.
 */
export class PRSOrchestrator {
  private state: PRSState;
  private listeners: Set<(state: PRSState) => void>;
  private milestones: MilestoneNotification[];

  constructor() {
    this.state = { ...INITIAL_STATE };
    this.listeners = new Set();
    this.milestones = [];
  }

  // -------------------------------------------------------------------------
  // State Management
  // -------------------------------------------------------------------------

  /**
   * Get current state
   */
  getState(): PRSState {
    return { ...this.state };
  }

  /**
   * Subscribe to state changes
   */
  subscribe(listener: (state: PRSState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Update state and notify listeners
   */
  private setState(updates: Partial<PRSState>): void {
    this.state = { ...this.state, ...updates };
    this.listeners.forEach(listener => listener(this.state));
  }

  /**
   * Emit event to event bus
   */
  private emit(type: PRSEventType, payload: PRSEventPayload): void {
    eventBus.emit({
      type: type as any,
      payload,
      source: 'ui',
      domain: 'phase',
    });
  }

  // -------------------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------------------

  /**
   * Initialize orchestrator for a design
   */
  async initialize(designId: string): Promise<void> {
    this.setState({
      designId,
      isLoading: true,
      error: null,
    });

    try {
      await this.sync();
    } catch (error) {
      this.setState({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to initialize',
      });
    }
  }

  /**
   * Reset orchestrator
   */
  reset(): void {
    this.state = { ...INITIAL_STATE };
    this.milestones = [];
    this.listeners.forEach(listener => listener(this.state));
  }

  // -------------------------------------------------------------------------
  // Sync Operations
  // -------------------------------------------------------------------------

  /**
   * Sync with backend
   */
  async sync(): Promise<void> {
    const { designId } = this.state;
    if (!designId) return;

    this.setState({ isLoading: true });

    try {
      const response = await phaseAPI.listPhases(designId);
      const phases: Record<string, PhaseStatus> = {};
      let activePhase: PhaseName | null = null;
      const pendingApproval: PhaseName[] = [];
      const blockedPhases: PhaseName[] = [];

      for (const info of response.data.phases) {
        phases[info.phase] = info.status;

        if (info.status === 'active') {
          activePhase = info.phase;
        }
        if (info.status === 'completed') {
          pendingApproval.push(info.phase);
        }
        if (info.status === 'blocked') {
          blockedPhases.push(info.phase);
        }
      }

      this.setState({
        phases: phases as Record<PhaseName, PhaseStatus>,
        activePhase,
        pendingApproval,
        blockedPhases,
        isLoading: false,
        lastSyncAt: new Date().toISOString(),
        error: null,
      });
    } catch (error) {
      this.setState({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Sync failed',
      });
      this.emit('prs:error', { error: 'Sync failed' });
    }
  }

  // -------------------------------------------------------------------------
  // Phase Operations
  // -------------------------------------------------------------------------

  /**
   * Check if phase can be started
   */
  canStartPhase(phase: PhaseName): { canStart: boolean; blockers: string[] } {
    const blockers: string[] = [];

    // Check dependencies
    const deps = PHASE_DEPENDENCIES[phase] ?? [];
    for (const dep of deps) {
      const depStatus = this.state.phases[dep];
      if (depStatus !== 'approved' && depStatus !== 'completed') {
        blockers.push(`${dep} must be completed or approved first`);
      }
    }

    // Check current status
    const currentStatus = this.state.phases[phase];
    if (currentStatus === 'active') {
      blockers.push(`${phase} is already active`);
    }
    if (currentStatus === 'approved') {
      blockers.push(`${phase} is already approved`);
    }

    return {
      canStart: blockers.length === 0,
      blockers,
    };
  }

  /**
   * Start a phase
   */
  async startPhase(phase: PhaseName): Promise<TransitionResult> {
    const { designId } = this.state;
    if (!designId) {
      return { success: false, fromPhase: null, toPhase: phase, message: 'No design loaded' };
    }

    const { canStart, blockers } = this.canStartPhase(phase);
    if (!canStart) {
      return {
        success: false,
        fromPhase: this.state.activePhase,
        toPhase: phase,
        message: 'Cannot start phase',
        blockers,
      };
    }

    this.setState({ isLoading: true });

    try {
      const response = await phaseAPI.runPhase(designId, phase);
      const fromPhase = this.state.activePhase;

      // Update state
      const phases = { ...this.state.phases };
      phases[phase] = 'active';
      if (fromPhase && fromPhase !== phase) {
        phases[fromPhase] = 'completed';
      }

      this.setState({
        phases,
        activePhase: phase,
        isLoading: false,
      });

      this.emit('prs:phase_changed', { phase, status: 'active' });

      return {
        success: true,
        fromPhase,
        toPhase: phase,
        message: `Started ${phase}`,
      };
    } catch (error) {
      this.setState({ isLoading: false });
      return {
        success: false,
        fromPhase: this.state.activePhase,
        toPhase: phase,
        message: error instanceof Error ? error.message : 'Failed to start phase',
      };
    }
  }

  /**
   * Complete the current phase
   */
  async completePhase(phase: PhaseName): Promise<TransitionResult> {
    const { designId } = this.state;
    if (!designId) {
      return { success: false, fromPhase: phase, toPhase: null, message: 'No design loaded' };
    }

    this.setState({ isLoading: true });

    try {
      // Validate first
      const validation = await phaseAPI.validatePhase(designId, phase);
      if (!validation.data.passed) {
        this.setState({ isLoading: false });
        return {
          success: false,
          fromPhase: phase,
          toPhase: null,
          message: `Validation failed: ${validation.data.errors} errors`,
        };
      }

      // Mark as completed
      const phases = { ...this.state.phases };
      phases[phase] = 'completed';

      const pendingApproval = [...this.state.pendingApproval];
      if (!pendingApproval.includes(phase)) {
        pendingApproval.push(phase);
      }

      this.setState({
        phases,
        pendingApproval,
        isLoading: false,
      });

      this.emit('prs:phase_completed', { phase, status: 'completed' });
      this.addMilestone(phase, 'phase_completed', `${phase} completed`);

      return {
        success: true,
        fromPhase: phase,
        toPhase: getNextPhase(phase),
        message: `${phase} completed`,
      };
    } catch (error) {
      this.setState({ isLoading: false });
      return {
        success: false,
        fromPhase: phase,
        toPhase: null,
        message: error instanceof Error ? error.message : 'Failed to complete phase',
      };
    }
  }

  /**
   * Approve a phase
   */
  async approvePhase(phase: PhaseName, comment?: string): Promise<TransitionResult> {
    const { designId } = this.state;
    if (!designId) {
      return { success: false, fromPhase: phase, toPhase: null, message: 'No design loaded' };
    }

    if (this.state.phases[phase] !== 'completed') {
      return {
        success: false,
        fromPhase: phase,
        toPhase: null,
        message: 'Phase must be completed before approval',
      };
    }

    this.setState({ isLoading: true });

    try {
      await phaseAPI.approvePhase(designId, phase, comment);

      const phases = { ...this.state.phases };
      phases[phase] = 'approved';

      const pendingApproval = this.state.pendingApproval.filter(p => p !== phase);

      this.setState({
        phases,
        pendingApproval,
        isLoading: false,
      });

      this.emit('prs:phase_approved', { phase, status: 'approved' });
      this.addMilestone(phase, 'phase_approved', `${phase} approved`);

      // Check for major milestones
      this.checkMilestones();

      return {
        success: true,
        fromPhase: phase,
        toPhase: getNextPhase(phase),
        message: `${phase} approved`,
      };
    } catch (error) {
      this.setState({ isLoading: false });
      return {
        success: false,
        fromPhase: phase,
        toPhase: null,
        message: error instanceof Error ? error.message : 'Failed to approve phase',
      };
    }
  }

  // -------------------------------------------------------------------------
  // Milestone Management
  // -------------------------------------------------------------------------

  /**
   * Add a milestone notification
   */
  private addMilestone(
    phase: PhaseName,
    type: MilestoneNotification['type'],
    message: string
  ): void {
    const milestone: MilestoneNotification = {
      id: `${phase}-${type}-${Date.now()}`,
      type,
      phase,
      message,
      timestamp: new Date().toISOString(),
      dismissed: false,
    };

    this.milestones.push(milestone);
  }

  /**
   * Check for major milestones
   */
  private checkMilestones(): void {
    const approvedCount = Object.values(this.state.phases)
      .filter(s => s === 'approved').length;

    // 25% milestone
    if (approvedCount === 2) {
      this.addMilestone('hull_form', 'milestone_reached', 'Design 25% Complete');
      this.emit('prs:milestone_reached', { message: 'Design 25% Complete' });
    }

    // 50% milestone
    if (approvedCount === 4) {
      this.addMilestone('systems', 'milestone_reached', 'Design 50% Complete');
      this.emit('prs:milestone_reached', { message: 'Design 50% Complete' });
    }

    // 75% milestone
    if (approvedCount === 6) {
      this.addMilestone('compliance', 'milestone_reached', 'Design 75% Complete');
      this.emit('prs:milestone_reached', { message: 'Design 75% Complete' });
    }

    // 100% milestone
    if (approvedCount === 8) {
      this.addMilestone('production', 'milestone_reached', 'Design Complete!');
      this.emit('prs:milestone_reached', { message: 'Design Complete!' });
    }
  }

  /**
   * Get undismissed milestones
   */
  getMilestones(): MilestoneNotification[] {
    return this.milestones.filter(m => !m.dismissed);
  }

  /**
   * Dismiss a milestone
   */
  dismissMilestone(id: string): void {
    const milestone = this.milestones.find(m => m.id === id);
    if (milestone) {
      milestone.dismissed = true;
    }
  }

  // -------------------------------------------------------------------------
  // Progress Helpers
  // -------------------------------------------------------------------------

  /**
   * Get overall progress percentage
   */
  getProgress(): number {
    const approved = Object.values(this.state.phases)
      .filter(s => s === 'approved').length;
    return Math.round((approved / PHASE_ORDER.length) * 100);
  }

  /**
   * Get current phase index (0-based)
   */
  getCurrentPhaseIndex(): number {
    if (!this.state.activePhase) {
      // Find first non-approved phase
      for (let i = 0; i < PHASE_ORDER.length; i++) {
        if (this.state.phases[PHASE_ORDER[i]] !== 'approved') {
          return i;
        }
      }
      return PHASE_ORDER.length - 1;
    }
    return getPhaseIndex(this.state.activePhase);
  }

  /**
   * Check if design is complete
   */
  isComplete(): boolean {
    return Object.values(this.state.phases)
      .every(s => s === 'approved');
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Default PRS orchestrator instance
 */
export const prsOrchestrator = new PRSOrchestrator();

/**
 * React hook for PRS orchestrator
 */
export function usePRSOrchestrator() {
  return prsOrchestrator;
}
