/**
 * MAGNET UI PRS Orchestrator Tests
 * BRAVO OWNS THIS FILE.
 *
 * Tests for PRSOrchestrator phase workflow management.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PRSOrchestrator } from '../../systems/PRSOrchestrator';
import { PHASE_ORDER } from '../../api/phase';
import type { PhaseName, PhaseStatus } from '../../api/phase';

// Mock the phaseAPI
vi.mock('../../api/phase', async () => {
  const actual = await vi.importActual('../../api/phase');
  return {
    ...actual,
    phaseAPI: {
      listPhases: vi.fn(),
      getPhase: vi.fn(),
      runPhase: vi.fn(),
      validatePhase: vi.fn(),
      approvePhase: vi.fn(),
    },
  };
});

// Mock the eventBus
vi.mock('../../systems/UIEventBus', () => ({
  eventBus: {
    emit: vi.fn(),
    on: vi.fn(() => () => {}),
  },
}));

import { phaseAPI } from '../../api/phase';
import { eventBus } from '../../systems/UIEventBus';

describe('PRSOrchestrator', () => {
  let orchestrator: PRSOrchestrator;

  beforeEach(() => {
    orchestrator = new PRSOrchestrator();
    vi.clearAllMocks();
  });

  afterEach(() => {
    orchestrator.reset();
  });

  describe('Initial State', () => {
    it('should initialize with default state', () => {
      const state = orchestrator.getState();

      expect(state.designId).toBeNull();
      expect(state.activePhase).toBeNull();
      expect(state.pendingApproval).toEqual([]);
      expect(state.blockedPhases).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should have all phases as pending', () => {
      const state = orchestrator.getState();

      for (const phase of PHASE_ORDER) {
        expect(state.phases[phase]).toBe('pending');
      }
    });
  });

  describe('Subscription', () => {
    it('should notify subscribers on state changes', async () => {
      const listener = vi.fn();
      orchestrator.subscribe(listener);

      // Trigger state change via initialize
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: PHASE_ORDER.map((phase) => ({
            phase,
            status: 'pending' as PhaseStatus,
            completedAt: null,
            approvedAt: null,
          })),
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');

      expect(listener).toHaveBeenCalled();
    });

    it('should unsubscribe correctly', () => {
      const listener = vi.fn();
      const unsubscribe = orchestrator.subscribe(listener);

      unsubscribe();
      orchestrator.reset(); // Triggers state change

      // Should not be called since we unsubscribed
      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('Initialize', () => {
    it('should set designId and fetch phases', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'active', completedAt: null, approvedAt: null },
            { phase: 'hull_form', status: 'pending', completedAt: null, approvedAt: null },
            ...PHASE_ORDER.slice(2).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');

      const state = orchestrator.getState();
      expect(state.designId).toBe('DESIGN-001');
      expect(state.activePhase).toBe('mission');
      expect(state.phases.mission).toBe('active');
    });

    it('should handle initialization errors', async () => {
      vi.mocked(phaseAPI.listPhases).mockRejectedValue(new Error('Network error'));

      await orchestrator.initialize('DESIGN-001');

      const state = orchestrator.getState();
      expect(state.error).toBe('Network error');
      expect(state.isLoading).toBe(false);
    });
  });

  describe('Phase Dependencies', () => {
    it('should not allow starting a phase with unmet dependencies', () => {
      // hull_form depends on mission being completed/approved
      const result = orchestrator.canStartPhase('hull_form');

      expect(result.canStart).toBe(false);
      expect(result.blockers.length).toBeGreaterThan(0);
      expect(result.blockers[0]).toContain('mission');
    });

    it('should allow starting mission phase (no dependencies)', () => {
      const result = orchestrator.canStartPhase('mission');

      expect(result.canStart).toBe(true);
      expect(result.blockers).toEqual([]);
    });

    it('should allow starting phase when dependencies are approved', async () => {
      // Set up state with mission approved
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'approved', completedAt: '2024-01-01', approvedAt: '2024-01-02' },
            ...PHASE_ORDER.slice(1).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');

      const result = orchestrator.canStartPhase('hull_form');
      expect(result.canStart).toBe(true);
    });

    it('should not allow starting already active phase', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'active', completedAt: null, approvedAt: null },
            ...PHASE_ORDER.slice(1).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');

      const result = orchestrator.canStartPhase('mission');
      expect(result.canStart).toBe(false);
      expect(result.blockers).toContain('mission is already active');
    });
  });

  describe('Start Phase', () => {
    beforeEach(async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: PHASE_ORDER.map((phase) => ({
            phase,
            status: 'pending' as PhaseStatus,
            completedAt: null,
            approvedAt: null,
          })),
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');
    });

    it('should start a valid phase', async () => {
      vi.mocked(phaseAPI.runPhase).mockResolvedValue({
        data: { success: true, message: 'Phase started' },
      } as any);

      const result = await orchestrator.startPhase('mission');

      expect(result.success).toBe(true);
      expect(result.toPhase).toBe('mission');

      const state = orchestrator.getState();
      expect(state.activePhase).toBe('mission');
      expect(state.phases.mission).toBe('active');
    });

    it('should emit phase_changed event', async () => {
      vi.mocked(phaseAPI.runPhase).mockResolvedValue({
        data: { success: true },
      } as any);

      await orchestrator.startPhase('mission');

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'prs:phase_changed',
          payload: expect.objectContaining({ phase: 'mission', status: 'active' }),
        })
      );
    });

    it('should fail if no design is loaded', async () => {
      orchestrator.reset();

      const result = await orchestrator.startPhase('mission');

      expect(result.success).toBe(false);
      expect(result.message).toBe('No design loaded');
    });

    it('should return blockers if phase cannot start', async () => {
      const result = await orchestrator.startPhase('hull_form');

      expect(result.success).toBe(false);
      expect(result.blockers).toBeDefined();
      expect(result.blockers!.length).toBeGreaterThan(0);
    });
  });

  describe('Complete Phase', () => {
    beforeEach(async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'active', completedAt: null, approvedAt: null },
            ...PHASE_ORDER.slice(1).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');
    });

    it('should complete a phase after validation passes', async () => {
      vi.mocked(phaseAPI.validatePhase).mockResolvedValue({
        data: { passed: true, errors: 0, warnings: 0 },
      } as any);

      const result = await orchestrator.completePhase('mission');

      expect(result.success).toBe(true);

      const state = orchestrator.getState();
      expect(state.phases.mission).toBe('completed');
      expect(state.pendingApproval).toContain('mission');
    });

    it('should fail completion if validation fails', async () => {
      vi.mocked(phaseAPI.validatePhase).mockResolvedValue({
        data: { passed: false, errors: 3, warnings: 1 },
      } as any);

      const result = await orchestrator.completePhase('mission');

      expect(result.success).toBe(false);
      expect(result.message).toContain('Validation failed');
    });

    it('should emit phase_completed event', async () => {
      vi.mocked(phaseAPI.validatePhase).mockResolvedValue({
        data: { passed: true, errors: 0, warnings: 0 },
      } as any);

      await orchestrator.completePhase('mission');

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'prs:phase_completed',
        })
      );
    });
  });

  describe('Approve Phase', () => {
    beforeEach(async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'completed', completedAt: '2024-01-01', approvedAt: null },
            ...PHASE_ORDER.slice(1).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');
    });

    it('should approve a completed phase', async () => {
      vi.mocked(phaseAPI.approvePhase).mockResolvedValue({
        data: { success: true },
      } as any);

      const result = await orchestrator.approvePhase('mission');

      expect(result.success).toBe(true);

      const state = orchestrator.getState();
      expect(state.phases.mission).toBe('approved');
      expect(state.pendingApproval).not.toContain('mission');
    });

    it('should not approve a non-completed phase', async () => {
      const result = await orchestrator.approvePhase('hull_form');

      expect(result.success).toBe(false);
      expect(result.message).toContain('must be completed');
    });

    it('should emit phase_approved event', async () => {
      vi.mocked(phaseAPI.approvePhase).mockResolvedValue({
        data: { success: true },
      } as any);

      await orchestrator.approvePhase('mission');

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'prs:phase_approved',
        })
      );
    });
  });

  describe('Milestones', () => {
    it('should add milestone on phase completion', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'active', completedAt: null, approvedAt: null },
            ...PHASE_ORDER.slice(1).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');

      vi.mocked(phaseAPI.validatePhase).mockResolvedValue({
        data: { passed: true, errors: 0, warnings: 0 },
      } as any);

      await orchestrator.completePhase('mission');

      const milestones = orchestrator.getMilestones();
      expect(milestones.length).toBeGreaterThan(0);
      expect(milestones[0].type).toBe('phase_completed');
    });

    it('should dismiss milestone', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'active', completedAt: null, approvedAt: null },
            ...PHASE_ORDER.slice(1).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');

      vi.mocked(phaseAPI.validatePhase).mockResolvedValue({
        data: { passed: true, errors: 0, warnings: 0 },
      } as any);

      await orchestrator.completePhase('mission');

      const milestones = orchestrator.getMilestones();
      const milestoneId = milestones[0].id;

      orchestrator.dismissMilestone(milestoneId);

      const remaining = orchestrator.getMilestones();
      expect(remaining.find(m => m.id === milestoneId)).toBeUndefined();
    });
  });

  describe('Progress', () => {
    it('should return 0% progress initially', () => {
      expect(orchestrator.getProgress()).toBe(0);
    });

    it('should calculate progress based on approved phases', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'approved', completedAt: '2024-01-01', approvedAt: '2024-01-02' },
            { phase: 'hull_form', status: 'approved', completedAt: '2024-01-03', approvedAt: '2024-01-04' },
            ...PHASE_ORDER.slice(2).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');

      // 2 out of 8 phases approved = 25%
      expect(orchestrator.getProgress()).toBe(25);
    });

    it('should return 100% when all phases approved', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: PHASE_ORDER.map((phase) => ({
            phase,
            status: 'approved' as PhaseStatus,
            completedAt: '2024-01-01',
            approvedAt: '2024-01-02',
          })),
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');

      expect(orchestrator.getProgress()).toBe(100);
      expect(orchestrator.isComplete()).toBe(true);
    });
  });

  describe('Reset', () => {
    it('should reset to initial state', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue({
        data: {
          phases: [
            { phase: 'mission', status: 'active', completedAt: null, approvedAt: null },
            ...PHASE_ORDER.slice(1).map((phase) => ({
              phase,
              status: 'pending' as PhaseStatus,
              completedAt: null,
              approvedAt: null,
            })),
          ],
          designHash: 'hash123',
        },
      } as any);

      await orchestrator.initialize('DESIGN-001');
      orchestrator.reset();

      const state = orchestrator.getState();
      expect(state.designId).toBeNull();
      expect(state.activePhase).toBeNull();
      expect(orchestrator.getMilestones()).toEqual([]);
    });
  });
});
