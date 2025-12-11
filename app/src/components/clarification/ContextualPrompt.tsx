/**
 * MAGNET UI Contextual Prompt
 *
 * Dynamic positioned prompt for contextual 3D selection requests.
 * Anchors near target position with pointer arrow.
 */

import React, { useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ContextualPromptProps } from '../../types/clarification';
import { CLARIFICATION_MOTION } from '../../types/clarification';
import { skipClarification } from '../../stores/domain/clarificationStore';
import { getViewportDimensions } from '../../types/common';
import styles from './ContextualPrompt.module.css';

/**
 * Card dimensions
 */
const CARD_WIDTH = 320;
const CARD_HEIGHT = 160;
const CARD_PADDING = 24;
const POINTER_SIZE = 12;

/**
 * ContextualPrompt component
 *
 * @example
 * ```tsx
 * <ContextualPrompt
 *   request={{
 *     id: 'clar-1',
 *     type: 'contextual',
 *     question: 'Select the component to adjust',
 *     context: 'Click on a component in the workspace.',
 *     targetPosition: { x: 400, y: 300 },
 *     // ...
 *   }}
 * />
 * ```
 */
export const ContextualPrompt: React.FC<ContextualPromptProps> = ({ request }) => {
  // Calculate position
  const position = useMemo(() => {
    const viewport = getViewportDimensions();
    const target = request.targetPosition ?? {
      x: viewport.width / 2,
      y: viewport.height / 2,
    };

    // Responsive offset (not fixed 80px)
    const offset = Math.min(80, viewport.height * 0.08);

    // Calculate Y position (below target, clamped to viewport)
    let y = target.y + offset;
    const maxY = viewport.height - CARD_HEIGHT - CARD_PADDING;
    const minY = CARD_PADDING;
    y = Math.max(minY, Math.min(maxY, y));

    // Calculate X position (centered on target, clamped to viewport)
    let x = target.x - CARD_WIDTH / 2;
    const maxX = viewport.width - CARD_WIDTH - CARD_PADDING;
    const minX = CARD_PADDING;
    x = Math.max(minX, Math.min(maxX, x));

    // Determine pointer position
    let pointerSide: 'top' | 'bottom' = 'top';
    let pointerX = target.x - x - POINTER_SIZE / 2;

    // If card had to move above target (clamped), flip pointer
    if (target.y + offset > maxY) {
      pointerSide = 'bottom';
      y = target.y - offset - CARD_HEIGHT;
      y = Math.max(minY, y);
    }

    // Clamp pointer X within card bounds
    pointerX = Math.max(20, Math.min(CARD_WIDTH - 20 - POINTER_SIZE, pointerX));

    return { x, y, pointerSide, pointerX };
  }, [request.targetPosition]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    skipClarification(request.id);
  }, [request.id]);

  // Card variants
  const cardVariants = {
    hidden: {
      opacity: 0,
      y: position.pointerSide === 'top' ? -20 : 20,
      scale: 0.95,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: 'spring',
        ...CLARIFICATION_MOTION.spring,
      },
    },
    exit: {
      opacity: 0,
      y: position.pointerSide === 'top' ? -12 : 12,
      scale: 0.98,
      transition: { duration: 0.15 },
    },
  };

  return (
    <div className={styles.overlay}>
      {/* Dim background */}
      <motion.div
        className={styles.dimmer}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
      />

      <AnimatePresence mode="wait">
        <motion.div
          className={styles.card}
          style={{
            left: position.x,
            top: position.y,
            width: CARD_WIDTH,
          }}
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          {/* Pointer arrow */}
          <div
            className={`${styles.pointer} ${styles[`pointer-${position.pointerSide}`]}`}
            style={{ left: position.pointerX }}
          />

          {/* Scene lighting */}
          <div className={styles.sceneLighting} />

          {/* Edge highlight */}
          <div className={styles.edgeHighlight} />

          {/* Content */}
          <div className={styles.content}>
            <p className={styles.question}>{request.question}</p>
            {request.context && <p className={styles.context}>{request.context}</p>}
          </div>

          {/* Instructions */}
          <div className={styles.instructions}>
            <span className={styles.icon}>
              <ClickIcon />
            </span>
            <span className={styles.instructionText}>
              Click on a component in the workspace
            </span>
          </div>

          {/* Cancel action */}
          <div className={styles.actions}>
            <motion.button
              className={styles.cancelButton}
              onClick={handleCancel}
              whileHover={{ opacity: 0.8 }}
              whileTap={{ scale: 0.98 }}
            >
              Cancel
            </motion.button>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

/**
 * Click icon
 */
const ClickIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path
      d="M6 2V10L8 8L10 12L12 11L10 7L13 6L6 2Z"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export default ContextualPrompt;
