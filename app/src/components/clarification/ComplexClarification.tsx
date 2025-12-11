/**
 * MAGNET UI Complex Clarification
 *
 * Spatial modal form for complex multi-parameter input.
 * VisionOS-style with bright fog overlay and dynamic field rendering.
 */

import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ComplexClarificationProps, ClarificationField } from '../../types/clarification';
import { CLARIFICATION_MOTION } from '../../types/clarification';
import { GlassPicker } from './GlassPicker';
import {
  respondToClarification,
  skipClarification,
} from '../../stores/domain/clarificationStore';
import styles from './ComplexClarification.module.css';

/**
 * ComplexClarification component
 *
 * @example
 * ```tsx
 * <ComplexClarification
 *   request={{
 *     id: 'clar-1',
 *     type: 'complex',
 *     question: 'Configure load conditions',
 *     context: 'These parameters affect stability calculations.',
 *     fields: [
 *       { id: 'draft', type: 'number', label: 'Draft', unit: 'm', min: 0, max: 20 },
 *       { id: 'cargo', type: 'slider', label: 'Cargo Load', min: 0, max: 100, unit: '%' },
 *       { id: 'type', type: 'picker', label: 'Condition', options: [...] }
 *     ],
 *     // ...
 *   }}
 * />
 * ```
 */
export const ComplexClarification: React.FC<ComplexClarificationProps> = ({ request }) => {
  // Initialize form values from defaults
  const [values, setValues] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    request.fields?.forEach((field) => {
      initial[field.id] = field.defaultValue ?? getFieldDefault(field);
    });
    return initial;
  });

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Update a single field value
  const updateField = useCallback((fieldId: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [fieldId]: value }));
    // Clear error on change
    setErrors((prev) => {
      const next = { ...prev };
      delete next[fieldId];
      return next;
    });
  }, []);

  // Validate form
  const validate = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    request.fields?.forEach((field) => {
      const value = values[field.id];

      // Required check
      if (field.required && (value === undefined || value === null || value === '')) {
        newErrors[field.id] = 'This field is required';
        return;
      }

      // Number range check
      if (field.type === 'number' || field.type === 'slider') {
        const num = Number(value);
        if (field.min !== undefined && num < field.min) {
          newErrors[field.id] = `Minimum value is ${field.min}`;
        }
        if (field.max !== undefined && num > field.max) {
          newErrors[field.id] = `Maximum value is ${field.max}`;
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [request.fields, values]);

  // Handle submit
  const handleSubmit = useCallback(() => {
    if (!validate()) return;
    respondToClarification(request.id, values);
  }, [request.id, values, validate]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    skipClarification(request.id);
  }, [request.id]);

  // Modal variants
  const overlayVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
    exit: { opacity: 0 },
  };

  const modalVariants = {
    hidden: { opacity: 0, scale: 0.92, y: 40, rotateX: 4 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      rotateX: 1,
      transition: {
        type: 'spring',
        ...CLARIFICATION_MOTION.spring,
        staggerChildren: CLARIFICATION_MOTION.staggerDelay,
        delayChildren: 0.1,
      },
    },
    exit: {
      opacity: 0,
      scale: 0.96,
      y: 20,
      transition: { duration: 0.2 },
    },
  };

  const fieldVariants = {
    hidden: { opacity: 0, y: 12 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring',
        ...CLARIFICATION_MOTION.spring,
      },
    },
  };

  return (
    <AnimatePresence>
      <motion.div
        className={styles.overlay}
        variants={overlayVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
      >
        {/* Bright fog overlay (NOT black) */}
        <div className={styles.brightFog} />

        <motion.div
          className={styles.modal}
          variants={modalVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          {/* Scene lighting */}
          <div className={styles.sceneLighting} />

          {/* Edge highlight */}
          <div className={styles.edgeHighlight} />

          {/* Header */}
          <div className={styles.header}>
            <h2 className={styles.title}>{request.question}</h2>
            {request.context && <p className={styles.context}>{request.context}</p>}
          </div>

          {/* Form fields */}
          <div className={styles.form}>
            {request.fields?.map((field) => (
              <motion.div
                key={field.id}
                className={styles.fieldGroup}
                variants={fieldVariants}
              >
                <label className={styles.label}>
                  {field.label}
                  {field.required && <span className={styles.required}>*</span>}
                </label>

                {renderField(field, values[field.id], (v) => updateField(field.id, v))}

                {errors[field.id] && (
                  <span className={styles.error}>{errors[field.id]}</span>
                )}
              </motion.div>
            ))}
          </div>

          {/* Actions */}
          <div className={styles.actions}>
            <motion.button
              className={styles.cancelButton}
              onClick={handleCancel}
              whileHover={{ opacity: 0.8 }}
              whileTap={{ scale: 0.98 }}
            >
              Cancel
            </motion.button>

            <motion.button
              className={styles.applyButton}
              onClick={handleSubmit}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Apply
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

/**
 * Get default value for field type
 */
function getFieldDefault(field: ClarificationField): unknown {
  switch (field.type) {
    case 'text':
      return '';
    case 'number':
      return field.min ?? 0;
    case 'slider':
      return field.min ?? 0;
    case 'toggle':
      return false;
    case 'picker':
      return field.options?.[0]?.value ?? '';
    default:
      return '';
  }
}

/**
 * Render field based on type
 */
function renderField(
  field: ClarificationField,
  value: unknown,
  onChange: (value: unknown) => void
): React.ReactNode {
  switch (field.type) {
    case 'text':
      return (
        <input
          type="text"
          className={styles.textInput}
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
        />
      );

    case 'number':
      return (
        <div className={styles.numberWrapper}>
          <input
            type="number"
            className={styles.numberInput}
            value={Number(value ?? 0)}
            onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
            min={field.min}
            max={field.max}
            step={field.step ?? 1}
            placeholder={field.placeholder}
          />
          {field.unit && <span className={styles.unit}>{field.unit}</span>}
        </div>
      );

    case 'slider':
      const sliderValue = Number(value ?? field.min ?? 0);
      const min = field.min ?? 0;
      const max = field.max ?? 100;
      const percentage = ((sliderValue - min) / (max - min)) * 100;
      return (
        <div className={styles.sliderWrapper}>
          <div className={styles.sliderTrack}>
            <div
              className={styles.sliderFill}
              style={{ width: `${percentage}%` }}
            />
            <input
              type="range"
              className={styles.sliderInput}
              value={sliderValue}
              onChange={(e) => onChange(parseFloat(e.target.value))}
              min={min}
              max={max}
              step={field.step ?? 1}
            />
          </div>
          <span className={styles.sliderValue}>
            {sliderValue}
            {field.unit && ` ${field.unit}`}
          </span>
        </div>
      );

    case 'toggle':
      return (
        <button
          type="button"
          className={`${styles.toggle} ${value ? styles.toggleOn : ''}`}
          onClick={() => onChange(!value)}
        >
          <span className={styles.toggleThumb} />
        </button>
      );

    case 'picker':
      return (
        <GlassPicker
          value={String(value ?? '')}
          options={field.options ?? []}
          onChange={(v) => onChange(v)}
          placeholder={field.placeholder}
        />
      );

    default:
      return null;
  }
}

export default ComplexClarification;
