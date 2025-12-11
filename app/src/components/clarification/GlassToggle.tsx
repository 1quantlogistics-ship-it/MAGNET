/**
 * MAGNET UI Module 04: GlassToggle
 *
 * VisionOS-style glass toggle switch.
 * Glass track with animated fill and 3D thumb.
 */

import React, { useCallback } from 'react';
import { motion } from 'framer-motion';
import type { GlassToggleProps } from '../../types/clarification';
import { CLARIFICATION_MOTION } from '../../types/clarification';
import styles from './GlassToggle.module.css';

/**
 * GlassToggle component
 *
 * Custom toggle switch with glass material and spring animation.
 */
export const GlassToggle: React.FC<GlassToggleProps> = ({
  value,
  onChange,
  label,
  className,
}) => {
  const handleClick = useCallback(() => {
    onChange(!value);
  }, [value, onChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onChange(!value);
      }
    },
    [value, onChange]
  );

  return (
    <div className={`${styles.container} ${className || ''}`}>
      {label && <span className={styles.label}>{label}</span>}

      <button
        type="button"
        className={`${styles.toggle} ${value ? styles.on : styles.off}`}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role="switch"
        aria-checked={value}
        aria-label={label}
      >
        {/* Track fill */}
        <motion.div
          className={styles.trackFill}
          initial={false}
          animate={{
            opacity: value ? 1 : 0,
          }}
          transition={{ duration: 0.2 }}
        />

        {/* Thumb */}
        <motion.div
          className={styles.thumb}
          initial={false}
          animate={{
            x: value ? 20 : 0,
          }}
          transition={{
            type: 'spring',
            ...CLARIFICATION_MOTION.spring,
          }}
        >
          {/* Inner lighting */}
          <div className={styles.thumbInner} />
        </motion.div>
      </button>
    </div>
  );
};

export default GlassToggle;
