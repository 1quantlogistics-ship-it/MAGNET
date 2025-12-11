/**
 * MAGNET UI Module 03: ChatMinimized
 *
 * Floating hologram pill for minimized chat state.
 * Multi-layer orb with edge glint.
 */

import React from 'react';
import { motion } from 'framer-motion';
import type { ChatMinimizedProps } from '../../types/chat';
import { VISIONOS_MOTION } from '../../types/chat';
import styles from './ChatMinimized.module.css';

/**
 * ChatMinimized component
 *
 * Floating pill that expands to full chat window.
 * Shows AI activity through orb animation intensity.
 */
export const ChatMinimized: React.FC<ChatMinimizedProps> = ({
  onExpand,
  isStreaming = false,
}) => {
  return (
    <motion.button
      className={styles.pill}
      onClick={onExpand}
      initial={{ opacity: 0, scale: 0.8, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.8, y: 20 }}
      whileHover={{
        scale: 1.06,
        y: -3,
        boxShadow:
          '0 20px 50px rgba(0, 0, 0, 0.3), 0 0 60px rgba(126, 184, 231, 0.12)',
      }}
      whileTap={{ scale: 0.98 }}
      transition={{
        type: 'spring',
        ...VISIONOS_MOTION.spring.default,
      }}
      type="button"
      aria-label="Expand chat window"
    >
      {/* Multi-layer orb glow */}
      <div className={styles.orbContainer}>
        <motion.div
          className={styles.orbOuter}
          animate={{
            scale: isStreaming ? [1, 1.3, 1] : [1, 1.1, 1],
            opacity: isStreaming ? [0.1, 0.25, 0.1] : [0.05, 0.12, 0.05],
          }}
          transition={{
            duration: isStreaming ? 1.5 : 4,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className={styles.orbInner}
          animate={{
            scale: isStreaming ? [1, 1.2, 1] : [1, 1.05, 1],
            opacity: isStreaming ? [0.6, 1, 0.6] : [0.4, 0.7, 0.4],
          }}
          transition={{
            duration: isStreaming ? 1 : 3,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </div>

      {/* Minimal text */}
      <span className={styles.label}>AI</span>

      {/* Edge glint */}
      <div className={styles.edgeGlint} />
    </motion.button>
  );
};

export default ChatMinimized;
