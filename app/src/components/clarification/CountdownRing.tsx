/**
 * MAGNET UI Module 04: CountdownRing
 *
 * Animated SVG ring for countdown visualization.
 * Replaces HTML progress bars with VisionOS-style spatial element.
 */

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import type { CountdownRingProps } from '../../types/clarification';
import { COUNTDOWN_RING_SIZES } from '../../types/clarification';
import styles from './CountdownRing.module.css';

/**
 * CountdownRing component
 *
 * Animated SVG ring showing countdown progress with radial pulse glow.
 */
export const CountdownRing: React.FC<CountdownRingProps> = ({
  duration,
  remaining,
  isPaused = false,
  size = 'md',
  className,
}) => {
  const diameter = COUNTDOWN_RING_SIZES[size];
  const strokeWidth = size === 'sm' ? 2 : size === 'md' ? 2.5 : 3;
  const radius = (diameter - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Calculate progress (0-1)
  const progress = useMemo(() => {
    if (duration <= 0) return 0;
    return Math.max(0, Math.min(1, remaining / duration));
  }, [duration, remaining]);

  // Stroke dash offset for progress
  const strokeDashoffset = circumference * (1 - progress);

  return (
    <div
      className={`${styles.container} ${className || ''}`}
      style={{ width: diameter, height: diameter }}
      data-paused={isPaused}
    >
      {/* Radial pulse glow */}
      {!isPaused && (
        <motion.div
          className={styles.pulse}
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.3, 0.1, 0.3],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}

      {/* SVG Ring */}
      <svg
        className={styles.ring}
        width={diameter}
        height={diameter}
        viewBox={`0 0 ${diameter} ${diameter}`}
      >
        {/* Track (background) */}
        <circle
          className={styles.track}
          cx={diameter / 2}
          cy={diameter / 2}
          r={radius}
          strokeWidth={strokeWidth}
          fill="none"
        />

        {/* Progress (foreground) */}
        <motion.circle
          className={styles.progress}
          cx={diameter / 2}
          cy={diameter / 2}
          r={radius}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          initial={false}
          animate={{ strokeDashoffset }}
          transition={{
            duration: 0.3,
            ease: 'easeOut',
          }}
          style={{
            transformOrigin: 'center',
            transform: 'rotate(-90deg)',
          }}
        />
      </svg>
    </div>
  );
};

export default CountdownRing;
