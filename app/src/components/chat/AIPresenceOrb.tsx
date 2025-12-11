/**
 * MAGNET UI Module 03: AIPresenceOrb
 *
 * 3-layer AI presence orb with phase-shifted breathing animation.
 * VisionOS-style concentric field system.
 */

import React from 'react';
import { motion } from 'framer-motion';
import type { AIPresenceOrbProps } from '../../types/chat';
import styles from './AIPresenceOrb.module.css';

/**
 * Size configurations for the orb
 */
const SIZE_CONFIGS = {
  sm: {
    core: 6,
    field1: 16,
    field2: 28,
    diffusion: 10,
  },
  md: {
    core: 8,
    field1: 20,
    field2: 36,
    diffusion: 14,
  },
  lg: {
    core: 10,
    field1: 24,
    field2: 44,
    diffusion: 18,
  },
};

/**
 * AIPresenceOrb component
 *
 * 3-layer concentric orb indicating AI presence/activity.
 * Outer layers animate slower with phase shifts for organic feel.
 */
export const AIPresenceOrb: React.FC<AIPresenceOrbProps> = ({
  isStreaming = false,
  size = 'md',
}) => {
  const config = SIZE_CONFIGS[size];

  // Animation configurations for each layer
  // Core: fastest response, outermost: slowest
  const coreAnimation = {
    scale: isStreaming ? [1, 1.15, 1] : [1, 1.018, 1],
    opacity: isStreaming ? [0.8, 1, 0.8] : [0.7, 0.9, 0.7],
  };

  const field1Animation = {
    scale: isStreaming ? [1, 1.12, 1] : [1, 1.04, 1],
    opacity: isStreaming ? [0.2, 0.35, 0.2] : [0.08, 0.16, 0.08],
  };

  const field2Animation = {
    scale: isStreaming ? [1, 1.08, 1] : [1, 1.025, 1],
    opacity: isStreaming ? [0.1, 0.2, 0.1] : [0.03, 0.08, 0.03],
  };

  return (
    <div
      className={styles.orbContainer}
      style={{
        width: config.field2,
        height: config.field2,
      }}
    >
      {/* Field 2 — outermost, slowest */}
      <motion.div
        className={styles.field2}
        style={{
          width: config.field2,
          height: config.field2,
        }}
        animate={field2Animation}
        transition={{
          duration: isStreaming ? 2 : 8,
          repeat: Infinity,
          ease: 'easeInOut',
          delay: 0.4, // Phase shift
        }}
      />

      {/* Field 1 — middle layer */}
      <motion.div
        className={styles.field1}
        style={{
          width: config.field1,
          height: config.field1,
        }}
        animate={field1Animation}
        transition={{
          duration: isStreaming ? 1.5 : 6,
          repeat: Infinity,
          ease: 'easeInOut',
          delay: 0.2, // Phase shift
        }}
      />

      {/* Core — innermost, fastest response */}
      <motion.div
        className={styles.core}
        style={{
          width: config.core,
          height: config.core,
        }}
        animate={coreAnimation}
        transition={{
          duration: isStreaming ? 1 : 4.8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Inner blur diffusion */}
      <div
        className={styles.diffusion}
        style={{
          width: config.diffusion,
          height: config.diffusion,
        }}
      />
    </div>
  );
};

export default AIPresenceOrb;
