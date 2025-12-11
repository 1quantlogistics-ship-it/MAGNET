/**
 * MAGNET UI Impact Chip
 *
 * VisionOS-style chip displaying a metric impact.
 * Shows metric name, change percentage, and directional indicator.
 */

import React, { memo, useMemo } from 'react';
import { motion } from 'framer-motion';
import type { ARSImpact } from '../../../types/ars';
import { VISIONOS_TIMING } from '../../../types/common';
import styles from './ImpactChip.module.css';

/**
 * Impact chip props
 */
export interface ImpactChipProps {
  /** Impact data */
  impact: ARSImpact;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show detailed view */
  detailed?: boolean;
  /** Click handler */
  onClick?: () => void;
  /** Optional className */
  className?: string;
}

/**
 * Format change value for display
 */
function formatChange(change: number, unit?: string): string {
  const sign = change >= 0 ? '+' : '';
  const formatted = Math.abs(change) < 1
    ? change.toFixed(2)
    : change.toFixed(1);
  const unitSuffix = unit ? ` ${unit}` : '%';
  return `${sign}${formatted}${unitSuffix}`;
}

/**
 * Impact chip component
 *
 * @example
 * ```tsx
 * <ImpactChip
 *   impact={{ metric: 'GM', change: 2.3, isPositive: true }}
 *   size="md"
 * />
 * ```
 */
export const ImpactChip = memo<ImpactChipProps>(
  ({
    impact,
    size = 'md',
    detailed = false,
    onClick,
    className,
  }) => {
    // Determine variant based on impact
    const variant = useMemo(() => {
      if (impact.isPositive) return 'positive';
      if (!impact.isPositive && Math.abs(impact.change) > 5) return 'negative';
      return 'neutral';
    }, [impact.isPositive, impact.change]);

    // Animation variants
    const chipVariants = {
      initial: { opacity: 0, scale: 0.9 },
      animate: {
        opacity: 1,
        scale: 1,
        transition: {
          type: 'spring',
          stiffness: VISIONOS_TIMING.stiffness,
          damping: VISIONOS_TIMING.damping,
        },
      },
      hover: {
        scale: 1.05,
        transition: {
          type: 'spring',
          stiffness: 400,
          damping: 25,
        },
      },
      tap: { scale: 0.98 },
    };

    const chipClasses = [
      styles.chip,
      styles[size],
      styles[variant],
      onClick ? styles.clickable : '',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    const ChipContent = (
      <>
        {/* Metric name */}
        <span className={styles.metric}>{impact.metric}</span>

        {/* Divider */}
        <span className={styles.divider} />

        {/* Change value with direction */}
        <span className={styles.change}>
          <DirectionArrow isPositive={impact.isPositive} />
          <span>{formatChange(impact.change, impact.unit)}</span>
        </span>

        {/* Detailed view shows full metric description */}
        {detailed && (
          <span className={styles.detail}>
            {impact.isPositive ? 'improvement' : 'impact'}
          </span>
        )}
      </>
    );

    if (onClick) {
      return (
        <motion.button
          className={chipClasses}
          onClick={onClick}
          variants={chipVariants}
          initial="initial"
          animate="animate"
          whileHover="hover"
          whileTap="tap"
          type="button"
        >
          {ChipContent}
        </motion.button>
      );
    }

    return (
      <motion.span
        className={chipClasses}
        variants={chipVariants}
        initial="initial"
        animate="animate"
      >
        {ChipContent}
      </motion.span>
    );
  }
);

ImpactChip.displayName = 'ImpactChip';

/**
 * Direction arrow component
 */
const DirectionArrow: React.FC<{ isPositive: boolean }> = memo(({ isPositive }) => (
  <svg
    className={styles.arrow}
    width="10"
    height="10"
    viewBox="0 0 10 10"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{
      transform: isPositive ? 'rotate(0deg)' : 'rotate(180deg)',
    }}
  >
    <path
      d="M5 2L2 6H8L5 2Z"
      fill="currentColor"
    />
  </svg>
));

DirectionArrow.displayName = 'DirectionArrow';

/**
 * Multiple impact chips container
 */
export interface ImpactChipsProps {
  /** Primary impact */
  impact: ARSImpact;
  /** Secondary impacts */
  secondaryImpacts?: ARSImpact[];
  /** Maximum secondary to show */
  maxSecondary?: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

export const ImpactChips = memo<ImpactChipsProps>(
  ({ impact, secondaryImpacts, maxSecondary = 2, size = 'md' }) => {
    const secondaryToShow = secondaryImpacts?.slice(0, maxSecondary) ?? [];

    return (
      <div className={styles.chipsContainer}>
        <ImpactChip impact={impact} size={size} />
        {secondaryToShow.map((secondary, index) => (
          <ImpactChip
            key={`${secondary.metric}-${index}`}
            impact={secondary}
            size="sm"
          />
        ))}
      </div>
    );
  }
);

ImpactChips.displayName = 'ImpactChips';

export default ImpactChip;
