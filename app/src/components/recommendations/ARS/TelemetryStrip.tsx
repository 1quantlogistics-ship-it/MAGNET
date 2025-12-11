/**
 * MAGNET UI Telemetry Strip
 *
 * VisionOS-style urgent notification bar for high-priority recommendations.
 * Appears at the top of the viewport with glass morphism and auto-dismiss.
 */

import React, { memo, useCallback, useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ARSRecommendation } from '../../../types/ars';
import { VISIONOS_TIMING } from '../../../types/common';
import { PriorityIndicator, getPriorityName } from './icons/PriorityIndicator';
import { ImpactChip } from './ImpactChip';
import styles from './TelemetryStrip.module.css';

/**
 * Telemetry strip props
 */
export interface TelemetryStripProps {
  /** Current recommendation to display */
  recommendation: ARSRecommendation | null;
  /** Queue length indicator */
  queueLength?: number;
  /** Auto-dismiss timeout in ms (0 to disable) */
  autoDismissMs?: number;
  /** Dismiss handler */
  onDismiss?: () => void;
  /** View handler */
  onView?: () => void;
  /** Apply handler */
  onApply?: () => void;
  /** Optional className */
  className?: string;
}

/**
 * Telemetry strip component
 *
 * @example
 * ```tsx
 * <TelemetryStrip
 *   recommendation={currentTelemetryItem}
 *   queueLength={telemetryQueue.length}
 *   autoDismissMs={10000}
 *   onDismiss={dismissTelemetry}
 *   onView={viewRecommendation}
 *   onApply={applyRecommendation}
 * />
 * ```
 */
export const TelemetryStrip = memo<TelemetryStripProps>(
  ({
    recommendation,
    queueLength = 0,
    autoDismissMs = 0,
    onDismiss,
    onView,
    onApply,
    className,
  }) => {
    const [isPaused, setIsPaused] = useState(false);
    const [progress, setProgress] = useState(1);
    const startTimeRef = useRef<number>(0);
    const remainingTimeRef = useRef<number>(autoDismissMs);

    // Auto-dismiss countdown
    useEffect(() => {
      if (!recommendation || autoDismissMs === 0 || isPaused) {
        return;
      }

      startTimeRef.current = Date.now();
      const intervalId = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current;
        const remaining = remainingTimeRef.current - elapsed;
        const newProgress = Math.max(0, remaining / autoDismissMs);

        setProgress(newProgress);

        if (newProgress <= 0) {
          onDismiss?.();
        }
      }, 50);

      return () => {
        clearInterval(intervalId);
        remainingTimeRef.current = Math.max(
          0,
          remainingTimeRef.current - (Date.now() - startTimeRef.current)
        );
      };
    }, [recommendation, autoDismissMs, isPaused, onDismiss]);

    // Reset on new recommendation
    useEffect(() => {
      if (recommendation) {
        remainingTimeRef.current = autoDismissMs;
        setProgress(1);
      }
    }, [recommendation?.id, autoDismissMs]);

    // Pause on hover
    const handleMouseEnter = useCallback(() => {
      setIsPaused(true);
    }, []);

    const handleMouseLeave = useCallback(() => {
      setIsPaused(false);
    }, []);

    // Action handlers
    const handleDismiss = useCallback(() => {
      onDismiss?.();
    }, [onDismiss]);

    const handleView = useCallback(() => {
      onView?.();
    }, [onView]);

    const handleApply = useCallback(() => {
      onApply?.();
    }, [onApply]);

    // Animation variants
    const stripVariants = {
      initial: {
        y: -80,
        opacity: 0,
        scale: 0.95,
      },
      animate: {
        y: 0,
        opacity: 1,
        scale: 1,
        transition: {
          type: 'spring',
          stiffness: VISIONOS_TIMING.stiffness * 0.8,
          damping: VISIONOS_TIMING.damping,
        },
      },
      exit: {
        y: -60,
        opacity: 0,
        scale: 0.98,
        transition: {
          duration: 0.3,
          ease: [0.4, 0, 0.2, 1],
        },
      },
    };

    // Get primary action from recommendation
    const primaryAction = recommendation?.actions?.find((a) => a.isPrimary);

    return (
      <AnimatePresence>
        {recommendation && (
          <motion.div
            className={`${styles.strip} ${className ?? ''}`}
            variants={stripVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            role="alert"
            aria-live="assertive"
          >
            {/* Glass background */}
            <div className={styles.glass} />

            {/* Progress bar */}
            {autoDismissMs > 0 && (
              <div className={styles.progressTrack}>
                <motion.div
                  className={styles.progressBar}
                  style={{ scaleX: progress }}
                  initial={{ scaleX: 1 }}
                  animate={{ scaleX: progress }}
                  transition={{ duration: 0.05 }}
                />
              </div>
            )}

            {/* Content */}
            <div className={styles.content}>
              {/* Priority indicator */}
              <div className={styles.priority}>
                <PriorityIndicator
                  priority={recommendation.priority}
                  size={20}
                  animated={recommendation.priority === 1}
                />
              </div>

              {/* Message */}
              <div className={styles.message}>
                <span className={styles.priorityLabel}>
                  {getPriorityName(recommendation.priority)}
                </span>
                <span className={styles.title}>{recommendation.title}</span>
              </div>

              {/* Impact */}
              <div className={styles.impact}>
                <ImpactChip impact={recommendation.impact} size="sm" />
              </div>

              {/* Queue indicator */}
              {queueLength > 0 && (
                <div className={styles.queue}>
                  <span>+{queueLength}</span>
                </div>
              )}

              {/* Actions */}
              <div className={styles.actions}>
                <button
                  className={styles.viewButton}
                  onClick={handleView}
                  type="button"
                >
                  View
                </button>
                {primaryAction && primaryAction.type === 'apply' && (
                  <button
                    className={styles.applyButton}
                    onClick={handleApply}
                    type="button"
                  >
                    {primaryAction.label}
                  </button>
                )}
                <button
                  className={styles.dismissButton}
                  onClick={handleDismiss}
                  aria-label="Dismiss"
                  type="button"
                >
                  <DismissIcon />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }
);

TelemetryStrip.displayName = 'TelemetryStrip';

/**
 * Dismiss icon component
 */
const DismissIcon: React.FC = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M4 4L12 12M12 4L4 12"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
);

export default TelemetryStrip;
