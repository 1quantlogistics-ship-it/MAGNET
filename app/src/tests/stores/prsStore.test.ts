/**
 * MAGNET UI PRS Store Tests
 *
 * Tests for Phase Readiness System state management.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  prsStore,
  getPRSState,
  getPhaseStatus,
  getActivePhase,
  getProgress,
  getCompletedCount,
  getApprovedCount,
  isDesignComplete,
  getActiveMilestones,
  getPhasesByStatus,
  canStartPhase,
  canApprovePhase,
  setDesignId,
  setPhaseStatus,
  setActivePhase,
  addPendingApproval,
  removePendingApproval,
  addBlockedPhase,
  removeBlockedPhase,
  addMilestone,
  dismissMilestone,
  clearDismissedMilestones,
  setPRSLoading,
  setPRSError,
  updateLastSync,
  reconcilePRSState,
  resetPRSStore,
  subscribeToPRS,
  PHASE_NAMES,
  type PhaseInfo,
} from '../../stores/domain/prsStore';
import type { PhaseName, PhaseStatus } from '../../api/phase';

// ============================================================================
// Test Setup
// ============================================================================

describe('prsStore', () => {
  beforeEach(() => {
    resetPRSStore();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Initial State Tests
  // ============================================================================

  describe('initial state', () => {
    it('has correct initial state', () => {
      const state = getPRSState();

      expect(state.designId).toBeNull();
      expect(state.activePhase).toBeNull();
      expect(state.pendingApproval).toEqual([]);
      expect(state.blockedPhases).toEqual([]);
      expect(state.milestones).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.lastSyncAt).toBeNull();
    });

    it('has all phases initialized as pending', () => {
      const state = getPRSState();

      for (const phaseName of PHASE_NAMES) {
        expect(state.phases[phaseName]).toBeDefined();
        expect(state.phases[phaseName].status).toBe('pending');
        expect(state.phases[phaseName].name).toBe(phaseName);
      }
    });

    it('has correct phase order', () => {
      expect(PHASE_NAMES).toEqual([
        'mission',
        'hull_form',
        'structure',
        'propulsion',
        'systems',
        'weight_stability',
        'compliance',
        'production',
      ]);
    });
  });

  // ============================================================================
  // Selector Tests
  // ============================================================================

  describe('selectors', () => {
    describe('getPhaseStatus', () => {
      it('returns phase status', () => {
        expect(getPhaseStatus('mission')).toBe('pending');

        setPhaseStatus('mission', 'active');
        expect(getPhaseStatus('mission')).toBe('active');
      });
    });

    describe('getActivePhase', () => {
      it('returns null when no phase is active', () => {
        expect(getActivePhase()).toBeNull();
      });

      it('returns active phase when set', () => {
        setActivePhase('hull_form');
        expect(getActivePhase()).toBe('hull_form');
      });
    });

    describe('getProgress', () => {
      it('returns 0 when no phases approved', () => {
        expect(getProgress()).toBe(0);
      });

      it('calculates correct progress percentage', () => {
        setPhaseStatus('mission', 'approved');
        setPhaseStatus('hull_form', 'approved');

        // 2 out of 8 phases = 25%
        expect(getProgress()).toBe(25);
      });

      it('returns 100 when all phases approved', () => {
        for (const phase of PHASE_NAMES) {
          setPhaseStatus(phase, 'approved');
        }
        expect(getProgress()).toBe(100);
      });
    });

    describe('getCompletedCount', () => {
      it('counts completed and approved phases', () => {
        expect(getCompletedCount()).toBe(0);

        setPhaseStatus('mission', 'completed');
        expect(getCompletedCount()).toBe(1);

        setPhaseStatus('hull_form', 'approved');
        expect(getCompletedCount()).toBe(2);
      });
    });

    describe('getApprovedCount', () => {
      it('counts only approved phases', () => {
        setPhaseStatus('mission', 'completed');
        expect(getApprovedCount()).toBe(0);

        setPhaseStatus('mission', 'approved');
        expect(getApprovedCount()).toBe(1);
      });
    });

    describe('isDesignComplete', () => {
      it('returns false when not all phases approved', () => {
        expect(isDesignComplete()).toBe(false);

        setPhaseStatus('mission', 'approved');
        expect(isDesignComplete()).toBe(false);
      });

      it('returns true when all phases approved', () => {
        for (const phase of PHASE_NAMES) {
          setPhaseStatus(phase, 'approved');
        }
        expect(isDesignComplete()).toBe(true);
      });
    });

    describe('getActiveMilestones', () => {
      it('returns only non-dismissed milestones', () => {
        const id1 = addMilestone('phase_completed', 'mission', 'Mission completed');
        const id2 = addMilestone('phase_approved', 'mission', 'Mission approved');

        expect(getActiveMilestones()).toHaveLength(2);

        dismissMilestone(id1);
        expect(getActiveMilestones()).toHaveLength(1);
        expect(getActiveMilestones()[0].id).toBe(id2);
      });
    });

    describe('getPhasesByStatus', () => {
      it('returns phases matching status', () => {
        setPhaseStatus('mission', 'completed');
        setPhaseStatus('hull_form', 'completed');
        setPhaseStatus('structure', 'active');

        const completed = getPhasesByStatus('completed');
        expect(completed).toContain('mission');
        expect(completed).toContain('hull_form');
        expect(completed).not.toContain('structure');

        const active = getPhasesByStatus('active');
        expect(active).toEqual(['structure']);
      });
    });

    describe('canStartPhase', () => {
      it('returns true for pending phase', () => {
        expect(canStartPhase('mission')).toBe(true);
      });

      it('returns false for active phase', () => {
        setPhaseStatus('mission', 'active');
        expect(canStartPhase('mission')).toBe(false);
      });

      it('returns false for approved phase', () => {
        setPhaseStatus('mission', 'approved');
        expect(canStartPhase('mission')).toBe(false);
      });

      it('returns false for blocked phase', () => {
        addBlockedPhase('hull_form');
        expect(canStartPhase('hull_form')).toBe(false);
      });
    });

    describe('canApprovePhase', () => {
      it('returns true only for completed phases', () => {
        expect(canApprovePhase('mission')).toBe(false);

        setPhaseStatus('mission', 'active');
        expect(canApprovePhase('mission')).toBe(false);

        setPhaseStatus('mission', 'completed');
        expect(canApprovePhase('mission')).toBe(true);
      });
    });
  });

  // ============================================================================
  // Action Tests
  // ============================================================================

  describe('actions', () => {
    describe('setDesignId', () => {
      it('sets design ID', () => {
        setDesignId('MAGNET-2024-ABC1');
        expect(getPRSState().designId).toBe('MAGNET-2024-ABC1');
      });

      it('clears design ID with null', () => {
        setDesignId('MAGNET-2024-ABC1');
        setDesignId(null);
        expect(getPRSState().designId).toBeNull();
      });
    });

    describe('setPhaseStatus', () => {
      it('updates phase status', () => {
        setPhaseStatus('mission', 'active');
        expect(getPhaseStatus('mission')).toBe('active');
      });

      it('sets lastModified timestamp', () => {
        const before = new Date().toISOString();
        setPhaseStatus('mission', 'completed');
        const after = new Date().toISOString();

        const phase = getPRSState().phases.mission;
        expect(phase.lastModified).toBeDefined();
        expect(phase.lastModified! >= before).toBe(true);
        expect(phase.lastModified! <= after).toBe(true);
      });
    });

    describe('setActivePhase', () => {
      it('sets active phase', () => {
        setActivePhase('hull_form');
        expect(getActivePhase()).toBe('hull_form');
      });

      it('clears active phase with null', () => {
        setActivePhase('hull_form');
        setActivePhase(null);
        expect(getActivePhase()).toBeNull();
      });
    });

    describe('pending approval management', () => {
      it('adds phase to pending approval', () => {
        addPendingApproval('mission');
        expect(getPRSState().pendingApproval).toContain('mission');
      });

      it('does not duplicate pending approval', () => {
        addPendingApproval('mission');
        addPendingApproval('mission');
        expect(getPRSState().pendingApproval.filter(p => p === 'mission')).toHaveLength(1);
      });

      it('removes phase from pending approval', () => {
        addPendingApproval('mission');
        addPendingApproval('hull_form');
        removePendingApproval('mission');

        expect(getPRSState().pendingApproval).not.toContain('mission');
        expect(getPRSState().pendingApproval).toContain('hull_form');
      });
    });

    describe('blocked phase management', () => {
      it('adds blocked phase', () => {
        addBlockedPhase('structure');
        expect(getPRSState().blockedPhases).toContain('structure');
      });

      it('does not duplicate blocked phase', () => {
        addBlockedPhase('structure');
        addBlockedPhase('structure');
        expect(getPRSState().blockedPhases.filter(p => p === 'structure')).toHaveLength(1);
      });

      it('removes blocked phase', () => {
        addBlockedPhase('structure');
        addBlockedPhase('propulsion');
        removeBlockedPhase('structure');

        expect(getPRSState().blockedPhases).not.toContain('structure');
        expect(getPRSState().blockedPhases).toContain('propulsion');
      });
    });

    describe('milestone management', () => {
      it('adds milestone and returns ID', () => {
        const id = addMilestone('phase_completed', 'mission', 'Mission phase completed');

        expect(id).toBeDefined();
        expect(id).toContain('mission');

        const milestones = getPRSState().milestones;
        expect(milestones).toHaveLength(1);
        expect(milestones[0].type).toBe('phase_completed');
        expect(milestones[0].phase).toBe('mission');
        expect(milestones[0].message).toBe('Mission phase completed');
        expect(milestones[0].dismissed).toBe(false);
      });

      it('dismisses milestone', () => {
        const id = addMilestone('phase_completed', 'mission', 'Test');
        dismissMilestone(id);

        const milestone = getPRSState().milestones.find(m => m.id === id);
        expect(milestone?.dismissed).toBe(true);
      });

      it('clears dismissed milestones', () => {
        const id1 = addMilestone('phase_completed', 'mission', 'Test 1');
        const id2 = addMilestone('phase_approved', 'hull_form', 'Test 2');

        dismissMilestone(id1);
        clearDismissedMilestones();

        const milestones = getPRSState().milestones;
        expect(milestones).toHaveLength(1);
        expect(milestones[0].id).toBe(id2);
      });
    });

    describe('loading and error state', () => {
      it('sets loading state', () => {
        setPRSLoading(true);
        expect(getPRSState().isLoading).toBe(true);

        setPRSLoading(false);
        expect(getPRSState().isLoading).toBe(false);
      });

      it('sets error state', () => {
        setPRSError('Something went wrong');
        expect(getPRSState().error).toBe('Something went wrong');

        setPRSError(null);
        expect(getPRSState().error).toBeNull();
      });
    });

    describe('sync timestamp', () => {
      it('updates last sync timestamp', () => {
        const before = new Date().toISOString();
        updateLastSync();
        const after = new Date().toISOString();

        const lastSync = getPRSState().lastSyncAt;
        expect(lastSync).toBeDefined();
        expect(lastSync! >= before).toBe(true);
        expect(lastSync! <= after).toBe(true);
      });
    });

    describe('reconcilePRSState', () => {
      it('reconciles full state from backend', () => {
        const phases: Record<PhaseName, PhaseInfo> = {
          mission: { name: 'mission', status: 'approved' },
          hull_form: { name: 'hull_form', status: 'completed' },
          structure: { name: 'structure', status: 'active' },
          propulsion: { name: 'propulsion', status: 'pending' },
          systems: { name: 'systems', status: 'pending' },
          weight_stability: { name: 'weight_stability', status: 'pending' },
          compliance: { name: 'compliance', status: 'pending' },
          production: { name: 'production', status: 'pending' },
        };

        reconcilePRSState(
          phases,
          'structure',
          ['hull_form'],
          ['production']
        );

        const state = getPRSState();
        expect(state.phases.mission.status).toBe('approved');
        expect(state.phases.hull_form.status).toBe('completed');
        expect(state.activePhase).toBe('structure');
        expect(state.pendingApproval).toEqual(['hull_form']);
        expect(state.blockedPhases).toEqual(['production']);
        expect(state.error).toBeNull();
        expect(state.lastSyncAt).toBeDefined();
      });
    });

    describe('resetPRSStore', () => {
      it('resets store to initial state', () => {
        // Modify state
        setDesignId('TEST-001');
        setPhaseStatus('mission', 'completed');
        setActivePhase('hull_form');
        addMilestone('phase_completed', 'mission', 'Test');

        // Reset
        resetPRSStore();

        // Verify reset
        const state = getPRSState();
        expect(state.designId).toBeNull();
        expect(state.activePhase).toBeNull();
        expect(state.milestones).toEqual([]);
        expect(getPhaseStatus('mission')).toBe('pending');
      });
    });
  });

  // ============================================================================
  // Subscription Tests
  // ============================================================================

  describe('subscription', () => {
    it('notifies subscribers on state change', () => {
      const listener = vi.fn();
      const unsubscribe = subscribeToPRS(listener);

      setPhaseStatus('mission', 'active');

      expect(listener).toHaveBeenCalled();
      const receivedState = listener.mock.calls[0][0];
      expect(receivedState.phases.mission.status).toBe('active');

      unsubscribe();
    });

    it('stops notifying after unsubscribe', () => {
      const listener = vi.fn();
      const unsubscribe = subscribeToPRS(listener);

      setPhaseStatus('mission', 'active');
      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();

      setPhaseStatus('hull_form', 'active');
      expect(listener).toHaveBeenCalledTimes(1);
    });
  });
});
