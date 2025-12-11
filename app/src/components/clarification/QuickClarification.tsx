/**
 * MAGNET UI Quick Clarification
 *
 * Inline spatial chips for simple either/or questions.
 * VisionOS-style with Z-offset, tilt, and micro-bounce animations.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { QuickClarificationProps, ClarificationOption } from '../../types/clarification';
import { CLARIFICATION_MOTION } from '../../types/clarification';
import { CountdownRing } from './CountdownRing';
import {
  respondToClarification,
  skipClarification,
  expireClarification,
} from '../../stores/domain/clarificationStore';
import styles from './QuickClarification.module.css';

/**
 * QuickClarification component
 *
 * @example
 * ```tsx
 * <QuickClarification
 *   request={{
 *     id: 'clar-1',
 *     type: 'quick',
 *     question: 'Which units should I use?',
 *     options: [
 *       { id: '1', label: 'Metric', value: 'metric', isDefault: true },
 *       { id: '2', label: 'Imperial', value: 'imperial' }
 *     ],
 *     // ...
 *   }}
 * />
 * ```
 */
export const QuickClarification: React.FC<QuickClarificationProps> = ({ request }) => {
  const [isPaused, setIsPaused] = useState(false);
  const [remaining, setRemaining] = useState(request.autoDismissMs ?? 30000);

  // Countdown timer
  useEffect(() => {
    if (!request.autoDismissMs || isPaused) return;

    const interval = setInterval(() => {
      setRemaining((prev) => {
        const next = prev - 100;
        if (next <= 0) {
          // Auto-dismiss - use default value
          expireClarification(request.id);
          return 0;
        }
        return next;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [request.id, request.autoDismissMs, isPaused]);

  // Handle chip selection
  const handleSelect = useCallback(
    (option: ClarificationOption) => {
      respondToClarification(request.id, option.value);
    },
    [request.id]
  );

  // Handle skip
  const handleSkip = useCallback(() => {
    skipClarification(request.id);
  }, [request.id]);

  // Find default option
  const defaultOption = useMemo(
    () => request.options?.find((o) => o.isDefault),
    [request.options]
  );

  // Container variants
  const containerVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring',
        ...CLARIFICATION_MOTION.spring,
        staggerChildren: CLARIFICATION_MOTION.staggerDelay,
        delayChildren: 0.1,
      },
    },
    exit: {
      opacity: 0,
      y: -12,
      transition: { duration: 0.2 },
    },
  };

  // Chip variants with micro-bounce
  const chipVariants = {
    hidden: { opacity: 0, scale: 0.85, y: 12 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: {
        type: 'spring',
        ...CLARIFICATION_MOTION.spring,
      },
    },
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        className={styles.container}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {/* Question */}
        <div className={styles.header}>
          <p className={styles.question}>{request.question}</p>

          {/* Countdown ring */}
          {request.autoDismissMs && (
            <div className={styles.countdown}>
              <CountdownRing
                duration={request.autoDismissMs}
                remaining={remaining}
                isPaused={isPaused}
                size="sm"
              />
            </div>
          )}
        </div>

        {/* Spatial chips */}
        <div className={styles.chips}>
          {request.options?.map((option, index) => (
            <motion.button
              key={option.id}
              className={`${styles.chip} ${option.isDefault ? styles.default : ''}`}
              variants={chipVariants}
              onClick={() => handleSelect(option)}
              whileHover={{
                scale: 1.06,
                y: -4,
                transition: { type: 'spring', stiffness: 400, damping: 20 },
              }}
              whileTap={{ scale: 0.95 }}
              style={{
                // Slight stagger in Z for depth
                transform: `translateZ(${16 + index * 2}px)`,
              }}
            >
              {/* Edge highlight */}
              <span className={styles.edgeHighlight} />

              {/* Label */}
              <span className={styles.label}>{option.label}</span>

              {/* Default indicator */}
              {option.isDefault && <span className={styles.defaultBadge}>Default</span>}
            </motion.button>
          ))}
        </div>

        {/* Assumption phrase */}
        {request.assumptionPhrase && defaultOption && (
          <motion.p
            className={styles.assumption}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            {request.assumptionPhrase}
          </motion.p>
        )}

        {/* Skip action */}
        <motion.button
          className={styles.skipButton}
          onClick={handleSkip}
          whileHover={{ opacity: 0.8 }}
          whileTap={{ scale: 0.98 }}
        >
          Skip
        </motion.button>
      </motion.div>
    </AnimatePresence>
  );
};

export default QuickClarification;
