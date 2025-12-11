/**
 * MAGNET UI Standard Clarification
 *
 * Floating spatial card for multiple option selection.
 * VisionOS-style with perspective tilt, volumetric shadows, and spatial occlusion.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { StandardClarificationProps, ClarificationOption } from '../../types/clarification';
import { CLARIFICATION_MOTION } from '../../types/clarification';
import { CountdownRing } from './CountdownRing';
import {
  respondToClarification,
  skipClarification,
  expireClarification,
} from '../../stores/domain/clarificationStore';
import styles from './StandardClarification.module.css';

/**
 * StandardClarification component
 *
 * @example
 * ```tsx
 * <StandardClarification
 *   request={{
 *     id: 'clar-1',
 *     type: 'standard',
 *     question: 'Which tank type should I configure?',
 *     context: 'Selecting the appropriate tank type affects capacity calculations.',
 *     options: [
 *       { id: '1', label: 'Ballast Tank', description: 'For stability control', value: 'ballast' },
 *       { id: '2', label: 'Fuel Tank', description: 'For propulsion', value: 'fuel', isDefault: true }
 *     ],
 *     // ...
 *   }}
 * />
 * ```
 */
export const StandardClarification: React.FC<StandardClarificationProps> = ({ request }) => {
  const [isPaused, setIsPaused] = useState(false);
  const [remaining, setRemaining] = useState(request.autoDismissMs ?? 30000);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => {
    // Pre-select default option(s)
    const defaults = request.options?.filter((o) => o.isDefault).map((o) => o.id) ?? [];
    return new Set(defaults);
  });

  // Countdown timer
  useEffect(() => {
    if (!request.autoDismissMs || isPaused) return;

    const interval = setInterval(() => {
      setRemaining((prev) => {
        const next = prev - 100;
        if (next <= 0) {
          expireClarification(request.id);
          return 0;
        }
        return next;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [request.id, request.autoDismissMs, isPaused]);

  // Handle option toggle
  const handleToggle = useCallback(
    (option: ClarificationOption) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (request.allowMultiple) {
          if (next.has(option.id)) {
            next.delete(option.id);
          } else {
            next.add(option.id);
          }
        } else {
          // Single select - replace
          next.clear();
          next.add(option.id);
        }
        return next;
      });
    },
    [request.allowMultiple]
  );

  // Handle confirm
  const handleConfirm = useCallback(() => {
    const selected = request.options?.filter((o) => selectedIds.has(o.id)) ?? [];
    const value = request.allowMultiple
      ? selected.map((o) => o.value)
      : selected[0]?.value;
    respondToClarification(request.id, value);
  }, [request.id, request.options, request.allowMultiple, selectedIds]);

  // Handle skip
  const handleSkip = useCallback(() => {
    skipClarification(request.id);
  }, [request.id]);

  // Check if confirm is enabled
  const canConfirm = selectedIds.size > 0;

  // Wrapper variants
  const wrapperVariants = {
    hidden: { opacity: 0, scale: 0.92, y: 30, rotateX: 3 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      rotateX: 1,
      transition: {
        type: 'spring',
        ...CLARIFICATION_MOTION.spring,
        staggerChildren: CLARIFICATION_MOTION.staggerDelay,
        delayChildren: 0.15,
      },
    },
    exit: {
      opacity: 0,
      scale: 0.96,
      y: 15,
      transition: { duration: 0.2 },
    },
  };

  // Option variants
  const optionVariants = {
    hidden: { opacity: 0, x: -16 },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        type: 'spring',
        ...CLARIFICATION_MOTION.spring,
      },
    },
  };

  return (
    <div className={styles.overlay}>
      {/* Non-linear blur background */}
      <div className={styles.blurMask} />

      <AnimatePresence mode="wait">
        <motion.div
          className={styles.card}
          variants={wrapperVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
        >
          {/* Scene lighting */}
          <div className={styles.sceneLighting} />

          {/* Edge highlight */}
          <div className={styles.edgeHighlight} />

          {/* Header */}
          <div className={styles.header}>
            <div className={styles.titleGroup}>
              <h3 className={styles.title}>{request.question}</h3>
              {request.context && <p className={styles.context}>{request.context}</p>}
            </div>

            {/* Countdown */}
            {request.autoDismissMs && (
              <div className={styles.countdown}>
                <CountdownRing
                  duration={request.autoDismissMs}
                  remaining={remaining}
                  isPaused={isPaused}
                  size="md"
                />
              </div>
            )}
          </div>

          {/* Options list */}
          <div className={styles.options}>
            {request.options?.map((option) => {
              const isSelected = selectedIds.has(option.id);
              return (
                <motion.button
                  key={option.id}
                  className={`${styles.option} ${isSelected ? styles.selected : ''}`}
                  variants={optionVariants}
                  onClick={() => handleToggle(option)}
                  whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.06)' }}
                  whileTap={{ scale: 0.98 }}
                >
                  {/* Spherical indicator */}
                  <span className={styles.indicator}>
                    {isSelected && (
                      <motion.span
                        className={styles.indicatorDot}
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                      />
                    )}
                  </span>

                  {/* Label and description */}
                  <span className={styles.optionContent}>
                    <span className={styles.optionLabel}>{option.label}</span>
                    {option.description && (
                      <span className={styles.optionDesc}>{option.description}</span>
                    )}
                  </span>

                  {/* Default badge */}
                  {option.isDefault && (
                    <span className={styles.defaultBadge}>Default</span>
                  )}
                </motion.button>
              );
            })}
          </div>

          {/* Actions */}
          <div className={styles.actions}>
            <motion.button
              className={styles.skipButton}
              onClick={handleSkip}
              whileHover={{ opacity: 0.8 }}
              whileTap={{ scale: 0.98 }}
            >
              Skip
            </motion.button>

            <motion.button
              className={`${styles.confirmButton} ${!canConfirm ? styles.disabled : ''}`}
              onClick={handleConfirm}
              disabled={!canConfirm}
              whileHover={canConfirm ? { scale: 1.02 } : {}}
              whileTap={canConfirm ? { scale: 0.98 } : {}}
            >
              Confirm
            </motion.button>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default StandardClarification;
