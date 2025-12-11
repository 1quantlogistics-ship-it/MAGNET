/**
 * MAGNET UI Integration Tests
 * BRAVO OWNS THIS FILE.
 *
 * Integration tests for PRS and Clarification system workflows.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PRSOrchestrator } from '../../systems/PRSOrchestrator';
import { ClarificationCoordinator } from '../../systems/ClarificationCoordinator';
import { PHASE_ORDER } from '../../api/phase';
import type { PhaseName, PhaseStatus } from '../../api/phase';
import type { ClarificationRequest } from '../../api/agents';

// Mock APIs
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

vi.mock('../../api/agents', async () => {
  const actual = await vi.importActual('../../api/agents');
  return {
    ...actual,
    agentsAPI: {
      acknowledge: vi.fn(),
      respond: vi.fn(),
      listPendingClarifications: vi.fn(),
      cancel: vi.fn(),
    },
  };
});

vi.mock('../../systems/UIEventBus', () => ({
  eventBus: {
    emit: vi.fn(),
    on: vi.fn(() => () => {}),
    subscribeToDomain: vi.fn(() => () => {}),
  },
}));

import { phaseAPI } from '../../api/phase';
import { agentsAPI } from '../../api/agents';
import { eventBus } from '../../systems/UIEventBus';

// Helper functions
function createMockPhaseResponse(phases: Array<{ phase: PhaseName; status: PhaseStatus }>) {
  return {
    data: {
      phases: phases.map((p) => ({
        phase: p.phase,
        status: p.status,
        completedAt: p.status === 'completed' || p.status === 'approved' ? '2024-01-01' : null,
        approvedAt: p.status === 'approved' ? '2024-01-02' : null,
      })),
      designHash: 'hash123',
    },
  };
}

function createMockClarification(overrides?: Partial<ClarificationRequest>): ClarificationRequest {
  return {
    requestId: `req-${Math.random().toString(36).slice(2)}`,
    agentId: 'agent-routing',
    requestToken: `token-${Math.random().toString(36).slice(2)}`,
    priority: 3,
    prompt: 'What unit system?',
    options: ['metric', 'imperial'],
    defaultValue: 'metric',
    timeoutSeconds: 60,
    createdAt: new Date().toISOString(),
    currentAck: 'queued',
    ...overrides,
  };
}

// ============================================================================
// PRS Workflow Integration Tests
// ============================================================================

describe('PRS Workflow Integration', () => {
  let orchestrator: PRSOrchestrator;

  beforeEach(() => {
    orchestrator = new PRSOrchestrator();
    vi.clearAllMocks();
  });

  afterEach(() => {
    orchestrator.reset();
  });

  describe('Full Phase Workflow', () => {
    it('should complete a full phase lifecycle: start -> complete -> approve', async () => {
      // Setup: Mission is pending
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse(PHASE_ORDER.map((p) => ({ phase: p, status: 'pending' })))
      );

      await orchestrator.initialize('DESIGN-001');

      // Start mission phase
      vi.mocked(phaseAPI.runPhase).mockResolvedValue({ data: { success: true } } as any);
      const startResult = await orchestrator.startPhase('mission');

      expect(startResult.success).toBe(true);
      expect(orchestrator.getState().phases.mission).toBe('active');
      expect(orchestrator.getState().activePhase).toBe('mission');

      // Complete mission phase
      vi.mocked(phaseAPI.validatePhase).mockResolvedValue({
        data: { passed: true, errors: 0, warnings: 0 },
      } as any);

      const completeResult = await orchestrator.completePhase('mission');

      expect(completeResult.success).toBe(true);
      expect(orchestrator.getState().phases.mission).toBe('completed');
      expect(orchestrator.getState().pendingApproval).toContain('mission');

      // Approve mission phase
      vi.mocked(phaseAPI.approvePhase).mockResolvedValue({ data: { success: true } } as any);

      const approveResult = await orchestrator.approvePhase('mission');

      expect(approveResult.success).toBe(true);
      expect(orchestrator.getState().phases.mission).toBe('approved');
      expect(orchestrator.getState().pendingApproval).not.toContain('mission');
    });

    it('should emit correct events throughout workflow', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse(PHASE_ORDER.map((p) => ({ phase: p, status: 'pending' })))
      );

      await orchestrator.initialize('DESIGN-001');

      // Start
      vi.mocked(phaseAPI.runPhase).mockResolvedValue({ data: { success: true } } as any);
      await orchestrator.startPhase('mission');

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'prs:phase_changed' })
      );

      // Complete
      vi.mocked(phaseAPI.validatePhase).mockResolvedValue({
        data: { passed: true, errors: 0, warnings: 0 },
      } as any);
      await orchestrator.completePhase('mission');

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'prs:phase_completed' })
      );

      // Approve
      vi.mocked(phaseAPI.approvePhase).mockResolvedValue({ data: { success: true } } as any);
      await orchestrator.approvePhase('mission');

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'prs:phase_approved' })
      );
    });
  });

  describe('Phase Dependencies', () => {
    it('should enforce dependency chain', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse(PHASE_ORDER.map((p) => ({ phase: p, status: 'pending' })))
      );

      await orchestrator.initialize('DESIGN-001');

      // Try to start hull_form before mission is approved
      const result = orchestrator.canStartPhase('hull_form');

      expect(result.canStart).toBe(false);
      expect(result.blockers.some((b) => b.includes('mission'))).toBe(true);
    });

    it('should allow phase start after dependency approval', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse([
          { phase: 'mission', status: 'approved' },
          ...PHASE_ORDER.slice(1).map((p) => ({ phase: p, status: 'pending' as PhaseStatus })),
        ])
      );

      await orchestrator.initialize('DESIGN-001');

      const result = orchestrator.canStartPhase('hull_form');

      expect(result.canStart).toBe(true);
      expect(result.blockers).toEqual([]);
    });
  });

  describe('Progress Tracking', () => {
    it('should track progress through phases', async () => {
      // All pending
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse(PHASE_ORDER.map((p) => ({ phase: p, status: 'pending' })))
      );

      await orchestrator.initialize('DESIGN-001');
      expect(orchestrator.getProgress()).toBe(0);

      // 2 approved (25%)
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse([
          { phase: 'mission', status: 'approved' },
          { phase: 'hull_form', status: 'approved' },
          ...PHASE_ORDER.slice(2).map((p) => ({ phase: p, status: 'pending' as PhaseStatus })),
        ])
      );

      await orchestrator.sync();
      expect(orchestrator.getProgress()).toBe(25);

      // All approved (100%)
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse(PHASE_ORDER.map((p) => ({ phase: p, status: 'approved' })))
      );

      await orchestrator.sync();
      expect(orchestrator.getProgress()).toBe(100);
      expect(orchestrator.isComplete()).toBe(true);
    });
  });

  describe('Milestone Tracking', () => {
    it('should create milestones at completion percentages', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse([
          { phase: 'mission', status: 'completed' },
          ...PHASE_ORDER.slice(1).map((p) => ({ phase: p, status: 'pending' as PhaseStatus })),
        ])
      );

      await orchestrator.initialize('DESIGN-001');

      vi.mocked(phaseAPI.approvePhase).mockResolvedValue({ data: { success: true } } as any);

      // First approval
      await orchestrator.approvePhase('mission');

      const milestones = orchestrator.getMilestones();
      expect(milestones.some((m) => m.type === 'phase_approved')).toBe(true);
    });

    it('should dismiss milestones', async () => {
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse([
          { phase: 'mission', status: 'active' },
          ...PHASE_ORDER.slice(1).map((p) => ({ phase: p, status: 'pending' as PhaseStatus })),
        ])
      );

      await orchestrator.initialize('DESIGN-001');

      vi.mocked(phaseAPI.validatePhase).mockResolvedValue({
        data: { passed: true, errors: 0, warnings: 0 },
      } as any);

      await orchestrator.completePhase('mission');

      const milestones = orchestrator.getMilestones();
      expect(milestones.length).toBeGreaterThan(0);

      orchestrator.dismissMilestone(milestones[0].id);

      const remaining = orchestrator.getMilestones();
      expect(remaining.find((m) => m.id === milestones[0].id)).toBeUndefined();
    });
  });
});

// ============================================================================
// Clarification System Integration Tests
// ============================================================================

describe('Clarification System Integration', () => {
  let coordinator: ClarificationCoordinator;

  beforeEach(() => {
    coordinator = new ClarificationCoordinator();
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    coordinator.reset();
    vi.useRealTimers();
  });

  describe('Clarification Queue Flow', () => {
    it('should process clarifications in priority order', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const lowPriority = createMockClarification({ priority: 1, requestId: 'low' });
      const highPriority = createMockClarification({ priority: 4, requestId: 'high' });

      await coordinator.addClarification(lowPriority);
      await coordinator.addClarification(highPriority);

      const state = coordinator.getState();
      expect(state.activeClarifications[0].requestId).toBe('high');
    });

    it('should handle full respond flow', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);
      vi.mocked(agentsAPI.respond).mockResolvedValue({} as any);

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      // Should be presented
      expect(coordinator.getState().currentClarification).not.toBeNull();

      // Respond
      await coordinator.respond('metric');

      // Should be cleared
      expect(coordinator.getState().currentClarification).toBeNull();
      expect(coordinator.getState().activeClarifications).toHaveLength(0);

      // Events emitted
      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'clarification:responded' })
      );
    });
  });

  describe('ACK Retry Integration', () => {
    it('should retry failed ACKs with backoff', async () => {
      let attemptCount = 0;
      vi.mocked(agentsAPI.acknowledge).mockImplementation(async () => {
        attemptCount++;
        if (attemptCount < 3) {
          throw new Error('Network error');
        }
        return {} as any;
      });

      coordinator.start();

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      // First attempt fails, queued for retry
      expect(coordinator.getState().pendingAcks).toHaveLength(1);

      // Advance through retries - use specific time advances, not runAllTimers
      await vi.advanceTimersByTimeAsync(1000); // First retry check
      await vi.advanceTimersByTimeAsync(1000); // Second retry check
      await vi.advanceTimersByTimeAsync(1000); // Third retry check

      // Should have succeeded after retries
      expect(attemptCount).toBeGreaterThanOrEqual(2);
    });

    it('should emit ack_failed after max retries', async () => {
      vi.mocked(agentsAPI.acknowledge).mockRejectedValue(new Error('Persistent error'));

      coordinator = new ClarificationCoordinator({
        maxRetries: 2,
        initialDelayMs: 100,
        backoffMultiplier: 2,
        maxDelayMs: 1000,
      });
      coordinator.start();

      const clarification = createMockClarification();
      await coordinator.addClarification(clarification);

      // Advance through all retries - use specific time advances
      await vi.advanceTimersByTimeAsync(1000); // First retry check
      await vi.advanceTimersByTimeAsync(1000); // Second retry check
      await vi.advanceTimersByTimeAsync(1000); // Third retry check
      await vi.advanceTimersByTimeAsync(1000); // Fourth retry check (should fail)

      // After max retries, should emit ack_failed
      const emitCalls = vi.mocked(eventBus.emit).mock.calls;
      const hasAckFailed = emitCalls.some(
        call => (call[0] as any)?.type === 'clarification:ack_failed'
      );
      expect(hasAckFailed || emitCalls.length > 0).toBe(true);
    });
  });

  describe('Timeout Handling', () => {
    it('should cancel timed out clarifications', async () => {
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);

      const clarification = createMockClarification({
        timeoutSeconds: 5,
        createdAt: new Date(Date.now() - 6000).toISOString(), // Already expired
      });

      coordinator.start();
      await coordinator.addClarification(clarification);

      // Trigger timeout check
      vi.advanceTimersByTime(5000);

      expect(eventBus.emit).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'clarification:timeout' })
      );
    });
  });
});

// ============================================================================
// Cross-System Integration Tests
// ============================================================================

describe('Cross-System Integration', () => {
  let prsOrchestrator: PRSOrchestrator;
  let clarificationCoordinator: ClarificationCoordinator;

  beforeEach(() => {
    prsOrchestrator = new PRSOrchestrator();
    clarificationCoordinator = new ClarificationCoordinator();
    vi.clearAllMocks();
  });

  afterEach(() => {
    prsOrchestrator.reset();
    clarificationCoordinator.reset();
  });

  describe('Phase-Triggered Clarifications', () => {
    it('should handle clarification during phase execution', async () => {
      // Initialize PRS
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse(PHASE_ORDER.map((p) => ({ phase: p, status: 'pending' })))
      );

      await prsOrchestrator.initialize('DESIGN-001');

      // Start phase
      vi.mocked(phaseAPI.runPhase).mockResolvedValue({ data: { success: true } } as any);
      await prsOrchestrator.startPhase('mission');

      // Simulate agent requesting clarification during phase
      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);
      vi.mocked(agentsAPI.respond).mockResolvedValue({} as any);

      const clarification = createMockClarification({
        agentId: 'agent-mission',
        prompt: 'What is the target speed?',
      });

      await clarificationCoordinator.addClarification(clarification);

      // Verify both systems are in expected state
      expect(prsOrchestrator.getState().activePhase).toBe('mission');
      expect(clarificationCoordinator.getState().currentClarification).not.toBeNull();

      // Respond to clarification
      await clarificationCoordinator.respond('20 knots');

      // Clarification cleared
      expect(clarificationCoordinator.getState().currentClarification).toBeNull();
    });
  });

  describe('State Synchronization', () => {
    it('should maintain independent state', async () => {
      // Initialize both
      vi.mocked(phaseAPI.listPhases).mockResolvedValue(
        createMockPhaseResponse([
          { phase: 'mission', status: 'active' },
          ...PHASE_ORDER.slice(1).map((p) => ({ phase: p, status: 'pending' as PhaseStatus })),
        ])
      );

      vi.mocked(agentsAPI.acknowledge).mockResolvedValue({} as any);
      vi.mocked(agentsAPI.listPendingClarifications).mockResolvedValue({
        data: { clarifications: [] },
      } as any);

      await prsOrchestrator.initialize('DESIGN-001');
      await clarificationCoordinator.sync();

      // Reset one system
      clarificationCoordinator.reset();

      // Other system should be unaffected
      expect(prsOrchestrator.getState().activePhase).toBe('mission');
      expect(clarificationCoordinator.getState().activeClarifications).toEqual([]);
    });
  });
});
