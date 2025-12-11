/**
 * MAGNET UI Module 04: SpatialSlider
 *
 * Custom spatial slider replacing native <input type="range">.
 * Glass track with gradient fill and 3D thumb.
 */

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import type { SpatialSliderProps } from '../../types/clarification';
import { CLARIFICATION_MOTION } from '../../types/clarification';
import styles from './SpatialSlider.module.css';

/**
 * SpatialSlider component
 *
 * Custom range slider with glass track and draggable 3D thumb.
 */
export const SpatialSlider: React.FC<SpatialSliderProps> = ({
  value,
  min,
  max,
  step = 1,
  unit,
  onChange,
  className,
}) => {
  const trackRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Calculate percentage
  const range = max - min;
  const percentage = range > 0 ? ((value - min) / range) * 100 : 0;

  // Calculate value from position
  const calculateValue = useCallback(
    (clientX: number): number => {
      if (!trackRef.current) return value;

      const rect = trackRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
      const ratio = x / rect.width;
      const rawValue = min + ratio * range;

      // Snap to step
      const steppedValue = Math.round(rawValue / step) * step;
      return Math.max(min, Math.min(max, steppedValue));
    },
    [min, max, step, range, value]
  );

  // Handle track click
  const handleTrackClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const newValue = calculateValue(e.clientX);
      onChange(newValue);
    },
    [calculateValue, onChange]
  );

  // Handle drag start
  const handleDragStart = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    setIsDragging(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, []);

  // Handle drag move
  const handleDragMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isDragging) return;
      const newValue = calculateValue(e.clientX);
      onChange(newValue);
    },
    [isDragging, calculateValue, onChange]
  );

  // Handle drag end
  const handleDragEnd = useCallback((e: React.PointerEvent) => {
    setIsDragging(false);
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
  }, []);

  // Format display value
  const displayValue = unit ? `${value}${unit}` : String(value);

  return (
    <div className={`${styles.container} ${className || ''}`}>
      {/* Track */}
      <div
        ref={trackRef}
        className={styles.track}
        onClick={handleTrackClick}
        role="slider"
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
      >
        {/* Fill */}
        <motion.div
          className={styles.fill}
          style={{ width: `${percentage}%` }}
          initial={false}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.1 }}
        />

        {/* Thumb */}
        <motion.div
          className={`${styles.thumb} ${isDragging ? styles.dragging : ''}`}
          style={{ left: `${percentage}%` }}
          onPointerDown={handleDragStart}
          onPointerMove={handleDragMove}
          onPointerUp={handleDragEnd}
          onPointerCancel={handleDragEnd}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          transition={{
            type: 'spring',
            ...CLARIFICATION_MOTION.spring,
          }}
        >
          {/* Inner lighting */}
          <div className={styles.thumbInner} />
        </motion.div>
      </div>

      {/* Value display */}
      <div className={styles.valueDisplay}>{displayValue}</div>
    </div>
  );
};

export default SpatialSlider;
