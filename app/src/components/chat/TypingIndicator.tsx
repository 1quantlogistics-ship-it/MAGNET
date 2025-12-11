/**
 * MAGNET UI Module 03: TypingIndicator
 *
 * Animated typing indicator with 3 bouncing dots.
 * VisionOS glass bubble style.
 */

import React from 'react';
import { motion } from 'framer-motion';
import type { TypingIndicatorProps } from '../../types/chat';
import styles from './TypingIndicator.module.css';

/**
 * TypingIndicator component
 *
 * Shows animated dots to indicate AI is thinking/typing.
 */
export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  speed = 1,
}) => {
  const duration = 1 / speed;

  return (
    <div className={styles.wrapper}>
      <div className={styles.bubble}>
        <div className={styles.dots}>
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className={styles.dot}
              animate={{
                y: [0, -5, 0],
                opacity: [0.3, 0.8, 0.3],
              }}
              transition={{
                duration,
                repeat: Infinity,
                delay: i * 0.15 * (1 / speed),
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
