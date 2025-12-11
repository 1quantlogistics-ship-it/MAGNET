/**
 * MAGNET UI MilestoneToast Component
 * BRAVO OWNS THIS FILE.
 *
 * Toast notification for design milestones.
 * Displays phase completion and approval events.
 */

import React, { useCallback, useEffect, useState } from 'react';
import type { PhaseName } from '../../api/phase';
import type { Milestone } from '../../stores/domain/prsStore';
import styles from './MilestoneToast.module.css';

// ============================================================================
// Types
// ============================================================================

export type MilestoneType = 'phase_started' | 'phase_completed' | 'phase_approved' | 'design_complete';

export interface MilestoneToastProps {
  /** Milestone data */
  milestone: Milestone;
  /** Auto-dismiss duration in ms (0 = no auto-dismiss) */
  autoDismissMs?: number;
  /** Callback when toast is dismissed */
  onDismiss: (id: string) => void;
  /** Callback when toast is clicked */
  onClick?: (milestone: Milestone) => void;
}

// ============================================================================
// Constants
// ============================================================================

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

const MILESTONE_MESSAGES: Record<MilestoneType, (phase?: PhaseName) => string> = {
  phase_started: (phase) => `${phase ? PHASE_LABELS[phase] : 'Phase'} started`,
  phase_completed: (phase) => `${phase ? PHASE_LABELS[phase] : 'Phase'} completed`,
  phase_approved: (phase) => `${phase ? PHASE_LABELS[phase] : 'Phase'} approved`,
  design_complete: () => 'Design review complete!',
};

const MILESTONE_ICONS: Record<MilestoneType, string> = {
  phase_started: '\u25B6',     // Play
  phase_completed: '\u2713',   // Checkmark
  phase_approved: '\u2605',    // Star
  design_complete: '\u2728',   // Sparkles (using stars)
};

// ============================================================================
// Component
// ============================================================================

export const MilestoneToast: React.FC<MilestoneToastProps> = ({
  milestone,
  autoDismissMs = 5000,
  onDismiss,
  onClick,
}) => {
  const [isExiting, setIsExiting] = useState(false);

  // Auto-dismiss timer
  useEffect(() => {
    if (autoDismissMs <= 0) return;

    const timer = setTimeout(() => {
      handleDismiss();
    }, autoDismissMs);

    return () => clearTimeout(timer);
  }, [autoDismissMs, milestone.id]);

  // Handlers
  const handleDismiss = useCallback(() => {
    setIsExiting(true);
    // Wait for exit animation
    setTimeout(() => {
      onDismiss(milestone.id);
    }, 200);
  }, [milestone.id, onDismiss]);

  const handleClick = useCallback(() => {
    onClick?.(milestone);
  }, [milestone, onClick]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    } else if (e.key === 'Escape') {
      handleDismiss();
    }
  }, [handleClick, handleDismiss]);

  // Get milestone display info
  const icon = MILESTONE_ICONS[milestone.type as MilestoneType] || '\u2139';
  const message = MILESTONE_MESSAGES[milestone.type as MilestoneType]?.(milestone.phase) ||
    milestone.message ||
    'Milestone reached';

  const containerClass = [
    styles.container,
    styles[`type-${milestone.type}`],
    isExiting ? styles.exiting : styles.entering,
  ].join(' ');

  return (
    <div
      className={containerClass}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="alert"
      tabIndex={0}
      aria-live="polite"
    >
      <span className={styles.icon} aria-hidden="true">
        {icon}
      </span>

      <div className={styles.content}>
        <span className={styles.message}>{message}</span>
        {milestone.timestamp && (
          <span className={styles.timestamp}>
            {new Date(milestone.timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>

      <button
        className={styles.dismissButton}
        onClick={(e) => {
          e.stopPropagation();
          handleDismiss();
        }}
        aria-label="Dismiss notification"
      >
        &times;
      </button>

      {/* Progress bar for auto-dismiss */}
      {autoDismissMs > 0 && (
        <div
          className={styles.progressBar}
          style={{ animationDuration: `${autoDismissMs}ms` }}
        />
      )}
    </div>
  );
};

// ============================================================================
// Toast Container
// ============================================================================

export interface MilestoneToastContainerProps {
  /** Active milestones to display */
  milestones: Milestone[];
  /** Callback when a milestone is dismissed */
  onDismiss: (id: string) => void;
  /** Callback when a milestone is clicked */
  onMilestoneClick?: (milestone: Milestone) => void;
  /** Position on screen */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  /** Maximum toasts to show */
  maxToasts?: number;
}

export const MilestoneToastContainer: React.FC<MilestoneToastContainerProps> = ({
  milestones,
  onDismiss,
  onMilestoneClick,
  position = 'top-right',
  maxToasts = 3,
}) => {
  // Limit displayed toasts
  const visibleMilestones = milestones.slice(0, maxToasts);

  return (
    <div className={`${styles.toastContainer} ${styles[position]}`}>
      {visibleMilestones.map((milestone) => (
        <MilestoneToast
          key={milestone.id}
          milestone={milestone}
          onDismiss={onDismiss}
          onClick={onMilestoneClick}
        />
      ))}
    </div>
  );
};

export default MilestoneToast;
