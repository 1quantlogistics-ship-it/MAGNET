/**
 * MAGNET UI PhaseItem Component
 * BRAVO OWNS THIS FILE.
 *
 * Individual phase row in the PRS panel.
 * Displays phase status with visual indicators.
 */

import React, { useCallback, useMemo } from 'react';
import type { PhaseName, PhaseStatus } from '../../api/phase';
import styles from './PhaseItem.module.css';

// ============================================================================
// Types
// ============================================================================

export interface PhaseItemProps {
  /** Phase name */
  phase: PhaseName;
  /** Current status */
  status: PhaseStatus;
  /** Whether this phase is currently active */
  isActive: boolean;
  /** Whether this phase can be started */
  canStart: boolean;
  /** Whether this phase can be approved */
  canApprove: boolean;
  /** Click handler for phase selection */
  onSelect?: (phase: PhaseName) => void;
  /** Click handler for start action */
  onStart?: (phase: PhaseName) => void;
  /** Click handler for approve action */
  onApprove?: (phase: PhaseName) => void;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Human-readable phase names
 */
const PHASE_LABELS: Record<PhaseName, string> = {
  mission: 'Mission Definition',
  hull_form: 'Hull Form',
  structure: 'Structure',
  propulsion: 'Propulsion',
  systems: 'Systems',
  weight_stability: 'Weight & Stability',
  compliance: 'Compliance',
  production: 'Production',
};

/**
 * Status icons (using text for now, can be replaced with SVG)
 */
const STATUS_ICONS: Record<PhaseStatus, string> = {
  pending: '\u25CB',     // Empty circle
  active: '\u25D4',      // Circle with upper-right quadrant
  completed: '\u25CF',   // Filled circle
  approved: '\u2713',    // Checkmark
  failed: '\u2717',      // X mark
  blocked: '\u25A0',     // Filled square
};

// ============================================================================
// Component
// ============================================================================

export const PhaseItem: React.FC<PhaseItemProps> = ({
  phase,
  status,
  isActive,
  canStart,
  canApprove,
  onSelect,
  onStart,
  onApprove,
}) => {
  // Handlers
  const handleClick = useCallback(() => {
    onSelect?.(phase);
  }, [phase, onSelect]);

  const handleStart = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onStart?.(phase);
  }, [phase, onStart]);

  const handleApprove = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onApprove?.(phase);
  }, [phase, onApprove]);

  // Computed classes
  const containerClass = useMemo(() => {
    const classes = [styles.container];
    classes.push(styles[`status-${status}`]);
    if (isActive) classes.push(styles.active);
    return classes.join(' ');
  }, [status, isActive]);

  const iconClass = useMemo(() => {
    const classes = [styles.icon];
    classes.push(styles[`icon-${status}`]);
    return classes.join(' ');
  }, [status]);

  return (
    <div
      className={containerClass}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      aria-label={`${PHASE_LABELS[phase]}: ${status}`}
    >
      <span className={iconClass} aria-hidden="true">
        {STATUS_ICONS[status]}
      </span>

      <div className={styles.content}>
        <span className={styles.label}>{PHASE_LABELS[phase]}</span>
        <span className={styles.status}>{status}</span>
      </div>

      <div className={styles.actions}>
        {canStart && status === 'pending' && (
          <button
            className={styles.actionButton}
            onClick={handleStart}
            aria-label={`Start ${PHASE_LABELS[phase]}`}
          >
            Start
          </button>
        )}
        {canApprove && status === 'completed' && (
          <button
            className={styles.approveButton}
            onClick={handleApprove}
            aria-label={`Approve ${PHASE_LABELS[phase]}`}
          >
            Approve
          </button>
        )}
      </div>
    </div>
  );
};

export default PhaseItem;
