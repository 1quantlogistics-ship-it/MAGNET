/**
 * MAGNET UI Module 04: OccludableWindow
 *
 * Wrapper component that applies occlusion effects when clarifications are active.
 * Windows dim, blur, and shift back to create spatial depth hierarchy.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { useSpatialOcclusion } from '../../contexts/SpatialOcclusionContext';
import type { OccludableWindowProps } from '../../types/clarification';
import styles from './OccludableWindow.module.css';

/**
 * Occlusion animation variants
 */
const occlusionVariants = {
  normal: {
    opacity: 1,
    filter: 'blur(0px)',
    z: 0,
    scale: 1,
    transition: {
      duration: 0.4,
      ease: [0.4, 0, 0.2, 1],
    },
  },
  occluded: {
    opacity: 0.6,
    filter: 'blur(4px)',
    z: -40,
    scale: 0.98,
    transition: {
      duration: 0.4,
      ease: [0.4, 0, 0.2, 1],
    },
  },
};

/**
 * OccludableWindow component
 *
 * Wraps content that should be occluded when clarifications are shown.
 * Excluded windows (by ID) remain at full visibility.
 */
export const OccludableWindow: React.FC<OccludableWindowProps> = ({
  id,
  children,
  className,
}) => {
  const { occlusion } = useSpatialOcclusion();

  // Check if this window should be occluded
  const isOccluded = occlusion.isActive && !occlusion.excludeIds.includes(id);

  return (
    <motion.div
      className={`${styles.window} ${className || ''}`}
      variants={occlusionVariants}
      initial="normal"
      animate={isOccluded ? 'occluded' : 'normal'}
      data-window-id={id}
      data-occluded={isOccluded}
    >
      {children}
    </motion.div>
  );
};

export default OccludableWindow;
