/**
 * MAGNET UI ARS Module Tests
 *
 * Tests for Auto Recommendation System components.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { motion, AnimatePresence } from 'framer-motion';

// Import components
import { ARSCard, ARSCardSkeleton } from '../../components/recommendations/ARS/ARSCard';
import { ImpactChip, ImpactChips } from '../../components/recommendations/ARS/ImpactChip';
import { TelemetryStrip } from '../../components/recommendations/ARS/TelemetryStrip';
import { PriorityIndicator, getPriorityName } from '../../components/recommendations/ARS/icons/PriorityIndicator';

// Import types
import type { ARSRecommendation, ARSImpact, ARSPriority } from '../../types/ars';

// ============================================================================
// Test Data
// ============================================================================

const mockImpact: ARSImpact = {
  metric: 'GM',
  change: 2.3,
  isPositive: true,
};

const mockNegativeImpact: ARSImpact = {
  metric: 'Weight',
  change: -5.2,
  unit: 'tonnes',
  isPositive: false,
};

const mockRecommendation: ARSRecommendation = {
  id: 'rec-1',
  schema_version: { major: 1, minor: 0, patch: 0 },
  priority: 2,
  category: 'stability',
  status: 'active',
  title: 'Adjust Fuel Tank Position',
  subtitle: 'Moving forward would improve stability',
  description: 'The current fuel tank placement causes a 2.3% reduction in GM at full load condition.',
  impact: mockImpact,
  secondaryImpacts: [mockNegativeImpact],
  actions: [
    { id: 'apply', label: 'Apply', type: 'apply', isPrimary: true },
    { id: 'explain', label: 'Explain', type: 'explain' },
    { id: 'dismiss', label: 'Dismiss', type: 'dismiss' },
  ],
  targetId: 'fuel_tank_1',
  marker: {
    position: { x: 5, y: 1, z: 0 },
  },
  timestamp: Date.now(),
};

const mockCriticalRecommendation: ARSRecommendation = {
  ...mockRecommendation,
  id: 'rec-critical',
  priority: 1,
  category: 'structure',
  title: 'Structural Integrity Warning',
  subtitle: 'Frame stress exceeds safety threshold',
};

// ============================================================================
// PriorityIndicator Tests
// ============================================================================

describe('PriorityIndicator', () => {
  it('renders critical priority icon', () => {
    render(<PriorityIndicator priority={1} size={20} />);
    expect(screen.getByLabelText('Critical priority')).toBeInTheDocument();
  });

  it('renders high priority icon', () => {
    render(<PriorityIndicator priority={2} size={20} />);
    expect(screen.getByLabelText('High priority')).toBeInTheDocument();
  });

  it('renders medium priority icon', () => {
    render(<PriorityIndicator priority={3} size={20} />);
    expect(screen.getByLabelText('Medium priority')).toBeInTheDocument();
  });

  it('renders low priority icon', () => {
    render(<PriorityIndicator priority={4} size={20} />);
    expect(screen.getByLabelText('Low priority')).toBeInTheDocument();
  });

  it('renders info priority icon', () => {
    render(<PriorityIndicator priority={5} size={20} />);
    expect(screen.getByLabelText('Informational')).toBeInTheDocument();
  });

  it('applies custom size', () => {
    const { container } = render(<PriorityIndicator priority={1} size={32} />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '32');
    expect(svg).toHaveAttribute('height', '32');
  });
});

describe('getPriorityName', () => {
  it('returns correct names for all priorities', () => {
    expect(getPriorityName(1)).toBe('Critical');
    expect(getPriorityName(2)).toBe('High');
    expect(getPriorityName(3)).toBe('Medium');
    expect(getPriorityName(4)).toBe('Low');
    expect(getPriorityName(5)).toBe('Info');
  });
});

// ============================================================================
// ImpactChip Tests
// ============================================================================

describe('ImpactChip', () => {
  it('renders metric name and change value', () => {
    render(<ImpactChip impact={mockImpact} />);
    expect(screen.getByText('GM')).toBeInTheDocument();
    expect(screen.getByText('+2.3%')).toBeInTheDocument();
  });

  it('renders negative change with unit', () => {
    render(<ImpactChip impact={mockNegativeImpact} />);
    expect(screen.getByText('Weight')).toBeInTheDocument();
    expect(screen.getByText('-5.2 tonnes')).toBeInTheDocument();
  });

  it('applies positive variant styling', () => {
    const { container } = render(<ImpactChip impact={mockImpact} />);
    // CSS modules hash class names, so check for partial class match
    const element = container.firstChild as HTMLElement;
    expect(element).toBeInTheDocument();
    expect(element.className).toMatch(/positive/i);
  });

  it('applies negative variant styling', () => {
    const { container } = render(<ImpactChip impact={mockNegativeImpact} />);
    // CSS modules hash class names, so check for partial class match
    const element = container.firstChild as HTMLElement;
    expect(element).toBeInTheDocument();
    expect(element.className).toMatch(/negative/i);
  });

  it('handles click events when clickable', () => {
    const handleClick = vi.fn();
    render(<ImpactChip impact={mockImpact} onClick={handleClick} />);

    fireEvent.click(screen.getByText('GM').closest('button')!);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders multiple chips with ImpactChips', () => {
    render(
      <ImpactChips
        impact={mockImpact}
        secondaryImpacts={[mockNegativeImpact]}
      />
    );

    expect(screen.getByText('GM')).toBeInTheDocument();
    expect(screen.getByText('Weight')).toBeInTheDocument();
  });
});

// ============================================================================
// ARSCard Tests
// ============================================================================

describe('ARSCard', () => {
  it('renders recommendation title and subtitle', () => {
    render(<ARSCard recommendation={mockRecommendation} />);

    expect(screen.getByText('Adjust Fuel Tank Position')).toBeInTheDocument();
    expect(screen.getByText('Moving forward would improve stability')).toBeInTheDocument();
  });

  it('renders priority indicator', () => {
    render(<ARSCard recommendation={mockRecommendation} />);
    expect(screen.getByLabelText('High priority')).toBeInTheDocument();
  });

  it('renders category badge', () => {
    render(<ARSCard recommendation={mockRecommendation} />);
    expect(screen.getByText('stability')).toBeInTheDocument();
  });

  it('renders impact chip', () => {
    render(<ARSCard recommendation={mockRecommendation} />);
    expect(screen.getByText('GM')).toBeInTheDocument();
  });

  it('renders action buttons', () => {
    render(<ARSCard recommendation={mockRecommendation} />);

    expect(screen.getByText('Apply')).toBeInTheDocument();
    expect(screen.getByText('Explain')).toBeInTheDocument();
  });

  it('handles click to select', () => {
    const handleClick = vi.fn();
    render(<ARSCard recommendation={mockRecommendation} onClick={handleClick} />);

    fireEvent.click(screen.getByRole('article'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('handles expand toggle', async () => {
    const handleToggle = vi.fn();
    render(
      <ARSCard
        recommendation={mockRecommendation}
        onToggleExpand={handleToggle}
      />
    );

    const expandButton = screen.getByLabelText('Expand');
    fireEvent.click(expandButton);
    expect(handleToggle).toHaveBeenCalledTimes(1);
  });

  it('shows description when expanded', async () => {
    render(
      <ARSCard
        recommendation={mockRecommendation}
        isExpanded={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/current fuel tank placement/i)).toBeInTheDocument();
    });
  });

  it('handles action button clicks', () => {
    const handleAction = vi.fn();
    render(
      <ARSCard
        recommendation={mockRecommendation}
        onAction={handleAction}
      />
    );

    fireEvent.click(screen.getByText('Apply'));
    expect(handleAction).toHaveBeenCalledWith('apply');
  });

  it('applies critical variant for priority 1', () => {
    const { container } = render(
      <ARSCard recommendation={mockCriticalRecommendation} />
    );

    // The GlassCard should have critical variant
    expect(container.querySelector('[data-variant="critical"]')).toBeInTheDocument();
  });

  it('applies selected styling', () => {
    const { container } = render(
      <ARSCard recommendation={mockRecommendation} isSelected={true} />
    );

    expect(container.querySelector('[data-selected="true"]')).toBeInTheDocument();
  });
});

describe('ARSCardSkeleton', () => {
  it('renders skeleton loading state', () => {
    const { container } = render(<ARSCardSkeleton />);
    // CSS modules hash class names, so check that element exists and has skeleton class
    const element = container.firstChild as HTMLElement;
    expect(element).toBeInTheDocument();
    expect(element.className).toMatch(/skeleton/i);
  });
});

// ============================================================================
// TelemetryStrip Tests
// ============================================================================

describe('TelemetryStrip', () => {
  it('renders recommendation in strip', () => {
    render(<TelemetryStrip recommendation={mockRecommendation} />);

    expect(screen.getByText('Adjust Fuel Tank Position')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders queue length indicator', () => {
    render(
      <TelemetryStrip
        recommendation={mockRecommendation}
        queueLength={3}
      />
    );

    expect(screen.getByText('+3')).toBeInTheDocument();
  });

  it('handles dismiss action', () => {
    const handleDismiss = vi.fn();
    render(
      <TelemetryStrip
        recommendation={mockRecommendation}
        onDismiss={handleDismiss}
      />
    );

    fireEvent.click(screen.getByLabelText('Dismiss'));
    expect(handleDismiss).toHaveBeenCalledTimes(1);
  });

  it('handles view action', () => {
    const handleView = vi.fn();
    render(
      <TelemetryStrip
        recommendation={mockRecommendation}
        onView={handleView}
      />
    );

    fireEvent.click(screen.getByText('View'));
    expect(handleView).toHaveBeenCalledTimes(1);
  });

  it('renders apply button for apply actions', () => {
    render(<TelemetryStrip recommendation={mockRecommendation} />);
    expect(screen.getByText('Apply')).toBeInTheDocument();
  });

  it('does not render when recommendation is null', () => {
    const { container } = render(<TelemetryStrip recommendation={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows progress bar with auto-dismiss', () => {
    const { container } = render(
      <TelemetryStrip
        recommendation={mockRecommendation}
        autoDismissMs={10000}
      />
    );

    // CSS modules hash class names, so look for element with progressTrack in class
    const progressElement = Array.from(container.querySelectorAll('*')).find(
      el => el.className && el.className.toString().match(/progressTrack/i)
    );
    expect(progressElement).toBeInTheDocument();
  });
});

// ============================================================================
// Integration Tests
// ============================================================================

describe('ARS Component Integration', () => {
  it('renders complete recommendation flow', async () => {
    const handleSelect = vi.fn();
    const handleExpand = vi.fn();
    const handleAction = vi.fn();

    render(
      <ARSCard
        recommendation={mockRecommendation}
        isSelected={false}
        isExpanded={false}
        onClick={handleSelect}
        onToggleExpand={handleExpand}
        onAction={handleAction}
      />
    );

    // Click to select
    fireEvent.click(screen.getByRole('article'));
    expect(handleSelect).toHaveBeenCalled();

    // Expand
    fireEvent.click(screen.getByLabelText('Expand'));
    expect(handleExpand).toHaveBeenCalled();

    // Apply action
    fireEvent.click(screen.getByText('Apply'));
    expect(handleAction).toHaveBeenCalledWith('apply');
  });

  it('handles telemetry to card transition', () => {
    const handleTelemetryView = vi.fn();
    const handleCardClick = vi.fn();

    const { rerender } = render(
      <TelemetryStrip
        recommendation={mockRecommendation}
        onView={handleTelemetryView}
      />
    );

    // Click view in telemetry
    fireEvent.click(screen.getByText('View'));
    expect(handleTelemetryView).toHaveBeenCalled();

    // Simulate transition to card view
    rerender(
      <ARSCard
        recommendation={mockRecommendation}
        isSelected={true}
        onClick={handleCardClick}
      />
    );

    expect(screen.getByRole('article')).toBeInTheDocument();
  });
});

// ============================================================================
// Accessibility Tests
// ============================================================================

describe('ARS Accessibility', () => {
  it('ARSCard has proper role and is focusable', () => {
    render(<ARSCard recommendation={mockRecommendation} />);

    const card = screen.getByRole('article');
    expect(card).toHaveAttribute('tabIndex', '0');
  });

  it('TelemetryStrip has alert role', () => {
    render(<TelemetryStrip recommendation={mockRecommendation} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('Priority indicators have accessible labels', () => {
    const priorities: ARSPriority[] = [1, 2, 3, 4, 5];

    priorities.forEach((priority) => {
      const { unmount } = render(<PriorityIndicator priority={priority} />);
      expect(screen.getByLabelText(/priority|informational/i)).toBeInTheDocument();
      unmount();
    });
  });

  it('Expand toggle has aria-expanded', () => {
    const { rerender } = render(
      <ARSCard recommendation={mockRecommendation} isExpanded={false} />
    );

    expect(screen.getByLabelText('Expand')).toHaveAttribute('aria-expanded', 'false');

    rerender(<ARSCard recommendation={mockRecommendation} isExpanded={true} />);
    expect(screen.getByLabelText('Collapse')).toHaveAttribute('aria-expanded', 'true');
  });
});
