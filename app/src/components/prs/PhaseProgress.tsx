/**
 * MAGNET UI PhaseProgress Component
 * BRAVO OWNS THIS FILE.
 *
 * Progress indicator for design phase workflow.
 * Shows overall completion and active phase status.
 */

import React, { useMemo } from 'react';
import type { PhaseName } from '../../api/phase';
import styles from './PhaseProgress.module.css';

// ============================================================================
// Types
// ============================================================================

export interface PhaseProgressProps {
  /** Progress value (0-1) */
  progress: number;
  /** Number of completed phases */
  completedCount: number;
  /** Total number of phases */
  totalCount: number;
  /** Currently active phase */
  activePhase: PhaseName | null;
  /** Size variant */
  size?: 'small' | 'medium' | 'large';
  /** Show percentage label */
  showPercentage?: boolean;
  /** Show phase count */
  showCount?: boolean;
}

// ============================================================================
// Constants
// ============================================================================

const PHASE_LABELS: Record<PhaseName, string> = {
  mission: 'Mission',
  hull_form: 'Hull',
  structure: 'Structure',
  propulsion: 'Propulsion',
  systems: 'Systems',
  weight_stability: 'Stability',
  compliance: 'Compliance',
  production: 'Production',
};

// ============================================================================
// Component
// ============================================================================

export const PhaseProgress: React.FC<PhaseProgressProps> = ({
  progress,
  completedCount,
  totalCount,
  activePhase,
  size = 'medium',
  showPercentage = true,
  showCount = true,
}) => {
  // Clamp progress to 0-1
  const clampedProgress = useMemo(() => {
    return Math.max(0, Math.min(1, progress));
  }, [progress]);

  const percentage = Math.round(clampedProgress * 100);

  // Determine color based on progress
  const progressColor = useMemo(() => {
    if (clampedProgress === 1) return 'var(--color-success, #4aff7a)';
    if (clampedProgress >= 0.75) return 'var(--color-primary, #4a9eff)';
    if (clampedProgress >= 0.5) return 'var(--color-info, #4ae0ff)';
    return 'var(--color-text-muted, #888)';
  }, [clampedProgress]);

  return (
    <div className={`${styles.container} ${styles[size]}`}>
      {/* Progress bar */}
      <div className={styles.progressBar}>
        <div
          className={styles.progressFill}
          style={{
            width: `${percentage}%`,
            backgroundColor: progressColor,
          }}
        />
      </div>

      {/* Stats row */}
      <div className={styles.stats}>
        {showCount && (
          <span className={styles.count}>
            {completedCount} / {totalCount} phases
          </span>
        )}

        {activePhase && (
          <span className={styles.activePhase}>
            <span className={styles.activeIndicator} />
            {PHASE_LABELS[activePhase]}
          </span>
        )}

        {showPercentage && (
          <span className={styles.percentage} style={{ color: progressColor }}>
            {percentage}%
          </span>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Circular Progress Variant
// ============================================================================

export interface CircularPhaseProgressProps {
  /** Progress value (0-1) */
  progress: number;
  /** Size in pixels */
  size?: number;
  /** Stroke width */
  strokeWidth?: number;
  /** Show percentage in center */
  showPercentage?: boolean;
  /** Currently active phase */
  activePhase?: PhaseName | null;
}

export const CircularPhaseProgress: React.FC<CircularPhaseProgressProps> = ({
  progress,
  size = 64,
  strokeWidth = 4,
  showPercentage = true,
  activePhase,
}) => {
  const clampedProgress = Math.max(0, Math.min(1, progress));
  const percentage = Math.round(clampedProgress * 100);

  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (clampedProgress * circumference);

  // Determine color based on progress
  const progressColor = useMemo(() => {
    if (clampedProgress === 1) return 'var(--color-success, #4aff7a)';
    if (clampedProgress >= 0.75) return 'var(--color-primary, #4a9eff)';
    if (clampedProgress >= 0.5) return 'var(--color-info, #4ae0ff)';
    return 'var(--color-text-muted, #888)';
  }, [clampedProgress]);

  return (
    <div className={styles.circularContainer} style={{ width: size, height: size }}>
      <svg
        className={styles.circularSvg}
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
      >
        {/* Background circle */}
        <circle
          className={styles.circularBg}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          className={styles.circularProgress}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          style={{
            stroke: progressColor,
            strokeDasharray: circumference,
            strokeDashoffset,
          }}
        />
      </svg>

      {showPercentage && (
        <div className={styles.circularLabel}>
          <span className={styles.circularPercentage} style={{ color: progressColor }}>
            {percentage}%
          </span>
          {activePhase && (
            <span className={styles.circularPhase}>
              {PHASE_LABELS[activePhase]}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default PhaseProgress;
