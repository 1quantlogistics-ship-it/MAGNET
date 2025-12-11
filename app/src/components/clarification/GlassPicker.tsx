/**
 * MAGNET UI Module 04: GlassPicker
 *
 * Custom glass dropdown replacing native <select> elements.
 * VisionOS-style spatial dropdown with staggered animations.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GlassPickerProps, ClarificationOption } from '../../types/clarification';
import { CLARIFICATION_MOTION } from '../../types/clarification';
import styles from './GlassPicker.module.css';

/**
 * Chevron icon
 */
const ChevronIcon: React.FC<{ isOpen: boolean }> = ({ isOpen }) => (
  <motion.svg
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    animate={{ rotate: isOpen ? 180 : 0 }}
    transition={{ duration: 0.2 }}
  >
    <path
      d="M3 4.5L6 7.5L9 4.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </motion.svg>
);

/**
 * GlassPicker component
 *
 * Custom dropdown with glass material and spatial depth.
 */
export const GlassPicker: React.FC<GlassPickerProps> = ({
  value,
  options,
  onChange,
  placeholder = 'Select option',
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Find selected option
  const selectedOption = options.find((opt) => String(opt.value) === value);

  // Handle click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Handle option select
  const handleSelect = useCallback(
    (option: ClarificationOption) => {
      onChange(String(option.value));
      setIsOpen(false);
    },
    [onChange]
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    },
    []
  );

  return (
    <div
      ref={containerRef}
      className={`${styles.container} ${className || ''}`}
    >
      {/* Trigger button */}
      <button
        type="button"
        className={`${styles.trigger} ${isOpen ? styles.open : ''}`}
        onClick={() => setIsOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className={styles.value}>
          {selectedOption?.label || placeholder}
        </span>
        <ChevronIcon isOpen={isOpen} />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className={styles.dropdown}
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{
              type: 'spring',
              ...CLARIFICATION_MOTION.spring,
            }}
            role="listbox"
          >
            {/* Scene lighting */}
            <div className={styles.sceneLighting} />

            {/* Options */}
            {options.map((option, index) => (
              <motion.button
                key={option.id}
                type="button"
                className={`${styles.option} ${
                  String(option.value) === value ? styles.selected : ''
                }`}
                onClick={() => handleSelect(option)}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  delay: index * CLARIFICATION_MOTION.staggerDelay,
                }}
                role="option"
                aria-selected={String(option.value) === value}
              >
                {/* Spherical indicator */}
                <span className={styles.indicator}>
                  {String(option.value) === value && (
                    <motion.span
                      className={styles.indicatorDot}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
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
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default GlassPicker;
