/**
 * MAGNET UI PhasePanel Component
 * BRAVO OWNS THIS FILE.
 *
 * Main PRS panel displaying design phase workflow.
 * Shows all phases with status indicators and progress.
 */

import React, { useCallback, useEffect, useMemo } from 'react';
import { PhaseItem } from './PhaseItem';
import { PhaseProgress } from './PhaseProgress';
import type { PhaseName, PhaseStatus } from '../../api/phase';
import { PHASE_ORDER } from '../../api/phase';
import {
  getPRSState,
  getPhaseStatus,
  getActivePhase,
  getProgress,
  canStartPhase,
  canApprovePhase,
  subscribeToPRS,
} from '../../stores/domain/prsStore';
import { prsOrchestrator } from '../../systems/PRSOrchestrator';
import styles from './PhasePanel.module.css';

// ============================================================================
// Types
// ============================================================================

export interface PhasePanelProps {
  /** Design ID to track */
  designId: string;
  /** Whether the panel is collapsed */
  collapsed?: boolean;
  /** Callback when a phase is selected */
  onPhaseSelect?: (phase: PhaseName) => void;
  /** Callback when panel collapse state changes */
  onCollapseChange?: (collapsed: boolean) => void;
}

// ============================================================================
// Component
// ============================================================================

export const PhasePanel: React.FC<PhasePanelProps> = ({
  designId,
  collapsed = false,
  onPhaseSelect,
  onCollapseChange,
}) => {
  // Subscribe to PRS state changes
  const [prsState, setPRSState] = React.useState(getPRSState);

  useEffect(() => {
    // Initialize orchestrator with design
    prsOrchestrator.initialize(designId);

    // Subscribe to state changes
    const unsubscribe = subscribeToPRS((state) => {
      setPRSState(state);
    });

    return () => {
      unsubscribe();
    };
  }, [designId]);

  // Compute progress
  const progress = useMemo(() => getProgress(), [prsState]);
  const activePhase = useMemo(() => getActivePhase(), [prsState]);

  // Handlers
  const handlePhaseSelect = useCallback((phase: PhaseName) => {
    onPhaseSelect?.(phase);
  }, [onPhaseSelect]);

  const handlePhaseStart = useCallback(async (phase: PhaseName) => {
    try {
      await prsOrchestrator.startPhase(phase);
    } catch (error) {
      console.error(`Failed to start phase ${phase}:`, error);
    }
  }, []);

  const handlePhaseApprove = useCallback(async (phase: PhaseName) => {
    try {
      await prsOrchestrator.approvePhase(phase);
    } catch (error) {
      console.error(`Failed to approve phase ${phase}:`, error);
    }
  }, []);

  const handleToggleCollapse = useCallback(() => {
    onCollapseChange?.(!collapsed);
  }, [collapsed, onCollapseChange]);

  // Render collapsed state
  if (collapsed) {
    return (
      <div className={styles.containerCollapsed}>
        <button
          className={styles.expandButton}
          onClick={handleToggleCollapse}
          aria-label="Expand phase panel"
        >
          <span className={styles.expandIcon}>&#x25B6;</span>
          <span className={styles.collapsedLabel}>PRS</span>
          <span className={styles.collapsedProgress}>
            {Math.round(progress * 100)}%
          </span>
        </button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <button
          className={styles.collapseButton}
          onClick={handleToggleCollapse}
          aria-label="Collapse phase panel"
        >
          <span className={styles.collapseIcon}>&#x25BC;</span>
        </button>
        <h3 className={styles.title}>Phase Review System</h3>
        <span className={styles.designId}>{designId}</span>
      </div>

      {/* Progress indicator */}
      <PhaseProgress
        progress={progress}
        completedCount={prsState.phases ?
          Object.values(prsState.phases).filter(p =>
            p.status === 'completed' || p.status === 'approved'
          ).length : 0
        }
        totalCount={PHASE_ORDER.length}
        activePhase={activePhase}
      />

      {/* Phase list */}
      <div className={styles.phaseList}>
        {PHASE_ORDER.map((phase) => {
          const phaseInfo = prsState.phases?.[phase];
          const status: PhaseStatus = phaseInfo?.status ?? 'pending';
          const isActive = phase === activePhase;

          return (
            <PhaseItem
              key={phase}
              phase={phase}
              status={status}
              isActive={isActive}
              canStart={canStartPhase(phase)}
              canApprove={canApprovePhase(phase)}
              onSelect={handlePhaseSelect}
              onStart={handlePhaseStart}
              onApprove={handlePhaseApprove}
            />
          );
        })}
      </div>

      {/* Loading overlay */}
      {prsState.isLoading && (
        <div className={styles.loadingOverlay}>
          <span className={styles.spinner} />
        </div>
      )}

      {/* Error message */}
      {prsState.error && (
        <div className={styles.error}>
          <span className={styles.errorIcon}>&#x26A0;</span>
          <span className={styles.errorText}>{prsState.error}</span>
        </div>
      )}
    </div>
  );
};

export default PhasePanel;
