/**
 * MAGNET UI PRS Module Tests
 * BRAVO OWNS THIS FILE.
 *
 * Tests for Phase Review System components.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Import components
import { PhaseItem } from '../../components/prs/PhaseItem';
import { PhaseProgress, CircularPhaseProgress } from '../../components/prs/PhaseProgress';
import { MilestoneToast, MilestoneToastContainer } from '../../components/prs/MilestoneToast';

// Import types
import type { PhaseName, PhaseStatus } from '../../api/phase';
import type { Milestone } from '../../stores/domain/prsStore';

// ============================================================================
// Test Data
// ============================================================================

const mockMilestone: Milestone = {
  id: 'milestone-1',
  type: 'phase_completed',
  phase: 'mission',
  message: 'Mission Definition completed',
  timestamp: Date.now(),
  dismissed: false,
};

const mockApprovalMilestone: Milestone = {
  id: 'milestone-2',
  type: 'phase_approved',
  phase: 'hull_form',
  message: 'Hull Form approved',
  timestamp: Date.now(),
  dismissed: false,
};

const mockDesignCompleteMilestone: Milestone = {
  id: 'milestone-3',
  type: 'design_complete',
  phase: 'production',
  message: 'Design review complete!',
  timestamp: Date.now(),
  dismissed: false,
};

// ============================================================================
// PhaseItem Tests
// ============================================================================

describe('PhaseItem', () => {
  const defaultProps = {
    phase: 'mission' as PhaseName,
    status: 'pending' as PhaseStatus,
    isActive: false,
    canStart: true,
    canApprove: false,
  };

  it('renders phase label', () => {
    render(<PhaseItem {...defaultProps} />);
    expect(screen.getByText('Mission Definition')).toBeInTheDocument();
  });

  it('renders phase status', () => {
    render(<PhaseItem {...defaultProps} />);
    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  it('renders Start button when canStart is true and status is pending', () => {
    render(<PhaseItem {...defaultProps} canStart={true} status="pending" />);
    expect(screen.getByRole('button', { name: /start mission definition/i })).toBeInTheDocument();
  });

  it('does not render Start button when status is not pending', () => {
    render(<PhaseItem {...defaultProps} canStart={true} status="active" />);
    expect(screen.queryByRole('button', { name: /start/i })).not.toBeInTheDocument();
  });

  it('renders Approve button when canApprove is true and status is completed', () => {
    render(<PhaseItem {...defaultProps} canApprove={true} status="completed" />);
    expect(screen.getByRole('button', { name: /approve mission definition/i })).toBeInTheDocument();
  });

  it('does not render Approve button when status is not completed', () => {
    render(<PhaseItem {...defaultProps} canApprove={true} status="pending" />);
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const onSelect = vi.fn();
    render(<PhaseItem {...defaultProps} onSelect={onSelect} />);

    // Get the main container button (not the action button)
    // The container has aria-label like "Mission Definition: pending"
    fireEvent.click(screen.getByRole('button', { name: /mission definition: pending/i }));
    expect(onSelect).toHaveBeenCalledWith('mission');
  });

  it('calls onStart when Start button clicked', () => {
    const onStart = vi.fn();
    render(<PhaseItem {...defaultProps} onStart={onStart} />);

    fireEvent.click(screen.getByRole('button', { name: /start mission definition/i }));
    expect(onStart).toHaveBeenCalledWith('mission');
  });

  it('calls onApprove when Approve button clicked', () => {
    const onApprove = vi.fn();
    render(<PhaseItem {...defaultProps} canApprove={true} status="completed" onApprove={onApprove} />);

    fireEvent.click(screen.getByRole('button', { name: /approve mission definition/i }));
    expect(onApprove).toHaveBeenCalledWith('mission');
  });

  it('prevents event propagation when action button clicked', () => {
    const onSelect = vi.fn();
    const onStart = vi.fn();
    render(<PhaseItem {...defaultProps} onSelect={onSelect} onStart={onStart} />);

    fireEvent.click(screen.getByRole('button', { name: /start mission definition/i }));
    expect(onStart).toHaveBeenCalled();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('has correct aria-label', () => {
    render(<PhaseItem {...defaultProps} status="active" />);
    expect(screen.getByRole('button', { name: /mission definition: active/i })).toBeInTheDocument();
  });

  describe('Phase Labels', () => {
    const phases: Array<{ phase: PhaseName; label: string }> = [
      { phase: 'mission', label: 'Mission Definition' },
      { phase: 'hull_form', label: 'Hull Form' },
      { phase: 'structure', label: 'Structure' },
      { phase: 'propulsion', label: 'Propulsion' },
      { phase: 'systems', label: 'Systems' },
      { phase: 'weight_stability', label: 'Weight & Stability' },
      { phase: 'compliance', label: 'Compliance' },
      { phase: 'production', label: 'Production' },
    ];

    phases.forEach(({ phase, label }) => {
      it(`renders correct label for ${phase}`, () => {
        render(<PhaseItem {...defaultProps} phase={phase} />);
        expect(screen.getByText(label)).toBeInTheDocument();
      });
    });
  });

  describe('Status Icons', () => {
    const statuses: PhaseStatus[] = ['pending', 'active', 'completed', 'approved', 'failed', 'blocked'];

    statuses.forEach((status) => {
      it(`renders icon for ${status} status`, () => {
        const { container } = render(<PhaseItem {...defaultProps} status={status} />);
        // Icon should be present (aria-hidden)
        // Find the icon span element
        const icon = container.querySelector('[aria-hidden="true"]');
        expect(icon).toBeInTheDocument();
      });
    });
  });
});

// ============================================================================
// PhaseProgress Tests
// ============================================================================

describe('PhaseProgress', () => {
  const defaultProps = {
    progress: 0.5,
    completedCount: 4,
    totalCount: 8,
    activePhase: 'systems' as PhaseName,
  };

  it('renders progress percentage', () => {
    render(<PhaseProgress {...defaultProps} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('renders phase count', () => {
    render(<PhaseProgress {...defaultProps} />);
    expect(screen.getByText(/4 \/ 8 phases/)).toBeInTheDocument();
  });

  it('renders active phase name', () => {
    render(<PhaseProgress {...defaultProps} />);
    expect(screen.getByText('Systems')).toBeInTheDocument();
  });

  it('clamps progress to 0-1', () => {
    render(<PhaseProgress {...defaultProps} progress={1.5} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('handles negative progress', () => {
    render(<PhaseProgress {...defaultProps} progress={-0.5} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('respects showPercentage prop', () => {
    render(<PhaseProgress {...defaultProps} showPercentage={false} />);
    expect(screen.queryByText('50%')).not.toBeInTheDocument();
  });

  it('respects showCount prop', () => {
    render(<PhaseProgress {...defaultProps} showCount={false} />);
    expect(screen.queryByText(/4 \/ 8/)).not.toBeInTheDocument();
  });

  it('handles null activePhase', () => {
    render(<PhaseProgress {...defaultProps} activePhase={null} />);
    expect(screen.queryByText('Systems')).not.toBeInTheDocument();
  });

  describe('Size Variants', () => {
    (['small', 'medium', 'large'] as const).forEach((size) => {
      it(`renders ${size} size`, () => {
        const { container } = render(<PhaseProgress {...defaultProps} size={size} />);
        // CSS modules hash class names, so check for partial class match
        const element = container.firstChild as HTMLElement;
        expect(element).toBeInTheDocument();
        // With CSS modules, the class name contains the size variant
        expect(element.className).toMatch(new RegExp(size, 'i'));
      });
    });
  });
});

describe('CircularPhaseProgress', () => {
  const defaultProps = {
    progress: 0.75,
  };

  it('renders percentage', () => {
    render(<CircularPhaseProgress {...defaultProps} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('renders SVG circles', () => {
    const { container } = render(<CircularPhaseProgress {...defaultProps} />);
    const circles = container.querySelectorAll('circle');
    expect(circles.length).toBe(2); // Background + progress
  });

  it('respects size prop', () => {
    const { container } = render(<CircularPhaseProgress {...defaultProps} size={100} />);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('width')).toBe('100');
    expect(svg?.getAttribute('height')).toBe('100');
  });

  it('respects showPercentage prop', () => {
    render(<CircularPhaseProgress {...defaultProps} showPercentage={false} />);
    expect(screen.queryByText('75%')).not.toBeInTheDocument();
  });

  it('renders active phase when provided', () => {
    render(<CircularPhaseProgress {...defaultProps} activePhase="hull_form" />);
    expect(screen.getByText('Hull')).toBeInTheDocument();
  });
});

// ============================================================================
// MilestoneToast Tests
// ============================================================================

describe('MilestoneToast', () => {
  const defaultProps = {
    milestone: mockMilestone,
    onDismiss: vi.fn(),
  };

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders milestone message', () => {
    render(<MilestoneToast {...defaultProps} />);
    expect(screen.getByText('Mission Definition completed')).toBeInTheDocument();
  });

  it('renders dismiss button', () => {
    render(<MilestoneToast {...defaultProps} />);
    expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button clicked', async () => {
    const onDismiss = vi.fn();
    render(<MilestoneToast {...defaultProps} onDismiss={onDismiss} />);

    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));

    // Wait for animation
    vi.advanceTimersByTime(200);

    expect(onDismiss).toHaveBeenCalledWith(mockMilestone.id);
  });

  it('auto-dismisses after timeout', () => {
    const onDismiss = vi.fn();
    render(<MilestoneToast {...defaultProps} onDismiss={onDismiss} autoDismissMs={3000} />);

    expect(onDismiss).not.toHaveBeenCalled();

    vi.advanceTimersByTime(3000);

    // Wait for exit animation
    vi.advanceTimersByTime(200);

    expect(onDismiss).toHaveBeenCalledWith(mockMilestone.id);
  });

  it('does not auto-dismiss when autoDismissMs is 0', () => {
    const onDismiss = vi.fn();
    render(<MilestoneToast {...defaultProps} onDismiss={onDismiss} autoDismissMs={0} />);

    vi.advanceTimersByTime(10000);

    expect(onDismiss).not.toHaveBeenCalled();
  });

  it('calls onClick when toast clicked', () => {
    const onClick = vi.fn();
    render(<MilestoneToast {...defaultProps} onClick={onClick} />);

    fireEvent.click(screen.getByRole('alert'));
    expect(onClick).toHaveBeenCalledWith(mockMilestone);
  });

  it('has alert role for accessibility', () => {
    render(<MilestoneToast {...defaultProps} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  describe('Milestone Types', () => {
    it('renders phase_completed milestone', () => {
      render(<MilestoneToast {...defaultProps} />);
      expect(screen.getByText(/completed/i)).toBeInTheDocument();
    });

    it('renders phase_approved milestone', () => {
      render(<MilestoneToast {...defaultProps} milestone={mockApprovalMilestone} />);
      expect(screen.getByText(/approved/i)).toBeInTheDocument();
    });

    it('renders design_complete milestone', () => {
      render(<MilestoneToast {...defaultProps} milestone={mockDesignCompleteMilestone} />);
      expect(screen.getByText(/complete/i)).toBeInTheDocument();
    });
  });
});

describe('MilestoneToastContainer', () => {
  const defaultProps = {
    milestones: [mockMilestone, mockApprovalMilestone],
    onDismiss: vi.fn(),
  };

  it('renders multiple toasts', () => {
    render(<MilestoneToastContainer {...defaultProps} />);
    expect(screen.getAllByRole('alert')).toHaveLength(2);
  });

  it('limits toasts to maxToasts', () => {
    const milestones = [
      mockMilestone,
      mockApprovalMilestone,
      mockDesignCompleteMilestone,
      { ...mockMilestone, id: 'extra-1' },
    ];

    render(<MilestoneToastContainer {...defaultProps} milestones={milestones} maxToasts={2} />);
    expect(screen.getAllByRole('alert')).toHaveLength(2);
  });

  it('applies position classes', () => {
    const { container } = render(
      <MilestoneToastContainer {...defaultProps} position="bottom-left" />
    );
    // CSS modules hash class names, so check for partial class match
    const element = container.firstChild as HTMLElement;
    expect(element).toBeInTheDocument();
    expect(element.className).toMatch(/bottom-left/i);
  });

  describe('Position Variants', () => {
    const positions = ['top-right', 'top-left', 'bottom-right', 'bottom-left'] as const;

    positions.forEach((position) => {
      it(`renders ${position} position`, () => {
        const { container } = render(
          <MilestoneToastContainer {...defaultProps} position={position} />
        );
        // CSS modules hash class names, so check for partial class match
        const element = container.firstChild as HTMLElement;
        expect(element).toBeInTheDocument();
        // Convert position for regex (e.g., "bottom-left" -> /bottom-left/i)
        expect(element.className).toMatch(new RegExp(position, 'i'));
      });
    });
  });
});
